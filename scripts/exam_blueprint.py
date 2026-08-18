#!/usr/bin/env python3
"""แปลง "สเปกข้อสอบ" ที่ผู้ใช้สั่ง ให้เป็นพิมพ์เขียวรายข้อ ก่อนลงมือเขียน .tex

usage:
  python3 exam_blueprint.py --part comp --format mixed --difficulty hard \\
          --focus loop,algocount --count 30 --set 2

  python3 exam_blueprint.py --part math --difficulty standard --count 50 --set 8
  python3 exam_blueprint.py --list                 # ดูรหัสหัวข้อ/ระดับ/พรีเซ็ตทั้งหมด

ผลลัพธ์คือตาราง "ข้อที่ / หัวข้อ / ระดับความยาก / รูปแบบ" + โควตาที่ต้องคุม
+ ชื่อไฟล์และข้อความปกที่ต้องใช้ เอาไปวางเป็นคอมเมนต์หัวไฟล์ verify.py ได้เลย

สคริปต์นี้ไม่ได้ออกโจทย์ให้ — มันล็อกสัดส่วนไว้ก่อน เพื่อไม่ให้เขียนไปเรื่อย ๆ
แล้วได้ข้อง่ายกระจุกหรือหัวข้อซ้ำ
"""
import argparse
import random
import sys

# ---------------------------------------------------------------- หัวข้อ

# code -> (ชื่อไทย, น้ำหนักมาตรฐาน, ระดับที่ออกได้)
MATH_TOPICS = {
    'numtheory': ('ทฤษฎีจำนวน มอดุลาร์ ตัวหาร การหารลงตัว', 12, (2, 5)),
    'realnum':   ('จำนวนจริง กรณฑ์ เลขยกกำลัง สัดส่วน', 6, (1, 4)),
    'func':      ('ฟังก์ชัน อินเวอร์ส ฟังก์ชันประกอบ พาราโบลา', 8, (2, 5)),
    'equation':  ('สมการ อสมการ ค่าสัมบูรณ์ พหุนาม', 8, (1, 4)),
    'set':       ('เซต เพาเวอร์เซต ผลคูณคาร์ทีเซียน เพิ่มเข้า-ตัดออก', 5, (2, 4)),
    'logic':     ('ตรรกศาสตร์ ตารางค่าความจริง การอ้างเหตุผล คนโกหก', 5, (2, 5)),
    'geometry':  ('เรขาคณิต สามเหลี่ยมคล้าย วงกลม พื้นที่ พิกัด', 10, (2, 5)),
    'counting':  ('การนับ เรียงสับเปลี่ยน จัดหมู่ รังนกพิราบ', 10, (2, 5)),
    'sequence':  ('ลำดับเลขคณิต/เรขาคณิต ฟีโบนักชี ความสัมพันธ์เวียนเกิด', 8, (2, 5)),
    'wordprob':  ('โจทย์ปัญหา งาน อัตราเร็ว ผสมสาร', 6, (1, 4)),
}

COMP_TOPICS = {
    'pyexpr':    ('นิพจน์ไพธอน ลำดับดำเนินการ // % ** ชนิดข้อมูล', 10, (1, 3)),
    'pycond':    ('เงื่อนไข if ซ้อน and/or/not นิพจน์ตรรกะสมมูล', 10, (2, 4)),
    'pyloop':    ('วนซ้ำ while ไล่ค่าตัวแปร เงื่อนไขหยุด', 14, (2, 4)),
    'pymix':     ('if+while ผสม ตัวไม่แปรผัน พิสูจน์ว่าหยุด/ไม่หยุด', 12, (3, 5)),
    'algotrace': ('ทำตามขั้นตอนวิธีที่โจทย์ให้ หาผลลัพธ์จากอินพุต', 14, (2, 4)),
    'algocount': ('นับจำนวนครั้งที่คำสั่ง/การเปรียบเทียบถูกทำงาน', 12, (3, 5)),
    'algomod':   ('เปลี่ยนขั้นตอนบางจุด แล้ววิเคราะห์ว่าผลลัพธ์เปลี่ยนอย่างไร', 10, (3, 5)),
    'simulate':  ('จำลองสถานการณ์ตามกฎที่ให้ (คิว ทรัพยากร เส้นทาง)', 10, (3, 5)),
    'greedy':    ('เลือกที่ดีที่สุดทีละขั้น ครอบคลุมช่วง จับคู่ ค่าสุดขีด', 8, (3, 5)),
}

