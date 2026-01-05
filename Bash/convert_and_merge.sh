#!/bin/bash

if [[ "${DEBUG:-false}" == "true" ]]; then
  set -ex  # Enable debugging and exit on error
else
  set -e  # Exit on error only
fi

INPUT_DIR="${1:-.}"
INPUT_DIR="$(realpath "$INPUT_DIR")"
TEMP_DIR=$(mktemp -d)
OUTPUT_FILE="$INPUT_DIR/merged_output.pdf"

echo "Script Debug Info:"
echo "- Input directory: $INPUT_DIR"
echo "- Temp directory: $TEMP_DIR"
echo "- Output file: $OUTPUT_FILE"
echo "- Current directory: $(pwd)"
echo "- Files in input dir:"
ls -la "$INPUT_DIR"

# Conversion and merging logic remains the same
for file in "$INPUT_DIR"/*; do
  if [[ -f "$file" ]]; then
    filename=$(basename "$file")
    ext="${filename##*.}"
    ext_lower=$(echo "$ext" | tr '[:upper:]' '[:lower:]')

    case "$ext_lower" in
      doc|docx|ppt|pptx)
        echo "Converting $file to PDF..."
        libreoffice --headless --convert-to pdf --outdir "$TEMP_DIR" "$file"
        ;;
      pdf)
        echo "Copying $file to temp..."
        cp "$file" "$TEMP_DIR/"
        ;;
      *)
        echo "Skipping unsupported file: $file"
        ;;
    esac
  fi
done

echo "Files to be merged:"
ls -la "$TEMP_DIR"/*.pdf

# Check if any PDF files exist in the temporary directory
if ! ls "$TEMP_DIR"/*.pdf >/dev/null 2>&1; then
  echo "❌ No PDF files found in the temporary directory. Exiting."
  rm -r "$TEMP_DIR"
  exit 1
fi
echo "Merging PDFs..."
pdfunite "$TEMP_DIR"/*.pdf "$OUTPUT_FILE"

echo "Verifying output:"
ls -la "$OUTPUT_FILE" || echo "Output file not found!"

rm -r "$TEMP_DIR"
echo "✅ Merged PDF created: $OUTPUT_FILE"