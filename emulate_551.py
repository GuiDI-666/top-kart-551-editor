from pathlib import Path
import os
import re
import struct
import sys

import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
from capstone.x86 import X86_OP_MEM, X86_OP_REG
import unicorn.x86_const as ux
from unicorn import (
    Uc, UC_ARCH_X86, UC_MODE_64, UC_HOOK_CODE, UC_HOOK_MEM_INVALID,
    UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE,
)
from unicorn.x86_const import *


def find_top_kart_dll() -> Path:
    candidates = []
    configured = os.environ.get("TOP_KART_DLL")
    if configured:
        candidates.append(Path(configured))
    here = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
    candidates.extend([
        here / "Top-Kart.dll",
        here.parent / "Top-Kart.dll",
    ])
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(
        "未找到 Top-Kart.dll；请放到工具目录，或设置 TOP_KART_DLL 环境变量"
    )


DLL = find_top_kart_dll()
IMAGE_BASE = 0x180000000
IMAGE_SIZE = 0x3200000
STACK_BASE = 0x300000000
STACK_SIZE = 0x200000
OBJECT_BASE = 0x310000000
OBJECT_SIZE = 0x300000
DATA_BASE = 0x320000000
DATA_SIZE = 0x200000
ARG_BASE = 0x330000000
ARG_SIZE = 0x10000
SENTINEL = 0x340000000


def align_up(value: int, alignment: int = 0x1000) -> int:
    return (value + alignment - 1) & ~(alignment - 1)


def load_image(uc: Uc) -> None:
    pe = pefile.PE(str(DLL), fast_load=False)
    uc.mem_map(IMAGE_BASE, IMAGE_SIZE)
    headers = DLL.read_bytes()[: pe.OPTIONAL_HEADER.SizeOfHeaders]
    uc.mem_write(IMAGE_BASE, headers)
    for section in pe.sections:
        raw = section.get_data()
        if raw:
            uc.mem_write(IMAGE_BASE + section.VirtualAddress, raw)


def load_yaml_data(path: Path) -> bytes:
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    # Some files wrap exactly between the `0x` prefix and its two digits.
    text = re.sub(r"0x\s*\r?\n\s*([0-9A-Fa-f]{2})(?=,)", r"0x\1", text)
    # The root capture inserts a bare `0x,` as a visual group separator. It is
    # not a byte (real zero bytes are written as 0x00/0x0 in normal exports).
    tokens = re.findall(r"0x(?:[0-9A-Fa-f]{2})?|\b\d+\b", text)
    out = bytearray()
    for token in tokens:
        if token.lower() == "0x":
            continue
        elif token.lower().startswith("0x"):
            out.append(int(token, 16) & 0xFF)
        else:
            out.append(int(token) & 0xFF)
    return bytes(out)


