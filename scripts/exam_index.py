#!/usr/bin/env python3
"""ดัชนี "ไอเดียชี้ขาด" ของทุกข้อที่เคยออก — ใช้กันโจทย์ซ้ำโดยไม่ต้องเปิด PDF ชุดเก่า

usage:
  python3 exam_index.py check comp 3 --ideas ideas.json   # ซ้ำกับของเก่าไหม (ก่อนเขียน)
  python3 exam_index.py add   comp 3 --ideas ideas.json   # บันทึกเข้าดัชนี (หลังส่งมอบ)
  python3 exam_index.py variants comp-set2#7              # ต้นฉบับนี้ถูกทำ variant ไปกี่ข้อ

ทำไมต้องมีไฟล์นี้
  checklist ข้อ "ไม่มีโจทย์ซ้ำกับชุดก่อนหน้า" เป็นข้อเดียวที่ไม่เคยมีเครื่องมือรองรับ
  ตอนมี 2 ชุดยังไล่ด้วยตาไหว ตอนมี 10 ชุดคือต้องเปิด PDF 10 ไฟล์เข้า context ทุกครั้ง
  จนโมเดลจะเริ่มข้ามแล้วรายงานว่า "ตรวจแล้ว" — ข้อนี้จึงพังก่อนเพื่อนและพังแบบเงียบ ๆ
  ดัชนีนี้ไม่กี่ KB อ่านทั้งไฟล์ได้ในครั้งเดียว

รูปแบบไฟล์ index.jsonl (บรรทัดละข้อ)
  {"part":"comp","set":2,"n":7,"topic":"pyloop","level":4,"idea":"...","variant_of":null}

  topic ดึงจากพิมพ์เขียว blueprints/<part>-set<N>.json ไม่กรอกมือ
  level มาจาก ideas.json เพราะเป็นระดับจริงหลังเขียนเสร็จ ซึ่งอาจไม่ตรงกับที่วางแผนไว้
  ถ้าไม่มีพิมพ์เขียว สคริปต์นี้หยุดทันที ไม่เดาให้

รูปแบบไฟล์ ideas.json ที่ต้องเขียนเอง (คีย์ = เลขข้อ ต้องครบทุกข้อ)
  {
    "1": {"level": 4, "idea": "นับส่วนเติมเต็มแทนการนับตรง"},
    "3": {"level": 4, "idea": "while ลดค่าทีละ 3 ถามจำนวนรอบก่อนติดลบ",
          "variant_of": "comp-set2#7"}
  }

  `level` คือระดับ **จริงหลังเขียนโจทย์เสร็จ** ไม่ใช่ระดับที่พิมพ์เขียวสั่งไว้
  preflight.py เอาสองค่านี้มาเทียบกันเพื่อดูว่าชุดที่เขียนออกมาเพี้ยนจากแผนแค่ไหน
  ถ้ากรอกตามพิมพ์เขียวโดยไม่ประเมินใหม่ การตรวจข้อนั้นจะไร้ความหมาย
"""
import argparse
import difflib
import json
import re
import sys
from pathlib import Path

POSN_ROOT = Path.home() / 'Documents' / 'POSN.Computer'
BLUEPRINT_DIR = POSN_ROOT / 'blueprints'
INDEX_PATH = POSN_ROOT / 'index.jsonl'

# เกินค่านี้ถือว่าเป็นไอเดียเดียวกัน — ตั้งจากการเทียบไอเดียที่เขียนคนละสำนวนแต่เรื่องเดียวกัน
SIMILAR = 0.72
MAX_VARIANTS = 5


def die(msg):
    sys.exit(f'exam_index: {msg}')


