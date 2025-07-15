#!/usr/bin/env python3

import os
import sys
import struct

def get_total_ram():
    try:
        with open('/proc/meminfo', 'r') as f:
            for line in f:
                if line.startswith('MemTotal:'):
                    parts = line.split()
                    # MemTotal is in kB
                    return int(parts[1]) * 1024
    except Exception as e:
        print(f"Could not determine total RAM size: {e}")
        sys.exit(1)
    print("Could not determine total RAM size from /proc/meminfo")
    sys.exit(1)
    
def read_pci_device(device_path, offset, length):
    try:
        with open(device_path, 'rb') as f:
            # Use os.pread to read from the offset
            data = os.pread(f.fileno(), length, offset)
            return data
    except Exception as e:
        print(f"Error reading from device: {e}")
        sys.exit(1)

def print_hex(data):
    # Print hex dump, 16 bytes per line
    for i in range(0, len(data), 16):
        line = data[i:i+16]
        hex_bytes = ' '.join(f'{b:02x}' for b in line)
        ascii_bytes = ''.join((chr(b) if 32 <= b < 127 else '.') for b in line)
        print(f'{i:08x}  {hex_bytes:<48}  {ascii_bytes}')
def dump_full_ram(start_offset, chunk_size, total_ram, out_file):
    with open(out_file, 'wb') as out:
        offset = start_offset
        while offset < total_ram:
            to_read = min(chunk_size, total_ram - offset)
            data = read_pci_device(device, offset, to_read)
            if data is None:
                print(f"\n[!] Stopping at offset {offset:#x} due to read error.")
                break
            out.write(data)
            offset += to_read
            print(f"\r[+] Dumped {offset / (1024 ** 2):.2f} MiB / {total_ram / (1024 ** 2):.2f} MiB", end='', flush=True)
    print(f"\n[+] Dump completed. Output saved to {out_file}")
if __name__ == '__main__':
    if len(sys.argv) == 5 and sys.argv[4] == '--full-dump':
        device = sys.argv[1]
        offset_str = sys.argv[2]
        length_str = sys.argv[3]
        try:
            start_offset = int(offset_str, 0)
            chunk_size = int(length_str)  # base 10
        except ValueError:
            print("Offset and length must be integers (decimal or hex for offset, decimal for length)")
            sys.exit(1)

        total_ram = get_total_ram()
        print(f"[+] Detected total RAM: {total_ram / (1024 ** 2):.2f} MiB")
        out_file = "memory_dump.bin"
        dump_full_ram(start_offset, chunk_size, total_ram, out_file)
    elif len(sys.argv) != 4:
        print(f"Usage: {sys.argv[0]} <device> <offset> <length>")
        print("  <device>  Path to character device (e.g. /dev/pci-io)")
        print("  <offset>  Offset to start reading (in hex or decimal)")
        print("  <length>  Number of bytes to read")
        sys.exit(1)

    device = sys.argv[1]
    offset_str = sys.argv[2]
    length_str = sys.argv[3]

    # Allow offset to be in hex (e.g. 0x10)
    try:
        offset = int(offset_str, 0)
        length = int(length_str, 0)
    except ValueError:
        print("Offset and length must be integers (decimal or hex)")
        sys.exit(1)

    data = read_pci_device(device, offset, length)
    print_hex(data)

