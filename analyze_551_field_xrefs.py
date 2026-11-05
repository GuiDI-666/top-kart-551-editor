from __future__ import annotations

import bisect
import struct
from pathlib import Path

import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
from capstone.x86 import X86_OP_MEM, X86_REG_RIP


DLL = Path(__file__).with_name("Top-Kart.dll")
TARGETS = (
    "m_iMinTurnSpeed",
    "m_iDirKeyForce",
    "m_iDirKeyTwist",
    "m_iBannerTwist",
    "m_iBannerKeyTwist",
    "m_iBannerVecForce",
    "m_iMaxWec",
    "m_iSuaiJianTwist",
    "m_iDirUpKeyForce",
    "m_iBannerHeadForce",
    "m_iSlidFricForce",
    "m_iRollFricForce",
    "m_iStartWec",
)


def main() -> None:
    pe = pefile.PE(str(DLL), fast_load=False)
    image_base = pe.OPTIONAL_HEADER.ImageBase
    raw = DLL.read_bytes()
    text_section = next(section for section in pe.sections if section.Name.rstrip(b"\0") == b".text")
    text = text_section.get_data()
    text_va = image_base + text_section.VirtualAddress

    names: dict[int, str] = {}
    for target in TARGETS:
        needle = target.encode("ascii") + b"\0"
        start = 0
        while True:
            file_offset = raw.find(needle, start)
            if file_offset < 0:
                break
            rva = pe.get_rva_from_offset(file_offset)
            names[image_base + rva] = target
            start = file_offset + 1

    pdata = next(section for section in pe.sections if section.Name.rstrip(b"\0") == b".pdata")
    functions = []
    pdata_raw = pdata.get_data()
    for offset in range(0, len(pdata_raw) - 11, 12):
        begin, end, unwind = struct.unpack_from("<III", pdata_raw, offset)
        if begin and begin < end:
            functions.append((image_base + begin, image_base + end, unwind))
    functions.sort()
    begins = [item[0] for item in functions]

    md = Cs(CS_ARCH_X86, CS_MODE_64)
    md.detail = True
    md.skipdata = True
    refs: list[tuple[int, int, str, str]] = []
    for insn in md.disasm(text, text_va):
        if insn.id == 0:
            continue
        for operand in insn.operands:
            if operand.type != X86_OP_MEM or operand.mem.base != X86_REG_RIP:
                continue
            destination = insn.address + insn.size + operand.mem.disp
            name = names.get(destination)
            if name:
                refs.append((insn.address, destination, name, f"{insn.mnemonic} {insn.op_str}"))

    print(f"strings={len(names)} refs={len(refs)}")
    for address, string_va, name, instruction in refs:
        pos = bisect.bisect_right(begins, address) - 1
        function = functions[pos] if pos >= 0 and address < functions[pos][1] else None
        if function:
            begin, end, _ = function
            begin_rva = begin - image_base
            code = pe.get_data(begin_rva, min(end - begin, 0x2000))
            listing = list(md.disasm(code, begin))
            index = next((i for i, item in enumerate(listing) if item.address == address), 0)
            print(f"\n{name} string={string_va:#x} xref={address:#x} function={begin:#x}-{end:#x}")
            for item in listing[max(0, index - 10):index + 16]:
                marker = ">" if item.address == address else " "
                print(f"{marker} {item.address:#x}: {item.mnemonic:7} {item.op_str}")
        else:
            print(f"\n{name} string={string_va:#x} xref={address:#x} function=? {instruction}")


if __name__ == "__main__":
    main()
