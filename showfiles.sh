#!/bin/bash

# Usage: ./showfiles.sh /path/to/dir txt

# Input validation
if [ $# -ne 2 ]; then
  echo "Usage: $0 <directory> <extension>" >&2
  exit 1
fi

DIR="$1"
EXT="$2"

# Check if directory exists
if [ ! -d "$DIR" ]; then
  echo "Error: Directory '$DIR' does not exist." >&2
  exit 1
fi

# Loop over matching files
shopt -s nullglob
for file in "$DIR"/*."$EXT"; do
  echo "===== $(basename "$file") ====="
  cat "$file"
  echo
done
