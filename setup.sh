#!/bin/bash
set -euo pipefail

ROOT_DIR=$(pwd)

# Paths
SHIM_DIR="${ROOT_DIR}/shim"
EDK2_DIR="${ROOT_DIR}/edk2"
EFITOOLS_DIR="${ROOT_DIR}/efitools"
KEYS_DIR="${ROOT_DIR}/keys"
GRUB_DIR="${ROOT_DIR}/grub"
ISO_DIR="${ROOT_DIR}/iso"
IMG="fat.img"

PATCHED_SHIM="${ROOT_DIR}/patched_shim.c"
PATCHED_DSC="${ROOT_DIR}/patched_OvmfPkgX64.dsc"

# Check for required patch files
if [[ ! -f "${PATCHED_SHIM}" || ! -f "${PATCHED_DSC}" ]]; then
    echo "[!] Error: Missing patched_shim.c or patched_OvmfPkgX64.dsc in ${ROOT_DIR}"
    exit 1
fi

echo "[*] Cleaning old artifacts..."
rm -rf "${SHIM_DIR}" "${EDK2_DIR}" "${EFITOOLS_DIR}" "${KEYS_DIR}" "${GRUB_DIR}" "${ISO_DIR}" "${IMG}" *.auth *.esl *.crt *.key *.cer shimx64* grubx64*

# Clone shim and apply patched shim.c
echo "[*] Cloning Shim..."
git clone https://github.com/rhboot/shim.git "${SHIM_DIR}"
cd "${SHIM_DIR}"
make update

echo "[*] Applying patched shim.c..."
cp "${PATCHED_SHIM}" "${SHIM_DIR}/shim.c"

make clean
cd "${ROOT_DIR}"

# Clone EDK2 and apply patched OvmfPkgX64.dsc
echo "[*] Cloning EDK2..."
git clone https://github.com/tianocore/edk2.git "${EDK2_DIR}"
cd "${EDK2_DIR}"
git submodule update --init --recursive

echo "[*] Applying patched OvmfPkgX64.dsc with Secure Boot enabled..."
cp "${PATCHED_DSC}" "${EDK2_DIR}/OvmfPkg/OvmfPkgX64.dsc"

# Build OVMF with Secure Boot enabled
source edksetup.sh
make -C BaseTools
build -a X64 -t GCC5 -b DEBUG -p OvmfPkg/OvmfPkgX64.dsc
OVMF_FD="${EDK2_DIR}/Build/OvmfX64/DEBUG_GCC5/FV/OVMF.fd"
cd "${ROOT_DIR}"

# Build efitools and generate Secure Boot keys
git clone https://git.kernel.org/pub/scm/linux/kernel/git/jejb/efitools.git "${EFITOOLS_DIR}"
cd "${EFITOOLS_DIR}"
make

mkdir -p "${KEYS_DIR}"
cd "${KEYS_DIR}"

# Generate Secure Boot keys and certs
openssl req -new -x509 -newkey rsa:2048 -keyout PK.key -out PK.crt -days 3650 -nodes -subj "/CN=Platform Key/"
openssl req -new -x509 -newkey rsa:2048 -keyout KEK.key -out KEK.crt -days 3650 -nodes -subj "/CN=Key Exchange Key/"
openssl req -new -x509 -newkey rsa:2048 -keyout DB.key -out DB.crt -days 3650 -nodes -subj "/CN=DB Key/"

openssl x509 -req -in <(openssl x509 -in KEK.crt -x509toreq -signkey KEK.key) -CA PK.crt -CAkey PK.key -CAcreateserial -out KEK.crt -days 3650
openssl x509 -req -in <(openssl x509 -in DB.crt -x509toreq -signkey DB.key) -CA KEK.crt -CAkey KEK.key -CAcreateserial -out DB.crt -days 3650

cert-to-efi-sig-list -g "$(uuidgen)" PK.crt  PK.esl
cert-to-efi-sig-list -g "$(uuidgen)" KEK.crt KEK.esl
cert-to-efi-sig-list -g "$(uuidgen)" DB.crt  DB.esl

sign-efi-sig-list -k PK.key -c PK.crt PK  PK.esl  PK.auth
sign-efi-sig-list -k PK.key -c PK.crt KEK KEK.esl KEK.auth
sign-efi-sig-list -k KEK.key -c KEK.crt db  DB.esl  DB.auth

# Generate GRUB signing key and embedded cert
openssl req -new -x509 -newkey rsa:2048 -keyout grub.key -out grub.crt -days 3650 -nodes -subj "/CN=Grub Signing Cert/"
openssl x509 -in grub.crt -outform DER -out grub.cer

# Rebuild shim with embedded cert
cd "${SHIM_DIR}"
make clean
make V=1 ENABLE_SHIM_DEVEL=1 VENDOR_CERT_FILE="${KEYS_DIR}/grub.cer" OPTIMIZATIONS="-O0 -g3 -gdwarf-4"

cd "${ROOT_DIR}"
sbsign --key "${KEYS_DIR}/DB.key" --cert "${KEYS_DIR}/DB.crt" \
  --output shimx64-signed.efi "${SHIM_DIR}/shimx64.efi"

# Clone and build GRUB from your GitHub fork
echo "[*] Cloning GRUB from GitHub fork with stable gnulib..."
git clone https://github.com/nathanrayburn/grub.git "${GRUB_DIR}"
cd "${GRUB_DIR}"
./bootstrap
./configure --with-platform=efi --target=x86_64 --disable-werror --enable-sbat
make -j$(nproc)

# Create SBAT metadata
cat <<EOF > sbat.csv
sbat,1,SBAT Version,https://github.com/rhboot/shim/blob/main/SBAT.md
bootloader.nathan,1,HEIG,bootloader.nathan,1,https://heig.ch/
EOF

./grub-mkimage --directory=./grub-core --sbat=../sbat.csv \
  -O x86_64-efi -o ../grubx64.efi -p /EFI/boot part_gpt fat ext2 normal linux configfile search echo

cd "${ROOT_DIR}"
sbsign --key keys/grub.key --cert keys/grub.crt --output grubx64-signed.efi grubx64.efi

# Create FAT image with EFI binaries
mkdir -p "${ISO_DIR}/EFI/Boot"
cp shimx64-signed.efi "${ISO_DIR}/EFI/Boot/BOOTX64.EFI"
cp grubx64-signed.efi "${ISO_DIR}/EFI/Boot/grubx64.efi"

dd if=/dev/zero of="${IMG}" bs=1M count=64
mkfs.vfat "${IMG}"
mcopy -i "${IMG}" -s iso/* ::/

echo "[✓] Secure Boot environment built successfully."
echo "    OVMF firmware: ${OVMF_FD}"
echo "    FAT image:     ${IMG}"
