# Secure Boot UEFI Environment – Required Packages

This environment is used to build and debug a full UEFI Secure Boot chain including:
- Shim (with debug symbols)
- GRUB (with SBAT metadata)
- OVMF firmware (EDK II)
- FAT disk image
- Custom Secure Boot key hierarchy

The following packages are required on Debian/Ubuntu-based systems.

---

## 📦 APT Packages

Install all required packages with:

```bash
sudo apt update
sudo apt install \
  build-essential gcc g++ make pkg-config autoconf automake libtool m4 bison flex git iasl \
  uuid-dev nasm qemu-system-x86 \
  sbsigntool efitools openssl libssl-dev \
  mtools dosfstools \
  gettext texinfo autopoint gawk \
  libefivar-dev gnu-efi \
  libfile-slurp-perl help2man
```