def normalize(text):
    """ตัดสิ่งที่ไม่ใช่เนื้อความคิดออก เหลือเฉพาะคำ เพื่อให้เทียบสำนวนต่างกันได้

    ตัวเลขถูกตัดทิ้งด้วย เพราะโจทย์ที่เปลี่ยนแค่ตัวเลขคือโจทย์ซ้ำ ไม่ใช่โจทย์ใหม่
    """
    text = re.sub(r'\d+', '', text)
    text = re.sub(r'[^\w฀-๿]+', ' ', text)
    return ' '.join(text.split())


def similarity(a, b):
    return difflib.SequenceMatcher(None, normalize(a), normalize(b)).ratio()


def load_index():
    if not INDEX_PATH.exists():
        return []
    out = []
    for lineno, line in enumerate(INDEX_PATH.read_text(encoding='utf-8').splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError as e:
            die(f'{INDEX_PATH} บรรทัด {lineno} อ่านไม่ได้: {e}')
    return out


def load_blueprint(part, setno):
    path = BLUEPRINT_DIR / f'{part}-set{setno}.json'
    if not path.exists():
        die(f'ไม่มีพิมพ์เขียว {path}\n'
            f'        สร้างก่อนด้วย: exam_blueprint.py --part {part} --set {setno} ... --json')
    bp = json.loads(path.read_text(encoding='utf-8'))
    return {q['n']: q for q in bp['questions']}


def load_ideas(path, blueprint):
    """อ่าน ideas.json — idea กับ level มาจากไฟล์นี้ topic มาจากพิมพ์เขียว ต้องครบทุกข้อ"""
    path = Path(path)
    if not path.exists():
        die(f'ไม่มี {path} — ทุกข้อต้องเขียนไอเดียชี้ขาดได้เป็นประโยคเดียว')
    raw = json.loads(path.read_text(encoding='utf-8'))
    out = []
    for key, val in raw.items():
        n = int(key)
        if n not in blueprint:
            die(f'ideas.json มีข้อ {n} ซึ่งไม่มีในพิมพ์เขียว')
        if not isinstance(val, dict):
            die(f'ข้อ {n} ต้องเป็น object ที่มี level กับ idea '
                f'เช่น {{"level": 4, "idea": "..."}}')
        idea = val.get('idea', '')
        level = val.get('level')
        variant_of = val.get('variant_of')
        if not str(idea).strip():
            die(f'ข้อ {n} ไม่มีไอเดียชี้ขาด — เขียนเป็นประโยคเดียวให้ได้ก่อน '
                f'ถ้าเขียนไม่ได้แปลว่าข้อนั้นยังไม่มีไอเดีย')
        if level not in (1, 2, 3, 4, 5):
            die(f'ข้อ {n} ต้องระบุ level 1-5 ที่ประเมินใหม่หลังเขียนโจทย์เสร็จ '
                f'(พบ {level!r})')
        out.append({'n': n, 'topic': blueprint[n]['topic'],
                    'level': level, 'idea': str(idea).strip(),
                    'variant_of': variant_of})
    missing = sorted(set(blueprint) - {r['n'] for r in out})
    if missing:
        die(f'ideas.json ขาดข้อ {missing} — ทุกข้อต้องเขียนไอเดียชี้ขาดได้')
    return sorted(out, key=lambda r: r['n'])


def find_duplicates(rows, index, part, setno):
    """คืนรายการ (ข้อของเรา, ข้อที่ซ้ำในดัชนี, คะแนนความเหมือน)"""
    others = [e for e in index if not (e['part'] == part and e['set'] == setno)]
    hits = []
    for r in rows:
        best, score = None, 0.0
        for e in others:
            s = similarity(r['idea'], e['idea'])
            if s > score:
                best, score = e, s
        if best and score >= SIMILAR:
            hits.append((r, best, score))
    return hits


def cmd_check(args):
    blueprint = load_blueprint(args.part, args.set)
    rows = load_ideas(args.ideas, blueprint)
    index = load_index()
    hits = find_duplicates(rows, index, args.part, args.set)

    # variant ที่ชี้ต้นฉบับเดียวกันเกิน 1 ข้อในชุดเดียว = ฝึกไอเดียเดิมกระจุกในชุดเดียว
    seen = {}
    for r in rows:
        if r['variant_of']:
            seen.setdefault(r['variant_of'], []).append(r['n'])
    clashes = {k: v for k, v in seen.items() if len(v) > 1}

    print(f'ดัชนีมี {len(index)} ข้อ | ชุดนี้ {len(rows)} ข้อ | เกณฑ์ความเหมือน {SIMILAR}')
    if hits:
        print(f'\nซ้ำกับของเดิม {len(hits)} ข้อ')
        for r, e, s in hits:
            print(f'  ข้อ {r["n"]} ({s:.2f}) ซ้ำกับ {e["part"]}-set{e["set"]}#{e["n"]}')
            print(f'      ของเรา: {r["idea"]}')
            print(f'      ของเดิม: {e["idea"]}')
    if clashes:
        print('\nvariant ชี้ต้นฉบับเดียวกันหลายข้อในชุดเดียว (อนุญาตได้ข้อเดียว)')
        for src, ns in clashes.items():
            print(f'  {src} ← ข้อ {ns}')
    if hits or clashes:
        sys.exit(1)
    print('ผ่าน: ไม่มีไอเดียซ้ำกับชุดก่อนหน้า')


def cmd_add(args):
    blueprint = load_blueprint(args.part, args.set)
    rows = load_ideas(args.ideas, blueprint)
    index = load_index()

    already = [e for e in index if e['part'] == args.part and e['set'] == args.set]
    if already:
        die(f'ชุด {args.part}-set{args.set} อยู่ในดัชนีแล้ว {len(already)} ข้อ '
            f'— ห้ามบันทึกซ้ำ ถ้าจะแก้ ให้แก้ {INDEX_PATH} เอง')

    hits = find_duplicates(rows, index, args.part, args.set)
    if hits:
        die(f'ยังมีไอเดียซ้ำกับชุดเดิม {len(hits)} ข้อ — รัน `check` ดูรายละเอียดแล้วแก้ก่อน')

    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    with INDEX_PATH.open('a', encoding='utf-8') as f:
        for r in rows:
            line = {'part': args.part, 'set': args.set, 'n': r['n'],
                    'topic': r['topic'], 'level': r['level'], 'idea': r['idea']}
            if r['variant_of']:
                line['variant_of'] = r['variant_of']
            f.write(json.dumps(line, ensure_ascii=False) + '\n')
    print(f'บันทึก {len(rows)} ข้อลง {INDEX_PATH}')


def cmd_variants(args):
    index = load_index()
    kids = [e for e in index if e.get('variant_of') == args.source]
    print(f'{args.source} ถูกทำ variant ไปแล้ว {len(kids)} ข้อ')
    for e in kids:
        print(f'  {e["part"]}-set{e["set"]}#{e["n"]}  {e["idea"]}')
    if len(kids) >= MAX_VARIANTS:
        print(f'\n! เกินเพดาน {MAX_VARIANTS} ข้อ — กำลังฝึกไอเดียเดิมมากเกินไป '
              f'ถามผู้ใช้ก่อนสร้างเพิ่ม')
        sys.exit(1)


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest='cmd', required=True)

    for name, fn, helptext in (('check', cmd_check, 'ตรวจว่าไอเดียซ้ำของเดิมไหม'),
                               ('add', cmd_add, 'บันทึกชุดใหม่เข้าดัชนี')):
        sp = sub.add_parser(name, help=helptext)
        sp.add_argument('part', choices=['math', 'comp', 'both'])
        sp.add_argument('set', type=int)
        sp.add_argument('--ideas', required=True, help='ไฟล์ ideas.json')
        sp.set_defaults(func=fn)

    sp = sub.add_parser('variants', help='นับ variant ของต้นฉบับหนึ่ง')
    sp.add_argument('source', help='เช่น comp-set2#7')
    sp.set_defaults(func=cmd_variants)

    args = p.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
