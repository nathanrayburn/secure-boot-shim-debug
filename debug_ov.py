import gdb
import re
import subprocess
import os

class DebugOvmfCommand(gdb.Command):
    """Load symbols for OVMF modules from debug.log.
    Usage: debugovmf [build_dir] [debug_log]
    Default build_dir: Build/OvmfX64/DEBUG_GCC5/X64
    Default debug_log: debug.log
    """

    def __init__(self):
        super(DebugOvmfCommand, self).__init__("debugovmf", gdb.COMMAND_USER)

    def get_section_offsets(self, elf_file):
        try:
            output = subprocess.check_output(["objdump", "-h", elf_file]).decode()
            text_offset = None
            data_offset = None
            for line in output.splitlines():
                fields = line.strip().split()
                if len(fields) < 5:
                    continue
                name = fields[1]
                try:
                    vma = int(fields[3], 16)
                except ValueError:
                    continue
                if name == ".text":
                    text_offset = vma
                elif name == ".data":
                    data_offset = vma
            return text_offset, data_offset
        except subprocess.CalledProcessError as e:
            gdb.write(f"Error running objdump on {elf_file}: {e}\n")
            return None, None

    def invoke(self, arg, from_tty):
        args = arg.split()
        build_dir = args[0] if len(args) >= 1 else "Build/OvmfX64/DEBUG_GCC5/X64"
        debug_log = args[1] if len(args) >= 2 else "debug.log"

        if not os.path.isfile(debug_log):
            gdb.write(f"Missing {debug_log}\n", gdb.STDERR)
            return

        log_pattern = re.compile(r'Loading .* at (0x[0-9a-fA-F]+).* ([\w\d]+\.efi)')

        with open(debug_log) as f:
            for line in f:
                match = log_pattern.search(line)
                if not match:
                    continue

                base_addr = int(match.group(1), 16)
                efi_file = match.group(2)
                debug_file = os.path.join(build_dir, efi_file.replace(".efi", ".debug"))

                if not os.path.isfile(debug_file):
                    gdb.write(f"# Skipping {efi_file}: Not found at {debug_file}\n")
                    continue

                text_off, data_off = self.get_section_offsets(debug_file)
                if text_off is None or data_off is None:
                    gdb.write(f"# Skipping {efi_file}: Section offsets not found\n")
                    continue

                text_addr = base_addr + text_off
                data_addr = base_addr + data_off

                try:
                    gdb.execute(f'add-symbol-file {debug_file} 0x{text_addr:X} -s .data 0x{data_addr:X}')
                    gdb.write(f"✔ Loaded {efi_file} at 0x{text_addr:X}\n")
                except gdb.error as e:
                    gdb.write(f"# Failed to add symbols for {efi_file}: {e}\n")

DebugOvmfCommand()
