# GDB script to scan and dump valid memory regions
start = 0x00000000
end = 0x7E800000
step = 0x100000  # 1MB

for addr in range(start, end, step):
    try:
        gdb.execute(f"x/1x {addr}", to_string=True)
        out = f"mem_{addr:08x}.bin"
        gdb.execute(f"dump binary memory {out} {addr:#x} {addr + step:#x}")
        print(f"Dumped: {out}")
    except gdb.error:
        print(f"Skipped: {addr:#x}")
