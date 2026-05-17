#!/usr/bin/env python
import os

if os.path.exists('inspect_output.txt'):
    with open('inspect_output.txt', 'r', encoding='utf-16') as f:
        content = f.read()
    
    with open('inspect_readable.txt', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(content)
