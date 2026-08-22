#!/usr/bin/env python3
"""แปลงหน้า PDF ที่ระบุเป็น PNG เพื่อเปิดดูด้วยตา

usage: python3 render_pages.py FILE.pdf 1 4 9        # เฉพาะหน้าที่ preflight ชี้
       python3 render_pages.py FILE.pdf 1 4 9 --dpi 120

**ห้าม render ทุกหน้าโดยไม่มีเหตุผล** ชุด 50 ข้อ + เฉลย 40 หน้าคือการอ่านภาพ 50+ ภาพ
เข้า context ซึ่งแพงที่สุดในไปป์ไลน์ทั้งหมด และแพงโดยไม่ได้อะไรเพิ่ม เพราะหน้าที่เป็น
ข้อความล้วนไม่เคยพัง ให้ `preflight.py` บอกก่อนว่าหน้าไหนเสี่ยง แล้ว render เฉพาะหน้านั้น

สคริปต์นี้จึงบังคับให้ระบุเลขหน้า ไม่มีโหมด "ทั้งไฟล์"
"""
import sys
from pathlib import Path

try:
    import pymupdf
except ImportError:
    sys.exit('ต้องมี PyMuPDF — ติดตั้งด้วย: python3 -m pip install pymupdf')


def main():
    args = [a for a in sys.argv[1:]]
    dpi = 100
    if '--dpi' in args:
        i = args.index('--dpi')
        dpi = int(args[i + 1])
        del args[i:i + 2]
    if len(args) < 2:
        print(__doc__)
        sys.exit(2)

    pdf = Path(args[0])
    if not pdf.exists():
        sys.exit(f'ไม่มีไฟล์ {pdf}')
    pages = sorted({int(a) for a in args[1:]})

    doc = pymupdf.open(pdf)
    for n in pages:
        if not 1 <= n <= len(doc):
            sys.exit(f'หน้า {n} ไม่มีใน {pdf.name} (มี {len(doc)} หน้า)')
        out = pdf.with_name(f'{pdf.stem}-p{n}.png')
        doc[n - 1].get_pixmap(dpi=dpi).save(out)
        print(out)
    doc.close()


if __name__ == '__main__':
    main()
