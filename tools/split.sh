#!/bin/bash
INPUT="./test/oleg-couch.webm"
MAX_BYTES=$((18 * 1024 * 1024))  # 18 MB
DURATION=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 "$INPUT")
TOTAL=$(stat -c%s "$INPUT")
CHUNK_DURATION=$(echo "$DURATION * $MAX_BYTES / $TOTAL" | bc -l)

i=0
START=0
while (( $(echo "$START < $DURATION" | bc -l) )); do
    ffmpeg -ss $START -i "$INPUT" -t $CHUNK_DURATION -c copy "chunk_$(printf '%03d' $i).webm" -y
    START=$(echo "$START + $CHUNK_DURATION" | bc -l)
    ((i++))
done