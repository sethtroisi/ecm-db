"""Takes a Work Unit and runs some quantum of with ecm. """

import argparse
import multiprocessing as mp
import os
import re
import subprocess
import time

from collections import defaultdict
from datetime import datetime
from dataclasses import dataclass
from typing import List, Tuple


@dataclass(frozen=True)
class WorkUnit:
    uid: int
    n: str
    params: Tuple[str]
    B1: str
    B2: str
    resume_line: str = ""


@dataclass(frozen=True)
class Env:
    ecm_path: str
    extra_params: Tuple[str]
    input_path: str
    output_path: str


@dataclass()
class EcmOutput:
    factors: Tuple[str]
    exit_status: int
    resume_line: str
    using: str
    version: str
    status: str
    runtime: float


RE_FACTORS_FMT1 = re.compile(r"factor found.*: ([0-9]+)$", re.I | re.MULTILINE)
RE_FACTORS_FMT2 = re.compile(r"^([0-9]+) [0-9()+*/#!-]", re.I | re.MULTILINE)
RE_USING = re.compile(r"Using", re.I | re.MULTILINE)
RE_VERSION = re.compile(r"^GMP-ECM ", re.I | re.MULTILINE)
RE_RESUME_N = re.compile(r"\bN=([0-9]+)\b")
RE_B1_B2 = re.compile(r"\bB1=([0-9]+)\b(.*B2=([0-9]+))?")


def get_argparser():
    parser = argparse.ArgumentParser(description='ecm runner.')
    parser.add_argument('-N', '-n', help='Number to run')
    parser.add_argument('-t', '--threads',
            type=int, default=1,
            help='Number of threads to run')
    parser.add_argument('--B1', '--b1', help='B1 param')
    parser.add_argument('--B2', '--b2', help='B2 param')
    parser.add_argument('-r', '--resume', help='Resume residues from file')
    #parser.add_argument('--stop_early', action="store_true", help='Stop after finding first factor')
    parser.add_argument('ecm_path', help='ecm binary')
    return parser


def validate_args(args):
    path = args.ecm_path
    assert os.path.exists(path), f"ecm_path({path}) doesn't exist"
    assert os.path.isfile(path), f"ecm_path({path}) isn't a file"

    if not args.resume:
        assert args.B1, "B1 must be specified (unless resuming)"
        assert args.N, "N must be specified (unless resuming)"



def get_env(args):
    # TODO use params and stuff
    # return Env(args.ecm_path, ("-q",), "", "test.output")
    return Env(args.ecm_path, tuple(), "", "test.output")


def get_command(wu: WorkUnit, env: Env) -> List[str]:
    stdin = wu.n

    cmd = []
    cmd.append(f"{env.ecm_path}")
    cmd.extend(wu.params)
    cmd.extend(env.extra_params)

    if wu.resume_line:
        stdin = wu.resume_line
        # Reads the resume line from stdin
        cmd.extend(["-resume", "-"])

    if wu.B1:
        cmd.append(wu.B1)
    if wu.B2:
        cmd.append(wu.B2)

    return (stdin, cmd)


def get_work_units(args, count: int) -> List[WorkUnit]:
    import random

    if args.resume:
        units = resume_to_work_units(args, count)
        args.resume = None
        return units

    if args.N:
        units = []
        for _ in range(count):
            uid = random.randint(0, 10**9)
            assert args.N
            assert args.B1
            wu = WorkUnit(uid, args.N, ("-v", "-timestamp"), B1=args.B1, B2=args.B2)
            units.append(wu)
        return units

    return []


def resume_to_work_units(args, count) -> List[WorkUnit]:
    with open(args.resume) as f:
        units = []
        for i, line in enumerate(f):
            if not line:
                continue

            match = RE_RESUME_N.search(line)
            assert match, "N not found in resume line: " + repr(line)
            N = match.group()

            match = RE_B1_B2.search(line)
            assert match, "B1, B2 not found in resume line"
            B1, _, B2 = match.groups()
            unit = WorkUnit(i, N, ("-v",), B1=B1, B2=B2, resume_line=line)
            units.append(unit)

    return units


