qemu-system-x86_64 \
  -m 2048 \
  -drive if=pflash,format=raw,readonly=on,file=ovmf/OVMF_CODE.fd \
  -drive if=pflash,format=raw,file=ovmf/OVMF_VARS.fd \
  -drive file=fat.img,format=raw \
  -s \
  -serial mon:stdio \
  -nographic \
  -debugcon file:debug.log \
  -global isa-debugcon.iobase=0x402
