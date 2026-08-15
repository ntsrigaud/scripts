#!/bin/bash

# Default values
SPEED="1.0"
REMOVE_AUDIO=false
RESET_TIMESTAMPS=1
MAX_SIZE=$((9 * 1024 * 1024))
OUT_DIR="converted"

# Parse CLI flags
while [[ $# -gt 0 ]]; do
  case "$1" in
    -s|--speed)
      SPEED="$2"
      shift 2
      ;;
    -n|--no-audio|--mute|-an)
      REMOVE_AUDIO=true
      shift 1
      ;;
    -reset_timestamps|--reset-timestamps|-r)
      # Accept flag with optional numerical argument (e.g. -reset_timestamps 1 or -reset_timestamps)
      if [[ "$2" =~ ^[0-9]+$ ]]; then
        RESET_TIMESTAMPS="$2"
        shift 2
      else
        RESET_TIMESTAMPS=1
        shift 1
      fi
      ;;
    -h|--help)
      echo "Usage: $0 [-s|--speed MULTIPLIER] [-n|--no-audio] [-reset_timestamps 1]"
      echo "  -s, --speed           Video playback speed multiplier (default: 1.0)"
      echo "  -n, --no-audio        Remove audio from converted video (default: keep audio)"
      echo "  -reset_timestamps 1   Reset timestamps when splitting segments (enabled by default)"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      echo "Usage: $0 [-s|--speed MULTIPLIER] [-n|--no-audio] [-reset_timestamps 1]"
      exit 1
      ;;
  esac
done

# Create the output directory if it doesn't exist
mkdir -p "$OUT_DIR"

# ==============================================================================
# Helper Function: Build audio tempo filter string for ffmpeg
# ==============================================================================
build_atempo_filter() {
  local speed="$1"
  local filter=""
  
  while $(awk -v s="$speed" 'BEGIN {exit !(s > 2.0)}'); do
    filter="${filter}atempo=2.0,"
    speed=$(awk -v s="$speed" 'BEGIN {print s / 2.0}')
  done
  
  while $(awk -v s="$speed" 'BEGIN {exit !(s < 0.5)}'); do
    filter="${filter}atempo=0.5,"
    speed=$(awk -v s="$speed" 'BEGIN {print s / 0.5}')
  done
  
  filter="${filter}atempo=${speed}"
  echo "$filter"
}

split_if_large() {
  local filepath="$1"
  
  # Get exact file size safely
  local filesize=$(wc -c < "$filepath" | tr -d ' ')

  if [ "$filesize" -gt "$MAX_SIZE" ]; then
    echo "Notice: File $filepath is over 9MB. Splitting..."
    
    local duration=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$filepath")
    local seg_time=$(awk -v dur="$duration" -v size="$filesize" -v max="$MAX_SIZE" 'BEGIN { print (dur / (size / max)) * 0.95 }')
    
    local dir=$(dirname "$filepath")
    local base=$(basename "$filepath" .mp4)
    
    # Split the video losslessly
    ffmpeg -i "$filepath" -c copy -map 0 -segment_time "$seg_time" -f segment -reset_timestamps 1 -segment_start_number 1 "${dir}/${base}-part-%d.mp4"
    
    # Remove the original oversized file to save space and prevent re-splitting
    rm "$filepath"
  fi
}

# ==============================================================================
# Task 1: Check and Convert missing .mov files
# ==============================================================================
echo "Starting conversion check..."

# Enable nullglob so the loop safely skips if no .mov files exist
shopt -s nullglob

for recording in *.mov; do
  # Extract the date and time string
  time_str=$(echo "$recording" | sed -E 's/.*Recording (.*) at (.*)\.mov/\1_\2/' | tr -d ' ')
  
  base_out_name="demo-${time_str}"
  expected_output="$OUT_DIR/${base_out_name}.mp4"
  expected_split_output="$OUT_DIR/${base_out_name}-part-1.mp4"

  # Check if the file (or its first split part) already exists in 'converted/'
  if [ -f "$expected_output" ] || [ -f "$expected_split_output" ]; then
    echo "Skipping '$recording': Already converted."
  else
    echo "Converting '$recording'..."
    ffmpeg -i "$recording" -vcodec libx264 -crf 23 -preset medium -acodec aac -b:a 128k "$expected_output"
  fi
done

# ==============================================================================
# Task 2: Review 'converted/' directory and split any oversized files
# ==============================================================================
echo "Reviewing $OUT_DIR directory for large files..."

for file in "$OUT_DIR"/*.mp4; do
  # Skip files that already have "-part-" in their name
  if [[ "$file" != *"-part-"* ]]; then
    split_if_large "$file"
  fi
done

# Disable nullglob to return shell behavior to normal
shopt -u nullglob

echo "Pipeline complete!"