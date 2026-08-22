#!/usr/bin/env python3
"""ตรวจทุกอย่างก่อนส่งมอบ ในคำสั่งเดียว — บรรทัดละการตรวจ เจอ FAIL แล้วหยุดทันที

usage: python3 preflight.py <part> <set>      (รันในโฟลเดอร์งานที่มี examN.tex)

ไฟล์ที่ต้องมีในโฟลเดอร์งาน — ขาดอันไหนหยุดทันที ไม่มีทางเลือกสำรอง
  verify.py  verify_out.json  ideas.json
  exam<N>.tex  exam<N>.pdf  exam<N>.log  answer<N>.tex
และพิมพ์เขียว ~/Documents/POSN.Computer/blueprints/<part>-set<N>.json

ทำไมต้องรวมเป็นสคริปต์เดียว
  เดิมต้องรัน 4 สคริปต์แยกกันแล้วไล่ checklist 20+ ข้อด้วยตา ซึ่งกินหลาย tool call
  และอ่าน output หลายก้อน พอทำซ้ำหลายรอบโมเดลจะเริ่มข้ามแล้วรายงานว่า "ตรวจแล้ว"
  ทุกข้อที่เครื่องตรวจแทนได้ ต้องให้เครื่องตรวจ เหลือให้คนเฉพาะข้อที่ต้องใช้สายตาจริง

เจอ FAIL ข้อใดข้อหนึ่ง → exit 1 ทันที ไม่ตรวจต่อ และไม่เสนอทางแก้
(ทางแก้ขึ้นกับว่าโจทย์ข้อนั้นตั้งใจวัดอะไร ซึ่งสคริปต์ไม่รู้ — คนต้องเป็นคนตัดสิน)
"""
import json
import re
import subprocess
import sys
from collections import Counter
from fractions import Fraction
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
import check_answer_key as cak          # noqa: E402  ใช้ตัว parse ตัวเดียวกับที่ตรวจเฉลย

POSN_ROOT = Path.home() / 'Documents' / 'POSN.Computer'
BLUEPRINT_DIR = POSN_ROOT / 'blueprints'
REAL_EXAM = POSN_ROOT / 'ไฟล์ข้อสอบ' / 'ข้อสอบสอวนคอมปี 68.pdf'

DIST_LO, DIST_HI = 0.20, 0.30      # สัดส่วนที่ยอมรับได้ของ ก/ข/ค/ง แต่ละตัว
ASCENDING_MAX = 0.60               # ข้อที่ตัวเลือกเรียงน้อยไปมาก ห้ามเกินสัดส่วนนี้
LEVEL_DRIFT = 0.20                 # จำนวนข้อรายระดับ เพี้ยนจากพิมพ์เขียวได้ไม่เกินนี้
FONT_TOL = 0.01                    # ratio ต้องอยู่ในช่วง 1.00 ± ค่านี้

# ตรวจเฉพาะข้างในบล็อกโค้ดกับ \code{} — คำอย่าง "for" ในข้อความอังกฤษไม่ใช่โค้ด
OUT_OF_SCOPE = r'\b(def|for|range|import|lambda|return)\b|\.(split|append|upper|lower)\('
CODE_BLOCK = re.compile(r'\\begin\{pycode\}(.*?)\\end\{pycode\}|\\code\{([^{}]*)\}',
                        re.S)


class Stop(Exception):
    """precondition ไม่ครบ — ไม่ใช่ผลการตรวจ แต่คือตรวจไม่ได้"""


def need(path):
    if not Path(path).exists():
        raise Stop(f'ไม่มีไฟล์ {path}')
    return Path(path)


def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.returncode, (p.stdout + p.stderr).strip()


# ---------------------------------------------------------------- การตรวจแต่ละข้อ

def check_verify(ctx):
    code, out = run([sys.executable, str(ctx['verify'])])
    if code != 0:
        return False, out.splitlines()[-1] if out else f'exit {code}'
    vo = json.loads(ctx['verify_out'].read_text(encoding='utf-8'))
    if vo['part'] != ctx['part'] or vo['set'] != ctx['set']:
        return False, (f'verify_out.json เป็นของ {vo["part"]}-set{vo["set"]} '
                       f'ไม่ใช่ชุดที่กำลังตรวจ')
    missing = [n for n in ctx['bp_by_n'] if str(n) not in vo['answers']]
    if missing:
        return False, f'ไม่มีคำตอบของข้อ {missing}'
    ctx['verify_data'] = vo
    return True, f'{len(vo["answers"])} ข้อมีคำตอบครบ'


