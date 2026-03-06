"""Fix terminal.ini settings for MT5"""
from terminal_config import TerminalConfigManager
import os

manager = TerminalConfigManager()

# Make writable first
try:
    os.chmod(manager.terminal_ini_path, 0o644)
except:
    pass

# Read content
with open(manager.terminal_ini_path, 'r', encoding='utf-16') as f:
    content = f.read()

# Build the path properly - use UTF-16 template-based .set file
set_path = "MQL5\\Profiles\\Tester\\test_from_template.set"

# Process line by line
lines = content.split('\n')
new_lines = []
expert_params_found = False

for line in lines:
    stripped = line.strip()

    if stripped.startswith('ExpertParameters='):
        new_lines.append(f'ExpertParameters={set_path}')
        expert_params_found = True
    elif stripped.startswith('TicksMode='):
        new_lines.append('TicksMode=4')
    elif stripped.startswith('LastTicksMode='):
        new_lines.append('LastTicksMode=4')
    elif stripped.startswith('OptMode='):
        new_lines.append('OptMode=1')
    elif stripped.startswith('LastOptimization='):
        new_lines.append('LastOptimization=1')
    elif stripped.startswith('LastDelay='):
        new_lines.append('LastDelay=50')
    else:
        new_lines.append(line)
        # Add ExpertParameters after Expert= if not found
        if stripped.startswith('Expert=') and 'Last' not in stripped and not expert_params_found:
            new_lines.append(f'ExpertParameters={set_path}')
            expert_params_found = True

content = '\n'.join(new_lines)

# Write back
with open(manager.terminal_ini_path, 'w', encoding='utf-16') as f:
    f.write(content)

# Verify by reading back
with open(manager.terminal_ini_path, 'r', encoding='utf-16') as f:
    verify = f.read()

print('Verified settings in terminal.ini:')
for line in verify.split('\n'):
    s = line.strip()
    if any(x in s for x in ['ExpertParam', 'TicksMode', 'OptMode', 'LastDelay']):
        print(f'  {s}')

print()
print('File is WRITABLE - ready for MT5')
