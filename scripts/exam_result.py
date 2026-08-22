#!/usr/bin/env python3
"""บันทึกและสรุปผลสอบของผู้ใช้ — เจ้าของไฟล์ results/<part>-set<N>.json แต่เพียงผู้เดียว

usage:
  exam_result.py score  comp 3 --wrong "3 7 12" --minutes 95
  exam_result.py detail comp 3 --n 7 --error-type wrong-approach --note "..."
  exam_result.py feynman comp 3 --n 12 --gap "..." --gap "..." [--key-suspect]
  exam_result.py weakness
  exam_result.py calibrate

ทำไมต้องเป็นสคริปต์ ไม่ให้โมเดลคิดเลขเอง
  by_topic / by_level / อัตราผิด เป็นการนับล้วน ๆ ที่ผิดแล้วไม่มีใครจับได้
  และเป็นข้อมูลที่ใช้ตัดสินว่าจะออกข้อสอบชุดหน้าเน้นอะไร ถ้านับพลาดคือชี้ผิดทั้งสาย
  หัวข้อกับระดับของแต่ละข้อดึงจากพิมพ์เขียวเสมอ ไม่ถามผู้ใช้ซ้ำ ไม่เดา

  สคริปต์นี้รายงานตัวเลขอย่างเดียว ไม่ตัดสินใจแทนคน ไม่แก้ DIFFICULTY.md
  และไม่รัน exam_blueprint.py ต่อให้เอง
"""
import argparse
import datetime
import json
import sys
from pathlib import Path

POSN_ROOT = Path.home() / 'Documents' / 'POSN.Computer'
BLUEPRINT_DIR = POSN_ROOT / 'blueprints'
RESULT_DIR = POSN_ROOT / 'results'
INDEX_PATH = POSN_ROOT / 'index.jsonl'

# ชุดปิดของประเภทความผิด — คุณเป็นคนตัดสิน ห้ามถามผู้ใช้ว่าเป็นประเภทไหน
ERROR_TYPES = ['misread', 'wrong-approach', 'boundary', 'complexity',
               'implementation', 'knowledge-gap']

MIN_SETS_FOR_TREND = 3      # น้อยกว่านี้ สถิติหลอกได้ง่ายพอ ๆ กับการไล่โจทย์ด้วยตา
MIN_QUESTIONS_TOPIC = 10    # หัวข้อที่ทำมารวมน้อยกว่านี้ ห้ามสรุป
DRIFT = 0.25                # est_min เบี่ยงเกินเท่านี้ถือว่าเอียง


def die(msg):
    sys.exit(f'exam_result: {msg}')


def blueprint_path(part, setno):
    return BLUEPRINT_DIR / f'{part}-set{setno}.json'


def result_path(part, setno):
    return RESULT_DIR / f'{part}-set{setno}.json'


def load_blueprint(part, setno):
    path = blueprint_path(part, setno)
    if not path.exists():
        die(f'ไม่มีพิมพ์เขียว {path}\n'
            f'        ชุดนี้ถูกสร้างโดยไม่ผ่าน --json จึงไม่รู้ว่าข้อไหนหัวข้ออะไรระดับไหน\n'
            f'        สร้างพิมพ์เขียวก่อน แล้วค่อยบันทึกผล — ห้ามถามหัวข้อจากผู้ใช้แทน')
    return json.loads(path.read_text(encoding='utf-8'))


def load_result(part, setno):
    path = result_path(part, setno)
    if not path.exists():
        die(f'ยังไม่มีผลสอบของชุดนี้ ({path}) — รัน `/posn-score {part} {setno}` ก่อน')
    return json.loads(path.read_text(encoding='utf-8'))


def save_result(part, setno, data):
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    result_path(part, setno).write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def all_results():
    if not RESULT_DIR.exists():
        return []
    out = []
    for path in sorted(RESULT_DIR.glob('*.json')):
        out.append(json.loads(path.read_text(encoding='utf-8')))
    return out


# ---------------------------------------------------------------- score

