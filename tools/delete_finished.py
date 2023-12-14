"""Removes lines from a partial file that have already been processed in a ecm_runner_X.log file."""

import re
import sys


def read_log(fn):
  finished = set()
  with open(fn) as f:
    for line in f:
      if line.startswith("Input number is"):
        match = re.match("^Input number is (.*) \([0-9]+ digits\)$", line)
        assert match
        N = match.group(1)
        finished.add(N)
  return sorted(finished)


def N_matches(line, finished):
  match = re.search("N=([^;]*);", line)
  if match:
    N = match.group(1)
    if N in finished:
      return True
    if N.startswith("0x") and str(int(N, 16)) in finished:
      return True
  return False


def remove_matched(resume_fn, result_fn, finished):
  matched = 0

  with open(resume_fn) as f, open(result_fn, "w") as copy_f:
    for line in f:
      if N_matches(line, finished):
        matched += 1
        continue
      copy_f.write(line)

  print(f"Removed {matched}/{len(finished)} finished results")


def main(resume_fn, log_fn):
  finished = read_log(log_fn)
  if not finished:
    print(f"No finished results in {log_fn!r}")
    exit(1)

  remove_matched(resume_fn, resume_fn + ".filtered", finished)



if __name__ == "__main__":
  if len(sys.argv) != 3:
    print("{sys.argv[0]} takes 2 args: resume_fn and log_fn")
    exit(1)

  main(sys.argv[1], sys.argv[2])
