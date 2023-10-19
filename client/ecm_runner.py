"""Takes a Work Unit and runs some quantum of with ecm. """

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


RE_FACTORS_FMT1 = re.compile(r"\bfactor.*: ([0-9]*)$", re.I | re.MULTILINE)
RE_FACTORS_FMT2 = re.compile(r"^([0-9]*) [0-9()+*/#!-]", re.I | re.MULTILINE)


def get_command(wu: WorkUnit, env: Env) -> List[str]:
    cmd = []
    cmd.append(f"{env.ecm_path}")
    cmd.extend(wu.params)
    cmd.extend(env.extra_params)
    if env.input_path:
        cmd.append("-resume")
        cmd.append(f"{env.input_path}")

    if wu.B1:
        cmd.append(wu.B1)
    if wu.B2:
        cmd.append(wu.B2)

    return cmd


def run(wu: WorkUnit, env: Env) -> subprocess.CompletedProcess:
    """Run a WorkUnit in Env"""
    command = get_command(wu, env)
    output = subprocess.run(command, input=str(wu.n), capture_output=True, text=True)
    return output


def parse_returncode(code: int):
    """
    Parse return code according to ecm man page.

    Bit 0: 0 if normal program termination, 1 if error occurred
    Bit 1: 0 if no proper factor was found, 1 otherwise
    Bit 2: 0 if factor is composite, 1 if factor is a probable prime
    Bit 3: 0 if cofactor is composite, 1 if cofactor is a probable prime
    """
    return code & 1, (code >> 1) & 1, (code >> 2) & 1, (code >> 3) & 1

def run_resume(wu: WorkUnit, env: Env) -> EcmOutput:
    """Run each line in a resume file seperately"""
    pass


def get_fake_work_units(count: int) -> List[WorkUnit]:
    import random
    units = []
    for _ in range(count):
        uid = random.randint(0, 10**9)
        wu = WorkUnit(uid, 2 ** 137 - 1, ("-v", "-timestamp"), B1="1e5", B2="1e7")
        units.append(wu)
    return units


def get_env():
    # TODO use params and stuff
    return Env("../../gmp-ecm/ecm", ("-q",), "", "test.output")


def process_output(wu: WorkUnit, output: subprocess.CompletedProcess):
    is_error, found_factor, prime_factor, prime_coprime = parse_returncode(output.returncode)
    assert not is_error

    factors = tuple()
    if found_factor:
        print("-" * 80)
        print(output.stdout)
        print(f"Return: {output.returncode} {is_error = }, {found_factor = }, {prime_factor = }")
        # Find factor in output either
        #   .*Factor.*[NUMBER]
        # Or in quiet mode
        #   [NUMBER] [COPRIME]
        factors1 = RE_FACTORS_FMT1.findall(output.stdout)
        factors2 = RE_FACTORS_FMT2.findall(output.stdout)
        factors = tuple(map(int, factors1 + factors2))
        print(factors)
        print("-" * 80)
        assert factors

    result = EcmOutput(factors, output.returncode, resume_line="", status="", runtime=0)

"""
@dataclass()
class EcmOutput:
    factors: Tuple[str]
    exit_status: int
    resume_line: str
    status: str
    runtime: float
"""



def run_client():
    env = get_env()

    # TODO get WorkUnits from server
    try:
        work = []
        while True:
            if len(work) == 0:
                work.extend(get_fake_work_units(1))

            # TODO this isn't a work
            wu = work.pop()
            #print(datetime.now().isoformat(), len(work), wu)

            output = run(wu, env)
            process_output(wu, output)

    except KeyboardInterrupt:
        print("TODO graceful shutdown in the future")


run_client()
