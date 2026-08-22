#!/usr/bin/env python3
"""วัดขนาดฟอนต์ไทยของ PDF เราเทียบกับข้อสอบจริง

usage: python3 measure_font_size.py REAL.pdf MINE.pdf [real_pages] [mine_pages]
       (ค่าเริ่มต้น real=2-7  mine=2-9  ข้ามหน้าปกเพราะขนาดตัวอักษรต่างจากเนื้อใน)

หลักการ
  PyMuPDF คืนขนาดฟอนต์จริง (em size, หน่วย pt) ของทุก span ในหน้า จึงเทียบได้ตรง ๆ
  ไม่ต้องจับคู่คำเหมือนวิธีเดิมที่ใช้ `pdftotext -bbox` ซึ่งคืน "กล่องฟอนต์"
  (ascent+descent ≈ 1.1 เท่าของ em) แทนที่จะเป็นขนาดฟอนต์

  นับเฉพาะ span ที่มีอักษรไทย ถ่วงน้ำหนักด้วยจำนวนตัวอักษร แล้วเอาขนาดที่ครองหน้ามากที่สุด
  (ตัวเนื้อความ) มาเทียบกัน — หัวข้อกับเชิงอรรถขนาดต่างออกไปจึงไม่ถูกนับ

  ratio = 1.00 คือขนาดตรงกัน   ratio > 1 คือของเราใหญ่กว่า
  ปรับด้วย  Scale ใหม่ = Scale เดิม / ratio

ข้อจำกัด
  เทียบเฉพาะข้อความไทยกับข้อความไทย ที่เป็นฟอนต์ตระกูลเดียวกัน (TH Sarabun)
  อย่าเอาไปเทียบตัวเลข/อักษรละติน เพราะของเราเป็น Computer Modern คนละ metrics
"""
import collections
import re
import sys

try:
    import pymupdf
except ImportError:
    sys.exit('ต้องมี PyMuPDF — ติดตั้งด้วย: python3 -m pip install pymupdf')

THAI = re.compile(r'[฀-๿]')


def parse_pages(spec, default):
    if not spec:
        return default
    lo, _, hi = spec.partition('-')
    return range(int(lo) - 1, int(hi or lo))


def thai_sizes(path, pages):
    """คืน Counter ของ {ขนาดฟอนต์: จำนวนตัวอักษรไทยที่ใช้ขนาดนั้น}"""
    doc = pymupdf.open(path)
    out = collections.Counter()
    for i in pages:
        if i >= len(doc):
            break
        for block in doc[i].get_text('dict')['blocks']:
            for line in block.get('lines', []):
                for span in line['spans']:
                    if THAI.search(span['text']):
                        out[round(span['size'], 2)] += len(span['text'])
    doc.close()
    return out


def dominant(counter, label):
    if not counter:
        sys.exit(f'ไม่พบข้อความไทยใน {label} — ตรวจว่าช่วงหน้าถูกต้องไหม')
    return max(counter.items(), key=lambda kv: kv[1])[0]


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(2)
    real_path, mine_path = sys.argv[1], sys.argv[2]
    real_pages = parse_pages(sys.argv[3] if len(sys.argv) > 3 else '', range(1, 7))
    mine_pages = parse_pages(sys.argv[4] if len(sys.argv) > 4 else '', range(1, 9))

    real = thai_sizes(real_path, real_pages)
    mine = thai_sizes(mine_path, mine_pages)
    r, m = dominant(real, 'ข้อสอบจริง'), dominant(mine, 'ไฟล์ของเรา')

    print(f'ขนาดที่ครองหน้า  จริง={r:.2f} pt ({real[r]} ตัวอักษร)  '
          f'เรา={m:.2f} pt ({mine[m]} ตัวอักษร)')
    for name, c in (('จริง', real), ('เรา', mine)):
        others = ', '.join(f'{s:.2f}pt×{n}' for s, n in c.most_common(4)[1:])
        if others:
            print(f'  ขนาดอื่นใน{name}: {others}')

    med = m / r
    print(f'\nMEDIAN RATIO (เรา/จริง) = {med:.4f}')
    if abs(med - 1) < 0.01:
        print('ขนาดตรงกันแล้ว ไม่ต้องแก้')
    else:
        print(f'ยังไม่ตรง  ->  Scale ใหม่ = Scale เดิม / {med:.4f}')
        print(f'   ถ้าตอนนี้ Scale = 1.112  ให้ใช้ {1.112 / med:.3f}')


if __name__ == '__main__':
    main()
