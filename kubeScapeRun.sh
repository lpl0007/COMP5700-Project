#!/bin/bash
FILE="$1"
CONTENT=$(tr -s '[:space:]' ' ' < "$FILE" | sed 's/^ //;s/ $//')

if [[ "$CONTENT" == "NO DIFFERENCES FOUND" ]]; then
    echo "NO DIFFERENCES FOUND"
else
    sh "$FILE"
fi
