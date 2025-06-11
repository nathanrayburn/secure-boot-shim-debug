import gdb

class NvmeReadDump(gdb.FinishBreakpoint):
    def __init__(self, buffer, blocks):
        super().__init__(gdb.newest_frame(), internal=True)
        self.buffer = int(buffer)
        self.size = int(blocks) * 512

    def stop(self):
        filename = f"nvme_read_dump_{self.buffer:x}.bin"
        gdb.execute(f"dump memory {filename} 0x{self.buffer:x} 0x{self.buffer + self.size:x}")
        gdb.write(f"Dumped NvmeRead buffer to {filename} ({self.size} bytes)\n")
        return False  # Don't stop at the return

class NvmeHook(gdb.Breakpoint):
    def __init__(self):
        super().__init__("NvmeRead", gdb.BP_BREAKPOINT, internal=False)

    def stop(self):
        frame = gdb.newest_frame()
        args = frame.read_var("Buffer"), frame.read_var("Blocks")
        NvmeReadDump(args[0], args[1])
        return False  # Don't stop at entry

NvmeHook()
print("NvmeRead hook installed (will dump Buffer after each call)")
