#!/bin/bash

set -e

TARGET_DEV="/dev/nvme0n1"
IMG_SIZE_MB=128

echo "[*] WARNING: This will completely overwrite $TARGET_DEV"
read -p "Type 'YES' to continue: " confirm
if [ "$confirm" != "YES" ]; then
    echo "[!] Aborted."
    exit 1
fi

echo "[*] Cleaning up old files..."
rm -rf iso fat.img bootable.img esp.img

echo "[*] Preparing EFI tree..."
mkdir -p iso/EFI/Boot

echo "[*] Copying binaries..."
cp shimx64.efi iso/EFI/boot/bootx64.efi
cp grubx64.efi iso/EFI/boot/grubx64.efi

echo "[*] Creating ESP FAT image..."
dd if=/dev/zero of=esp.img bs=1M count=64
mkfs.vfat esp.img

echo "[*] Copying files into ESP image..."
mcopy -i esp.img -s iso/* ::/

echo "[*] Creating GPT-partitioned bootable image..."
dd if=/dev/zero of=bootable.img bs=1M count=$IMG_SIZE_MB

parted bootable.img --script mklabel gpt
parted bootable.img --script mkpart ESP fat32 1MiB 100%
parted bootable.img --script set 1 esp on

LOOP_DEV=$(losetup --find --show --partscan bootable.img)
echo "[*] Mapped to $LOOP_DEV"

echo "[*] Formatting ESP partition..."
mkfs.vfat ${LOOP_DEV}p1

echo "[*] Copying ESP contents to partition..."
mcopy -i ${LOOP_DEV}p1 -s iso/* ::/

sync

echo "[*] Cleaning up loop device..."
losetup -d $LOOP_DEV

echo "[*] Flashing to $TARGET_DEV ..."
read -p "Final confirmation: type 'FLASH' to continue: " confirm_flash
if [ "$confirm_flash" != "FLASH" ]; then
    echo "[!] Flash aborted."
    exit 1
fi

# Unmount any mounted partitions
echo "[*] Unmounting any partitions on $TARGET_DEV ..."
umount ${TARGET_DEV}p* || true

dd if=bootable.img of=$TARGET_DEV bs=4M status=progress
sync

echo "[✓] Flash complete."
echo "[*] You can now reboot the machine and boot from $TARGET_DEV for testing."
