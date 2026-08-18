#!/usr/bin/env bash
# POSN Mock Exam Builder — installer for a fresh machine.
# Idempotent: safe to re-run. Installs everything under $HOME, no sudo needed.
#
#   bash install.sh              # install everything
#   bash install.sh --check      # verify only, install nothing
#   bash install.sh --no-rclone  # skip Google Drive tooling
#
# Also runs straight off GitHub with no checkout:
#   curl -fsSL https://raw.githubusercontent.com/PeerawitDeesamer/posn-pack/main/install.sh | bash
set -uo pipefail

# ---- EDIT THIS after creating the GitHub repo -------------------------------
# Used only for the curl-pipe path above, to fetch the rest of the files.
DEFAULT_REPO="PeerawitDeesamer/posn-pack"
# -----------------------------------------------------------------------------

SELF="${BASH_SOURCE[0]:-}"
SRC_DIR=""
[ -n "$SELF" ] && [ -f "$SELF" ] && SRC_DIR="$(cd "$(dirname "$SELF")" && pwd)"

# Piped from curl: no sibling files on disk, so pull the repo tarball first.
if [ -z "$SRC_DIR" ] || [ ! -f "$SRC_DIR/SKILL.md" ]; then
  REPO="${POSN_REPO:-$DEFAULT_REPO}"
  BRANCH="${POSN_BRANCH:-main}"
  case "$REPO" in
    YOUR-GITHUB-USERNAME/*)
      echo "SKILL.md not found next to this script, and DEFAULT_REPO is still a placeholder." >&2
      echo "Either clone the repo and run 'bash install.sh' inside it, or re-run as:" >&2
      echo "  POSN_REPO=owner/repo bash <(curl -fsSL https://raw.githubusercontent.com/owner/repo/main/install.sh)" >&2
      exit 2 ;;
  esac
  echo "==> fetching $REPO@$BRANCH"
  FETCH_DIR="$(mktemp -d)"
  curl -fsSL "https://codeload.github.com/$REPO/tar.gz/$BRANCH" | tar xz -C "$FETCH_DIR" \
    || { echo "download failed: $REPO@$BRANCH" >&2; exit 1; }
  SRC_DIR=""   # GitHub wraps the tree in a repo-branch/ directory
  for d in "$FETCH_DIR"/*/; do [ -f "$d/SKILL.md" ] && SRC_DIR="${d%/}" && break; done
  [ -n "$SRC_DIR" ] || { echo "SKILL.md not found in $REPO@$BRANCH" >&2; exit 1; }
  trap 'rm -rf "$FETCH_DIR"' EXIT
fi
SKILL_DIR="$HOME/.claude/skills/posn"
FONT_DIR="$HOME/.local/share/fonts/thsarabunnew"
WORK_DIR="$HOME/Downloads/POSN.Computer"
BIN_DIR="$HOME/.local/bin"

CHECK_ONLY=0
WANT_RCLONE=1
for a in "$@"; do
  case "$a" in
    --check) CHECK_ONLY=1 ;;
    --no-rclone) WANT_RCLONE=0 ;;
    -h|--help) [ -f "$0" ] && sed -n '2,10p' "$0" || echo "usage: install.sh [--check] [--no-rclone]"; exit 0 ;;
    *) echo "unknown option: $a" >&2; exit 2 ;;
  esac
done

ok()   { printf '  \033[32mOK\033[0m   %s\n' "$*"; }
miss() { printf '  \033[33mMISS\033[0m %s\n' "$*"; }
die()  { printf '\033[31mFAIL\033[0m %s\n' "$*" >&2; exit 1; }
step() { printf '\n\033[1m==> %s\033[0m\n' "$*"; }

