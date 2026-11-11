#!/usr/bin/env python3
"""Check the user's500GB project limit before allocating an entire artifact batch."""
from pathlib import Path
import argparse,json,shutil,subprocess

LIMIT_BYTES=500_000_000_000

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--planned-bytes',type=int,default=0,
                        help='Conservative allocated size of all files/clones in the batch')
    args=parser.parse_args()
    if args.planned_bytes<0:parser.error('planned bytes must be nonnegative')
    root=Path(__file__).resolve().parents[1]
    current=int(subprocess.check_output(['du','-sk',str(root)],text=True).split()[0])*1024
    admitted=current+args.planned_bytes<=LIMIT_BYTES
    print(json.dumps(dict(root=str(root),current_accounted_bytes=current,
                         planned_batch_bytes=args.planned_bytes,limit_bytes=LIMIT_BYTES,
                         admitted=admitted,disk_free_bytes=shutil.disk_usage(root).free,
                         accounting='du allocated bytes; shared APFS clones counted conservatively'),indent=2))
    return 0 if admitted else 1

if __name__=='__main__':raise SystemExit(main())
