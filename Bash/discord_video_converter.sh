#!/bin/bash

# Define the maximum file size (10 MB in bytes)
MAX_SIZE=$((10 * 1024 * 1024))
OUT_DIR="converted"

# Create the output directory if it doesn't exist
mkdir -p "$OUT_DIR"

# ==============================================================================
# Function: Split file if it is larger than 10 MB
# ==============================================================================
split_if_large() {
  local filepath="$1"
  
  # Get exact file size safely
  local filesize=$(wc -c < "$filepath" | tr -d ' ')

  if [ "$filesize" -gt "$MAX_SIZE" ]; then
    echo "Notice: File $filepath is over 10MB. Splitting..."
    
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