# ---------------------------------------------------------------- ความยาก

LEVELS = {
    1: ('ง่ายมาก', 'แทนค่า/อ่านตรง ๆ 1 ขั้น จบใน 1 นาที'),
    2: ('ง่าย', 'ขั้นตอนกลไกมาตรฐาน 2-3 ขั้น จบใน 1-2 นาที'),
    3: ('กลาง', 'ต้องมีข้อสังเกต 1 อย่างก่อน แล้วตามด้วย 2-3 ขั้น 2-4 นาที'),
    4: ('ยาก', 'ต้องมีไอเดียชี้ขาด + แบ่งกรณี/ตัดกรณีทิ้ง 4-7 นาที'),
    5: ('ยากมาก', 'ไอเดียชี้ขาด 2 ชั้น หรือต้องอธิบายว่าดีกว่านี้ไม่ได้ 7-12 นาที'),
}

# preset -> สัดส่วน % ของระดับ 1..5
DIFF_PRESETS = {
    'easy':     {1: 20, 2: 40, 3: 30, 4: 10, 5: 0},
    'standard': {1: 10, 2: 30, 3: 35, 4: 20, 5: 5},   # เทียบข้อสอบจริงปี 67-68
    'hard':     {1: 0,  2: 15, 3: 35, 4: 35, 5: 15},
    'brutal':   {1: 0,  2: 5,  3: 25, 4: 40, 5: 30},
}
DIFF_ALIAS = {
    'ง่าย': 'easy', 'มาตรฐาน': 'standard', 'ปกติ': 'standard', 'จริง': 'standard',
    'ยาก': 'hard', 'โหด': 'brutal', 'normal': 'standard', 'real': 'standard',
}

# นาทีต่อข้อโดยประมาณ ใช้ประเมินว่าเวลาสอบพอไหม
MINUTES = {1: 1.0, 2: 1.8, 3: 3.0, 4: 5.5, 5: 9.0}

# ---------------------------------------------------------------- พรีเซ็ตชุดข้อสอบจริง

# ปีจริง -> (คำอธิบาย, [(ชื่อตอน, part, format, จำนวนข้อ, คะแนนต่อข้อ)])
YEAR_PRESETS = {
    '68': ('ปี 68 — โครงล่าสุด ใช้เป็นค่าปริยาย', [
        ('ตอนที่ 1 คณิตศาสตร์', 'math', 'mcq', 30, 1),
        ('ตอนที่ 2 วิทยาการคำนวณ', 'comp', 'mcq', 25, 1),
        ('ตอนที่ 3 วิทยาการคำนวณ เติมคำตอบ', 'comp', 'fill', 5, 2),
    ]),
    '67': ('ปี 67 — ฉบับยาว 80 ข้อ', [
        ('ตอนที่ 1.1 คณิตศาสตร์', 'math', 'mcq', 40, 1),
        ('ตอนที่ 1.2 วิทยาการคำนวณ', 'comp', 'mcq', 34, 1),
        ('ตอนที่ 2 วิทยาการคำนวณ เติมคำตอบ', 'comp', 'fill', 6, 2),
    ]),
    '66': ('ปี 66 — ปรนัยล้วน 100 ข้อ', [
        ('ตอนที่ 1 คณิตศาสตร์', 'math', 'mcq', 60, 1),
        ('ตอนที่ 2 กระบวนการคิด', 'comp', 'mcq', 40, 1),
    ]),
}

PART_NAME = {'math': 'คณิตศาสตร์', 'comp': 'วิทยาการคำนวณ', 'both': 'คณิตศาสตร์+วิทยาการคำนวณ'}
FORMAT_NAME = {'mcq': 'ปรนัย 4 ตัวเลือก', 'fill': 'อัตนัย เติมคำตอบ',
               'mixed': 'ปรนัย + อัตนัย'}
