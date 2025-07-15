#!/usr/bin/env python3

import os
import sys

def get_file_size(path):
    try:
        return os.path.getsize(path)
    except Exception as e:
        print(f"Could not get file size: {e}")
        sys.exit(1)

def write_pci_device(device_path, offset, data):
    try:
        with open(device_path, 'wb') as f:
            written = os.pwrite(f.fileno(), data, offset)
            return written
    except Exception as e:
        print(f"Error writing to device: {e}")
        sys.exit(1)

def write_file_to_pci_device(device, offset, input_file, chunk_size=0x1000):
    file_size = get_file_size(input_file)
    written_total = 0

    with open(input_file, 'rb') as f:
        while written_total < file_size:
            to_read = min(chunk_size, file_size - written_total)
            chunk = f.read(to_read)
            if not chunk:
                print("\n[!] Unexpected end of file.")
                break

            written = write_pci_device(device, offset + written_total, chunk)
            if written != len(chunk):
                print(f"\n[!] Partial write at offset {offset + written_total:#x}. Written {written} bytes, expected {len(chunk)}.")
                break

            written_total += written
            print(f"\r[+] Written {written_total / 1024:.2f} KiB / {file_size / 1024:.2f} KiB", end='', flush=True)

    print(f"\n[+] Write completed. Total {written_total} bytes written to {device} at offset {offset:#x}.")

if __name__ == '__main__':
    if len(sys.argv) != 4:
        print(f"Usage: {sys.argv[0]} <device> <offset> <input_file>")
        print("  <device>      Path to character device (e.g. /dev/pci-io)")
        print("  <offset>      Offset to start writing (hex or decimal)")
        print("  <input_file>  Path to binary file to write into memory")
        sys.exit(1)

    device = sys.argv[1]
    offset_str = sys.argv[2]
    input_file = sys.argv[3]

    try:
        offset = int(offset_str, 0)
    except ValueError:
        print("Offset must be an integer (decimal or hex)")
        sys.exit(1)

    write_file_to_pci_device(device, offset, input_file)