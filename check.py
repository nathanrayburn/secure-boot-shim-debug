import re
from collections import deque

LOG_FILE = "gdb-trace-direct.log"  # or your actual file path

enter_re = re.compile(r'\[\d+:\d+:\d+\] >> ENTER\s+(.*)')
exit_re = re.compile(r'\[\d+:\d+:\d+\] << EXIT\s+(.*)')

stack = deque()
errors = []

with open(LOG_FILE, 'r') as f:
    for line_num, line in enumerate(f, 1):
        line = line.strip()
        enter_match = enter_re.match(line)
        exit_match = exit_re.match(line)

        if enter_match:
            func = enter_match.group(1).strip()
            stack.append((func, line_num))

        elif exit_match:
            func = exit_match.group(1).strip()
            if not stack:
                errors.append(f"[Line {line_num}] EXIT '{func}' with empty stack!")
            else:
                last_func, last_line = stack.pop()
                if last_func != func:
                    errors.append(
                        f"[Line {line_num}] EXIT '{func}' does not match ENTER '{last_func}' at line {last_line}"
                    )

# Final check: any unclosed functions?
while stack:
    func, line_num = stack.pop()
    errors.append(f"[Line {line_num}] ENTER '{func}' has no matching EXIT")

# Output
if not errors:
    print("✅ All function ENTER/EXIT pairs match correctly.")
else:
    print("❌ Found mismatches:")
    for err in errors:
        print(err)
