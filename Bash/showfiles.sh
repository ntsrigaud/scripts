#!/bin/bash

# Usage: ./showfiles.sh /path/to/dir txt md log

# Input validation
if [ $# -lt 2 ]; then
  echo "Usage: $0 <directory> <extension1> [extension2 ...]" >&2
  exit 1
fi

DIR="$1"
shift  # Remove first argument so $@ contains only extensions

# Check if directory exists
if [ ! -d "$DIR" ]; then
  echo "Error: Directory '$DIR' does not exist." >&2
  exit 1
fi

shopt -s nullglob
file_count=0

for EXT in "$@"; do
  EXT="${EXT#.}"  # Remove leading dot if provided
  for file in "$DIR"/*."$EXT"; do
    echo "===== $(basename "$file") ====="
    cat "$file"
    echo
    file_count=$((file_count + 1))
  done
done

# Check if no files were processed
if [ "$file_count" -eq 0 ]; then
  echo "No files with the given extensions found in '$DIR'."
fi