# DRIVE — อัปไฟล์ขึ้น Google Drive ของผู้ใช้

บัญชี: บัญชี Google ที่ authorize ไว้ใน rclone remote ชื่อ `gdrive`
โฟลเดอร์ปลายทาง: `POSN.Computer` (folder ID เขียนแทนด้วย `<FOLDER_ID>` ในเอกสารนี้)

หา folder ID ของตัวเอง (ใช้ตอนยืนยันผ่าน MCP เท่านั้น — `rclone` ใช้ชื่อโฟลเดอร์ ไม่ต้องใช้ ID):

```bash
~/.local/bin/rclone lsjson gdrive: --dirs-only | python3 -c "
import sys, json
for d in json.load(sys.stdin):
    if d['Name'] == 'POSN.Computer': print(d['ID'])"
```

## วิธีที่ใช้ได้ — rclone

```bash
~/.local/bin/rclone copy "<ไฟล์>" gdrive:POSN.Computer
~/.local/bin/rclone ls gdrive:POSN.Computer
```

ยืนยันว่าเป็น PDF จริง ไม่โดนแปลงเป็น Google Docs:

```
mcp__claude_ai_Google_Drive__search_files
  query: parentId = '<FOLDER_ID>' and title contains '<ชื่อ>'
  excludeContentSnippets: true
```
ดูว่า `mimeType` เป็น `application/pdf` และ `fileSize` ตรงกับไฟล์ต้นทาง

`rclone copy` เขียนทับไฟล์ชื่อเดียวกันโดยคง Drive file id เดิม → **ลิงก์แชร์เดิมยังใช้ได้**
เหมาะกับการอัปเวอร์ชันแก้ไข

## วิธีที่ใช้ไม่ได้ (ทดสอบแล้ว 2026-07-31 อย่าเสียเวลาซ้ำ)

### 1. MCP tool `create_file` — ใช้ได้เฉพาะไฟล์เล็ก
รับ base64 เป็น **text parameter** แปลว่าต้องอ่าน base64 เข้า context ก่อน
PDF 56 KB → base64 74,672 ตัวอักษร → ประมาณ **240,000 tokens** (base64 tokenize แย่มาก
~3 tokens ต่อตัวอักษร) ใช้กับไฟล์ไบนารีไม่ไหว

ใช้ได้เฉพาะไฟล์ข้อความเล็ก ๆ

### 2. GNOME Online Accounts / gvfs mount — ไม่มี backend
Ubuntu 26.04 แพ็กเกจ `gvfs-backends` มี `gvfsd-onedrive` แต่ **ไม่มี `gvfsd-google`**
เพิ่มบัญชี Google ใน Settings ก็ไม่มีอะไรโผล่ที่ `/run/user/1000/gvfs`

ตรวจซ้ำได้ด้วย `ls /usr/libexec/gvfsd-* | grep google`

### 3. apt install อะไรก็ตาม — ไม่มี passwordless sudo

## ข้อควรระวัง

- **ใช้ `copy` ห้ามใช้ `sync`** — `sync` ลบไฟล์ปลายทางที่ไม่มีในต้นทาง
- **อย่ากรอง output ของ rclone ทิ้งหมด** เช่น `2>&1 | grep -v NOTICE` จะทำให้ไม่เห็น
  ข้อความที่ rclone รายงานเกี่ยวกับไฟล์ปลายทาง ถ้าจะกรองให้เก็บ log ไว้ด้วย
- ก่อนอัปทับไฟล์เดิม ให้ `rclone ls` ดูก่อนว่ามีอะไรอยู่
- ถ้าไฟล์ในโฟลเดอร์หายไป เช็คถังขยะก่อนสรุปว่าใครลบ:
  `~/.local/bin/rclone lsf gdrive: --drive-trashed-only -R --files-only`
  และ **ถามผู้ใช้ก่อนกู้คืน** — ผู้ใช้อาจลบเองตั้งใจ (เคยเกิดขึ้นแล้ว)

## การจัดโฟลเดอร์

ผู้ใช้ระบุ (2026-07-31) ว่าให้จัดโฟลเดอร์ย่อย **เฉพาะในเครื่อง** ส่วน Drive ให้ปล่อยไฟล์
ลอยไว้ใน `POSN.Computer` ตามเดิม อย่าไปสร้างโฟลเดอร์ย่อยบน Drive เองโดยไม่ถาม
