from __future__ import annotations

import bisect
import collections
import os
import struct
import sys
from pathlib import Path

import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
from capstone.x86 import X86_OP_MEM, X86_REG_RIP


def _resolve_network_dll() -> Path:
    """定位 Network.dll：优先命令行参数，其次 NETWORK_DLL 环境变量，最后脚本目录。"""
    if len(sys.argv) > 1:
        return Path(sys.argv[1])
    configured = os.environ.get("NETWORK_DLL")
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parent / "Network.dll"


DLL = _resolve_network_dll()
TARGETS = (
    "m_iBaseTurnRate", "m_iVolatileTurnRate", "m_iMaxTurnSpeed", "m_iMinTurnSpeed",
    "m_iMaxAccuTime", "m_iBaseAccuRate", "m_iMaxAffectSpeed", "m_iGravity",
    "m_iAdditionalLocalZSpeed", "m_iStartVec", "m_iEndVecFist", "m_iEndVecSecon",
    "m_iDirKeyForce", "m_iDirKeyTwist", "m_iBannerTwist", "m_iBannerKeyTwist",
    "m_iBannerVecForce", "m_iBannerHeadForce", "m_iSlidFricForce", "m_iRollFricForce",
    "m_iStartWec", "m_iMaxWec", "m_iSuaiJianTwist", "m_iDirUpKeyForce",
    "m_iCrashCompensatePower", "m_iDefenseRate", "m_iEnergyConvert",
    "m_iCollisionRadius", "m_iCollisionLength", "m_iCollisionWidth",
    "m_iCollisionHeight", "m_iCollisionLostCtrlTime", "m_iBoxLength", "m_iBoxWidth",
    "m_iBoxHeight", "m_iAdjustOffset", "m_iAdjustPickGap", "m_iAdjustRemoteOffset",
    "m_iAdjustBevelOffset", "m_iControllerOffset",
)


def main():
    pe = pefile.PE(str(DLL), fast_load=False)
    image_base = pe.OPTIONAL_HEADER.ImageBase
    raw = DLL.read_bytes()
    text_section = next(section for section in pe.sections if section.Name.rstrip(b"\0") == b".text")
    text = text_section.get_data()
    text_va = image_base + text_section.VirtualAddress
    string_names = {}
    for name in TARGETS:
        start = 0
        needle = name.encode()
        while True:
            offset = raw.find(needle, start)
            if offset < 0:
                break
            string_names[image_base + pe.get_rva_from_offset(offset)] = name
            start = offset + 1

    pdata = next(section for section in pe.sections if section.Name.rstrip(b"\0") == b".pdata")
    functions = []
    for offset in range(0, len(pdata.get_data()) - 11, 12):
        begin, end, _ = struct.unpack_from("<III", pdata.get_data(), offset)
        if begin and begin < end:
            functions.append((image_base + begin, image_base + end))
    functions.sort()
    begins = [item[0] for item in functions]

    md = Cs(CS_ARCH_X86, CS_MODE_64)
    md.detail = True
    md.skipdata = True
    grouped = collections.defaultdict(list)
    for insn in md.disasm(text, text_va):
        if insn.id == 0:
            continue
        for operand in insn.operands:
            if operand.type != X86_OP_MEM or operand.mem.base != X86_REG_RIP:
                continue
            target = insn.address + insn.size + operand.mem.disp
            name = string_names.get(target)
            if not name:
                continue
            pos = bisect.bisect_right(begins, insn.address) - 1
            if pos >= 0 and insn.address < functions[pos][1]:
                grouped[functions[pos][0]].append((insn.address, name))

    for function, refs in sorted(grouped.items(), key=lambda item: -len(item[1])):
        unique = {name for _, name in refs}
        if len(unique) < 5:
            continue
        print(f"function={function:#x} refs={len(refs)} unique={len(unique)}")
        for address, name in refs:
            print(f"  {address:#x} {name}")


if __name__ == "__main__":
    main()