PART_ALIAS = {'คณิต': 'math', 'คณิตศาสตร์': 'math', 'math': 'math',
              'คอม': 'comp', 'คอมพิวเตอร์': 'comp', 'วิทยาการคำนวณ': 'comp',
              'comp': 'comp', 'cs': 'comp',
              'ผสม': 'both', 'ทั้งสอง': 'both', 'both': 'both', 'full': 'both'}
FORMAT_ALIAS = {'ปรนัย': 'mcq', 'mcq': 'mcq', 'choice': 'mcq',
                'อัตนัย': 'fill', 'เติมคำตอบ': 'fill', 'fill': 'fill',
                'ผสม': 'mixed', 'mixed': 'mixed', 'both': 'mixed'}


def alias(value, table, what):
    key = (value or '').strip().lower()
    if key in table:
        return table[key]
    if value in table:
        return table[value]
    sys.exit(f'ไม่รู้จัก{what} "{value}" — ใช้ได้: {", ".join(sorted(set(table.values())))}')


def spread(count, percent):
    """แจกจำนวนข้อตาม % ให้ผลรวมเท่ากับ count พอดี (largest remainder)"""
    raw = {k: count * v / 100 for k, v in percent.items()}
    out = {k: int(v) for k, v in raw.items()}
    left = count - sum(out.values())
    for k, _ in sorted(raw.items(), key=lambda kv: kv[1] - int(kv[1]), reverse=True):
        if left <= 0:
            break
        out[k] += 1
        left -= 1
    return out


def weighted_topics(pool, count, focus, rng):
    """เลือกหัวข้อให้ครบ count ข้อ โดยดันหัวข้อใน focus ขึ้นเป็น ~55% ของชุด"""
    weights = {k: v[1] for k, v in pool.items()}
    if focus:
        total = sum(weights.values())
        for k in focus:
            weights[k] = total * 0.55 / len(focus)
    keys = list(weights)
    picks = rng.choices(keys, weights=[weights[k] for k in keys], k=count)
    # การันตีว่าหัวข้อ focus โผล่จริง และไม่มีหัวข้อไหนกินเกินครึ่งชุดโดยไม่ได้สั่ง
    for k in focus:
        if k not in picks:
            picks[rng.randrange(count)] = k
    return picks


def fit_level(topic_range, want):
    """ดันระดับที่สุ่มได้ให้อยู่ในช่วงที่หัวข้อนั้นออกได้จริง"""
    lo, hi = topic_range
    return max(lo, min(hi, want))


def build_section(name, part, fmt, count, points, diff, focus, start, rng):
    pool = MATH_TOPICS if part == 'math' else COMP_TOPICS
    focus_here = [f for f in focus if f in pool]
    topics = weighted_topics(pool, count, focus_here, rng)

    levels = []
    for lv, n in sorted(spread(count, DIFF_PRESETS[diff]).items()):
        levels += [lv] * n
    rng.shuffle(levels)
    # อัตนัยไม่ควรง่ายกว่าระดับ 3 เพราะได้ข้อละ 2 คะแนน
    if fmt == 'fill':
        levels = [max(3, lv) for lv in levels]

    rows = []
    for i in range(count):
        lv = fit_level(pool[topics[i]][2], levels[i])
        rows.append({'no': start + i, 'topic': topics[i], 'level': lv,
                     'format': fmt, 'points': points, 'section': name})
    # เรียงให้ต้นตอนง่ายกว่าท้ายตอน (ข้อสอบจริงไล่ระดับแบบนี้) แต่ไม่เรียงเป๊ะ
    rows.sort(key=lambda r: r['level'] + rng.random() * 1.2)
    for i, r in enumerate(rows):
        r['no'] = start + i
    return rows