def cmd_score(args):
    bp = load_blueprint(args.part, args.set)
    questions = {q['n']: q for q in bp['questions']}

    path = result_path(args.part, args.set)
    if path.exists():
        die(f'มีผลสอบของชุดนี้อยู่แล้ว: {path}\n'
            f'        ถ้าตั้งใจบันทึกใหม่ ให้ลบไฟล์เดิมเองก่อน')

    wrong = sorted({int(x) for x in args.wrong.replace(',', ' ').split()})
    bad = [n for n in wrong if n not in questions]
    if bad:
        die(f'ข้อ {bad} ไม่มีในชุดนี้ (มี {min(questions)}-{max(questions)})')

    by_topic, by_level = {}, {}
    for n, q in questions.items():
        t = by_topic.setdefault(q['topic'], {'total': 0, 'wrong': 0})
        lv = by_level.setdefault(str(q['level']), {'total': 0, 'wrong': 0})
        t['total'] += 1
        lv['total'] += 1
        if n in wrong:
            t['wrong'] += 1
            lv['wrong'] += 1

    data = {
        'part': args.part,
        'set': args.set,
        'date': datetime.date.today().isoformat(),
        'total_min': args.minutes,
        'est_min_total': round(sum(q['est_min'] for q in bp['questions']), 1),
        'count': len(questions),
        'wrong': wrong,
        'by_topic': dict(sorted(by_topic.items())),
        'by_level': dict(sorted(by_level.items())),
    }
    save_result(args.part, args.set, data)

    n = len(questions)
    print(f'บันทึกแล้ว: {result_path(args.part, args.set)}')
    print(f'ถูก {n - len(wrong)}/{n} ข้อ | ใช้เวลา {args.minutes} นาที '
          f'(ประเมินไว้ {data["est_min_total"]} นาที)')
    print('\nรายหัวข้อ (ผิด/ทั้งหมด)')
    for t, v in data['by_topic'].items():
        print(f'  {t:<11} {v["wrong"]}/{v["total"]}')
    print('รายระดับ (ผิด/ทั้งหมด)')
    for lv, v in data['by_level'].items():
        print(f'  L{lv}  {v["wrong"]}/{v["total"]}')


# ---------------------------------------------------------------- detail / feynman

def cmd_detail(args):
    data = load_result(args.part, args.set)
    if args.error_type not in ERROR_TYPES:
        die(f'error_type "{args.error_type}" ไม่อยู่ในชุดปิด: {", ".join(ERROR_TYPES)}')
    entries = data.setdefault('detail', [])
    if any(e['n'] == args.n for e in entries):
        die(f'ข้อ {args.n} มีบันทึกอยู่แล้วใน detail — ลบของเดิมก่อนถ้าจะเขียนใหม่')
    entries.append({'n': args.n, 'error_type': args.error_type, 'note': args.note})
    entries.sort(key=lambda e: e['n'])
    save_result(args.part, args.set, data)
    print(f'บันทึกข้อ {args.n} → {args.error_type}')


def cmd_feynman(args):
    data = load_result(args.part, args.set)
    entries = data.setdefault('feynman', [])
    if any(e['n'] == args.n for e in entries):
        die(f'ข้อ {args.n} มีบันทึก feynman อยู่แล้ว — ลบของเดิมก่อนถ้าจะเขียนใหม่')
    entries.append({'n': args.n, 'error_type': 'knowledge-gap',
                    'gaps': args.gap, 'answer_key_suspect': args.key_suspect})
    entries.sort(key=lambda e: e['n'])
    save_result(args.part, args.set, data)
    print(f'บันทึก feynman ข้อ {args.n} ({len(args.gap)} จุด)'
          + (' | เฉลยข้อนี้น่าสงสัย' if args.key_suspect else ''))


# ---------------------------------------------------------------- weakness

def load_index():
    if not INDEX_PATH.exists():
        return []
    return [json.loads(l) for l in INDEX_PATH.read_text(encoding='utf-8').splitlines() if l.strip()]


