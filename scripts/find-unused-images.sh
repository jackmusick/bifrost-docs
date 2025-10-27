#!/bin/bash

# Find unused images in src/assets directory
# Usage: ./find-unused-images.sh [--delete]

DELETE_MODE=false

if [[ "$1" == "--delete" ]]; then
    DELETE_MODE=true
    echo "⚠️  DELETE MODE ENABLED - Unused images will be removed!"
    echo ""
fi

echo "Scanning for unused images..."
echo ""

UNUSED_COUNT=0
TOTAL_COUNT=0

# Find all image files in assets
while IFS= read -r image; do
    TOTAL_COUNT=$((TOTAL_COUNT + 1))

    # Get just the filename
    filename=$(basename "$image")

    # Search for references in all markdown/mdx files and config files
    if ! grep -r -q "$filename" src/content/ astro.config.mjs 2>/dev/null; then
        if [ "$DELETE_MODE" = true ]; then
            echo "Deleting: $image"
            rm "$image"
        else
            echo $image
        fi

        UNUSED_COUNT=$((UNUSED_COUNT + 1))
    fi
done < <(find src/assets -type f \( -name "*.png" -o -name "*.jpg" -o -name "*.jpeg" -o -name "*.gif" -o -name "*.webp" -o -name "*.svg" \))

echo ""
if [ "$DELETE_MODE" = true ]; then
    echo "Scan complete! Deleted $UNUSED_COUNT unused images."
else
    echo "Scan complete! Run with --delete to remove $UNUSED_COUNT unused images."
fi
