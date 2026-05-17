#!/usr/bin/env python
import os

if os.path.exists('migration_log.txt'):
    with open('migration_log.txt', 'r', encoding='utf-16') as f:
        content = f.read()
    
    with open('migration_readable.txt', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(content)
