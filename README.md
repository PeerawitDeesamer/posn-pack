# POSN Pack — skill สร้างข้อสอบเทียม สอวน. คอมพิวเตอร์ (ค่าย 1)

Claude Code skill สำหรับสร้างข้อสอบเทียม พร้อมเฉลยละเอียด เป็น PDF ด้วย XeLaTeX
ฟอนต์ TH Sarabun New ขนาดตรงกับข้อสอบจริงปี 68 แล้วอัปขึ้น Google Drive

สั่งได้ว่าจะเอา

| เลือก | ตัวเลือก |
|---|---|
| พาร์ท | คณิตศาสตร์ / วิทยาการคำนวณ / ทั้งฉบับตามโครงปี 66-68 |
| รูปแบบ | ปรนัย 4 ตัวเลือก / อัตนัยเติมคำตอบ / ผสมสองตอน |
| ความยาก | `easy` `standard` (เท่าข้อสอบจริง) `hard` `brutal` — เกณฑ์ 5 ระดับที่วัดได้ |
| เรื่องที่เน้น | 19 หัวข้อ เช่น เรขาคณิต การนับ ลูป `while` การนับจำนวนครั้งการทำงาน |
| จำนวนข้อ + เลขชุด | กำหนดเองหรือใช้ค่าปริยาย |

`scripts/exam_blueprint.py` แปลงสเปกพวกนี้เป็นพิมพ์เขียวรายข้อ (ข้อไหนหัวข้ออะไร ระดับไหน)
พร้อมประเมินเวลาทำเทียบเวลาสอบจริง 180 นาที ก่อนเขียนโจทย์ข้อแรก

```bash
python3 scripts/exam_blueprint.py --list          # ดูรหัสหัวข้อ ระดับ พรีเซ็ตทั้งหมด
python3 scripts/exam_blueprint.py --part comp --format mixed \
        --difficulty hard --focus pyloop,algocount --count 30 --set 2
```

repo นี้คือชุดติดตั้ง — ลง skill พร้อม toolchain ทั้งหมดบนเครื่องใหม่ในคำสั่งเดียว

## ติดตั้งบนเครื่องใหม่

### วิธีที่ 1 — สั่ง Claude Code (ง่ายสุด)

วางข้อความนี้ใน Claude Code:

```
ติดตั้ง POSN skill จาก https://github.com/PeerawitDeesamer/posn-pack
git clone แล้วรัน bash install.sh
```

### วิธีที่ 2 — เทอร์มินัล

```bash
git clone https://github.com/PeerawitDeesamer/posn-pack.git
cd posn-pack
bash install.sh
```

### วิธีที่ 3 — บรรทัดเดียว ไม่ต้อง clone

```bash
curl -fsSL https://raw.githubusercontent.com/PeerawitDeesamer/posn-pack/main/install.sh | bash
```

`install.sh` รู้ตัวว่าถูก pipe มาแบบไม่มีไฟล์ข้าง ๆ แล้วดึง tarball ของ repo มาเองก่อนติดตั้ง
ถ้า fork ไปใช้ชื่ออื่น ชี้ repo ใหม่ด้วย `POSN_REPO` ได้ ไม่ต้องแก้ไฟล์:

```bash
POSN_REPO=owner/repo bash <(curl -fsSL https://raw.githubusercontent.com/owner/repo/main/install.sh)
```

รอ ~3-5 นาที (TinyTeX 50 MB + rclone 21 MB) เสร็จแล้วเปิด Claude Code สั่งได้เลย เช่น "สร้างข้อสอบเทียม ชุดที่ 6" หรือ
"ขอพาร์ทคอมชุดที่ 2 แบบยาก เน้นเรื่องลูป" — skill ชื่อ `posn` จะโหลดเอง

## installer ทำอะไรบ้าง

| ขั้น | ทำอะไร |
|---|---|
| 0 | ก๊อป skill ไป `~/.claude/skills/posn` |
| 1 | เช็ค `curl` `python3` `perl` `poppler-utils` |
| 2 | ลง TinyTeX ที่ `~/.TinyTeX` (ตรวจ arch เอง) |
| 3 | `tlmgr install` แพ็กเกจ LaTeX ที่ต้องใช้ (รวม `extsizes` สำหรับ `extarticle` 14pt) |
| 4 | โหลดฟอนต์ TH Sarabun New 4 น้ำหนัก ลง fontconfig **และ** TEXMF tree |
| 5 | ลง rclone ที่ `~/.local/bin/rclone` |
| 6 | สร้าง `~/Downloads/POSN.Computer/` พร้อมโฟลเดอร์แยกตามพาร์ท |
| 7 | คอมไพล์ไฟล์ทดสอบ แล้วเช็คด้วย `pdffonts` ว่าฝังครบทั้ง 4 น้ำหนัก |

