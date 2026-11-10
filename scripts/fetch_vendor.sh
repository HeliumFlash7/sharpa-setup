#!/usr/bin/env bash
# Download the vendor software from the official GitHub releases into vendor/, verify SHA-256 and
# unpack the Manus teleop package. Re-running skips what is already there.
#
#   bash scripts/fetch_vendor.sh              # Sharpa Pilot 2.0.11 + sharpa-manus-sdk v1.0.1 (~1.2 GB)
#   bash scripts/fetch_vendor.sh --no-manus   # Sharpa Pilot only
#   bash scripts/fetch_vendor.sh --haptics    # also sharpa-manus-sdk v1.2.0 (MetaGloves Pro *Haptics* only)
#
# These files are licensed by Sharpa / Manus and must not be redistributed; vendor/ is gitignored.
set -euo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/_common.sh"

MANUS=1 HAPTICS=0
for a in "$@"; do
  case "$a" in
    --no-manus) MANUS=0 ;;
    --haptics) HAPTICS=1 ;;
    *) die "unknown option $a (see the header of $0)" ;;
  esac
done

REL=https://github.com/sharpa-robotics
DL="$ROOT/vendor/downloads"
mkdir -p "$DL"

fetch() {  # url  local-name  sha256
  local f="$DL/$2"
  if [ -f "$f" ] && echo "$3  $f" | sha256sum -c --status; then ok "$2 (already downloaded)"; return; fi
  echo "  GET   $1"
  curl -fL --retry 3 -C - -o "$f.part" "$1"
  if ! echo "$3  $f.part" | sha256sum -c --status; then
    rm -f "$f.part"; die "checksum mismatch for $2 (partial file deleted, re-run)"
  fi
  mv "$f.part" "$f"
  ok "$2"
}

unpack() {  # archive  destination-folder   (archive has a single top-level folder)
  if [ -d "$2" ]; then ok "$(basename "$2")/ (already unpacked)"; return; fi
  local tmp="$2.tmp"
  rm -rf "$tmp" && mkdir -p "$tmp"
  case "$1" in
    *.tar.gz) tar xzf "$1" -C "$tmp" ;;
    *.zip) python3 - "$1" "$tmp" <<'PY'  # like `unzip`, but keeps the executable bits
import os, sys, zipfile
with zipfile.ZipFile(sys.argv[1]) as z:
    for zi in z.infolist():
        path = z.extract(zi, sys.argv[2])
        mode = (zi.external_attr >> 16) & 0o777
        if mode:
            os.chmod(path, mode)
PY
      ;;
  esac
  mv "$tmp"/* "$2" && rmdir "$tmp"
  ok "unpacked $(basename "$2")/"
}

hdr "Sharpa Pilot (bundles the matching Sharpa Wave SDK)"
fetch "$REL/sharpa-wave/releases/download/v2.0.11/sharpa-pilot_2.0.11_amd64_linux.deb" \
  sharpa-pilot_2.0.11_amd64_linux.deb da5e9929f761b8115042eff30416367c552882b16f7a157476830d30b921e40e

if [ $MANUS = 1 ]; then
  hdr "sharpa-manus-sdk v1.0.1 (Manus MetaGloves Pro)"
  fetch "$REL/sharpa-manus-sdk/releases/download/V1.0.1/sharpa-manus-sdk_release.tar.gz" \
    sharpa-manus-sdk_v1.0.1_release.tar.gz abf587eb21b5acdca4cef76ace1b4bbc32df6e89cdb4a21641f79889ecbcdba1
  unpack "$DL/sharpa-manus-sdk_v1.0.1_release.tar.gz" "$ROOT/vendor/sharpa-manus-sdk-1.0.1"
fi

if [ $HAPTICS = 1 ]; then
  hdr "sharpa-manus-sdk v1.2.0 (Manus MetaGloves Pro Haptics)"
  fetch "$REL/sharpa-manus-sdk/releases/download/v1.2.0/sharpa-manus-sdk-manus-pro-haptics.zip" \
    sharpa-manus-sdk_v1.2.0_manus-pro-haptics.zip aac0503500dabf9513abe30172af2cc109d804eaab1f531e35ffb7a57c952543
  unpack "$DL/sharpa-manus-sdk_v1.2.0_manus-pro-haptics.zip" "$ROOT/vendor/sharpa-manus-sdk-1.2.0-haptics"
fi

echo
echo "Done. Next: install Pilot (README step 2):"
echo "  sudo apt install $DL/sharpa-pilot_2.0.11_amd64_linux.deb"
