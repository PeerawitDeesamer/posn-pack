# INSTALL — ย้าย skill ไปเครื่องใหม่

Skill นี้ไม่มีอะไรผูกกับเครื่องเดิมแล้ว ยกเว้น 3 อย่างที่ต้องขนไปเอง:
**ไฟล์ PDF ข้อสอบจริง**, **การ authorize Google Drive**, และ **โฟลเดอร์ปลายทางบน Drive**

## ขั้นที่ 1 — แพ็กจากเครื่องเก่า

```bash
bash ~/.claude/skills/posn/pack.sh --with-pdfs
# → ~/Downloads/posn-skill-YYYYMMDD.tar.gz
```

`--with-pdfs` ใส่ `ไฟล์ข้อสอบ/` (ข้อสอบจริงปี 64-68 + เนื้อหาที่ใช้สอบ) และ `ข้อสอบเทียม/`
(ชุดที่ทำไปแล้ว ใช้กันโจทย์ซ้ำ) เข้าไปด้วย ไฟล์จะใหญ่ ถ้าไม่อยากขน ให้แพ็กเปล่า ๆ
แล้วโหลด PDF จาก Google Drive บนเครื่องใหม่แทน

ถ้าเครื่องเก่าเข้าไม่ได้แล้ว: ก๊อป `~/.claude/skills/posn/` ทั้งโฟลเดอร์ก็พอ

## ขั้นที่ 2 — ติดตั้งบนเครื่องใหม่

```bash
tar xzf posn-skill-*.tar.gz && cd posn-skill
bash skill/install.sh
```

installer ทำให้ทั้งหมดนี้ ข้ามขั้นที่ทำไว้แล้วเอง (รันซ้ำได้ ไม่พัง):

| ขั้น | ทำอะไร |
|---|---|
| 0 | ก๊อป skill ไป `~/.claude/skills/posn` |
| 1 | เช็ค `curl` `python3` `perl` `poppler-utils` |
| 2 | ลง TinyTeX ที่ `~/.TinyTeX` (ตรวจ arch เอง) |
| 3 | `tlmgr install` แพ็กเกจ LaTeX ที่ต้องใช้ (รวม `extsizes`) |
| 4 | โหลดฟอนต์ TH Sarabun New 4 น้ำหนัก ลง **2 ที่** (ดูด้านล่าง) |
| 5 | ลง rclone ที่ `~/.local/bin/rclone` |
| 6 | สร้าง `~/Downloads/POSN.Computer/{ไฟล์ข้อสอบ,ข้อสอบเทียม}` |
| 7 | คอมไพล์ไฟล์ทดสอบ แล้วเช็คด้วย `pdffonts` ว่าฝังครบทั้ง 4 น้ำหนัก |

รองรับ Linux (x86_64 / aarch64) และ macOS (arm64 / x86_64) ลงในโฮมทั้งหมด ไม่ใช้ sudo
ยกเว้น `poppler-utils` ที่ต้องลงระดับระบบ (`apt install poppler-utils` /
`brew install poppler`) — ไม่มีก็ยังคอมไพล์ได้ แต่วัดขนาดฟอนต์และดูภาพหน้าไม่ได้

**ทำไมฟอนต์ต้องลง 2 ที่**

- `~/.local/share/fonts/thsarabunnew/` → fontconfig เห็น (`fc-list`, `pdffonts`, แอปอื่น)
- `TEXMFHOME/fonts/truetype/public/thsarabunnew/` → kpathsea เห็น ทำให้ preamble เขียนแค่
  `\setmainfont{THSarabunNew}[Extension=.ttf, ...]` **ไม่ต้องมี `Path=` ที่เป็น path เต็ม**
  ซึ่งคือจุดเดียวใน skill เดิมที่ผูกกับ `/home/<user>/` ตายตัว

## ขั้นที่ 3 — Google Drive (ต้องทำเอง ครั้งเดียว)

authorize ต้องเปิด browser ทำแทนไม่ได้ พิมพ์ในเทอร์มินัลเครื่องใหม่:

```bash
~/.local/bin/rclone config create gdrive drive scope=drive
~/.local/bin/rclone lsd gdrive:          # ต้องเห็นรายชื่อโฟลเดอร์
```

ทางลัดถ้าเครื่องเก่ายังเข้าได้: ก๊อป `~/.config/rclone/rclone.conf` ไปวางที่เดิมบนเครื่องใหม่
ก็ใช้ token เดิมได้เลย ไม่ต้อง login ใหม่ (**ไฟล์นี้มี refresh token — อย่าใส่ในทาร์บอลที่ส่งต่อ
ให้คนอื่น และอย่า commit ขึ้น git** `pack.sh` จึงไม่แพ็กให้)

### folder ID บน Drive

`docs/DRIVE.md` มี ID ของโฟลเดอร์ `POSN.Computer` เขียนไว้ตายตัว (ใช้ตอนยืนยัน mimeType
ผ่าน MCP) ID นี้ผูกกับบัญชี ถ้าเปลี่ยนบัญชี Google ให้หา ID ใหม่:

```bash
~/.local/bin/rclone lsjson gdrive: --dirs-only | grep -A2 POSN.Computer
```

แล้วแก้ตัวเลขใน `docs/DRIVE.md` และหัวข้อ 8 ของ `SKILL.md` ถ้าใช้บัญชีเดิม ไม่ต้องแก้อะไร
ส่วนคำสั่ง `rclone copy ... gdrive:POSN.Computer` ใช้ชื่อโฟลเดอร์ ไม่ใช่ ID จึงใช้ได้เลย

## ขั้นที่ 4 — ตรวจ

```bash
bash ~/.claude/skills/posn/install.sh --check
```

ต้องได้ OK หมด ยกเว้นบรรทัด PDF ถ้ายังไม่ได้ก๊อปไฟล์ข้อสอบมา

ทดสอบจริงอีกชั้น: เปิด Claude Code แล้วสั่ง "สร้างข้อสอบเทียม ชุดที่ N"
skill จะโหลดเอง (ชื่อ `posn`) ถ้าไม่โหลด เช็คว่า `~/.claude/skills/posn/SKILL.md` มีจริง
และ frontmatter `name`/`description` ยังอยู่

## ที่เครื่องใหม่มักพัง

| อาการ | สาเหตุ | แก้ |
|---|---|---|
| `Font THSarabunNew.ttf not found` | kpathsea ยังไม่เห็นฟอนต์ | `install.sh` ซ้ำ หรือ `mktexlsr` เอง |
| `extarticle.cls not found` | ไม่มี `extsizes` | `tlmgr install extsizes` |
| `xelatex: command not found` | PATH ไม่มี TinyTeX | `export PATH="$(ls -d $HOME/.TinyTeX/bin/*/):$PATH"` |
| เลขหน้าเป็น `??` | คอมไพล์รอบเดียว | คอมไพล์ 2 รอบ |
| ภาษาไทยล้นขอบขวา | ลืม `\XeTeXlinebreaklocale "th"` | ใส่กลับ |
| rclone บอก `didn't find section in config` | ยังไม่ authorize | ขั้นที่ 3 |

error อื่น ๆ ที่เคยเจอจริง ดู [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