- รันซ้ำได้ ข้ามขั้นที่ทำไว้แล้วเอง
- ลงในโฮมทั้งหมด **ไม่ใช้ sudo**
- รองรับ Linux (x86_64 / aarch64) และ macOS (arm64 / x86_64)
- `bash install.sh --check` = ตรวจอย่างเดียว ไม่ติดตั้ง
- `bash install.sh --no-rclone` = ข้ามส่วน Google Drive

ต้องมี `poppler-utils` ระดับระบบ (`apt install poppler-utils` / `brew install poppler`)
ไม่มีก็ยังคอมไพล์ได้ แต่วัดขนาดฟอนต์และดูภาพหน้าไม่ได้

## สองอย่างที่ repo นี้ให้ไม่ได้

1. **ไฟล์ PDF ข้อสอบจริง สอวน. ปี 64-68 และ `เนื้อหาที่ใช้สอบ.pdf`**
   เป็นงานลิขสิทธิ์ของมูลนิธิ สอวน. `.gitignore` กัน `*.pdf` ไว้แล้ว ห้ามอัปขึ้น repo สาธารณะ
   ให้ก๊อปเองจากเครื่องเก่าหรือ Google Drive ไปไว้ที่
   `~/Downloads/POSN.Computer/ไฟล์ข้อสอบ/`
   ไม่มีไฟล์พวกนี้ skill ยังสร้างข้อสอบได้ แต่เทียบขนาดฟอนต์กับของจริงไม่ได้
   และเช็คขอบเขตเนื้อหาไม่ได้

2. **การ authorize Google Drive** ต้องเปิด browser ทำเอง ครั้งเดียว:
   ```bash
   ~/.local/bin/rclone config create gdrive drive scope=drive
   ```
   ทางลัด: ก๊อป `~/.config/rclone/rclone.conf` จากเครื่องเก่ามาวางที่เดิม ใช้ token เดิมได้เลย
   **ไฟล์นั้นมี refresh token — ห้าม commit** (`.gitignore` กันไว้แล้ว)

ก๊อปชุดข้อสอบเทียมที่เคยทำ (`ข้อสอบเทียม/`) มาด้วยจะดี ใช้กันโจทย์ซ้ำกับชุดใหม่

## โครงสร้าง repo

```
SKILL.md          สเปกข้อสอบ, กติกาการออกข้อสอบ+เฉลย, preamble LaTeX, checklist ก่อนส่งมอบ
install.sh        ตัวติดตั้ง/ตรวจ
pack.sh           แพ็ก skill (+PDF ถ้าสั่ง) เป็น tarball ไว้ขนแบบ offline
docs/SPEC.md      แปลคำสั่งผู้ใช้เป็นสเปก ข้อความบนปก รหัสชุดวิชา
docs/DIFFICULTY.md        เกณฑ์ความยาก 5 ระดับ วิธีเพิ่ม/ลดอย่างถูกวิธี
docs/COMPUTER-PART.md     พาร์ทวิทยาการคำนวณ ขอบเขตไพธอน 9 หัวข้อ โครง verify.py
docs/SUBJECTIVE.md        ตอนอัตนัยเติมคำตอบ แม่แบบ LaTeX และการตรวจ
docs/INSTALL.md   ขั้นตอนย้ายเครื่อง + ตารางอาการพังที่เจอบ่อย
docs/SETUP.md     ขั้นตอนติดตั้งแบบทำมือ ถ้า install.sh พัง
docs/DRIVE.md     รายละเอียดการอัป Drive + วิธีที่ลองแล้วใช้ไม่ได้
docs/TROUBLESHOOTING.md   error จริงที่เคยเจอและวิธีแก้
scripts/exam_blueprint.py      สเปก -> พิมพ์เขียวรายข้อ + โควตาที่ต้องคุม
scripts/check_answer_key.py    ตรวจตารางเฉลยกับตัวเลือกจริง (ปรนัย + อัตนัย)
scripts/measure_font_size.py   วัดขนาดฟอนต์เทียบข้อสอบจริง
```

## แก้ skill แล้วอัปกลับ

ต้นฉบับที่ Claude Code ใช้จริงคือ `~/.claude/skills/posn/` ส่วน repo นี้คือชุดแจกจ่าย
แก้ที่ไหนแล้วอย่าลืม sync อีกฝั่ง:

```bash
cd "$HOME/Downloads/Posn Pack"
cp -R ~/.claude/skills/posn/{SKILL.md,docs,scripts} .
git add -A && git commit -m "update skill" && git push
```

**ห้าม `git add -f` ไฟล์ PDF** — `.gitignore` กันไว้เพราะข้อสอบจริงเป็นลิขสิทธิ์มูลนิธิ สอวน.
และ repo นี้ public
