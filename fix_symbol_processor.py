"""Fix indentation and self->bot references in symbol_processor.py"""
import subprocess, sys

with open('superbot/services/symbol_processor.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
in_func = False
for i, line in enumerate(lines):
    stripped = line.rstrip()
    if stripped == 'def process_symbol(bot, symbol: str):':
        in_func = True
        new_lines.append(line)
        continue
    if in_func:
        if stripped == '':
            new_lines.append('\n')
        elif line.startswith('        '):  # 8 spaces -> 4
            new_lines.append(line[4:])
        elif line.startswith('    '):
            new_lines.append(line)
        else:
            new_lines.append(line)
    else:
        new_lines.append(line)

# Fix 'self' references that should be 'bot'
content = ''.join(new_lines)
content = content.replace('getattr(self,', 'getattr(bot,')
content = content.replace('hasattr(self,', 'hasattr(bot,')
# Line 98: _real_balance = getattr(self, '_cached_balance', 0.0)
content = content.replace("_real_balance = getattr(bot, '_cached_balance'", "_real_balance = getattr(bot, '_cached_balance'")

with open('superbot/services/symbol_processor.py', 'w', encoding='utf-8') as f:
    f.write(content)

r = subprocess.run([sys.executable, '-m', 'py_compile', 'superbot/services/symbol_processor.py'],
                   capture_output=True, text=True)
if r.returncode == 0:
    print('OK: symbol_processor.py compiles without errors')
else:
    print('FAIL:', r.stderr)
