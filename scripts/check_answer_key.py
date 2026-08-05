#!/usr/bin/env python3
"""ตรวจว่าตารางเฉลย + วิธีทำ ตรงกับตัวเลือกในข้อสอบจริงหรือไม่

usage: python3 check_answer_key.py exam.tex answer.tex

ตรวจ 3 อย่าง
  1. ตัวอักษรใน "ตารางเฉลย" ตรงกับตัวอักษรที่ \\ansline ของแต่ละข้อ
  2. ค่าที่ \\ansline อ้าง ตรงกับตัวเลือกที่อยู่ในตำแหน่งนั้นของข้อสอบ
  3. การกระจาย ก/ข/ค/ง สมดุลพอ

ข้อที่คำตอบเป็นข้อความล้วน (ตรรกศาสตร์ ช่วง สูตร) สคริปต์จะข้ามและรายงานให้ไล่ดูเอง
"""
import re
import sys
from collections import Counter

LETTERS = ['ก', 'ข', 'ค', 'ง']


def brace_args(text, cmd, count=4):
    """ดึงอาร์กิวเมนต์ {} ที่ต่อกันของ \\cmd โดยนับวงเล็บซ้อน"""
    i = text.find('\\' + cmd + '{')
    if i < 0:
        return None
    i += len(cmd) + 2
    out, depth, cur = [], 1, ''
    while i < len(text) and len(out) < count:
        c = text[i]
        if c == '{':
            depth += 1
            cur += c
        elif c == '}':
            depth -= 1
            if depth == 0:
                out.append(cur)
                cur = ''
                if i + 1 < len(text) and text[i + 1] == '{':
                    depth = 1
                    i += 1
                else:
                    break
            else:
                cur += c
        else:
            cur += c
        i += 1
    return out


def normalize(t):
    """ลดรูป LaTeX ให้เทียบกันได้: เศษส่วน -> a/b, ตัดคำสั่งและสัญลักษณ์จัดรูป

    ต้องคงเครื่องหมายจุลภาคที่คั่นค่าไว้ (เช่น พิกัด (13/3, 0)) ไม่งั้นตัวเลขจะติดกัน
    เป็น 13/30 จึงลบเฉพาะจุลภาคหลักพัน: {,} ของ LaTeX และ ,ddd ในข้อความไทย
    """
    t = t.replace('{,}', '')                                  # $17{,}010$ -> 17010
    t = re.sub(r'\\[dt]?frac\{([^{}]*)\}\{([^{}]*)\}', r'\1/\2', t)
    t = re.sub(r'\\[a-zA-Z]+', '', t)
    t = re.sub(r'[${}\s~]', '', t)
    return re.sub(r'(?<=\d),(?=\d{3}(?!\d))', '', t)          # 12,800 -> 12800


def nums(t):
    """ดึงลำดับตัวเลข (รวมเศษส่วนและจำนวนลบ) ออกมาเทียบกัน

    เทียบด้วยตัวเลขแทนการเทียบข้อความทั้งก้อน เพราะข้อความใน \\ansline มักเขียนย่อกว่า
    ตัวเลือกในข้อสอบ (เช่น "จุดตัดแกน y คือ (0,5/3)" กับ "จุดตัดแกน y ของกราฟ f คือ (0,5/3)")
    """
    return re.findall(r'-?\d+(?:/\d+)?', normalize(t))


def parse_exam(path):
    src = open(path, encoding='utf-8').read()
    body = src.split(r'\begin{qlist}')[1].split(r'\end{qlist}')[0]
    questions = re.split(r'\n\\item ', body)[1:]
    out = []
    for q in questions:
        ch = None
        for cmd in ('chfour', 'chtwo', 'chstack'):
            ch = brace_args(q, cmd)
            if ch and len(ch) == 4:
                break
        out.append(ch)
    return out


