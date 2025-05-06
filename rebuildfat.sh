#!/bin/bash

echo "[*] Cleaning up old files..."
rm -rf iso fat.img
echo "[*] Preparing ISO tree..."
mkdir -p iso/EFI/Boot

echo "[*] Copying binaries..."

#cp shimx64-signed.efi iso/EFI/Boot/BOOTX64.efi
cp grubx64-signed.efi iso/EFI/Boot/grubx64.efi
cp efitools/KeyTool.efi iso/EFI/Boot/BOOTX64.efi

echo "[*] Copying Secure Boot keys (.der)..."

cp keys/DB.auth keys/KEK.auth keys/PK.auth iso/

echo "[*] Creating FAT image..."
dd if=/dev/zero of=fat.img bs=1M count=64
mkfs.vfat fat.img

echo "[*] Copying files into FAT image..."
mcopy -i fat.img -s iso/* ::/

echo "[✓] FAT image rebuilt successfully as fat.img"