def print_plan(rows, part, args):
    pools = {'math': MATH_TOPICS, 'comp': COMP_TOPICS}
    print('=' * 78)
    sec = None
    for r in rows:
        if r['section'] != sec:
            sec = r['section']
            print(f"\n## {sec}  ({FORMAT_NAME[r['format']]}, ข้อละ {r['points']} คะแนน)")
            print(f"{'ข้อ':>4}  {'ระดับ':<9} {'รหัสหัวข้อ':<11} หัวข้อ")
        pool = pools['math' if r['topic'] in MATH_TOPICS else 'comp']
        print(f"{r['no']:>4}  L{r['level']} {LEVELS[r['level']][0]:<7} "
              f"{r['topic']:<11} {pool[r['topic']][0]}")

    n = len(rows)
    lv_count = {lv: sum(1 for r in rows if r['level'] == lv) for lv in range(1, 6)}
    minutes = sum(MINUTES[r['level']] for r in rows)
    idea = sum(1 for r in rows if r['level'] >= 3)

    print('\n' + '=' * 78)
    print('โควตาที่ต้องคุม')
    print(f"  รวม {n} ข้อ | " + ' '.join(f'L{lv}={lv_count[lv]}' for lv in range(1, 6)))
    goal = 35 if args.difficulty in ('easy', 'ง่าย') else 50
    mark = 'ok' if idea * 100 // n >= goal else '!'
    print(f"  ข้อที่มีไอเดียชี้ขาด (L3+) = {idea} ข้อ ({idea * 100 // n}%) "
          f"[{mark}] เป้าของระดับนี้ ≥ {goal}%")
    print(f"  เวลาทำโดยประมาณ {minutes:.0f} นาที ({minutes / 60:.1f} ชม.) "
          f"เทียบเวลาสอบจริง 180 นาที")
    if minutes > 180:
        print('  ! เกินเวลาสอบ ลดระดับบางข้อ หรือลดจำนวนข้อ')
    elif minutes < 90:
        print('  ! เหลือเวลาเยอะเกิน เพิ่มข้อ L4-L5 ได้อีก')

    mcq = sum(1 for r in rows if r['format'] == 'mcq')
    if mcq:
        per = mcq // 4
        print(f"  คำตอบปรนัย {mcq} ข้อ → ก/ข/ค/ง ควรได้ตัวละ {per}-{per + 1} ข้อ")
    fill = sum(1 for r in rows if r['format'] == 'fill')
    if fill:
        print(f"  อัตนัย {fill} ข้อ — คำตอบทุกข้อต้องเป็นจำนวนเต็ม 0-9999 เท่านั้น")
    print("  ข้อไล่ค่าซ้ำ ๆ (คาบ/ตารางยาว) ห้ามเกิน 2 ข้อทั้งชุด — นับเองตอนเขียนโจทย์")

    print('\nไฟล์ที่จะได้')
    tag = {'math': 'ชุดที่', 'comp': 'พาร์ทคอมชุดที่', 'both': 'ฉบับเต็มชุดที่'}[part]
    folder = {'math': 'พาร์ทคณิตศาสตร์', 'comp': 'พาร์ทคอมพิวเตอร์',
              'both': 'ฉบับเต็ม'}[part]
    base = f'ข้อสอบเทียม_สอวนคอมพิวเตอร์_{tag}{args.set}'
    print(f'  ~/Downloads/POSN.Computer/ข้อสอบเทียม/{folder}/{base}.pdf')
    print(f'  ~/Downloads/POSN.Computer/ข้อสอบเทียม/{folder}/เฉลย_{base}.pdf')
    print(f'  รหัสชุดวิชาบนปก: 0000{ {"math": "0", "comp": "1", "both": "2"}[part] }'
          f'{args.set:02d}')
    print('=' * 78)


