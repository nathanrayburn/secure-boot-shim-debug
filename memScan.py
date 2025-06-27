import gdb

# === USER CONFIG ===

der_path = "/Volumes/data/uefi_build/empty-env 2/env/keys/grub.der"
match_length = 16                

start = 0x00000000                
end = 0x7E800000
chunk_size = 0x1000                  # 4KB chunks

# === LOAD DER FILE ===

with open(der_path, "rb") as f:
    der_bytes = f.read()

if len(der_bytes) < match_length:
    print(f"Error: DER file only has {len(der_bytes)} bytes, less than requested match_length {match_length}.")
    raise SystemExit

pattern = der_bytes[:match_length]
print(f"[+] Loaded DER file, using first {match_length} bytes for matching:")
print(' '.join(f'{b:02x}' for b in pattern))

# === SCANNER ===

inf = gdb.inferiors()[0]
found = False

print(f"[+] Starting memory scan from {start:#x} to {end:#x}")

addr = start
while addr < end:
    try:
        mem = inf.read_memory(addr, chunk_size).tobytes()
        idx = mem.find(pattern)
        if idx != -1:
            found_addr = addr + idx
            print(f"\n[+] Pattern found at address: {found_addr:#x}")
            found = True
    except gdb.MemoryError:
        # Skip unreadable pages silently
        pass
    addr += chunk_size

if not found:
    print("\n[-] Pattern not found in the specified range.")
else:
    print("\n[+] Scan complete.")
