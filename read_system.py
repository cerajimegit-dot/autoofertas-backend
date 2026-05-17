#!/usr/bin/env python
import os

if os.path.exists('SYSTEM_READY.md'):
    with open('SYSTEM_READY.md', 'r', encoding='utf-16', errors='ignore') as f:
        content = f.read()
    
    with open('SYSTEM_READY.txt', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(content)
