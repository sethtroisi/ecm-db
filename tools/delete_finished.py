"""Removes lines from a partial file that have already been processed in a ecm_runner_X.log file."""

import argparse
import re
import sys


def get_argparser():
    parser = argparse.ArgumentParser(description='delete finished lines from a resume file.')
    parser.add_argument('-n', '--dry-run', action='store_true',
                        help="Dry Run, don't save file")
    parser.add_argument('resume_file', type=str,
                        help='resume file, finished lines will be deleted from this file.')
    parser.add_argument('log_file', type=str,
                        help='log file to serach for finished results.')
    return parser


def read_log(fn):
  INPUT_MATCH = re.compile(r"^Input number is (.*) \([0-9]+ digits\)$")
  finished = set()
  with open(fn) as f:
    for line in f:
      if line.startswith("Input number is"):
        match = INPUT_MATCH.match(line)
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


def remove_matched(args, result_fn, finished):
  saved = 0
  filtered = 0

  should_save = not args.dry_run

  with open(args.resume_file) as f:
    if should_save:
      print(f"Saving filtered results to {result_fn!r}")
      copy_f =  open(result_fn, "w")

    for line in f:
      if N_matches(line, finished):
        filtered += 1
        continue

      saved += 1
      if should_save:
        copy_f.write(line)

  if should_save:
      copy_f.close()

  n = saved + filtered
  print(f"Removed {filtered}/{n} finished results, {saved}/{n} remaining lines")


def main(args):
  finished = read_log(args.log_file)
  if not finished:
    print(f"No finished results in {log_fn!r}")
    exit(1)

  new_name = args.resume_file + ".filtered"
  remove_matched(args, new_name, finished)



if __name__ == "__main__":
  parser = get_argparser()
  args = parser.parse_args()

  main(args)
