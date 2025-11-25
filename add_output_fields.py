#!/usr/bin/env python3
"""Quick script to add impulse wave output fields to Module 14"""
import sys

# Read file
file_path = "processor/modules/fix14_mgann_swing.py"
with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find line with pb_wave_strength_ok
target_line = 'bar_state["pb_wave_strength_ok"] = bool(self.pb_wave_strength_flag)\n'
new_lines_to_add = [
    '        \n',
    '        # === NEW: Export wave strength validation fields (v1.3.0) ===\n',
    '        bar_state["impulse_wave_strength_ok"] = bool(self.impulse_wave_strength_ok)\n',
    '        bar_state["impulse_speed"] = round(self.impulse_speed, 4)\n',
    '        bar_state["pullback_speed"] = round(self.pullback_speed, 4)\n',
    '        bar_state["avg_delta"] = round(self.avg_delta, 2)\n',
    '        bar_state["avg_volume"] = round(self.avg_volume, 2)\n',
    '        bar_state["avg_speed"] = round(self.avg_speed, 4)\n',
]

# Find index and insert
modified = False
for i, line in enumerate(lines):
    if target_line in line:
        # Check if already added
        if i + 1 < len(lines) and 'impulse_wave_strength_ok' in lines[i+1]:
            print("Already added!")
            sys.exit(0)
        
        # Insert after this line
        for j, new_line in enumerate(new_lines_to_add):
            lines.insert(i + 1 + j, new_line)
        modified = True
        break

if modified:   
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print("Fields added successfully!")
else:
    print("Target line not found!")
