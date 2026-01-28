#!/usr/bin/env bash
set -Eeuo pipefail

FFMPEG_BIN="ffmpeg"
FFPROBE_BIN="ffprobe"
CONCAT_FILE="videos_to_concat.txt"

die() {
  echo "Error: $*" >&2
  exit 1
}

cleanup() {
  rm -f "$CONCAT_FILE"
}
trap cleanup EXIT

# ------------------------------------------------------------------------------
# Args
# ------------------------------------------------------------------------------

[[ $# -eq 1 ]] || die "Usage: $0 <directory>"
TARGET_DIR=$1
[[ -d "$TARGET_DIR" ]] || die "Not a directory: $TARGET_DIR"

command -v "$FFMPEG_BIN" >/dev/null || die "ffmpeg not found"
command -v "$FFPROBE_BIN" >/dev/null || die "ffprobe not found"

cd "$TARGET_DIR"

# ------------------------------------------------------------------------------
# Discover video files (real ones, not by extension)
# ------------------------------------------------------------------------------

mapfile -t video_files < <(
  find . -maxdepth 1 -type f -print0 |
  while IFS= read -r -d '' file; do
    if "$FFPROBE_BIN" -v error \
      -select_streams v:0 \
      -show_entries stream=index \
      -of csv=p=0 "$file" >/dev/null 2>&1; then
      printf '%s\n' "${file#./}"
    fi
  done | sort
)

(( ${#video_files[@]} > 0 )) || die "No video files found in $TARGET_DIR"

# ------------------------------------------------------------------------------
# Build concat file
# ------------------------------------------------------------------------------

for file in "${video_files[@]}"; do
  printf "file '%s'\n" "$file" >> "$CONCAT_FILE"
done

first_file="${video_files[0]}"

# ------------------------------------------------------------------------------
# Timestamp (portable)
# ------------------------------------------------------------------------------

if stat -f %B "$first_file" >/dev/null 2>&1; then
  timestamp=$(stat -f %B "$first_file")
elif stat -c %W "$first_file" >/dev/null 2>&1; then
  timestamp=$(stat -c %W "$first_file")
else
  die "Cannot read file timestamps"
fi

if [[ "$timestamp" -le 0 ]]; then
  if stat -f %m "$first_file" >/dev/null 2>&1; then
    timestamp=$(stat -f %m "$first_file")
  else
    timestamp=$(stat -c %Y "$first_file")
  fi
fi

DATE=$(date -r "$timestamp" +"%Y-%m-%d") || die "Date formatting failed"

output_file="${DATE}.mp4"

# ------------------------------------------------------------------------------
# Merge
# ------------------------------------------------------------------------------

"$FFMPEG_BIN" \
  -loglevel error \
  -stats \
  -f concat \
  -safe 0 \
  -i "$CONCAT_FILE" \
  -c copy \
  "$output_file"

echo "Merged ${#video_files[@]} videos → $output_file"
