# SETUP — ติดตั้งเครื่องมือใหม่ (แบบทำมือ)

> **ทางลัด**: `bash ~/.claude/skills/posn/install.sh` ทำทุกอย่างในหน้านี้ให้อัตโนมัติ
> และตรวจผลให้ด้วย ใช้หน้านี้เมื่อ installer พัง หรืออยากรู้ว่ามันทำอะไรบ้าง
> ย้ายเครื่องทั้งชุด ดู [INSTALL.md](INSTALL.md)

ใช้เมื่อเครื่องเปลี่ยน หรือของหาย **เช็คก่อนติดตั้งซ้ำ**

```bash
bash ~/.claude/skills/posn/install.sh --check     # เช็คทุกอย่างในคำสั่งเดียว
# หรือเช็คเอง:
ls ~/.TinyTeX/bin/*/xelatex ~/.local/bin/rclone
fc-list | grep -i "sarabun new"
```

## ข้อจำกัดของเครื่องนี้

- **ไม่มี passwordless sudo** → ติดตั้งอะไรผ่าน `apt` ไม่ได้ ต้องลงในโฮมไดเรกทอรีเท่านั้น
- ไม่มี LaTeX ระดับระบบ ไม่มี pandoc/typst/weasyprint
- Python 3.14 มีแต่ stdlib (ไม่มี numpy/sympy/reportlab/matplotlib) — ใช้ `fractions`,
  `itertools`, `math`, `collections` ให้พอ อย่าไปติดตั้ง package เพิ่มโดยไม่จำเป็น
- มี PyMuPDF (`python3 -m pip install --user pymupdf`) สำหรับวัดขนาดฟอนต์และ render หน้า

## 1. TinyTeX (XeLaTeX โดยไม่ต้อง sudo)

```bash
curl -sL "https://yihui.org/tinytex/install-bin-unix.sh" -o install-tinytex.sh
sh install-tinytex.sh          # ~2-3 นาที ลงที่ ~/.TinyTeX
export PATH="$HOME/.TinyTeX/bin/x86_64-linux:$PATH"

tlmgr install xetex fontspec geometry amsmath amsfonts enumitem multicol \
  graphics pgf fancyhdr array xkeyval etoolbox unicode-math l3packages \
  l3kernel euenc ucharcat realscripts extsizes lastpage needspace
```

`extsizes` จำเป็นเพราะต้องใช้ `extarticle` 14pt (article ปกติมีแค่ถึง 12pt)

## 2. ฟอนต์ TH Sarabun New

```bash
mkdir -p ~/.local/share/fonts/thsarabunnew && cd ~/.local/share/fonts/thsarabunnew
base="https://raw.githubusercontent.com/epsilonxe/SIPAFonts/master"
curl -sfL -o "THSarabunNew.ttf"            "$base/THSarabunNew.ttf"
curl -sfL -o "THSarabunNew Bold.ttf"       "$base/THSarabunNew%20Bold.ttf"
curl -sfL -o "THSarabunNew Italic.ttf"     "$base/THSarabunNew%20Italic.ttf"
curl -sfL -o "THSarabunNew BoldItalic.ttf" "$base/THSarabunNew%20BoldItalic.ttf"
fc-cache -f ~/.local/share/fonts

# ก๊อปเข้า TEXMF tree ด้วย เพื่อให้ preamble ไม่ต้องเขียน Path= เป็น path เต็ม
d="$(kpsewhich -var-value TEXMFHOME)/fonts/truetype/public/thsarabunnew"
mkdir -p "$d" && cp ~/.local/share/fonts/thsarabunnew/*.ttf "$d"/ && mktexlsr
kpsewhich "THSarabunNew BoldItalic.ttf"    # ต้องคืน path ออกมา ไม่ใช่เงียบ
```

repo `epsilonxe/SIPAFonts` คือชุดฟอนต์แห่งชาติของ SIPA ตัวจริง

**อย่าใช้ Sarabun ของ Google Fonts** (`google/fonts/ofl/sarabun`) — คนละฟอนต์ ออกแบบโดย
Cadson Demak ความกว้างตัวอักษรและ metrics ต่างกัน ทำให้ layout ไม่ตรงข้อสอบจริง

**อย่าใช้ Noto Looped Thai / Noto Serif Thai / Noto Sans Thai** — ไม่มี glyph อักษรละติน
จะได้ `Missing character: There is no m (U+006D)` เต็ม log และตัวอักษรอังกฤษหายทั้งหมด

## 3. rclone + Google Drive

```bash
curl -sfL -o rclone.zip "https://downloads.rclone.org/rclone-current-linux-amd64.zip"
# แตกไฟล์ rclone ออกมาไว้ที่ ~/.local/bin/rclone แล้ว chmod 755
# (ดาวน์โหลดช้า ~21MB ให้รันแบบ background)
```

การ authorize ต้องให้ผู้ใช้ทำเอง (เปิด browser login) — บอกให้รันคำสั่งนี้ในเทอร์มินัล:

```bash
~/.local/bin/rclone config create gdrive drive scope=drive
```

คำสั่งเดียวจบ ไม่ต้องตอบ prompt สิบกว่าข้อแบบ `rclone config`

ตรวจว่าใช้ได้: `~/.local/bin/rclone lsd gdrive:`

### คำเตือนที่ rclone แจ้ง
remote นี้ใช้ shared client_id ของ rclone ซึ่ง Google จะเลิกรองรับภายในปี 2026
ถ้าวันหนึ่ง auth พัง ต้องสร้าง client_id ของตัวเอง:
https://rclone.org/drive/#making-your-own-client-id