def cmd_weakness(args):
    results = all_results()
    print(f'ผลสอบที่มี {len(results)} ชุด')
    if len(results) < MIN_SETS_FOR_TREND:
        print(f'\nยังสรุปไม่ได้ — ต้องมีอย่างน้อย {MIN_SETS_FOR_TREND} ชุด')
        print('สถิติจากผลไม่กี่ชุดหลอกได้ง่ายพอ ๆ กับการไล่โจทย์ด้วยตา '
              'ทำชุดเพิ่มแล้วบันทึกด้วย /posn-score ก่อน')
        return

    agg = {}
    for r in results:
        for t, v in r['by_topic'].items():
            a = agg.setdefault(t, {'total': 0, 'wrong': 0})
            a['total'] += v['total']
            a['wrong'] += v['wrong']

    print('\nอัตราผิดรายหัวข้อ (เรียงมากไปน้อย)')
    ranked = sorted(agg.items(), key=lambda kv: -kv[1]['wrong'] / kv[1]['total'])
    solid = []
    for t, v in ranked:
        rate = v['wrong'] * 100 // v['total']
        thin = v['total'] < MIN_QUESTIONS_TOPIC
        tag = '  (ข้อมูลน้อย)' if thin else ''
        print(f'  {t:<11} {v["wrong"]}/{v["total"]}  = {rate}%{tag}')
        if not thin:
            solid.append((t, v))

    print(f'\nหัวข้อที่ทำมารวมน้อยกว่า {MIN_QUESTIONS_TOPIC} ข้อ ห้ามสรุป — '
          f'ตัวเลขยังแกว่งเกินกว่าจะบอกอะไรได้')

    if not solid:
        print('ยังไม่มีหัวข้อไหนมีข้อมูลพอจะสรุป')
        return

    print('\nจุดอ่อนอันดับ 1-2 (นับเฉพาะหัวข้อที่ข้อมูลพอ)')
    for t, v in solid[:2]:
        print(f'  {t}  {v["wrong"]}/{v["total"]}')

    # ผิดซ้ำในไอเดียเดียวกัน — ดูจาก variant_of + wrong
    index = load_index()
    wrong_keys = set()
    for r in results:
        for n in r['wrong']:
            wrong_keys.add((r['part'], r['set'], n))
    family = {}
    for e in index:
        key = (e['part'], e['set'], e['n'])
        if key not in wrong_keys:
            continue
        root = e.get('variant_of') or f'{e["part"]}-set{e["set"]}#{e["n"]}'
        family.setdefault(root, []).append(key)
    repeats = {k: v for k, v in family.items() if len(v) > 2}
    if repeats:
        print('\nผิดซ้ำในไอเดียเดียวกันเกิน 2 ครั้ง')
        for root, ks in repeats.items():
            where = ', '.join(f'{p}-set{s}#{n}' for p, s, n in ks)
            print(f'  {root}  ({len(ks)} ครั้ง: {where})')
            print(f'    → /posn-variant {root} --count 3')

    print('\nคำสั่งที่ควรรันต่อ (คุณตัดสินใจเอง สคริปต์ไม่รันให้)')
    focus = ','.join(t for t, _ in solid[:2])
    part = results[-1]['part']
    print(f'  python3 ~/.claude/skills/posn/scripts/exam_blueprint.py \\')
    print(f'      --part {part} --difficulty hard --focus {focus} --count 20 '
          f'--set <เลขถัดไป> --json')


# ---------------------------------------------------------------- calibrate