def check_distractor_clash(ctx):
    vo = ctx['verify_data']
    bad = []
    for n, right in vo['answers'].items():
        for label, value in vo['distractors'].get(n, {}).items():
            if value == right:
                bad.append(f'ข้อ {n} "{label}"={value}')
    if bad:
        return False, 'ตัวลวงเท่ากับคำตอบถูก: ' + ', '.join(bad)
    total = sum(len(d) for d in vo['distractors'].values())
    return True, f'ตัวลวง {total} ตัว ไม่มีตัวไหนซ้ำคำตอบถูก'


def check_choices_from_D(ctx):
    """ตัวเลือกที่ไม่ใช่คำตอบถูก ต้องเป็นค่าที่คำนวณไว้ใน D[] ไม่ใช่ตัวเลขที่แต่งขึ้น"""
    vo = ctx['verify_data']
    bad, skipped = [], 0
    for i, item in enumerate(ctx['items'], start=1):
        if item['kind'] != 'mcq':
            continue
        want = {tuple(cak.nums(str(v)))
                for v in vo['distractors'].get(str(i), {}).values()}
        want.add(tuple(cak.nums(str(vo['answers'][str(i)]))))
        got = [tuple(cak.nums(c)) for c in item['choices']]
        if any(not g for g in got) or not all(want):
            skipped += 1          # ตัวเลือกเป็นข้อความล้วน เทียบด้วยตัวเลขไม่ได้
            continue
        stray = [c for c, g in zip(item['choices'], got) if g not in want]
        if stray:
            bad.append(f'ข้อ {i}: {stray}')
    if bad:
        return False, 'ตัวเลือกที่ไม่มีที่มาจาก D[]: ' + ' | '.join(bad)
    note = f' (ข้ามข้อความล้วน {skipped} ข้อ)' if skipped else ''
    return True, f'ตัวเลือกทุกตัวมีที่มาจาก D[]{note}'


def check_answer_key(ctx):
    code, out = run([sys.executable, str(SCRIPTS / 'check_answer_key.py'),
                     str(ctx['exam_tex']), str(ctx['answer_tex'])])
    if code != 0:
        return False, out.splitlines()[-1] if out else f'exit {code}'
    return True, 'ตารางเฉลยตรงกับตัวเลือกจริง'


def check_distribution(ctx):
    dist = Counter(t for t in ctx['table'] if t in cak.LETTERS)
    total = sum(dist.values())
    if not total:
        return True, 'ไม่มีข้อปรนัย ข้ามการตรวจ'
    parts = ' '.join(f'{L}={dist.get(L, 0)}' for L in cak.LETTERS)
    off = [L for L in cak.LETTERS
           if not (DIST_LO <= dist.get(L, 0) / total <= DIST_HI)]
    if off:
        return False, f'{parts} — {"/".join(off)} หลุดช่วง {DIST_LO:.0%}-{DIST_HI:.0%}'
    return True, parts


def check_ascending(ctx):
    mcq = [it for it in ctx['items'] if it['kind'] == 'mcq']
    if not mcq:
        return True, 'ไม่มีข้อปรนัย ข้ามการตรวจ'
    asc = 0
    for it in mcq:
        vals = [Fraction(cak.nums(c)[0]) if cak.nums(c) else None
                for c in it['choices']]
        if None in vals:
            continue
        if all(a < b for a, b in zip(vals, vals[1:])):
            asc += 1
    ratio = asc / len(mcq)
    msg = f'เรียงน้อยไปมาก {asc}/{len(mcq)} ข้อ ({ratio:.0%})'
    if ratio > ASCENDING_MAX:
        return False, msg + f' เกิน {ASCENDING_MAX:.0%} — เดาตำแหน่งคำตอบได้'
    return True, msg


