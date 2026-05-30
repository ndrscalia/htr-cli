#!/bin/bash

# Generate *_ids.txt files from *_text.txt files
for split in train val; do
  cut -d' ' -f1 "dataset/${split}_text.txt" > "dataset/${split}_ids.txt"
done