texbin() { ls -d "$HOME"/.TinyTeX/bin/*/ 2>/dev/null | head -1; }

# ---------------------------------------------------------------- platform
OS="$(uname -s)"
ARCH="$(uname -m)"
case "$OS" in
  Linux)  case "$ARCH" in
            x86_64)         RCLONE_PKG=linux-amd64 ;;
            aarch64|arm64)  RCLONE_PKG=linux-arm64 ;;
            *) die "unsupported Linux arch: $ARCH" ;;
          esac ;;
  Darwin) case "$ARCH" in
            arm64)  RCLONE_PKG=osx-arm64 ;;
            x86_64) RCLONE_PKG=osx-amd64 ;;
          esac ;;
  *) die "unsupported OS: $OS (Linux and macOS only)" ;;
esac

# ---------------------------------------------------------------- 0. skill files
step "0. Skill files"
if [ "$SRC_DIR" != "$SKILL_DIR" ]; then
  if [ "$CHECK_ONLY" = 1 ]; then
    [ -f "$SKILL_DIR/SKILL.md" ] && ok "installed at $SKILL_DIR" || miss "not installed at $SKILL_DIR"
  else
    mkdir -p "$SKILL_DIR"
    cp -R "$SRC_DIR"/SKILL.md "$SRC_DIR"/install.sh "$SRC_DIR"/docs "$SRC_DIR"/scripts "$SKILL_DIR"/
    [ -f "$SRC_DIR/pack.sh" ] && cp "$SRC_DIR/pack.sh" "$SKILL_DIR"/
    ok "copied skill to $SKILL_DIR"
  fi
else
  ok "running from $SKILL_DIR"
fi

# ---------------------------------------------------------------- 1. prerequisites
step "1. System prerequisites"
for c in curl python3 perl; do
  command -v "$c" >/dev/null && ok "$c" || die "$c missing — install it first (TinyTeX needs perl, scripts need python3)"
done
if command -v pdftotext >/dev/null && command -v pdftoppm >/dev/null; then
  ok "poppler-utils (pdftotext/pdftoppm/pdffonts)"
else
  miss "poppler-utils missing — font measuring and page previews will not work"
  echo "       Debian/Ubuntu: sudo apt install poppler-utils"
  echo "       macOS:         brew install poppler"
fi

# ---------------------------------------------------------------- 2. TinyTeX
step "2. TinyTeX (XeLaTeX)"
if [ -n "$(texbin)" ] && [ -x "$(texbin)xelatex" ]; then
  ok "xelatex at $(texbin)"
elif [ "$CHECK_ONLY" = 1 ]; then
  miss "TinyTeX not installed"
else
  echo "  installing TinyTeX (~2-3 min, ~50 MB)..."
  log="$(mktemp)"
  if ! curl -sL "https://yihui.org/tinytex/install-bin-unix.sh" | sh >"$log" 2>&1; then
    tail -15 "$log" >&2; die "TinyTeX install failed (log: $log)"
  fi
  rm -f "$log"
  [ -x "$(texbin)xelatex" ] || die "TinyTeX installed but xelatex not found"
  ok "TinyTeX installed at $(texbin)"
fi

TEXBIN="$(texbin)"
[ -n "$TEXBIN" ] && export PATH="${TEXBIN%/}:$PATH"

# ---------------------------------------------------------------- 3. LaTeX packages
# extsizes = extarticle 14pt; lastpage/needspace/fancyhdr/pgf used by the templates.
TL_PKGS="xetex fontspec geometry amsmath amsfonts enumitem multicol graphics pgf
  fancyhdr array xkeyval etoolbox unicode-math l3packages l3kernel euenc ucharcat
  realscripts extsizes lastpage needspace fancyvrb"

step "3. LaTeX packages"
if ! command -v xelatex >/dev/null; then
  miss "skipped — no xelatex"
elif [ "$CHECK_ONLY" = 1 ]; then
  for p in extsizes lastpage needspace fontspec fancyvrb; do
    kpsewhich "$p.sty" >/dev/null 2>&1 && ok "$p" || miss "$p"
  done
else
  # shellcheck disable=SC2086
  tlmgr install $TL_PKGS 2>&1 | grep -Ei "^tlmgr: (install|package)|already installed" | tail -3
  kpsewhich extsizes.sty >/dev/null 2>&1 || die "extsizes.sty still missing after tlmgr install"
  ok "packages installed"
fi

# ---------------------------------------------------------------- 4. TH Sarabun New
# Two copies on purpose:
#   ~/.local/share/fonts     -> fontconfig, so other apps and pdffonts see it
#   TEXMFHOME/fonts/truetype -> kpathsea, so the preamble needs no absolute Path=
step "4. Font TH Sarabun New"
FONT_FILES=("THSarabunNew.ttf" "THSarabunNew Bold.ttf" "THSarabunNew Italic.ttf" "THSarabunNew BoldItalic.ttf")
have_fonts=1
for f in "${FONT_FILES[@]}"; do [ -s "$FONT_DIR/$f" ] || have_fonts=0; done

if [ "$have_fonts" = 1 ]; then
  ok "4 weights in $FONT_DIR"
elif [ "$CHECK_ONLY" = 1 ]; then
  miss "fonts missing from $FONT_DIR"
else
  mkdir -p "$FONT_DIR"
  base="https://raw.githubusercontent.com/epsilonxe/SIPAFonts/master"
  for f in "${FONT_FILES[@]}"; do
    url="$base/$(printf '%s' "$f" | sed 's/ /%20/g')"
    curl -sfL -o "$FONT_DIR/$f" "$url" || die "font download failed: $f"
    [ -s "$FONT_DIR/$f" ] || die "font downloaded empty: $f"
  done
  command -v fc-cache >/dev/null && fc-cache -f "$HOME/.local/share/fonts" >/dev/null 2>&1
  ok "downloaded 4 weights to $FONT_DIR"
fi

if command -v kpsewhich >/dev/null; then
  TEXMFHOME="$(kpsewhich -var-value TEXMFHOME)"
  TEXFONTS="$TEXMFHOME/fonts/truetype/public/thsarabunnew"
  if kpsewhich "THSarabunNew BoldItalic.ttf" >/dev/null 2>&1; then
    ok "fonts visible to kpathsea"
  elif [ "$CHECK_ONLY" = 1 ]; then
    miss "fonts not in TEXMFHOME ($TEXFONTS)"
  else
    mkdir -p "$TEXFONTS"
    cp "$FONT_DIR"/*.ttf "$TEXFONTS"/ || die "copy to TEXMFHOME failed"
    mktexlsr >/dev/null 2>&1
    kpsewhich "THSarabunNew BoldItalic.ttf" >/dev/null 2>&1 \
      || die "fonts copied to $TEXFONTS but kpathsea still cannot find them"
    ok "fonts registered in $TEXFONTS"
  fi
fi

# ---------------------------------------------------------------- 5. rclone
step "5. rclone (Google Drive)"
if [ "$WANT_RCLONE" = 0 ]; then
  ok "skipped (--no-rclone)"
elif [ -x "$BIN_DIR/rclone" ] || command -v rclone >/dev/null; then
  ok "rclone present"
elif [ "$CHECK_ONLY" = 1 ]; then
  miss "rclone not installed"
else
  mkdir -p "$BIN_DIR"
  tmp="$(mktemp -d)"
  echo "  downloading rclone (~21 MB)..."
  curl -sfL -o "$tmp/rclone.zip" "https://downloads.rclone.org/rclone-current-$RCLONE_PKG.zip" \
    || die "rclone download failed"
  python3 - "$tmp/rclone.zip" "$BIN_DIR" <<'PY' || die "rclone unzip failed"
import os, sys, zipfile
zp, dest = sys.argv[1], sys.argv[2]
with zipfile.ZipFile(zp) as z:
    name = next(n for n in z.namelist() if n.endswith("/rclone") or n == "rclone")
    with z.open(name) as s, open(os.path.join(dest, "rclone"), "wb") as d:
        d.write(s.read())
os.chmod(os.path.join(dest, "rclone"), 0o755)
PY
  rm -rf "$tmp"
  ok "rclone installed at $BIN_DIR/rclone"
fi

RCLONE="$BIN_DIR/rclone"; [ -x "$RCLONE" ] || RCLONE="$(command -v rclone || true)"
if [ "$WANT_RCLONE" = 1 ] && [ -n "$RCLONE" ]; then
  if "$RCLONE" listremotes 2>/dev/null | grep -q '^gdrive:'; then
    ok "remote 'gdrive' configured"
  else
    miss "remote 'gdrive' not configured — authorization needs a browser, run it yourself:"
    echo "       $RCLONE config create gdrive drive scope=drive"
  fi
fi

# ---------------------------------------------------------------- 6. work directory
step "6. Work directory"
if [ "$CHECK_ONLY" = 1 ]; then
  [ -d "$WORK_DIR/ข้อสอบเทียม" ] && ok "$WORK_DIR" || miss "$WORK_DIR missing"
else
  # one folder per exam part — set numbers are counted per part
  mkdir -p "$WORK_DIR/ไฟล์ข้อสอบ" \
           "$WORK_DIR/ข้อสอบเทียม/พาร์ทคณิตศาสตร์" \
           "$WORK_DIR/ข้อสอบเทียม/พาร์ทคอมพิวเตอร์" \
           "$WORK_DIR/ข้อสอบเทียม/ฉบับเต็ม"
  ok "$WORK_DIR/{ไฟล์ข้อสอบ,ข้อสอบเทียม/{พาร์ทคณิตศาสตร์,พาร์ทคอมพิวเตอร์,ฉบับเต็ม}}"
fi
# Reference PDFs are the user's own data — never downloadable, must be copied over.
n_real=$(ls "$WORK_DIR/ไฟล์ข้อสอบ/"ข้อสอบสอวนคอมปี*.pdf 2>/dev/null | wc -l)
[ "$n_real" -gt 0 ] && ok "real exams: $n_real file(s) in ไฟล์ข้อสอบ/" \
  || miss "no ข้อสอบสอวนคอมปี*.pdf in $WORK_DIR/ไฟล์ข้อสอบ/ — copy from the old machine or Drive"
[ -f "$WORK_DIR/ไฟล์ข้อสอบ/เนื้อหาที่ใช้สอบ.pdf" ] && ok "reference: เนื้อหาที่ใช้สอบ.pdf" \
  || miss "missing $WORK_DIR/ไฟล์ข้อสอบ/เนื้อหาที่ใช้สอบ.pdf — copy from the old machine or Drive"
n_prev=$(find "$WORK_DIR/ข้อสอบเทียม" -name '*.pdf' 2>/dev/null | wc -l)
[ "$n_prev" -gt 0 ] && ok "previous mock sets: $n_prev PDF(s)" \
  || miss "no previous mock sets — copy ข้อสอบเทียม/ over to avoid repeating questions"

# ---------------------------------------------------------------- 7. smoke test
step "7. Compile smoke test"
if ! command -v xelatex >/dev/null; then
  miss "skipped — no xelatex"
else
  tmp="$(mktemp -d)"
  cat > "$tmp/smoke.tex" <<'TEX'
\documentclass[14pt]{extarticle}
\usepackage{fontspec}\usepackage{amsmath}\usepackage{lastpage}\usepackage{needspace}
\usepackage{fancyvrb}
\DefineVerbatimEnvironment{pycode}{Verbatim}{fontsize=\small, xleftmargin=2.4em}
\setmainfont{THSarabunNew}[Extension=.ttf, UprightFont=*, BoldFont=* Bold,
  ItalicFont=* Italic, BoldItalicFont=* BoldItalic, Scale=1.112]
\XeTeXlinebreaklocale "th"
\begin{document}
ทดสอบ abc \textbf{หนา} \textit{เอียง} \textbf{\textit{หนาเอียง}} $\binom{8}{3}=56$
\begin{pycode}
x = 2
while x < 20:
    x = x + 5
\end{pycode}
\end{document}
TEX
  ( cd "$tmp" && xelatex -interaction=nonstopmode smoke.tex >/dev/null 2>&1 )
  if [ -s "$tmp/smoke.pdf" ] && ! grep -q "Missing character" "$tmp/smoke.log"; then
    n=$(command -v pdffonts >/dev/null && pdffonts "$tmp/smoke.pdf" | grep -c THSarabunNew || echo 4)
    [ "$n" -eq 4 ] && ok "compiled, all 4 weights embedded" \
                   || { miss "compiled but only $n/4 font weights embedded"; }
  else
    miss "smoke test failed — see $tmp/smoke.log"
    grep -m3 "^!" "$tmp/smoke.log" 2>/dev/null
    exit 1
  fi
  rm -rf "$tmp"
fi

# ---------------------------------------------------------------- done
cat <<EOF

$( [ "$CHECK_ONLY" = 1 ] && echo "Check complete." || echo "Install complete." )

Add this to your shell profile (~/.zshrc or ~/.bashrc):

    export PATH="\$HOME/.TinyTeX/bin/$(basename "${TEXBIN%/}" 2>/dev/null || echo '*'):\$HOME/.local/bin:\$PATH"

Anything marked MISS above still needs a manual step. See docs/INSTALL.md.
EOF
