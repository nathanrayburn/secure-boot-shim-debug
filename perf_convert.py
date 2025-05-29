import json
from datetime import datetime
import re

INPUT_FILE = "gdb-trace-direct.log"
OUTPUT_FILE = "trace_perfetto.json"

def parse_trace(lines):
    events = []
    stack = []
    time_ref = None
    last_ts = None  # in microseconds

    for line in lines:
        match = re.match(r"\[(\d+:\d+:\d+)\]\s+(>>|<<)\s+(ENTER|EXIT)\s+(.*)", line)
        if not match:
            continue

        t_str, _, action, func = match.groups()
        dt = datetime.strptime(t_str, "%H:%M:%S")
        ts = int(dt.timestamp() * 1_000_000)  # microseconds

        # Enforce strictly increasing timestamps
        if last_ts is not None and ts <= last_ts:
            ts = last_ts + 1  # ensure uniqueness
        last_ts = ts

        # Reference time for relative scale
        if time_ref is None:
            time_ref = ts
        ts -= time_ref

        if action == "ENTER":
            stack.append((func, ts))
        elif action == "EXIT":
            for i in reversed(range(len(stack))):
                if stack[i][0] == func:
                    _, start_ts = stack.pop(i)
                    duration = ts - start_ts
                    events.append({
                        "name": func,
                        "ph": "X",
                        "ts": start_ts,
                        "dur": max(1, duration),
                        "pid": 1,
                        "tid": 1,
                        "cat": "shim-trace"
                    })
                    break
    return events

def write_perfetto_trace(events):
    trace = {
        "traceEvents": events,
        "displayTimeUnit": "us"
    }
    with open(OUTPUT_FILE, "w") as f:
        json.dump(trace, f, indent=2)
    print(f"Perfetto trace written to: {OUTPUT_FILE}")

def main():
    with open(INPUT_FILE, "r") as f:
        lines = f.readlines()
    events = parse_trace(lines)
    write_perfetto_trace(events)

if __name__ == "__main__":
    main()
