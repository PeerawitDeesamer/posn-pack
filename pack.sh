#!/usr/bin/env bash
# Bundle the POSN skill (and optionally the reference/output PDFs) into one
# tarball to carry to another machine.
#
#   bash pack.sh              # skill only, ~90 KB
#   bash pack.sh --with-pdfs  # skill + ~/Documents/POSN.Computer PDFs (large)
#   bash pack.sh --out DIR    # where to write the tarball (default: ~/Downloads)
set -euo pipefail

SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORK_DIR="$HOME/Documents/POSN.Computer"
OUT_DIR="$HOME/Downloads"
WITH_PDFS=0

while [ $# -gt 0 ]; do
  case "$1" in
    --with-pdfs) WITH_PDFS=1; shift ;;
    --out) OUT_DIR="$2"; shift 2 ;;
    -h|--help) sed -n '2,7p' "$0"; exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done

mkdir -p "$OUT_DIR"
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
ROOT="$STAGE/posn-skill"
mkdir -p "$ROOT/skill"

cp -R "$SRC_DIR"/SKILL.md "$SRC_DIR"/install.sh "$SRC_DIR"/pack.sh "$SRC_DIR"/assets \
      "$SRC_DIR"/docs "$SRC_DIR"/scripts "$ROOT/skill"/

if [ "$WITH_PDFS" = 1 ] && [ -d "$WORK_DIR" ]; then
  mkdir -p "$ROOT/POSN.Computer"
  for d in "ไฟล์ข้อสอบ" "ข้อสอบเทียม"; do
    [ -d "$WORK_DIR/$d" ] && cp -R "$WORK_DIR/$d" "$ROOT/POSN.Computer"/
  done
fi

cat > "$ROOT/README.txt" <<'TXT'
POSN Mock Exam Builder — transfer bundle

On the new machine:

    tar xzf posn-skill-*.tar.gz
    cd posn-skill
    bash skill/install.sh

install.sh copies the skill to ~/.claude/skills/posn and installs TinyTeX,
TH Sarabun New, and rclone under $HOME (no sudo).

If this bundle has a POSN.Computer/ folder, copy it over too:

    mkdir -p ~/Documents/POSN.Computer
    cp -R POSN.Computer/* ~/Documents/POSN.Computer/

Google Drive needs a browser login once, on the new machine:

    ~/.local/bin/rclone config create gdrive drive scope=drive

Then verify:  bash ~/.claude/skills/posn/install.sh --check
TXT

TARBALL="$OUT_DIR/posn-skill-$(date +%Y%m%d).tar.gz"
tar czf "$TARBALL" -C "$STAGE" posn-skill
printf 'wrote %s (%s)\n' "$TARBALL" "$(du -h "$TARBALL" | cut -f1)"
[ "$WITH_PDFS" = 0 ] && echo "note: PDFs not included — use --with-pdfs, or re-download them from Google Drive"
exit 0
