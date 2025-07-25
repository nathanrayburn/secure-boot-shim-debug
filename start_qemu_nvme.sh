#!/bin/bash

# QEMU VM with Secure Boot (OVMF), NVMe, and IOMMU enabled
qemu-system-x86_64 \
  -machine q35,smm=on \
  -m 2048 \
  -cpu qemu64 \
  -drive if=pflash,format=raw,readonly=on,file=ovmf/OVMF_CODE.fd \
  -drive if=pflash,format=raw,file=ovmf/OVMF_VARS.fd \
  -global driver=cfi.pflash01,property=secure,value=on \
  -device intel-iommu,intremap=on \
  -drive id=nvme0,file=fat.img,format=raw,if=none \
  -device nvme,drive=nvme0,serial=NVME01,bootindex=1 \
  -s \
  -serial mon:stdio \
  -nographic \
  -debugcon file:debug.log \
  -global isa-debugcon.iobase=0x402
