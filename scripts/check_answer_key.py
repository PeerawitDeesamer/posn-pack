#!/usr/bin/env python3
"""ตรวจว่าตารางเฉลย + วิธีทำ ตรงกับตัวเลือกในข้อสอบจริงหรือไม่

usage: python3 check_answer_key.py exam.tex answer.tex

รองรับทั้งข้อสอบปรนัยล้วน และข้อสอบผสม (ตอนที่ 1 ปรนัย + ตอนที่ 2 อัตนัยเติมคำตอบ)
ข้อปรนัยดูจาก \\chfour/\\chtwo/\\chstack ข้ออัตนัยดูจาก \\fillbox ที่ไม่มีตัวเลือก

ตรวจ 5 อย่าง
  1. ตัวอักษร/ตัวเลขใน "ตารางเฉลย" ตรงกับที่ \\ansline ของแต่ละข้อ
  2. ค่าที่ \\ansline อ้าง ตรงกับตัวเลือกที่อยู่ในตำแหน่งนั้นของข้อสอบ (เฉพาะข้อปรนัย)
  3. การกระจาย ก/ข/ค/ง สมดุลพอ (นับเฉพาะข้อปรนัย)
  4. คำตอบข้ออัตนัยเป็นจำนวนเต็ม 0-9999 ตามข้อกำหนดของ สอวน.
  5. จำนวนข้อในข้อสอบ ตารางเฉลย และวิธีทำ ตรงกันทั้งสามแหล่ง

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
    """คืนรายการข้อ ตามลำดับที่ปรากฏจริง

    แต่ละข้อเป็น dict: {'kind': 'mcq'|'fill', 'choices': [4 ตัวเลือก] หรือ None}
    รองรับหลาย environment ต่อไฟล์ (qlist = ตอนปรนัย, qlistb = ตอนอัตนัย)
    """
    src = open(path, encoding='utf-8').read()
    out = []
    for env in ('qlist', 'qlistb'):
        chunks = src.split('\\begin{' + env + '}')[1:]
        for chunk in chunks:
            body = chunk.split('\\end{' + env + '}')[0]
            for q in re.split(r'\n\\item ', body)[1:]:
                ch = None
                for cmd in ('chfour', 'chtwo', 'chstack'):
                    ch = brace_args(q, cmd)
                    if ch and len(ch) == 4:
                        break
                    ch = None
                if ch:
                    out.append({'kind': 'mcq', 'choices': ch})
                else:
                    out.append({'kind': 'fill', 'choices': None})
    return out


def parse_key_table(src):
    """อ่านช่องคำตอบจากตาราง \\textbf{ตอบ} & ก & ข & ... (หรือ & 45 & 128 & ...)

    ข้ออัตนัยใส่ตัวเลขในช่องแทนตัวอักษร จึงรับทั้งสองแบบ
    """
    cells = []
    for row in re.findall(r'\\textbf\{ตอบ\}([^\\\n]*(?:\\\\)?)', src):
        for cell in row.split('&')[1:]:
            cell = cell.replace('\\\\', '').replace('\\hline', '').strip()
            cell = cell.replace('$', '').replace('{,}', '').strip()
            if cell in LETTERS or re.fullmatch(r'-?\d+', cell):
                cells.append(cell)
    return cells


def parse_anslines(src):
    """อ่าน \\ansline{<ตัวอักษร>.\\ <ค่า>}{} หรือ \\ansline{<ตัวเลข>}{} ของแต่ละข้อ"""
    out = []
    for m in re.finditer(r'\\ansline\{', src):
        args = brace_args(src[m.start():], 'ansline', count=1)
        if not args:
            continue
        a = args[0].strip()
        letter = a[0] if a[:1] in LETTERS else None
        value = (a[1:].lstrip('.') if letter else a).replace('\\ ', ' ').strip()
        out.append((letter, value))
    return out


def check_mcq(q, item, tbl, ansline, problems, skipped):
    ch = item['choices']
    tbl_letter, (ans_letter, ans_value) = tbl, ansline
    if tbl_letter not in LETTERS:
        problems.append((q, f'ข้อปรนัยแต่ตารางเฉลยใส่ "{tbl_letter}" ไม่ใช่ ก/ข/ค/ง'))
        return
    if ans_letter != tbl_letter:
        problems.append((q, f'ตาราง={tbl_letter} แต่วิธีทำ={ans_letter}'))
        return

    pos = LETTERS.index(tbl_letter)
    want = nums(ans_value)
    got = nums(ch[pos])
    if not want:
        skipped.append(q)              # คำตอบเป็นข้อความล้วน ตรวจอัตโนมัติไม่ได้
        return
    if want != got:
        problems.append(
            (q, f'ตอบ {tbl_letter} อ้างค่า {want} แต่ตัวเลือก {tbl_letter} คือ {got}'))
        return
    twins = [LETTERS[j] for j in range(4) if j != pos and nums(ch[j]) == want]
    if twins:
        skipped.append(q)              # ตัวเลือกอื่นมีตัวเลขชุดเดียวกัน แยกด้วยเลขไม่ได้
        print(f'  ~ ข้อ {q}: ตัวเลือก {"/".join(twins)} มีตัวเลขชุดเดียวกัน ต้องดูข้อความเอง')


def check_fill(q, tbl, ansline, problems):
    """ข้ออัตนัย: ตารางกับวิธีทำต้องตรงกัน และต้องเป็นจำนวนเต็ม 0-9999"""
    ans_letter, ans_value = ansline
    if ans_letter is not None:
        problems.append((q, 'ข้ออัตนัยแต่วิธีทำขึ้นต้นด้วยตัวเลือก ก/ข/ค/ง'))
        return
    want = nums(ans_value)
    if not want:
        problems.append((q, f'ข้ออัตนัยต้องตอบเป็นตัวเลข แต่ \\ansline คือ "{ans_value}"'))
        return
    if len(want) > 1:
        problems.append((q, f'ข้ออัตนัยต้องมีคำตอบเดียว แต่พบ {want}'))
        return
    v = want[0]
    if '/' in v:
        problems.append((q, f'ข้ออัตนัยตอบเศษส่วน {v} ไม่ได้ ต้องเป็นจำนวนเต็ม'))
        return
    if not (0 <= int(v) <= 9999):
        problems.append((q, f'คำตอบ {v} อยู่นอกช่วงจำนวนเต็มไม่เกิน 4 หลัก (0-9999)'))
        return
    if nums(tbl) != want:
        problems.append((q, f'ตาราง={nums(tbl)} แต่วิธีทำ={want}'))


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(2)
    exam_path, ans_path = sys.argv[1], sys.argv[2]
    items = parse_exam(exam_path)
    ans_src = open(ans_path, encoding='utf-8').read()
    table = parse_key_table(ans_src)
    anslines = parse_anslines(ans_src)

    n = len(items)
    n_mcq = sum(1 for it in items if it['kind'] == 'mcq')
    n_fill = n - n_mcq
    print(f'ข้อสอบ {n} ข้อ (ปรนัย {n_mcq} / อัตนัย {n_fill}) | '
          f'ตารางเฉลย {len(table)} ช่อง | วิธีทำ {len(anslines)} ข้อ')
    problems, skipped = [], []

    if not (n == len(table) == len(anslines)):
        problems.append(('COUNT', 'จำนวนข้อไม่ตรงกันระหว่างสามแหล่ง'))

    for i in range(min(n, len(table), len(anslines))):
        q = i + 1
        item = items[i]
        if item['kind'] == 'mcq':
            if item['choices'] is None or len(item['choices']) != 4:
                problems.append((q, 'อ่านตัวเลือกไม่ได้ (macro ผิดรูป?)'))
                continue
            check_mcq(q, item, table[i], anslines[i], problems, skipped)
        else:
            check_fill(q, table[i], anslines[i], problems)

    dist = Counter(t for t in table if t in LETTERS)
    if dist:
        print('การกระจายคำตอบปรนัย:', ' '.join(f'{L}={dist.get(L, 0)}' for L in LETTERS))
        if max(dist.values()) - min(dist.get(L, 0) for L in LETTERS) > 6:
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
