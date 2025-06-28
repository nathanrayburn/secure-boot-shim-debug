import pefile

pe = pefile.PE("grubx64-signed.efi")
cert_dir = pe.OPTIONAL_HEADER.DATA_DIRECTORY[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_SECURITY"]]
offset = cert_dir.VirtualAddress
size = cert_dir.Size

with open("grubx64-signed.efi", "rb") as f:
    f.seek(offset)
    data = f.read(size)

with open("grub.pkcs7", "wb") as out:
    out.write(data[8:])  # skip WIN_CERTIFICATE header
