#!/bin/bash

# Usage: ./showfiles.sh /path/to/dir txt

# Input validation
if [ $# -ne 2 ]; then
  echo "Usage: $0 <directory> <extension>" >&2
  exit 1
fi

DIR="$1"
EXT="${2#.}"

# Check if directory exists
if [ ! -d "$DIR" ]; then
  echo "Error: Directory '$DIR' does not exist." >&2
  exit 1
fi

# Loop over matching files
shopt -s nullglob
file_count=0
for file in "$DIR"/*."$EXT"; do
  echo "===== $(basename "$file") ====="
  cat "$file"
  echo
  file_count=$((file_count + 1))
done

# Check if no files were processed
if [ "$file_count" -eq 0 ]; then
  echo "No files with extension '$EXT' found in directory '$DIR'."
fi
