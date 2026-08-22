#!/usr/bin/env python3
"""ตัวปิดท้ายของ verify.py — บังคับว่าตัวลวงทุกตัวถูกคำนวณมา ไม่ใช่แต่งขึ้น

วางไว้บรรทัดสุดท้ายของ verify.py:

    from verify_lib import emit
    emit(R, D, 'comp', 3)

R = {เลขข้อ: คำตอบที่ถูก}          — ทุกข้อต้องมี
D = {เลขข้อ: {"ชื่อความผิด": ค่าที่ได้ถ้าทำผิดแบบนั้น, ...}}

ทำไมต้องมีไฟล์นี้
  กฎเหล็กข้อ 3 บอกว่า "ห้ามเดาคำตอบ" แต่ก่อนหน้านี้ยัง "เดาตัวลวง" อยู่ — คำตอบถูก
  ผ่านสคริปต์ ส่วน ก/ข/ง มาจากการที่โมเดลคิดตัวเลขเอง แล้วเขียนย้อนหลังในเฉลยว่า
  "ข้อนี้น่าจะมาจากคนที่ลืมกรณี x<0" ซึ่งไม่เคยถูกตรวจว่าจริงไหม

  ตัวลวงที่คำนวณจากความผิดที่ระบุชื่อได้ ให้สองอย่างพร้อมกัน: ตัวเลือกที่สมจริง
  (เพราะมีคนทำผิดแบบนั้นจริง) และคำอธิบายในเฉลยที่ถูกต้องโดยอัตโนมัติ
  ถ้าคิดความผิดที่ทำให้ได้ตัวเลขนั้นไม่ออก แปลว่าตัวลวงนั้นไม่สมจริง
  ให้เปลี่ยนตัวลวง ไม่ใช่เปลี่ยนคำอธิบาย

ตรวจ 4 อย่าง แล้วเขียน verify_out.json ให้ preflight.py อ่านต่อ
  1. ทุกข้อในพิมพ์เขียวมีคำตอบใน R
  2. ข้อปรนัยต้องมีตัวลวงใน D ครบ 3 ตัว / ข้ออัตนัยอย่างน้อย 2 ค่า
     (ข้ออัตนัยไม่มีตัวเลือก แต่เฉลยต้องมีส่วน "คำตอบที่มักเขียนผิด" ซึ่งคือของสิ่งเดียวกัน)
  3. ไม่มีตัวลวงตัวไหนเท่ากับคำตอบถูก — เท่าเมื่อไหร่คือข้อนั้นมีคำตอบถูก 2 ตัว
  4. ตัวลวงในข้อเดียวกันห้ามซ้ำกันเอง ไม่งั้นตัวเลือกจริงเหลือ 3 ตัว
"""
import json
from pathlib import Path

POSN_ROOT = Path.home() / 'Documents' / 'POSN.Computer'
BLUEPRINT_DIR = POSN_ROOT / 'blueprints'

OUT_NAME = 'verify_out.json'


class VerifyError(Exception):
    """precondition ไม่ครบ — หยุดทันที ไม่มีทางเลือกสำรอง"""


def _norm(value):
    """เทียบค่าด้วยข้อความที่ normalize แล้ว เพื่อให้ 56 กับ '56' ถือว่าเท่ากัน"""
    return str(value).strip()


def emit(R, D, part, setno, out_path=OUT_NAME):
    bp_path = BLUEPRINT_DIR / f'{part}-set{setno}.json'
    if not bp_path.exists():
        raise VerifyError(
            f'ไม่มีพิมพ์เขียว {bp_path}\n'
            f'สร้างก่อนด้วย exam_blueprint.py --part {part} --set {setno} ... --json')
    bp = json.loads(bp_path.read_text(encoding='utf-8'))
    questions = {q['n']: q for q in bp['questions']}

    problems = []

    missing = sorted(set(questions) - set(R))
    if missing:
        problems.append(f'ข้อ {missing} ไม่มีคำตอบใน R[] — ทุกข้อต้องคำนวณด้วยสคริปต์')
    extra = sorted(set(R) - set(questions))
    if extra:
        problems.append(f'R[] มีข้อ {extra} ที่ไม่มีในพิมพ์เขียว')

    for n in sorted(set(questions) & set(R)):
        fmt = questions[n]['format']
        need = 3 if fmt == 'mcq' else 2
        what = 'ตัวลวง' if fmt == 'mcq' else 'คำตอบที่มักเขียนผิด'
        d = D.get(n)
        if not d:
            problems.append(
                f'ข้อ {n}: ไม่มี D[{n}] — {what}ทุกตัวต้องคำนวณจากความผิดที่ระบุชื่อได้')
            continue
        if fmt == 'mcq' and len(d) != need:
            problems.append(f'ข้อ {n}: ต้องมี{what} {need} ตัว แต่มี {len(d)} ตัว')
        elif fmt != 'mcq' and len(d) < need:
            problems.append(f'ข้อ {n}: ต้องมี{what}อย่างน้อย {need} ค่า แต่มี {len(d)} ค่า')

        right = _norm(R[n])
        seen = {}
        for label, value in d.items():
            if not str(label).strip():
                problems.append(f'ข้อ {n}: มี{what}ที่ไม่ได้ตั้งชื่อความผิด')
            v = _norm(value)
            if v == right:
                problems.append(
                    f'ข้อ {n}: {what} "{label}" = {v} เท่ากับคำตอบถูก '
                    f'→ ข้อนี้มีคำตอบถูก 2 ตัว')
            if v in seen:
                problems.append(
                    f'ข้อ {n}: "{label}" กับ "{seen[v]}" ได้ค่าเดียวกัน ({v}) '
                    f'→ ตัวเลือกจริงเหลือ 3 ตัว')
            seen[v] = label

    if problems:
        raise VerifyError('ตัวลวงยังไม่ผ่าน\n  ' + '\n  '.join(problems))

    data = {
        'part': part,
        'set': setno,
        'answers': {str(n): _norm(R[n]) for n in sorted(questions)},
        'distractors': {str(n): {str(k): _norm(v) for k, v in D[n].items()}
                        for n in sorted(questions)},
    }
    Path(out_path).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n',
                              encoding='utf-8')
    print(f'\nตัวลวงผ่านครบ {len(questions)} ข้อ → {out_path}')
    print('เอา key ของ D[] ไปเขียนส่วน "ทำไมตัวเลือกอื่นผิด" ในเฉลยตรง ๆ '
          'ห้ามเขียนคำอธิบายใหม่ที่ไม่ตรงกับตัวที่คำนวณ')
