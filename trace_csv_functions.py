import gdb
import csv
from datetime import datetime

CSV_PATH = "shim_functions_200.csv"
LOG_PATH = "gdb-trace-direct.log"

logfile = open(LOG_PATH, "a")

def log(msg):
    timestamp = datetime.now().strftime("%H:%M:%S")
    logfile.write(f"[{timestamp}] {msg}\n")
    logfile.flush()

# Entry breakpoint
class TraceEntry(gdb.Breakpoint):
    def __init__(self, func):
        super().__init__(func, internal=False)
        self.func = func
        self.silent = True

    def stop(self):
        log(f">> ENTER {self.func}")
        TraceExit(self.func, gdb.newest_frame())
        return False

# Exit breakpoint: tied to the current frame only
class TraceExit(gdb.FinishBreakpoint):
    def __init__(self, func, frame):
        super().__init__(frame=frame, internal=True)
        self.func = func
        self.silent = True

    def stop(self):
        log(f"<< EXIT  {self.func}")
        return False

# Load breakpoints from CSV
class TraceFromCSV(gdb.Command):
    def __init__(self):
        super().__init__("tracefromcsv", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        print(f"[+] Reading function names from: {CSV_PATH}")
        with open(CSV_PATH, newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                func = row['Function'].strip()
                if not func:
                    continue
                try:
                    TraceEntry(func)
                except Exception as e:
                    log(f"[!] Failed to set breakpoint on {func}: {e}")
        print("All breakpoints set. Use `continue` to begin tracing.")

TraceFromCSV()