def main():
    p = argparse.ArgumentParser(add_help=True)
    p.add_argument('--part', default='math', help='math | comp | both')
    p.add_argument('--format', default='auto', dest='fmt',
                   help='mcq | fill | mixed | auto (auto: math=mcq, comp=mixed)')
    p.add_argument('--difficulty', default='standard',
                   help='easy | standard | hard | brutal (หรือ ง่าย/มาตรฐาน/ยาก/โหด)')
    p.add_argument('--focus', default='', help='รหัสหัวข้อที่ต้องการเน้น คั่นด้วย ,')
    p.add_argument('--count', type=int, default=0, help='จำนวนข้อรวม (0 = ใช้โครงปีจริง)')
    p.add_argument('--fill-count', type=int, default=0,
                   help='จำนวนข้ออัตนัย เมื่อ format=mixed (ปริยาย 1/6 ของชุด)')
    p.add_argument('--year', default='68', help='โครงตามปีจริง: 68 | 67 | 66')
    p.add_argument('--set', type=int, default=1, help='เลขชุด')
    p.add_argument('--seed', type=int, default=0, help='0 = ใช้เลขชุดเป็น seed')
    p.add_argument('--list', action='store_true', help='แสดงรหัสหัวข้อ/ระดับ/พรีเซ็ต')
    args = p.parse_args()

    if args.list:
        for title, pool in (('หัวข้อคณิตศาสตร์', MATH_TOPICS),
                            ('หัวข้อวิทยาการคำนวณ', COMP_TOPICS)):
            print(f'\n{title}')
            for k, (name, w, rng_) in pool.items():
                print(f'  {k:<11} L{rng_[0]}-L{rng_[1]}  น้ำหนัก {w:>2}  {name}')
        print('\nระดับความยาก')
        for lv, (name, desc) in LEVELS.items():
            print(f'  L{lv} {name:<9} {desc}')
        print('\nพรีเซ็ตความยาก (% ของชุด)')
        for k, v in DIFF_PRESETS.items():
            print(f'  {k:<9} ' + ' '.join(f'L{lv}={v[lv]:>2}%' for lv in range(1, 6)))
        print('\nโครงตามปีจริง')
        for y, (desc, secs) in YEAR_PRESETS.items():
            print(f'  --year {y}  {desc}')
            for name, part, fmt, n, pts in secs:
                print(f'      {name}: {n} ข้อ {FORMAT_NAME[fmt]} ข้อละ {pts} คะแนน')
        return

    part = alias(args.part, PART_ALIAS, 'พาร์ท')
    diff = DIFF_ALIAS.get(args.difficulty, args.difficulty)
    if diff not in DIFF_PRESETS:
        sys.exit(f'ไม่รู้จักระดับความยาก "{args.difficulty}" — '
                 f'ใช้ได้: {", ".join(DIFF_PRESETS)}')
    fmt = args.fmt
    if fmt == 'auto':
        fmt = 'mcq' if part == 'math' else 'mixed'
    else:
        fmt = alias(fmt, FORMAT_ALIAS, 'รูปแบบ')
    focus = [f.strip() for f in args.focus.split(',') if f.strip()]
    known = set(MATH_TOPICS) | set(COMP_TOPICS)
    for f in focus:
        if f not in known:
            sys.exit(f'ไม่รู้จักรหัสหัวข้อ "{f}" — ดูรายการด้วย --list')

    rng = random.Random(args.seed or args.set * 7919)

    print(f'สเปก: พาร์ท {PART_NAME[part]} | รูปแบบ {FORMAT_NAME[fmt]} | '
          f'ความยาก {diff} | เน้น {", ".join(focus) or "ไม่ระบุ"} | ชุดที่ {args.set}')

    rows, no = [], 1
    if part == 'both' and args.count == 0:
        for name, spart, sfmt, n, pts in YEAR_PRESETS[args.year][1]:
            rows += build_section(name, spart, sfmt, n, pts, diff, focus, no, rng)
            no += n
    else:
        count = args.count or (50 if part == 'math' else 30)
        if fmt == 'mixed':
            nfill = args.fill_count or max(1, round(count / 6))
            nmcq = count - nfill
            rows += build_section(f'ตอนที่ 1 {PART_NAME[part]} แบบปรนัย', part, 'mcq',
                                  nmcq, 1, diff, focus, 1, rng)
            rows += build_section(f'ตอนที่ 2 {PART_NAME[part]} แบบเติมคำตอบ', part,
                                  'fill', nfill, 2, diff, focus, nmcq + 1, rng)
        else:
            rows += build_section(f'{PART_NAME[part]} {FORMAT_NAME[fmt]}', part, fmt,
                                  count, 2 if fmt == 'fill' else 1, diff, focus, 1, rng)

    print_plan(rows, part, args)


if __name__ == '__main__':
    main()
