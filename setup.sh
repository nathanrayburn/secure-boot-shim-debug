$#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")"  # Ensure we're running from the script's directory
ROOT_DIR=$(pwd)

# Paths
SHIM_DIR="${ROOT_DIR}/shim"
EDK2_DIR="${ROOT_DIR}/edk2"
EDK2PLATFORM_DIR="${ROOT_DIR}/edk2-platforms"
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
rm -rf "${SHIM_DIR}" "${EDK2_DIR}" "${EDK2PLATFORM_DIR}" "${EFITOOLS_DIR}" "${KEYS_DIR}" "${GRUB_DIR}" "${ISO_DIR}" "${IMG}" *.auth *.esl *.crt *.key *.cer shimx64* grubx64*

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
git clone https://github.com/tianocore/edk2-platforms.git "${ROOT_DIR}/edk2-platforms"

cd "${EDK2_DIR}"
git checkout 0d472346dffdbe40aa2ebac9b84bbd6b3ac7889e
git submodule update --init --recursive

echo "[*] Applying patched OvmfPkgX64.dsc..."
cp "${PATCHED_DSC}" "${EDK2_DIR}/OvmfPkg/OvmfPkgX64.dsc"

export PACKAGES_PATH="${EDK2_DIR}:${ROOT_DIR}/edk2-platforms/Silicon/Intel"
export PYTHON_COMMAND=python3
# Temporarily disable 'nounset' to allow unbound vars in edksetup.sh
set +u
source edksetup.sh
set -u
make -C BaseTools
build -a X64 -t GCC5 -b DEBUG -p OvmfPkg/OvmfPkgX64.dsc

cd "${ROOT_DIR}"
OVMF_CODE_FD="${EDK2_DIR}/Build/OvmfX64/DEBUG_GCC5/FV/OVMF_CODE.fd"
OVMF_VARS_FD="${EDK2_DIR}/Build/OvmfX64/DEBUG_GCC5/FV/OVMF_VARS.fd"
# Clone and build efitools
git clone https://git.kernel.org/pub/scm/linux/kernel/git/jejb/efitools.git "${EFITOOLS_DIR}"
cd "${EFITOOLS_DIR}"
make

# Generate Secure Boot keys
mkdir -p "${KEYS_DIR}"
cd "${KEYS_DIR}"

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

# Clone and build GRUB (make sure your fork uses gnulib_url=https://github.com/nathanrayburn/gnulib.git)
echo "[*] Cloning GRUB from GitHub fork..."
git clone https://github.com/nathanrayburn/grub.git "${GRUB_DIR}"
cd "${GRUB_DIR}"
./bootstrap
./configure --with-platform=efi --target=x86_64 --disable-werror --enable-sbat
make -j$(nproc)

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
echo "    FAT image:     ${IMG}"

echo "[*] Exporting OVMF firmware files..."
OVMF_OUTPUT_DIR="${ROOT_DIR}/ovmf"
rm -rf "${OVMF_OUTPUT_DIR}"
mkdir -p "${OVMF_OUTPUT_DIR}"

if [[ -f "${OVMF_CODE_FD}" ]]; then
    cp "${OVMF_CODE_FD}" "${OVMF_OUTPUT_DIR}/OVMF_CODE.fd"
else
    echo "[!] Error: OVMF_CODE.fd not found."
fi

if [[ -f "${OVMF_VARS_FD}" ]]; then
    cp "${OVMF_VARS_FD}" "${OVMF_OUTPUT_DIR}/OVMF_VARS.fd"
else
    echo "[!] Warning: OVMF_VARS.fd not found."
fi

echo "[✓] Firmware files copied to ${OVMF_OUTPUT_DIR}/"