def check_levels(ctx):
    plan = Counter(q['level'] for q in ctx['bp_by_n'].values())
    real = Counter(v['level'] for v in ctx['ideas'].values())
    n = len(ctx['bp_by_n'])
    off = []
    for lv in sorted(set(plan) | set(real)):
        if abs(real.get(lv, 0) - plan.get(lv, 0)) / n > LEVEL_DRIFT:
            off.append(f'L{lv} วางแผน {plan.get(lv, 0)} ได้จริง {real.get(lv, 0)}')
    shape = ' '.join(f'L{lv}={real.get(lv, 0)}' for lv in range(1, 6))
    if off:
        return False, f'{shape} — เพี้ยนเกิน {LEVEL_DRIFT:.0%}: ' + ', '.join(off)
    return True, shape


def check_font(ctx):
    if not REAL_EXAM.exists():
        raise Stop(f'ไม่มีข้อสอบจริงไว้เทียบขนาดฟอนต์: {REAL_EXAM}')
    code, out = run([sys.executable, str(SCRIPTS / 'measure_font_size.py'),
                     str(REAL_EXAM), str(ctx['exam_pdf'])])
    m = re.search(r'MEDIAN RATIO \(เรา/จริง\) = ([\d.]+)', out)
    if code != 0 or not m:
        return False, out.splitlines()[-1] if out else f'exit {code}'
    ratio = float(m.group(1))
    if abs(ratio - 1) > FONT_TOL:
        return False, f'ratio = {ratio:.4f} ห่างจาก 1.00 เกิน {FONT_TOL}'
    return True, f'ratio = {ratio:.4f}'


def check_log(ctx):
    hits = [l for l in ctx['log'].splitlines() if l.startswith('!')]
    if hits:
        return False, f'{len(hits)} error ใน log: {hits[0][:70]}'
    return True, 'ไม่มี ^! ใน log'


def check_scope(ctx):
    if ctx['part'] not in ('comp', 'both'):
        return True, 'ไม่ใช่พาร์ทคอม ข้ามการตรวจ'
    src = ctx['exam_tex'].read_text(encoding='utf-8')
    code = ' '.join(m.group(1) or m.group(2) for m in CODE_BLOCK.finditer(src))
    if not code.strip():
        raise Stop('พาร์ทคอมแต่ไม่มีบล็อก pycode หรือ \\code{} เลย — ตรวจขอบเขตไม่ได้')
    hits = sorted({m.group(0) for m in re.finditer(OUT_OF_SCOPE, code)})
    if hits:
        return False, f'พบไวยากรณ์นอกขอบเขตในโค้ด: {hits}'
    return True, f'โค้ด {len(code.split())} โทเคน อยู่ในขอบเขตทั้งหมด'