class Emulator:
    def __init__(self):
        self.uc = Uc(UC_ARCH_X86, UC_MODE_64)
        load_image(self.uc)
        self.uc.mem_map(STACK_BASE, STACK_SIZE)
        self.uc.mem_map(OBJECT_BASE, OBJECT_SIZE)
        self.uc.mem_map(DATA_BASE, DATA_SIZE)
        self.uc.mem_map(ARG_BASE, ARG_SIZE)
        self.uc.mem_map(SENTINEL, 0x1000)
        self.uc.mem_write(SENTINEL, b"\x90\x90\xC3")
        self.instructions = 0
        self.last_rip = 0
        self.trace_enabled = False
        self.pending_input = None
        self.decode_events = []
        self.decode_snapshots = {}
        self.uc.hook_add(UC_HOOK_CODE, self._on_code)
        self.uc.hook_add(UC_HOOK_MEM_INVALID, self._on_invalid)
        self.uc.hook_add(UC_HOOK_MEM_READ, self._on_read, begin=DATA_BASE, end=DATA_BASE + DATA_SIZE - 1)
        self.uc.hook_add(UC_HOOK_MEM_WRITE, self._on_object_write, begin=OBJECT_BASE, end=OBJECT_BASE + OBJECT_SIZE - 1)

    def _on_code(self, uc, address, size, user_data):
        self.instructions += 1
        self.last_rip = address
        if address == SENTINEL:
            uc.emu_stop()

    def _on_invalid(self, uc, access, address, size, value, user_data):
        print(f"invalid memory access={access} address={address:#x} size={size} rip={self.last_rip:#x}")
        return False

    def _on_read(self, uc, access, address, size, value, user_data):
        if self.trace_enabled and size == 1:
            self.pending_input = address - DATA_BASE
            rsp = uc.reg_read(UC_X86_REG_RSP)
            page = rsp & ~0xFFF
            self.pending_snapshot = (
                uc.context_save(), address, self.last_rip, page,
                bytes(uc.mem_read(page, 0x2000)),
            )

    def _on_object_write(self, uc, access, address, size, value, user_data):
        if self.trace_enabled and self.pending_input is not None:
            self.decode_events.append((self.pending_input, address - OBJECT_BASE, size, value, self.last_rip))
            self.decode_snapshots.setdefault(self.last_rip, self.pending_snapshot)
            self.pending_input = None

    def decoder_table(self, write_rip: int):
        context, input_address, read_rip, stack_page, stack_data = self.decode_snapshots[write_rip]
        md = Cs(CS_ARCH_X86, CS_MODE_64)
        md.detail = True
        insn = next(md.disasm(bytes(self.uc.mem_read(write_rip, 15)), write_rip))
        following = list(md.disasm(bytes(self.uc.mem_read(write_rip, 64)), write_rip))
        # Most VarInt decoders expose the decoded byte in the register tested
        # immediately after the memory update.  A few one-byte protocol fields
        # (notably SuperJetType) use a direct `mov [mem], reg` and have no test.
        if (insn.mnemonic == "mov" and len(insn.operands) == 2
                and insn.operands[0].type == X86_OP_MEM
                and insn.operands[1].type == X86_OP_REG):
            reg_name = insn.reg_name(insn.operands[1].reg).upper()
        else:
            test_insn = next(
                (item for item in following[1:]
                 if item.mnemonic == "test" and len(item.operands) == 2
                 and item.operands[0].type == X86_OP_REG
                 and item.operands[1].type == X86_OP_REG
                 and item.operands[0].reg == item.operands[1].reg),
                None,
            )
            if test_insn is None:
                raise RuntimeError(f"no continuation test after {write_rip:#x}: {insn.mnemonic} {insn.op_str}")
            reg_name = test_insn.reg_name(test_insn.operands[0].reg).upper()
        reg_id = getattr(ux, f"UC_X86_REG_{reg_name}")
        original_input = bytes(self.uc.mem_read(input_address, 1))
        table = []
        self.trace_enabled = False
        for encoded in range(256):
            self.uc.context_restore(context)
            self.uc.mem_write(stack_page, stack_data)
            self.uc.mem_write(input_address, bytes([encoded]))
            self.uc.emu_start(read_rip, write_rip, count=2000)
            if self.uc.reg_read(UC_X86_REG_RIP) != write_rip:
                raise RuntimeError(f"decoder probe did not reach {write_rip:#x} for {encoded:#x}")
            table.append(self.uc.reg_read(reg_id) & 0xFF)
        self.uc.mem_write(input_address, original_input)
        return table

    def call(self, address: int, rcx=0, rdx=0, r8=0, r9=0):
        rsp = STACK_BASE + STACK_SIZE - 0x1000
        rsp &= ~0xF
        rsp -= 8
        self.uc.mem_write(rsp, struct.pack("<Q", SENTINEL))
        self.uc.reg_write(UC_X86_REG_RSP, rsp)
        self.uc.reg_write(UC_X86_REG_RCX, rcx)
        self.uc.reg_write(UC_X86_REG_RDX, rdx)
        self.uc.reg_write(UC_X86_REG_R8, r8)
        self.uc.reg_write(UC_X86_REG_R9, r9)
        before = self.instructions
        self.uc.emu_start(address, SENTINEL + 1, count=200_000_000)
        return self.uc.reg_read(UC_X86_REG_RAX), self.instructions - before


def main() -> int:
    if len(sys.argv) < 2:
        print("用法: python emulate_551.py <sample.yml> [输出目录]", file=sys.stderr)
        print("示例: python emulate_551.py samples/100047.yml out", file=sys.stderr)
        return 2
    sample = Path(sys.argv[1])
    out_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path.cwd()
    out_dir.mkdir(parents=True, exist_ok=True)
    data = load_yaml_data(sample)
    print(f"sample={sample} bytes={len(data)} head={data[:24].hex(' ')}")

    emu = Emulator()
    result, count = emu.call(0x1808A7110, OBJECT_BASE)
    print(f"constructor result={result:#x} instructions={count}")

    emu.uc.mem_write(DATA_BASE, data)
    payload_base = DATA_BASE + 2
    emu.uc.mem_write(ARG_BASE, struct.pack("<Q", payload_base))
    emu.uc.mem_write(ARG_BASE + 8, struct.pack("<I", 0))
    emu.trace_enabled = True
    result, count = emu.call(
        0x1808A5FD0,
        OBJECT_BASE,
        ARG_BASE,
        DATA_BASE + len(data),
        ARG_BASE + 8,
    )
    offset = struct.unpack("<I", emu.uc.mem_read(ARG_BASE + 8, 4))[0]
    emu.trace_enabled = False
    print(f"parser result={result:#x} offset={offset}/{len(data) - 2} instructions={count}")
    Path(out_dir / "safe_551_object.bin").write_bytes(
        bytes(emu.uc.mem_read(OBJECT_BASE, 2132944))
    )
    trace_path = Path(out_dir / "safe_551_decode_events.csv")
    trace_path.write_text(
        "input_offset,object_offset,size,value,rip\n" + "".join(
            f"{i:#x},{o:#x},{s},{v:#x},{rip:#x}\n" for i, o, s, v, rip in emu.decode_events
        ),
        encoding="utf-8",
    )
    print(f"decode events={len(emu.decode_events)} trace={trace_path}")
    probe_rip = 0x180899BB3
    if (result & 0xFF) == 1 and probe_rip in emu.decode_snapshots:
        table = emu.decoder_table(probe_rip)
        inverse = [0] * 256
        for encoded, decoded in enumerate(table):
            inverse[decoded] = encoded
        print(
            f"codec {probe_rip:#x}: bijective={len(set(table)) == 256} "
            f"encode(0x70)={inverse[0x70]:#x} encode(0xae)={inverse[0xae]:#x}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
