#!/usr/bin/env bash
# Build HabitTracker.icns from the source app_icon.
#
# Uses only macOS built-ins (sips + iconutil), so no image libraries are needed.
# The generated .icns is a build artifact and is not committed.
set -euo pipefail

cd "$(dirname "$0")/.."

ICONSET="build/HabitTracker.iconset"
OUT="HabitTracker.icns"

# Accept whatever the icon file is actually named or whatever format it holds.
# `file` reports the real type, which matters: the source is not always a PNG
# even when it has a .PNG extension, and iconutil refuses mismatched data.
SRC=""
for candidate in app_icon.PNG app_icon.png app_icon.jpg app_icon.jpeg app_icon; do
  if [ -f "$candidate" ]; then
    SRC="$candidate"
    break
  fi
done

if [ -z "$SRC" ]; then
  echo "error: no app_icon file found in $(pwd)" >&2
  exit 1
fi

echo "using source: $SRC ($(file -b "$SRC" | cut -d, -f1))"

rm -rf "$ICONSET" "$OUT"
mkdir -p "$ICONSET"

# Normalise to a real 1024px PNG master first. Explicitly setting the format
# means every intermediate file is genuine PNG data regardless of the source,
# and 1024px means each output size is downscaled rather than upscaled.
MASTER="$(mktemp -t habittracker_icon)"
trap 'rm -f "$MASTER"' EXIT
sips -s format png -z 1024 1024 "$SRC" --out "$MASTER" >/dev/null

for size in 16 32 128 256 512; do
  sips -s format png -z $size $size "$MASTER" \
    --out "$ICONSET/icon_${size}x${size}.png" >/dev/null
  retina=$((size * 2))
  sips -s format png -z $retina $retina "$MASTER" \
    --out "$ICONSET/icon_${size}x${size}@2x.png" >/dev/null
done

# Confirm the intermediates really are PNG before asking iconutil to trust them.
for png in "$ICONSET"/*.png; do
  if ! file -b "$png" | grep -q "PNG image data"; then
    echo "error: $png is not valid PNG data" >&2
    exit 1
  fi
done

iconutil -c icns "$ICONSET" -o "$OUT"
echo "built $OUT ($(du -h "$OUT" | cut -f1))"