def check_set_free(ctx):
    """อัปขึ้น Drive แล้วจะไปทับไฟล์ของชุดอื่นไหม

    โฟลเดอร์ในเครื่องไม่ใช่บันทึกที่ครบ เคยเกิดขึ้นจริงว่าในเครื่องมีพาร์ทคอมแค่ชุดที่ 2
    แต่บน Drive มี 1-4 ครบ พอตั้งเลขจากที่เห็นในเครื่องจึงได้ 3 ซึ่งชนของจริง
    และ `rclone copy` เขียนทับให้เงียบ ๆ โดยไม่เตือน

    ถ้าชื่อไฟล์ปลายทางมีอยู่แล้วแต่ **ขนาดตรงกับของเราเป๊ะ** แปลว่าเป็นไฟล์ที่เราอัปไปเอง
    (รัน preflight ซ้ำหลังส่งมอบ) ไม่ใช่การทับงานคนอื่น จึงผ่านได้
    """
    import next_set as ns          # ใช้กติกาตั้งชื่อไฟล์ชุดเดียวกัน ไม่เขียนซ้ำ
    if not ns.RCLONE.exists():
        raise Stop(f'ไม่มี rclone ที่ {ns.RCLONE} — ตรวจไม่ได้ว่าจะทับของบน Drive ไหม')
    target = (f'ข้อสอบเทียม_สอวนคอมพิวเตอร์_'
              f'{ns.TAG[ctx["part"]]}{ctx["set"]}.pdf')
    # rclone เขียน NOTICE ลง stderr — ต้องอ่านเฉพาะ stdout ไม่งั้น JSON พัง
    proc = subprocess.run([str(ns.RCLONE), 'lsjson',
                           f'{ns.REMOTE}/{ns.FOLDER[ctx["part"]]}'],
                          capture_output=True, text=True)
    if proc.returncode != 0:
        raise Stop('เรียก Drive ไม่ได้ จึงตรวจไม่ได้ว่าเลขชุดนี้ทับของเดิมไหม')
    try:
        listing = json.loads(proc.stdout)
    except json.JSONDecodeError:
        raise Stop('อ่านรายการไฟล์บน Drive ไม่ได้')

    hit = next((f for f in listing if f['Name'] == target), None)
    if hit is None:
        return True, f'ชุดที่ {ctx["set"]} ยังไม่มีบน Drive'
    mine = ctx['exam_pdf'].stat().st_size
    if hit['Size'] == mine:
        return True, f'ชุดที่ {ctx["set"]} บน Drive คือไฟล์เดียวกับของเรา (อัปแล้ว)'
    return False, (f'ชุดที่ {ctx["set"]} มีอยู่บน Drive แล้วและเป็นคนละไฟล์ '
                   f'({hit["Size"]} ไบต์ ของเรา {mine}) — อัปแล้วจะทับของเดิมหาย '
                   f'เปลี่ยนเลขชุดด้วย next_set.py')


def check_index(ctx):
    code, out = run([sys.executable, str(SCRIPTS / 'exam_index.py'), 'check',
                     ctx['part'], str(ctx['set']), '--ideas', str(ctx['ideas_path'])])
    if code != 0:
        first = [l for l in out.splitlines() if 'ซ้ำ' in l or 'exam_index' in l]
        return False, first[0] if first else out.splitlines()[-1]
    return True, 'ไม่มีไอเดียซ้ำกับชุดก่อนหน้า'


CHECKS = [
    ('verify.py รันผ่าน ทุกข้อมีคำตอบ', check_verify),
    ('ตัวลวงไม่มีตัวไหนซ้ำคำตอบถูก', check_distractor_clash),
    ('ตัวเลือกทุกตัวมีที่มาจาก D[]', check_choices_from_D),
    ('ตารางเฉลยตรงตัวเลือกจริง', check_answer_key),
    ('การกระจาย ก/ข/ค/ง', check_distribution),
    ('ตัวเลือกไม่ได้เรียงน้อยไปมาก', check_ascending),
    ('จำนวนข้อรายระดับเทียบพิมพ์เขียว', check_levels),
    ('ขนาดฟอนต์เทียบข้อสอบจริง', check_font),
    ('ไม่มี ^! ใน log', check_log),
    ('ไวยากรณ์อยู่ในขอบเขตพาร์ทคอม', check_scope),
    ('ไอเดียไม่ซ้ำกับ index.jsonl', check_index),
    ('เลขชุดไม่ทับของบน Drive', check_set_free),
]


# ---------------------------------------------------------------- หน้าที่ต้องดูด้วยตา

RISKY = {
    r'\chstack': 'ตัวเลือกยาว เสี่ยงทับกัน',
    r'\chtwo': 'ตัวเลือกยาวปานกลาง',
    'pycode': 'บล็อกโค้ด เสี่ยงการเยื้องเพี้ยน',
    'tikzpicture': 'รูปวาด',
}