def parse_key_table(src):
    """อ่านตัวอักษรคำตอบจากตาราง \\textbf{ตอบ} & ก & ข & ..."""
    letters = []
    for row in re.findall(r'\\textbf\{ตอบ\}([^\\\n]*(?:\\\\)?)', src):
        for cell in row.split('&')[1:]:
            cell = cell.replace('\\\\', '').replace('\\hline', '').strip()
            if cell in LETTERS:
                letters.append(cell)
    return letters


def parse_anslines(src):
    """อ่าน \\ansline{<ตัวอักษร>.\\ <ค่า>}{} ของแต่ละข้อ"""
    out = []
    for m in re.finditer(r'\\ansline\{', src):
        args = brace_args(src[m.start():], 'ansline', count=1)
        if not args:
            continue
        a = args[0].strip()
        letter = a[0] if a[:1] in LETTERS else None
        value = a[1:].lstrip('.').replace('\\ ', ' ').strip()
        out.append((letter, value))
    return out


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(2)
    exam_path, ans_path = sys.argv[1], sys.argv[2]
    choices = parse_exam(exam_path)
    ans_src = open(ans_path, encoding='utf-8').read()
    table = parse_key_table(ans_src)
    anslines = parse_anslines(ans_src)

    n = len(choices)
    print(f'ข้อสอบ {n} ข้อ | ตารางเฉลย {len(table)} ช่อง | วิธีทำ {len(anslines)} ข้อ')
    problems, skipped = [], []

    if not (n == len(table) == len(anslines)):
        problems.append(('COUNT', 'จำนวนข้อไม่ตรงกันระหว่างสามแหล่ง'))

    for i in range(min(n, len(table), len(anslines))):
        q = i + 1
        ch = choices[i]
        tbl_letter = table[i]
        ans_letter, ans_value = anslines[i]

        if ch is None or len(ch) != 4:
            problems.append((q, 'อ่านตัวเลือกไม่ได้ (macro ผิดรูป?)'))
            continue
        if ans_letter != tbl_letter:
            problems.append((q, f'ตาราง={tbl_letter} แต่วิธีทำ={ans_letter}'))
            continue

        pos = LETTERS.index(tbl_letter)
        want = nums(ans_value)
        got = nums(ch[pos])
        if not want:
            skipped.append(q)          # คำตอบเป็นข้อความล้วน ตรวจอัตโนมัติไม่ได้
            continue
        if want != got:
            problems.append(
                (q, f'ตอบ {tbl_letter} อ้างค่า {want} แต่ตัวเลือก {tbl_letter} คือ {got}'))
            continue
        twins = [LETTERS[j] for j in range(4) if j != pos and nums(ch[j]) == want]
        if twins:
            skipped.append(q)          # ตัวเลือกอื่นมีตัวเลขชุดเดียวกัน แยกด้วยเลขไม่ได้
            print(f'  ~ ข้อ {q}: ตัวเลือก {"/".join(twins)} มีตัวเลขชุดเดียวกัน ต้องดูข้อความเอง')

    dist = Counter(table)
    print('การกระจายคำตอบ:', ' '.join(f'{L}={dist.get(L, 0)}' for L in LETTERS))
    if dist and max(dist.values()) - min(dist.get(L, 0) for L in LETTERS) > 6:
        print('  ! เอียงเกินไป ควรสลับตำแหน่งตัวเลือกบางข้อ')

    if skipped:
        print(f'ข้ามการตรวจอัตโนมัติ {len(skipped)} ข้อ (คำตอบเป็นข้อความ) '
              f'ต้องไล่ดูเอง: {skipped}')

    if problems:
        print(f'\nพบปัญหา {len(problems)} จุด')
        for q, msg in problems:
            print(f'  ข้อ {q}: {msg}')
        sys.exit(1)
    print('\nผ่าน: ทุกข้อที่ตรวจได้ ตัวเลือกตรงกับเฉลย')


if __name__ == '__main__':
    main()
