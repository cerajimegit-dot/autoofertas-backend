#!/usr/bin/env python
import os

if os.path.exists('verify_migration_output.txt'):
    with open('verify_migration_output.txt', 'r', encoding='utf-16', errors='ignore') as f:
        content = f.read()
    
    with open('migration_verify.txt', 'w', encoding='utf-8') as f:
        f.write(content)
else:
    print("File not found")
