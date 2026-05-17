#!/usr/bin/env python
import os

output_file = 'link_all_data_output.txt'

if os.path.exists(output_file):
    # Try reading as UTF-16
    try:
        with open(output_file, 'r', encoding='utf-16') as f:
            content = f.read()
            print(content)
    except:
        # Fall back to UTF-8 or default
        with open(output_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            print(content)
else:
    print(f"File not found: {output_file}")
