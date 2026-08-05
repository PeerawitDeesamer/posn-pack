#!/usr/bin/env python3
"""วัดขนาดฟอนต์ไทยของ PDF เราเทียบกับข้อสอบจริง

usage: python3 measure_font_size.py REAL.pdf MINE.pdf [real_pages] [mine_pages]
       (ค่าเริ่มต้น real=2-7  mine=2-9  ข้ามหน้าปกเพราะขนาดตัวอักษรต่างจากเนื้อใน)

หลักการ
  pdftotext -bbox คืน "กล่องฟอนต์" (ascent/descent ของฟอนต์) ไม่ใช่กล่องหมึกจริง
  ทุกคำในบรรทัดเดียวกันจึงสูงเท่ากัน = เทียบขนาดฟอนต์ได้ตรง
  สคริปต์จับคู่คำภาษาไทย "คำเดียวกัน" ที่มีทั้งสองไฟล์ แล้วหา median ของอัตราส่วน

  ratio = 1.00 คือขนาดตรงกัน   ratio > 1 คือของเราใหญ่กว่า
  ปรับด้วย  Scale ใหม่ = Scale เดิม / ratio

ข้อจำกัด
  ใช้ได้เฉพาะเมื่อทั้งสองไฟล์ใช้ฟอนต์ตระกูลเดียวกัน (TH Sarabun)
  อย่าเอาไปเทียบตัวเลข/อักษรละติน เพราะของเราเป็น Computer Modern คนละ metrics
"""
import re
import statistics
import subprocess
import sys
import tempfile
from collections import defaultdict

WORD_RE = re.compile(
    r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">(.*?)</word>')


def thai_word_heights(pdf, first, last):
    with tempfile.NamedTemporaryFile(suffix='.xml') as tmp:
        subprocess.run(['pdftotext', '-f', str(first), '-l', str(last), '-bbox', pdf, tmp.name],
                       check=True, capture_output=True)
        xml = open(tmp.name, encoding='utf-8').read()
    d = defaultdict(list)
    for _x0, y0, _x1, y1, t in WORD_RE.findall(xml):
        if any('฀' <= c <= '๿' for c in t):      # มีอักษรไทย
            d[t].append(float(y1) - float(y0))
    return {k: statistics.median(v) for k, v in d.items()}


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(2)
    real_pdf, mine_pdf = sys.argv[1], sys.argv[2]
    real_rng = sys.argv[3] if len(sys.argv) > 3 else '2-7'
    mine_rng = sys.argv[4] if len(sys.argv) > 4 else '2-9'
    rf, rl = (int(x) for x in real_rng.split('-'))
    mf, ml = (int(x) for x in mine_rng.split('-'))

    real = thai_word_heights(real_pdf, rf, rl)
    mine = thai_word_heights(mine_pdf, mf, ml)
    common = [w for w in real if w in mine]
    if not common:
        print('ไม่พบคำไทยที่ตรงกันเลย — ตรวจว่าช่วงหน้าถูกต้องไหม')
        sys.exit(1)

    ratios = [mine[w] / real[w] for w in common]
    med = statistics.median(ratios)
    print(f'คำไทยที่ตรงกัน {len(common)} คำ')
    for w in sorted(common, key=lambda w: -real[w])[:8]:
        print(f'   "{w}"  จริง={real[w]:5.2f}  เรา={mine[w]:5.2f}  ratio={mine[w]/real[w]:.3f}')
    print(f'\nMEDIAN RATIO (เรา/จริง) = {med:.4f}')
    if abs(med - 1) < 0.01:
        print('ขนาดตรงกันแล้ว ไม่ต้องแก้')
    else:
        print(f'ยังไม่ตรง  ->  Scale ใหม่ = Scale เดิม / {med:.4f}')
        print(f'   ถ้าตอนนี้ Scale = 1.112  ให้ใช้ {1.112 / med:.3f}')


if __name__ == '__main__':
    main()
