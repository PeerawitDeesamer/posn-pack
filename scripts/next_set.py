#!/usr/bin/env python3
"""หาเลขชุดว่างจริงของพาร์ทหนึ่ง โดยดูทั้งในเครื่องและบน Google Drive

usage:
  python3 next_set.py comp             # เลขชุดถัดไปที่ว่างจริง
  python3 next_set.py comp --check 5   # เลข 5 ว่างไหม (exit 1 ถ้าไม่ว่าง)
  python3 next_set.py comp --check 5 --drive-only   # ดูเฉพาะ Drive

`--drive-only` ใช้ตอนที่ไฟล์ของชุดนี้ถูกวางในเครื่องไปแล้ว (เช่นใน preflight) ซึ่งการ
นับในเครื่องจะเจอไฟล์ของตัวเองเสมอ สิ่งที่ยังต้องกันคือ **ทับของที่อยู่บน Drive**

ทำไมต้องดู Drive ด้วย
  โฟลเดอร์ในเครื่อง **ไม่ใช่บันทึกที่ครบ** — เคยเกิดขึ้นจริงว่าในเครื่องมีพาร์ทคอมแค่
  ชุดที่ 2 แต่บน Drive มีชุดที่ 1-4 ครบ พอตั้งเลขชุดจากที่เห็นในเครื่องอย่างเดียว
  จึงได้เลข 3 ซึ่งชนกับของจริง และ `rclone copy` จะเขียนทับไฟล์เดิมหายทันที
  โดยไม่มีอะไรเตือน

  Drive คือบันทึกที่ครบกว่าเสมอ เพราะทุกชุดที่ส่งมอบแล้วถูกอัปขึ้นไป ส่วนในเครื่อง
  อาจถูกลบหรือย้ายเมื่อไรก็ได้

ถ้าเรียก Drive ไม่ได้ (ไม่มีเน็ต/rclone พัง) สคริปต์นี้ **หยุดด้วย error**
ไม่เดาเลขชุดจากข้อมูลครึ่งเดียว เพราะเดาผิดแปลว่าทับงานเก่าของผู้ใช้
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

POSN_ROOT = Path.home() / 'Documents' / 'POSN.Computer'
RCLONE = Path.home() / '.local' / 'bin' / 'rclone'
REMOTE = 'gdrive:POSN.Computer'

FOLDER = {'math': 'พาร์ทคณิตศาสตร์', 'comp': 'พาร์ทคอมพิวเตอร์', 'both': 'ฉบับเต็ม'}
TAG = {'math': 'ชุดที่', 'comp': 'พาร์ทคอมชุดที่', 'both': 'ฉบับเต็มชุดที่'}


def die(msg):
    sys.exit(f'next_set: {msg}')


def sets_from(names, part):
    """ดึงเลขชุดออกจากชื่อไฟล์ เช่น ..._พาร์ทคอมชุดที่3.pdf -> 3

    ต้องยึด `_` หน้าแท็ก ไม่งั้นแท็กของพาร์ทคณิต ("ชุดที่") จะไปแมตช์ท้ายชื่อไฟล์
    ของพาร์ทคอม ("...พาร์ทคอมชุดที่3.pdf") ด้วย แล้วนับเลขชุดข้ามพาร์ทกันมั่ว
    """
    pat = re.compile('_' + re.escape(TAG[part]) + r'(\d+)\.pdf$')
    return {int(m.group(1)) for n in names if (m := pat.search(n))}


def local_sets(part):
    d = POSN_ROOT / 'ข้อสอบเทียม' / FOLDER[part]
    if not d.is_dir():
        return set()
    return sets_from([p.name for p in d.iterdir()], part)


def drive_sets(part):
    if not RCLONE.exists():
        die(f'ไม่มี rclone ที่ {RCLONE} — ตรวจ Drive ไม่ได้ จึงตั้งเลขชุดไม่ได้')
    # ต้องดูทั้งโฟลเดอร์ย่อยของพาร์ท และรากของ POSN.Computer เพราะไฟล์เก่าบางชุด
    # ถูกอัปลอยไว้ที่รากก่อนจะมีการแยกโฟลเดอร์ (เช่น พาร์ทคณิตชุดที่ 8)
    p = subprocess.run([str(RCLONE), 'lsf', '-R', REMOTE],
                       capture_output=True, text=True)
    if p.returncode != 0:
        tail = p.stderr.strip().splitlines()[-1] if p.stderr.strip() else ''
        die(f'เรียก Drive ไม่ได้ จึงตั้งเลขชุดไม่ได้ '
            f'(เดาจากข้อมูลครึ่งเดียว = เสี่ยงทับงานเก่า)\n        {tail}')
    return sets_from([n.rsplit('/', 1)[-1] for n in p.stdout.split('\n')], part)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('part', choices=['math', 'comp', 'both'])
    ap.add_argument('--check', type=int, help='ถามว่าเลขนี้ว่างไหม')
    ap.add_argument('--drive-only', action='store_true',
                    help='ไม่นับไฟล์ในเครื่อง (ใช้เมื่อไฟล์ของชุดนี้ถูกวางไปแล้ว)')
    args = ap.parse_args()

    drive = drive_sets(args.part)
    local = set() if args.drive_only else local_sets(args.part)
    used = local | drive

    print(f'พาร์ท {args.part} | ในเครื่อง {sorted(local) or "ไม่มี"} | '
          f'บน Drive {sorted(drive) or "ไม่มี"}')
    only_drive = sorted(drive - local)
    if only_drive:
        print(f'  ! ชุด {only_drive} มีแต่บน Drive ไม่มีในเครื่อง — '
              f'นี่คือเหตุผลที่ต้องดู Drive ด้วย')

    if args.check is not None:
        if args.check in used:
            where = 'ในเครื่อง' if args.check in local else ''
            where += (' และ ' if where and args.check in drive else '') + \
                     ('บน Drive' if args.check in drive else '')
            sys.exit(f'\nชุดที่ {args.check} ถูกใช้แล้ว ({where}) — '
                     f'เลขว่างถัดไปคือ {max(used) + 1 if used else 1}')
        print(f'\nชุดที่ {args.check} ว่าง ใช้ได้')
        return

    print(f'\nเลขชุดถัดไปที่ว่างจริง: {max(used) + 1 if used else 1}')


if __name__ == '__main__':
    main()