def parse_returncode(code: int):
    """
    Parse return code according to ecm man page.

    Bit 0: 0 if normal program termination, 1 if error occurred
    Bit 1: 0 if no proper factor was found, 1 otherwise
    Bit 2: 0 if factor is composite, 1 if factor is a probable prime
    Bit 3: 0 if cofactor is composite, 1 if cofactor is a probable prime
    """
    return code & 1, (code >> 1) & 1, (code >> 2) & 1, (code >> 3) & 1


def get_from_stdout(regexp, stdout):
    match = regexp.search(stdout)
    assert match, (regexp, stdout)
    return match.group()


def process_output(output: subprocess.CompletedProcess):
    is_error, found_factor, prime_factor, prime_coprime = (
            parse_returncode(output.returncode))
    assert not is_error

    factors = tuple()
    if found_factor:
        print("-" * 80)
        print(output.stdout)
        print(f"Return: {output.returncode} | {is_error = }, {found_factor = }, {prime_factor = }")
        factors1 = RE_FACTORS_FMT1.findall(output.stdout)
        factors2 = RE_FACTORS_FMT2.findall(output.stdout)
        factors = tuple(sorted(set(map(int, factors1 + factors2))))
        print("Factor(s):", " ".join(map(str, factors)))
        print("-" * 80)
        assert factors

    version = get_from_stdout(RE_VERSION, output.stdout)
    #using = get_from_stdout(RE_USING, output.stdout)

    result = EcmOutput(
        factors,
        output.returncode,
        resume_line="",
        #using=using,
        using="",
        version=version,
        status=output.stdout,
        runtime=0)

    return result


def run(wu: WorkUnit, env: Env) -> subprocess.CompletedProcess:
    """Run a WorkUnit in Env"""
    stdin, command = get_command(wu, env)
    # print("stdin:", stdin)
    # print("cmd:  ", command)
    output = subprocess.run(
        command, input=stdin, capture_output=True, text=True)
    return output


def ecm_worker(name, env, work, results):
    while True:
        wu = work.get()
        out = run(wu, env)
        result = process_output(out)
        results.put((wu, result))


def start_workers(env: Env, work: mp.Queue, results: mp.Queue, num_workers: int):
    print(f"Starting {num_workers}")
    workers = []
    for i in range(num_workers):
        worker = mp.Process(target=ecm_worker, name=i, args=(i, env, work, results))
        worker.start()
        workers.append(worker)
    return workers


def main_loop(args):
    env = get_env(args)

    work = mp.Queue()
    results = mp.Queue()
    finished = defaultdict(list)
    total_work = 0
    total_finished = 0

    workers = start_workers(env, work, results, num_workers=args.threads)
    time.sleep(0.02)

    try:
        while True:
            while not results.empty():
                wu, result = results.get_nowait()
                # print("Completed:", datetime.now().isoformat(), wu)
                total_finished += 1
                finished[wu.n].append(result)
                count_n = len(finished[wu.n])
                if count_n % 100 == 0:
                    print("Curves:", count_n, "N:", wu.n)

                if result.factors:
                    print("Result:", result, "from", wu)
                    print("Curve count:", count_n)
                    print("FACTOR:", result.factors)
                    for worker in workers:
                        worker.terminate()
                    return

            for worker in workers:
                assert worker.is_alive()

            if work.empty():
                # TODO get real WorkUnits from server
                # print("Adding work units")
                added = 0
                for wu in get_work_units(args, 10):
                    added += 1
                    work.put(wu)
                    if wu.n not in finished:
                        # Add to finished
                        finished[wu.n]
                        assert wu.n in finished
                        print("New N:", wu.n)

                if added == 0 and total_work == total_finished:
                    # No new work, all work finished
                    assert work.empty()
                    assert results.empty()
                    for worker in workers:
                        if worker:
                            worker.terminate()
                    exit(0)

            time.sleep(0.02)

    except KeyboardInterrupt:
        print("TODO graceful shutdown in the future")

    except:
        print("Main thread had exception!")
        for worker in workers:
            if worker:
                worker.terminate()
        raise


if __name__ == "__main__":
    parser = get_argparser()
    args = parser.parse_args()
    print(args)
    validate_args(args)

    main_loop(args)