def risky_pages(pdf, tex):
    """หาหน้าที่ควรเปิดดูด้วยตา จากคำสั่งที่เสี่ยง + หน้าแรกและหน้าสุดท้าย

    ไม่ใช่ render ทุกหน้า — ชุด 50 ข้อ + เฉลย 40 หน้าคือการอ่านภาพ 50+ ภาพเข้า context
    ซึ่งแพงที่สุดในไปป์ไลน์ทั้งหมด และแพงโดยไม่ได้อะไรเพิ่ม เพราะหน้าที่เป็นข้อความล้วน
    ไม่เคยพัง
    """
    try:
        import pymupdf
    except ImportError:
        raise Stop('ต้องมี PyMuPDF — python3 -m pip install pymupdf')
    doc = pymupdf.open(pdf)
    pages = [page.get_text() for page in doc]
    last = len(pages)
    doc.close()

    src = tex.read_text(encoding='utf-8')
    items = re.split(r'\n\\item ', src)[1:]
    flagged = {}
    for i, body in enumerate(items, start=1):
        for token, why in RISKY.items():
            if token in body:
                flagged.setdefault(i, set()).add(why)

    # หาว่าข้อที่ flag อยู่หน้าไหน โดยดูเลขข้อที่ขึ้นต้นบรรทัดในแต่ละหน้า
    where = {}
    for pageno, text in enumerate(pages, start=1):
        for m in re.finditer(r'^\s*(\d{1,3})\.\s', text, re.M):
            where.setdefault(int(m.group(1)), pageno)

    out_pages = {1: {'หน้าปก'}, last: {'หน้าสุดท้าย'}}
    for q, whys in flagged.items():
        pageno = where.get(q)
        if pageno:
            out_pages.setdefault(pageno, set()).update(f'ข้อ {q}: {w}' for w in whys)
    return dict(sorted(out_pages.items())), last


# ---------------------------------------------------------------- main

def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(2)
    part, setno = sys.argv[1], int(sys.argv[2])

    try:
        ctx = {'part': part, 'set': setno}
        ctx['verify'] = need('verify.py')
        ctx['verify_out'] = need('verify_out.json')
        ctx['ideas_path'] = need('ideas.json')
        ctx['exam_tex'] = need(f'exam{setno}.tex')
        ctx['exam_pdf'] = need(f'exam{setno}.pdf')
        ctx['answer_tex'] = need(f'answer{setno}.tex')
        ctx['log'] = need(f'exam{setno}.log').read_text(encoding='utf-8', errors='replace')

        bp_path = BLUEPRINT_DIR / f'{part}-set{setno}.json'
        if not bp_path.exists():
            raise Stop(f'ไม่มีพิมพ์เขียว {bp_path} — สร้างด้วย exam_blueprint.py --json')
        ctx['bp_by_n'] = {q['n']: q
                          for q in json.loads(bp_path.read_text(encoding='utf-8'))['questions']}
        ctx['ideas'] = {int(k): v for k, v in
                        json.loads(ctx['ideas_path'].read_text(encoding='utf-8')).items()}
        ctx['items'] = cak.parse_exam(str(ctx['exam_tex']))
        ctx['table'] = cak.parse_key_table(ctx['answer_tex'].read_text(encoding='utf-8'))
    except Stop as e:
        print(f'ตรวจไม่ได้: {e}')
        sys.exit(2)

    print(f'preflight {part}-set{setno} | {len(ctx["bp_by_n"])} ข้อ')
    print('-' * 72)
    for name, fn in CHECKS:
        try:
            ok, detail = fn(ctx)
        except Stop as e:
            print(f'ตรวจไม่ได้: {e}')
            sys.exit(2)
        print(f'{"PASS" if ok else "FAIL"}  {name:<34} {detail}')
        if not ok:
            print('-' * 72)
            print('หยุดที่ FAIL แรก — แก้แล้วรันใหม่')
            sys.exit(1)

    print('-' * 72)
    try:
        pages, total = risky_pages(ctx['exam_pdf'], ctx['exam_tex'])
    except Stop as e:
        print(f'ตรวจไม่ได้: {e}')
        sys.exit(2)
    print(f'ผ่านทุกข้อที่เครื่องตรวจได้ ({len(CHECKS)} รายการ)')
    print(f'\nหน้าที่ต้องเปิดดูด้วยตา {len(pages)}/{total} หน้า '
          f'— ห้าม render หน้าอื่นโดยไม่มีเหตุผล')
    for pageno, whys in pages.items():
        print(f'  หน้า {pageno}: ' + ', '.join(sorted(whys)))
    cmd = ' '.join(str(n) for n in pages)
    print(f'\n  python3 {SCRIPTS / "render_pages.py"} {ctx["exam_pdf"]} {cmd}')


if __name__ == '__main__':
    main()
