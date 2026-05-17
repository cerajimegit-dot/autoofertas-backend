#!/usr/bin/env python
import os

if os.path.exists('migration_log2.txt'):
    with open('migration_log2.txt', 'r', encoding='utf-16', errors='ignore') as f:
        content = f.read()
    
    with open('migration_final.txt', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(content)
else:
    print("Log file not found")
