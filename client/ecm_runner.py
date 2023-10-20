"""Takes a Work Unit and runs some quantum of with ecm. """

import multiprocessing as mp
import re
import subprocess
import time

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
    status: str
    runtime: float


RE_FACTORS_FMT1 = re.compile(r"factor found.*: ([0-9]*)$", re.I | re.MULTILINE)
RE_FACTORS_FMT2 = re.compile(r"^([0-9]*) [0-9()+*/#!-]", re.I | re.MULTILINE)


def get_command(wu: WorkUnit, env: Env) -> List[str]:
    cmd = []
    cmd.append(f"{env.ecm_path}")
    cmd.extend(wu.params)
    cmd.extend(env.extra_params)
    if env.input_path:
        # TODO probably needs more thought than this
        cmd.append("-resume")
        cmd.append(f"{env.input_path}")

    if wu.B1:
        cmd.append(wu.B1)
    if wu.B2:
        cmd.append(wu.B2)

    return cmd


def parse_returncode(code: int):
    """
    Parse return code according to ecm man page.

    Bit 0: 0 if normal program termination, 1 if error occurred
    Bit 1: 0 if no proper factor was found, 1 otherwise
    Bit 2: 0 if factor is composite, 1 if factor is a probable prime
    Bit 3: 0 if cofactor is composite, 1 if cofactor is a probable prime
    """
    return code & 1, (code >> 1) & 1, (code >> 2) & 1, (code >> 3) & 1


def get_fake_work_units(count: int) -> List[WorkUnit]:
    import random
    units = []
    for _ in range(count):
        uid = random.randint(0, 10**9)
        N = "2 ^ 137 - 1"
        wu = WorkUnit(uid, N, ("-v", "-timestamp"), B1="1e6", B2="1e8")
        units.append(wu)
    return units


def get_env():
    # TODO use params and stuff
    # return Env("../../gmp-ecm/ecm", ("-q",), "", "test.output")
    return Env("../../gmp-ecm/ecm", tuple(), "", "test.output")


def process_output(output: subprocess.CompletedProcess):
    is_error, found_factor, prime_factor, prime_coprime = (
            parse_returncode(output.returncode))
    assert not is_error

    factors = tuple()
    if found_factor:
        print("-" * 80)
        print(output.stdout)
        print(f"Return: {output.returncode} {is_error = }, {found_factor = }, {prime_factor = }")
        factors1 = RE_FACTORS_FMT1.findall(output.stdout)
        factors2 = RE_FACTORS_FMT2.findall(output.stdout)
        factors = tuple(sorted(set(map(int, factors1 + factors2))))
        print(factors)
        print("-" * 80)
        assert factors

    result = EcmOutput(
        factors,
        output.returncode,
        resume_line="",
        status=output.stdout,
        runtime=0)

    return result


def run_resume(wu: WorkUnit, env: Env) -> EcmOutput:
    """Run each line in a resume file seperately"""
    # TODO implement this
    raise NotImplementedError


def run(wu: WorkUnit, env: Env) -> subprocess.CompletedProcess:
    """Run a WorkUnit in Env"""
    command = get_command(wu, env)
    output = subprocess.run(
        command, input=str(wu.n), capture_output=True, text=True)
    return output


def ecm_worker(name, work, results):
    env = get_env()
    print("Started worker", name)
    while True:
        wu = work.get()
        out = run(wu, env)
        result = process_output(out)
        results.put((wu, result))


def start_workers(work: mp.Queue, results: mp.Queue, num_workers: int):
    workers = []
    for i in range(num_workers):
        worker = mp.Process(target=ecm_worker, name=i, args=(i, work, results))
        worker.start()
        workers.append(worker)
    return workers


def main_loop():
    work = mp.Queue()
    results = mp.Queue()

    workers = start_workers(work, results, num_workers=4)

    try:
        while True:
            while not results.empty():
                wu, result = results.get_nowait()
                print("Completed:", datetime.now().isoformat(), wu)
                if result.factors:
                    print("Result:", result, "from", wu)
                    print("FACTOR:", result.factors)
                    for worker in workers:
                        worker.terminate()
                    return

            for worker in workers:
                assert worker.is_alive()

            if work.empty():
                # TODO get real WorkUnits from server
                # print("Adding work units")
                for wu in get_fake_work_units(10):
                    work.put(wu)
                print("work queued:", work.qsize())

            time.sleep(0.02)

    except KeyboardInterrupt:
        print("TODO graceful shutdown in the future")


main_loop()