def cmd_calibrate(args):
    results = all_results()
    if not results:
        die('ยังไม่มีผลสอบสักชุด')
    results.sort(key=lambda r: (r['part'], r['set']))

    print('เวลาจริงเทียบเวลาที่ประเมินไว้')
    drifts = []
    for r in results:
        est = r['est_min_total']
        real = r['total_min']
        d = (real - est) / est if est else 0
        flag = '!' if abs(d) > DRIFT else ' '
        print(f'  {flag} {r["part"]}-set{r["set"]}  จริง {real} / ประเมิน {est} นาที '
              f'({d * 100:+.0f}%)')
        drifts.append(d)

    run, direction = 0, 0
    for d in drifts:
        if abs(d) > DRIFT and (direction == 0 or (d > 0) == (direction > 0)):
            run += 1
            direction = 1 if d > 0 else -1
        elif abs(d) > DRIFT:
            run, direction = 1, 1 if d > 0 else -1
        else:
            run, direction = 0, 0
        if run >= MIN_SETS_FOR_TREND:
            break
    if run >= MIN_SETS_FOR_TREND:
        way = 'ต่ำไป (ของจริงใช้เวลามากกว่า)' if direction > 0 else 'สูงไป (ของจริงเร็วกว่า)'
        print(f'\n! est_min เอียง {way} — เบี่ยงเกิน {DRIFT:.0%} ติดกัน {run} ชุด')
    else:
        print(f'\nest_min ยังไม่เอียง (ไม่มีการเบี่ยงเกิน {DRIFT:.0%} ติดกัน '
              f'{MIN_SETS_FOR_TREND} ชุด)')

    agg = {}
    for r in results:
        for lv, v in r['by_level'].items():
            a = agg.setdefault(int(lv), {'total': 0, 'wrong': 0})
            a['total'] += v['total']
            a['wrong'] += v['wrong']

    print('\nอัตราผิดรายระดับ (ต้องเรียงจากน้อยไปมากตาม L1→L5)')
    rates = []
    for lv in sorted(agg):
        v = agg[lv]
        rate = v['wrong'] / v['total']
        rates.append((lv, rate, v))
        print(f'  L{lv}  {v["wrong"]}/{v["total"]}  = {rate * 100:.0f}%')

    breaks = [(a[0], b[0]) for a, b in zip(rates, rates[1:]) if a[1] > b[1]]
    if breaks:
        pairs = ', '.join(f'L{a} ผิดมากกว่า L{b}' for a, b in breaks)
        print(f'\n! การติดป้ายระดับเพี้ยน: {pairs}')
        print('  ถ้าระบบติดป้ายถูก อัตราผิดต้องเพิ่มตามระดับเสมอ '
              'ที่ไม่เรียงแปลว่าปัญหาอยู่ที่การจัดระดับ ไม่ใช่ผู้ใช้อ่อนระดับนั้น')
    else:
        print('\nอัตราผิดเรียงตามระดับถูกต้อง — การติดป้ายระดับใช้ได้')
    print('\n(รายงานอย่างเดียว ไม่แก้ DIFFICULTY.md ให้)')


# ---------------------------------------------------------------- cli

def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest='cmd', required=True)

    def add_set_args(sp):
        sp.add_argument('part', choices=['math', 'comp', 'both'])
        sp.add_argument('set', type=int)

    sp = sub.add_parser('score', help='บันทึกผลสอบหนึ่งชุด')
    add_set_args(sp)
    sp.add_argument('--wrong', required=True, help='เลขข้อที่ผิด คั่นด้วยเว้นวรรค')
    sp.add_argument('--minutes', type=int, required=True, help='เวลาที่ใช้จริง (นาที)')
    sp.set_defaults(func=cmd_score)

    sp = sub.add_parser('detail', help='บันทึกสาเหตุที่ผิดของข้อหนึ่ง')
    add_set_args(sp)
    sp.add_argument('--n', type=int, required=True)
    sp.add_argument('--error-type', required=True, choices=ERROR_TYPES)
    sp.add_argument('--note', required=True, help='สรุปสิ่งที่ผู้ใช้เล่า 1-2 ประโยค')
    sp.set_defaults(func=cmd_detail)

    sp = sub.add_parser('feynman', help='บันทึกรูรั่วจากการอธิบายกลับ')
    add_set_args(sp)
    sp.add_argument('--n', type=int, required=True)
    sp.add_argument('--gap', action='append', required=True,
                    help='จุดที่ยังไม่เข้าใจ (ใส่ซ้ำได้หลายจุด)')
    sp.add_argument('--key-suspect', action='store_true',
                    help='อธิบายไม่ได้ทั้งที่อ่านเฉลยแล้ว = เฉลยข้อนี้อาจไม่ผ่านเกณฑ์ตัวเอง')
    sp.set_defaults(func=cmd_feynman)

    sub.add_parser('weakness', help='รวมจุดอ่อนข้ามทุกชุด').set_defaults(func=cmd_weakness)
    sub.add_parser('calibrate', help='ตรวจว่าป้ายความยากตรงความจริงไหม'
                   ).set_defaults(func=cmd_calibrate)

    args = p.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
