#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Top-Kart 551 密文的保留式编辑后端。

读取时调用原 DLL 的安全协议解析器；写入时只替换已确认字段的
VarInt/逐字段字节置换，未映射数据保持逐字节不变。
"""

from dataclasses import dataclass
from pathlib import Path
import copy
import struct
import sys
from typing import Dict, Iterable, List

from emulate_551 import Emulator, DATA_BASE, ARG_BASE, OBJECT_BASE, load_yaml_data


PARSER = 0x1808A5FD0
CONSTRUCTOR = 0x1808A7110
RECORD_BASES = (0x10, 0xAD980, 0x15B268, 0x208B54)
RECORD_SIZE = 0x8AD8
INTERNAL_ID_REL = 0x26F4

SUPERJET_TYPE_REL = 0x3D4D
SUPERJET_BLOCK_FIRST_REL = 0x415C
SUPERJET_BLOCK_LIMIT_REL = 0x4250
POST_JET_FIELD_REL = 0x4754

# 第 5 个 0x100 喷射配置对象的协议编码。取自当前 DLL/服务端已验证的
# 至尊-踏月配置，解码值为 6900, 3360, 180, 10, 18000, 777 等。
# 普通车切到超级喷时插入此完整对象；最终仍由 DLL 回读确认。
DEFAULT_SUPERJET_BLOCK = bytes.fromhex(
    "0d355732e400a90ac1d70101010101010101757c0758810000000000000000"
)

SCALAR_FIELDS = {
    # 694 份有外部车型标签的服务端样本完全吻合：4=普通，5=超级喷。
    "SuperJetType": SUPERJET_TYPE_REL,
    "NitroPower": 0x3D5C,
    "NitroDuration": 0x3D64,
    "SmallJetPower": 0x3E5C,
    "SmallJetDuration": 0x3E64,
    "CollectEfficiency": 0x405C,
    "BannerTwist": 0x4754,
    "DirKeyTwist": 0x4CD4,
    "BannerKeyTwist": 0x74E8,
    "BannerVecForce": 0x76F4,
    "DirUpKeyForce": 0x4D68,
    "TurnRate": 0x74E0,
    "VolatileTurnRate": 0x7590,
    "SlidFricForce": 0x4CB4,
    "AdditionalLocalZSpeed": 0x4CDC,
    "Gravity": 0x2790,
    "MaxTurnSpeed": 0x76EC,
    "MinTurnSpeed": 0x26E4,
    "BaseAccuRate": 0x3678,
    "MaxAccuTime": 0x4C14,
    "MaxAffectSpeed": 0x74F0,
    "StartVec": 0x7454,
    "EndVecFist": 0x7500,
    "EndVecSecon": 0x2944,
    "DirKeyForce": 0x3CBC,
    "BannerHeadForce": 0x3CC4,
    "RollFricForce": 0x1418,
    "StartWec": 0x3670,
    "MaxWec": 0x2788,
    "SuaiJianTwist": 0x35E4,
    # Network.dll 调试 schema + 589 份同名明文/密文样本及协议结构确认。
    # 半径/长度、拾取间隙/斜面偏移在现有数据中始终同值，暂不开放。
    "CollisionBoxWidth": 0x4E18,
    "CollisionBoxHeight": 0x4E10,
    "CollisionBoxLength": 0x4D84,
    "CollisionBoxAdjustOffset": 0x4E28,
    "CollisionBoxAdjustPickGap": 0x4E20,
    "CollisionBoxAdjustRemoteOffset": 0x4D7C,
    "CollisionBoxAdjustBevelOffset": 0x4E38,
    "CollisionBoxControllerOffset": 0x4E30,
    "CarCollisionRadius": 0x34,
    "CarCollisionLength": 0x24,
    "CarCollisionWidth": 0x2C,
    "CarCollisionHeight": 0x1C,
    "CarCollisionLostCtrlTime": 0x3C,
    # CSSafeSTKartPhysParam -> 客户端运行时物理结构转换函数确认。
    "CrashCompensatePower": 0x7780,
    "DefenseRate": 0x26EC,
    "SpeedupCardGenRate": 0x35DC,
    "ExtraFuncFlag": 0x2780,
    "EnergyConvert": 0x74F8,
    "SuperN2ORate": 0x4CBA,
    "CollisionLoseRate": 0x758A,
    "NotInterruptDrift": 0xC9,
    "AccelStatusCount": 0x2889,
    "CompensateParamCount": 0x2949,
    "ForwardAccelNum": 0x00CB,
    "ForwardDecelNum": 0x141D,
    "BackwardAccelNum": 0x4EC1,
    "BackwardDecelNum": 0x778D,
    "HasBoatParam": 0x4759,
    "BoatForwardAccelNum": 0x6189,
    # 条件结构的开关/计数。它们决定后续协议单元是否存在，读取时展示，
    # 写入时禁止单独修改；列表长度只能通过已有协议骨架确定。
    "HasSkateParam": 0x7595,
    "HasBattleModeSkillInfoList": 0x367D,
    "BattleSkillNum": 0x3689,
    "AddWeightNum": 0x4CBD,
    "WeightNum": 0x4C19,
    "HasAntiCollisionCfg": 0x2795,
    "AntiCollisionNum": 0x27A1,
    # 滑板参数仅在 HasSkateParam 非零的文件中进入协议流。
    "SkateTrackSpeed": 0x75A4,
    "SkateSpeedCoefAirBigJet": 0x75AC,
    "SkateSpeedCoefJump": 0x7640,
    "SkateSpeedCoefAirJetPoint": 0x7658,
    "SkateSpeedCoefMaxForce": 0x7648,
    "SkateOntrackAccRef": 0x7650,
    "SkateTrackAccRef": 0x7660,
    "SkateDashSkill": 0x7638,
    # Network.dll 调试 schema + 同 ID Kart 明文/551 密文相关性确认。
    "BoatSlidFricForce": 0x47F0,
    "BoatAirValue": 0x47F8,
    "BoatLRKeyVecForce": 0x4800,
    "BoatBannerKeyTwist": 0x4808,
    "BoatUpKeyVecForce": 0x4810,
    "BoatVecForceParamA": 0x489C,
    "BoatVecForceParamB": 0x48A4,
    "BoatLRKeyVecForceParamB": 0x48B4,
    "BoatHeightRatio": 0x48BC,
    "BoatDirUpKeyForce": 0x48AC,
    "BoatDTFRatio": 0x4950,
    "BoatVecForce": 0x4958,
    "BoatDirKeyForceParamC": 0x4968,
    "BoatDirKeyForceParamB": 0x4948,
    "BoatWecEffect": 0x4960,
    "BoatDirKeyForce": 0x49F4,
    "BoatBannerTwist": 0x49FC,
    "BoatUpKeyVecForceParamB": 0x4A04,
    "BoatDirKeyForceParamD": 0x4A0C,
    "BoatBannerKeyTwistParamA": 0x4A14,
    "BoatAddNO2PerSec": 0x4AA0,
    "BoatBannerTwistParamA": 0x4AA8,
    "BoatBannerKeyTwistParamB": 0x4AB0,
    "BoatUpKeyVecForceParamA": 0x4AB8,
    "BoatSuaiJianTwist": 0x4AC0,
    "BoatDTFLimitAngle": 0x4B64,
    "BoatLRKeyVecForceParamA": 0x4B6C,
    "BoatDirUpKeyForceParamB": 0x4B74,
    "BoatDirUpKeyForceParamA": 0x4B7C,
    "BoatDirKeyForceParamA": 0x4B84,
    "DirUpKeyForceParamA": 0x7788,
    "DirUpKeyForceParamB": 0x0C,
}

# 兼容早期快照中的临时命名；新导出统一使用 DLL 成员原名。
LEGACY_FIELD_ALIASES = {
    "DriftReverse": "DirKeyTwist",
    "DriftSteering": "BannerKeyTwist",
    "DriftSwing": "BannerVecForce",
    "Friction": "SlidFricForce",
    "DriftReturn": "BannerTwist",
    "DriftRate": "DirUpKeyForce",
    "Weight": "AdditionalLocalZSpeed",
    "Suspension": "Gravity",
}

ARRAY_FIELDS = {
    "AccelStatus": tuple(0x2890 + 8 * i for i in range(6)),
    "Compensate": (0x2964, 0x2A04, 0x2AA4, 0x2B44, 0x2BE4, 0x2C84, 0x2D24),
    "ForwardAccelKey": tuple(0xDC + 0xA0 * i for i in range(13)),
    "ForwardAccel": tuple(0xE4 + 0xA0 * i for i in range(13)),
    "ForwardDecelKey": tuple(0x142C + 0xA0 * i for i in range(5)),
    "ForwardDecel": tuple(0x1434 + 0xA0 * i for i in range(5)),
    "BackwardAccelKey": tuple(0x4ED4 + 0xA0 * i for i in range(5)),
    "BackwardAccel": tuple(0x4EDC + 0xA0 * i for i in range(5)),
    "BackwardDecelKey": tuple(0x779C + 0xA0 * i for i in range(5)),
    "BackwardDecel": tuple(0x77A4 + 0xA0 * i for i in range(5)),
    "BoatShape": (0x4B4C, 0x4B54, 0x4B5C),
    "BoatForwardAccelKey": tuple(0x619C + 0xA0 * i for i in range(13)),
    "BoatForwardAccel": tuple(0x61A4 + 0xA0 * i for i in range(13)),
}

# 条件数组在协议中只编码 count 个元素。固定展开最大容量会误把未出现的
# 单元当作 0，因此读取/写入必须以相邻计数成员为准。
VARIABLE_ARRAY_FIELDS = {
    # name: (count_rel, max_count, element_rels)
    "PhysInfoPID": (SUPERJET_TYPE_REL, 10, tuple(0x3DC8 + 0x100 * i for i in range(10))),
    "PhysInfoAffectID": (SUPERJET_TYPE_REL, 10, tuple(0x3D6C + 0x100 * i for i in range(10))),
    "PhysInfoParam": (SUPERJET_TYPE_REL, 10, tuple(0x3D5C + 0x100 * i for i in range(10))),
    "PhysInfoLifeTime": (SUPERJET_TYPE_REL, 10, tuple(0x3D64 + 0x100 * i for i in range(10))),
    "PhysInfoCommonParaNum": (SUPERJET_TYPE_REL, 10, tuple(0x3D71 + 0x100 * i for i in range(10))),
    "CompensatePercent": (0x2949, 20, tuple(0x295C + 0xA0 * i for i in range(20))),
    "BattleSkillID": (0x3689, 10, tuple(0x369A + 0x90 * i for i in range(10))),
    "BattleSkillLevel": (0x3689, 10, tuple(0x369D + 0x90 * i for i in range(10))),
    "AddWeightTable": (0x4CBD, 9, tuple(0x4CBF + 2 * i for i in range(9))),
    # 不使用字段名 Weight：旧版快照中 Weight 是 AdditionalLocalZSpeed 的别名。
    "WeightTable": (0x4C19, 9, tuple(0x4C1B + 2 * i for i in range(9))),
    "AntiCollisionPosition": (0x27A1, 12, tuple(0x27A8 + 8 * i for i in range(12))),
}

# 结构标记和长度字段只负责描述已有骨架。直接修改它们不会自动插入/删除
# 相应的条件协议块，所以明确禁止写入，防止生成客户端可解析但结构错位的文件。
STRUCTURE_FIELDS = {
    "HasSkateParam", "HasBattleModeSkillInfoList", "BattleSkillNum",
    "AddWeightNum", "WeightNum", "HasAntiCollisionCfg", "AntiCollisionNum",
    "PhysInfoCount", "PhysInfoPID", "PhysInfoAffectID", "PhysInfoParam",
    "PhysInfoLifeTime", "PhysInfoCommonParaNum", "AccelStatusCount",
    "CompensateParamCount", "ForwardAccelNum", "ForwardDecelNum",
    "BackwardAccelNum", "BackwardDecelNum", "HasBoatParam",
    "BoatForwardAccelNum",
}

SIGNED_SCALAR_FIELDS = {
    "AdditionalLocalZSpeed", "Gravity", "BoatUpKeyVecForceParamB",
    "CollisionBoxControllerOffset", "CrashCompensatePower", "DefenseRate",
    "SpeedupCardGenRate", "EnergyConvert", "DirUpKeyForceParamA",
    "DirUpKeyForceParamB", "SkateTrackSpeed", "SkateSpeedCoefAirBigJet",
    "SkateSpeedCoefJump", "SkateSpeedCoefAirJetPoint", "SkateSpeedCoefMaxForce",
    "SkateOntrackAccRef", "SkateTrackAccRef", "SkateDashSkill",
} | {name for name in SCALAR_FIELDS if name.startswith("Boat")}
SIGNED_ARRAY_FIELDS = {
    "ForwardDecel", "BackwardAccel", "BackwardDecel",
    "BoatShape", "BoatForwardAccelKey", "BoatForwardAccel",
    "BattleSkillID", "AntiCollisionPosition", "PhysInfoParam",
    "PhysInfoLifeTime",
}

# 该字段在现有服务端样本中始终为 0，尚不能从数据相关性证明。
UNVERIFIED_FIELDS = {"NitroRetention": "现有服务端样本均为 0，尚未确认安全成员偏移"}


@dataclass
class Cell:
    object_offset: int
    start: int
    end: int
    value: int
    rip: int


@dataclass
class Record:
    index: int
    base: int
    internal_id: int
    values: dict


@dataclass
class Document:
    path: Path
    raw_bytes: bytes
    payload_start: int
    parser_offset: int
    cells: Dict[int, Cell]
    records: List[Record]

    @property
    def has_length_prefix(self):
        return self.payload_start == 2

    @property
    def format_name(self):
        return "EncryptKart（两字节长度头）" if self.has_length_prefix else "网络 Data（无长度头）"


def format_plain_snapshot(doc: Document, record_values=None) -> str:
    """把 DLL 解码结果写成可重新套用到原密文载体的 SchemaVersion 1 快照。"""
    if record_values is None:
        record_values = [record.values for record in doc.records]
    record_values = list(record_values)
    if len(record_values) != len(doc.records):
        raise ValueError("快照记录数量与协议记录数量不一致")
    lines = [
        "SchemaVersion: 1",
        f"SourceFile: {doc.path.name}",
        f"CarrierFile: {doc.path.name}",
        f"SourceFormat: {doc.format_name}",
        "Records:",
    ]
    for record, values in zip(doc.records, record_values):
        internal_id = values.get("InternalKartID", record.internal_id)
        lines += [f"  - ProtocolRecord: {record.index}", f"    InternalKartID: {internal_id}"]
        for name, value in values.items():
            if name == "InternalKartID":
                continue
            rendered = "[" + ", ".join(map(str, value)) + "]" if isinstance(value, list) else str(value)
            lines.append(f"    {name}: {rendered}")
    lines += ["", "# 未验证字段："] + [f"# {key}: {note}" for key, note in UNVERIFIED_FIELDS.items()]
    return "\n".join(lines) + "\n"


PROFILE_PHYS_COMMON_BASE = 0x3D78
PROFILE_PHYS_STRIDE = 0x100
PROFILE_PHYS_COMMON_STRIDE = 8


def _yaml_scalar(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _write_scalar(lines, key, value, indent=0):
    lines.append(f"{' ' * indent}{key}: {_yaml_scalar(value)}")


def _write_list(lines, key, values, indent=0):
    lines.append(f"{' ' * indent}{key}:")
    for value in values:
        lines.append(f"{' ' * indent}- {_yaml_scalar(value)}")


def _write_pair_list(lines, key, keys, rows, indent=0):
    lines.append(f"{' ' * indent}{key}:")
    for row in rows:
        lines.append(f"{' ' * indent}- {keys[0]}: {_yaml_scalar(row[0])}")
        for name, value in zip(keys[1:], row[1:]):
            lines.append(f"{' ' * (indent + 2)}{name}: {_yaml_scalar(value)}")


def _profile_cell_value(doc: Document, record: Record, rel, default=0):
    cell = doc.cells.get(record.base + rel)
    if cell is None:
        return default
    return _signed(cell.value)


def _phys_common_para(doc: Document, record: Record, phys_index, count):
    return [
        _profile_cell_value(
            doc, record,
            PROFILE_PHYS_COMMON_BASE + PROFILE_PHYS_STRIDE * phys_index + PROFILE_PHYS_COMMON_STRIDE * item,
        )
        for item in range(count)
    ]


def _pairs(keys, values):
    count = min(len(keys), len(values))
    return list(zip(keys[:count], values[:count]))


def format_server_profile(doc: Document, record_values=None) -> str:
    """导出服务端 mode28346=3 可直接读取的 EncryptKart28346 明文配置。"""
    if record_values is None:
        record_values = [record.values for record in doc.records]
    record_values = list(record_values)
    if len(record_values) != len(doc.records):
        raise ValueError("明文配置记录数量与协议记录数量不一致")

    if len(doc.records) > 1:
        first_id = int(record_values[0].get("InternalKartID", doc.records[0].internal_id))
        lines = [
            "# Generated from EncryptKart 551 data for mode28346=3.",
            f"# SourceFile: {doc.path.name}",
            "SkateParaEnabled: 0",
            "HasBattleModeSkillInfoList: 0",
            "Records:",
        ]
        for record, values in zip(doc.records, record_values):
            lines.append(f"- ProtocolRecord: {record.index}")
            for line in _format_server_profile_record(doc, record, values, include_header=False, include_profile=False).splitlines():
                lines.append(f"  {line}")
        lines.append("Profile:")
        _write_scalar(lines, "Version", 1, 2)
        lines.append("  Mode: FinalWithRefitAndPet")
        _write_scalar(lines, "Account", 10001, 2)
        _write_scalar(lines, "BaseKartID", first_id, 2)
        _write_scalar(lines, "SkinID", 0, 2)
        _write_scalar(lines, "IncludesRefit", True, 2)
        _write_scalar(lines, "IncludesPet", True, 2)
        return "\n".join(lines) + "\n"

    return _format_server_profile_record(doc, doc.records[0], record_values[0])


def _format_server_profile_record(doc: Document, record: Record, values, include_header=True, include_profile=True) -> str:
    v = values
    kart_id = int(v.get("InternalKartID", record.internal_id))
    lines = []
    if include_header:
        lines.extend([
            "# Generated from EncryptKart 551 data for mode28346=3.",
            f"# SourceFile: {doc.path.name}",
        ])

    _write_scalar(lines, "KartID", kart_id)

    phys_count = int(v.get("PhysInfoCount", len(v.get("PhysInfoPID", []))))
    _write_scalar(lines, "PhysInfoCount", phys_count)
    lines.append("PhysInfo:")
    common_nums = v.get("PhysInfoCommonParaNum", [])
    for i in range(phys_count):
        common_count = int(common_nums[i]) if i < len(common_nums) else 0
        common_values = _phys_common_para(doc, record, i, common_count)
        lines.append(f"- PID: {v['PhysInfoPID'][i]}")
        lines.append(f"  AffectID: {v['PhysInfoAffectID'][i]}")
        lines.append(f"  Param: {v['PhysInfoParam'][i]}")
        lines.append(f"  LifeTime: {v['PhysInfoLifeTime'][i]}")
        lines.append(f"  CommonParaNum: {common_count}")
        if common_values:
            lines.append("  CommonPara:")
            for value in common_values:
                lines.append(f"  - {value}")
        else:
            lines.append("  CommonPara: []")

    _write_scalar(lines, "CompensateParamCount", int(v.get("CompensateParamCount", len(v.get("Compensate", [])))))
    _write_pair_list(lines, "CompensateParam", ("Percent", "Value"),
                     _pairs(v.get("CompensatePercent", []), v.get("Compensate", [])))

    lines.append("CollisionBoxParam:")
    for out_name, src_name in {
        "BoxLength": "CollisionBoxLength",
        "BoxWidth": "CollisionBoxWidth",
        "BoxHeight": "CollisionBoxHeight",
        "AdjustOffset": "CollisionBoxAdjustOffset",
        "AdjustPickGap": "CollisionBoxAdjustPickGap",
        "AdjustRemoteOffset": "CollisionBoxAdjustRemoteOffset",
        "AdjustBevelOffset": "CollisionBoxAdjustBevelOffset",
        "ControllerOffset": "CollisionBoxControllerOffset",
    }.items():
        _write_scalar(lines, out_name, v.get(src_name, 0), 2)

    lines.append("CarToCarCollisionParam:")
    for out_name, src_name in {
        "CollisionRadius": "CarCollisionRadius",
        "CollisionLength": "CarCollisionLength",
        "CollisionWidth": "CarCollisionWidth",
        "CollisionHeight": "CarCollisionHeight",
        "CollisionLostCtrlTime": "CarCollisionLostCtrlTime",
    }.items():
        _write_scalar(lines, out_name, v.get(src_name, 0), 2)

    for out_name, src_name in (
        ("BaseTurnRate", "TurnRate"), ("VolatileTurnRate", "VolatileTurnRate"),
        ("MaxTurnSpeed", "MaxTurnSpeed"), ("MinTurnSpeed", "MinTurnSpeed"),
        ("MaxAccuTime", "MaxAccuTime"), ("BaseAccuRate", "BaseAccuRate"),
        ("MaxAffectSpeed", "MaxAffectSpeed"), ("Gravity", "Gravity"),
        ("AdditionalLocalZSpeed", "AdditionalLocalZSpeed"), ("StartVec", "StartVec"),
        ("EndVecFist", "EndVecFist"), ("EndVecSecon", "EndVecSecon"),
        ("DirKeyForce", "DirKeyForce"), ("DirKeyTwist", "DirKeyTwist"),
        ("BannerTwist", "BannerTwist"), ("BannerKeyTwist", "BannerKeyTwist"),
        ("BannerVecForce", "BannerVecForce"), ("BannerHeadForce", "BannerHeadForce"),
        ("SlidFricForce", "SlidFricForce"), ("RollFricForce", "RollFricForce"),
        ("StartWec", "StartWec"), ("MaxWec", "MaxWec"),
        ("SuaiJianTwist", "SuaiJianTwist"), ("DirUpKeyForce", "DirUpKeyForce"),
    ):
        _write_scalar(lines, out_name, v.get(src_name, 0))

    _write_scalar(lines, "AccelStatusCount", int(v.get("AccelStatusCount", len(v.get("AccelStatus", [])))))
    _write_list(lines, "AccelStatus", v.get("AccelStatus", []))

    for count_name, key_name, value_name, out_name in (
        ("ForwardAccelNum", "ForwardAccelKey", "ForwardAccel", "ForwardAccel"),
        ("ForwardDecelNum", "ForwardDecelKey", "ForwardDecel", "ForwardDecel"),
        ("BackwardAccelNum", "BackwardAccelKey", "BackwardAccel", "BackwardAccel"),
        ("BackwardDecelNum", "BackwardDecelKey", "BackwardDecel", "BackwardDecel"),
    ):
        _write_scalar(lines, count_name, int(v.get(count_name, len(v.get(value_name, [])))))
        _write_pair_list(lines, out_name, ("Key", "Value"), _pairs(v.get(key_name, []), v.get(value_name, [])))

    for name in (
        "CrashCompensatePower", "DefenseRate", "SpeedupCardGenRate", "ExtraFuncFlag",
        "EnergyConvert", "SuperN2ORate", "CollisionLoseRate", "NotInterruptDrift",
    ):
        _write_scalar(lines, name, v.get(name, 0))

    _write_scalar(lines, "SkateParaEnabled", v.get("HasSkateParam", 0))
    _write_scalar(lines, "HasBattleModeSkillInfoList", v.get("HasBattleModeSkillInfoList", 0))
    _write_scalar(lines, "AddWeightNum", v.get("AddWeightNum", 0))
    _write_list(lines, "AddWeight", v.get("AddWeightTable", []))
    _write_scalar(lines, "WeightNum", v.get("WeightNum", len(v.get("WeightTable", []))))
    _write_list(lines, "Weight", v.get("WeightTable", []))

    _write_scalar(lines, "HasAntiCollisionCfg", v.get("HasAntiCollisionCfg", 0))
    lines.append("AntiCollisionCfg:")
    _write_scalar(lines, "Num", v.get("AntiCollisionNum", len(v.get("AntiCollisionPosition", []))), 2)
    _write_list(lines, "Position", v.get("AntiCollisionPosition", []), 2)

    _write_scalar(lines, "HasBoatParam", v.get("HasBoatParam", 0))
    lines.append("BoatParam:")
    for out_name, src_name in (
        ("DirKeyForceParamC", "BoatDirKeyForceParamC"),
        ("DirKeyForceParamD", "BoatDirKeyForceParamD"),
        ("DTFLimitAngle", "BoatDTFLimitAngle"),
        ("DTFRatio", "BoatDTFRatio"),
        ("UpKeyVecForce", "BoatUpKeyVecForce"),
        ("UpKeyVecForceParamA", "BoatUpKeyVecForceParamA"),
        ("UpKeyVecForceParamB", "BoatUpKeyVecForceParamB"),
        ("LRKeyVecForce", "BoatLRKeyVecForce"),
        ("LRKeyVecForceParamA", "BoatLRKeyVecForceParamA"),
        ("LRKeyVecForceParamB", "BoatLRKeyVecForceParamB"),
        ("VecForce", "BoatVecForce"),
        ("VecForceParamA", "BoatVecForceParamA"),
        ("VecForceParamB", "BoatVecForceParamB"),
        ("WecEffect", "BoatWecEffect"),
        ("BannerKeyTwist", "BoatBannerKeyTwist"),
        ("BannerKeyTwistParamA", "BoatBannerKeyTwistParamA"),
        ("BannerKeyTwistParamB", "BoatBannerKeyTwistParamB"),
        ("SuaiJianTwist", "BoatSuaiJianTwist"),
        ("BoatHeighRatio", "BoatHeightRatio"),
        ("BannerTwist", "BoatBannerTwist"),
        ("BannerTwistParamA", "BoatBannerTwistParamA"),
        ("DirUpKeyForce", "BoatDirUpKeyForce"),
        ("DirUpKeyForceParamA", "BoatDirUpKeyForceParamA"),
        ("DirUpKeyForceParamB", "BoatDirUpKeyForceParamB"),
        ("DirKeyForce", "BoatDirKeyForce"),
        ("DirKeyForceParamA", "BoatDirKeyForceParamA"),
        ("DirKeyForceParamB", "BoatDirKeyForceParamB"),
        ("AddNO2PerSec", "BoatAddNO2PerSec"),
        ("BoatAirValue", "BoatAirValue"),
        ("ifSlidFricForce", "BoatSlidFricForce"),
    ):
        _write_scalar(lines, out_name, v.get(src_name, 0), 2)
    _write_list(lines, "BoatShape", v.get("BoatShape", []), 2)

    _write_scalar(lines, "BoatForwardAccelNum", int(v.get("BoatForwardAccelNum", len(v.get("BoatForwardAccel", [])))))
    _write_pair_list(lines, "BoatForwardAccel", ("Key", "Value"),
                     _pairs(v.get("BoatForwardAccelKey", []), v.get("BoatForwardAccel", [])))

    _write_scalar(lines, "DirUpKeyForceParamA", v.get("DirUpKeyForceParamA", 0))
    _write_scalar(lines, "DirUpKeyForceParamB", v.get("DirUpKeyForceParamB", 0))

    if include_profile:
        lines.append("Profile:")
        _write_scalar(lines, "Version", 1, 2)
        lines.append("  Mode: FinalWithRefitAndPet")
        _write_scalar(lines, "Account", 10001, 2)
        _write_scalar(lines, "BaseKartID", kart_id, 2)
        _write_scalar(lines, "SkinID", 0, 2)
        _write_scalar(lines, "IncludesRefit", True, 2)
        _write_scalar(lines, "IncludesPet", True, 2)
    return "\n".join(lines) + "\n"


def _profile_strip_comment(line: str) -> str:
    return line.split("#", 1)[0].rstrip()


def _profile_clean_lines(text: str):
    return [
        _profile_strip_comment(line)
        for line in text.splitlines()
        if _profile_strip_comment(line).strip()
    ]


def _profile_scalar(lines, key, default=0):
    prefix = key + ":"
    for line in lines:
        if line.startswith(prefix):
            value = line.split(":", 1)[1].strip()
            if value in ("true", "True"):
                return 1
            if value in ("false", "False"):
                return 0
            return int(value) if value else default
    return default


def _profile_section(lines, key):
    marker = key + ":"
    for index, line in enumerate(lines):
        if line.strip() != marker:
            continue
        result = []
        for item in lines[index + 1:]:
            if item and not item.startswith(" ") and not item.startswith("- "):
                break
            result.append(item)
        return result
    return []


def _profile_simple_list(lines, key):
    return [
        int(line.strip()[2:].strip())
        for line in _profile_section(lines, key)
        if line.strip().startswith("- ")
    ]


def _profile_map_values(lines, key):
    values = {}
    for line in _profile_section(lines, key):
        stripped = line.strip()
        if ":" not in stripped or stripped.startswith("- "):
            continue
        name, value = (part.strip() for part in stripped.split(":", 1))
        if value:
            values[name] = int(value)
    return values


def _profile_pair_list(lines, key, first_name, second_name):
    rows = []
    current = None
    for line in _profile_section(lines, key):
        stripped = line.strip()
        if stripped.startswith(f"- {first_name}:"):
            current = [int(stripped.split(":", 1)[1].strip()), 0]
            rows.append(current)
        elif current is not None and stripped.startswith(f"{second_name}:"):
            current[1] = int(stripped.split(":", 1)[1].strip())
    return rows


def _parse_profile_record(lines, protocol_record):
    values = {}
    values["InternalKartID"] = _profile_scalar(lines, "KartID")

    phys = []
    current = None
    in_common = False
    for line in _profile_section(lines, "PhysInfo"):
        stripped = line.strip()
        if stripped.startswith("- PID:"):
            current = {"PID": int(stripped.split(":", 1)[1].strip())}
            phys.append(current)
            in_common = False
        elif current is not None and stripped.startswith(
            ("AffectID:", "Param:", "LifeTime:", "CommonParaNum:")
        ):
            name, value = (part.strip() for part in stripped.split(":", 1))
            current[name] = int(value)
            in_common = False
        elif current is not None and stripped == "CommonPara:":
            in_common = True
        elif current is not None and in_common and stripped.startswith("- "):
            in_common = True

    values["PhysInfoCount"] = _profile_scalar(
        lines, "PhysInfoCount", len(phys)
    )
    values["PhysInfoPID"] = [item.get("PID", 0) for item in phys]
    values["PhysInfoAffectID"] = [item.get("AffectID", 0) for item in phys]
    values["PhysInfoParam"] = [item.get("Param", 0) for item in phys]
    values["PhysInfoLifeTime"] = [item.get("LifeTime", 0) for item in phys]
    values["PhysInfoCommonParaNum"] = [
        item.get("CommonParaNum", 0) for item in phys
    ]

    compensate = _profile_pair_list(lines, "CompensateParam", "Percent", "Value")
    values["CompensateParamCount"] = _profile_scalar(
        lines, "CompensateParamCount", len(compensate)
    )
    values["CompensatePercent"] = [row[0] for row in compensate]
    values["Compensate"] = [row[1] for row in compensate]

    for input_name, output_name in {
        "BoxLength": "CollisionBoxLength",
        "BoxWidth": "CollisionBoxWidth",
        "BoxHeight": "CollisionBoxHeight",
        "AdjustOffset": "CollisionBoxAdjustOffset",
        "AdjustPickGap": "CollisionBoxAdjustPickGap",
        "AdjustRemoteOffset": "CollisionBoxAdjustRemoteOffset",
        "AdjustBevelOffset": "CollisionBoxAdjustBevelOffset",
        "ControllerOffset": "CollisionBoxControllerOffset",
    }.items():
        values[output_name] = _profile_map_values(lines, "CollisionBoxParam").get(
            input_name, 0
        )
    for input_name, output_name in {
        "CollisionRadius": "CarCollisionRadius",
        "CollisionLength": "CarCollisionLength",
        "CollisionWidth": "CarCollisionWidth",
        "CollisionHeight": "CarCollisionHeight",
        "CollisionLostCtrlTime": "CarCollisionLostCtrlTime",
    }.items():
        values[output_name] = _profile_map_values(
            lines, "CarToCarCollisionParam"
        ).get(input_name, 0)

    for input_name, output_name in (
        ("BaseTurnRate", "TurnRate"),
        ("VolatileTurnRate", "VolatileTurnRate"),
        ("MaxTurnSpeed", "MaxTurnSpeed"),
        ("MinTurnSpeed", "MinTurnSpeed"),
        ("MaxAccuTime", "MaxAccuTime"),
        ("BaseAccuRate", "BaseAccuRate"),
        ("MaxAffectSpeed", "MaxAffectSpeed"),
        ("Gravity", "Gravity"),
        ("AdditionalLocalZSpeed", "AdditionalLocalZSpeed"),
        ("StartVec", "StartVec"),
        ("EndVecFist", "EndVecFist"),
        ("EndVecSecon", "EndVecSecon"),
        ("DirKeyForce", "DirKeyForce"),
        ("DirKeyTwist", "DirKeyTwist"),
        ("BannerTwist", "BannerTwist"),
        ("BannerKeyTwist", "BannerKeyTwist"),
        ("BannerVecForce", "BannerVecForce"),
        ("BannerHeadForce", "BannerHeadForce"),
        ("SlidFricForce", "SlidFricForce"),
        ("RollFricForce", "RollFricForce"),
        ("StartWec", "StartWec"),
        ("MaxWec", "MaxWec"),
        ("SuaiJianTwist", "SuaiJianTwist"),
        ("DirUpKeyForce", "DirUpKeyForce"),
    ):
        values[output_name] = _profile_scalar(lines, input_name)

    values["AccelStatusCount"] = _profile_scalar(
        lines, "AccelStatusCount", len(_profile_simple_list(lines, "AccelStatus"))
    )
    values["AccelStatus"] = _profile_simple_list(lines, "AccelStatus")
    for count_name, section, key_name, value_name in (
        ("ForwardAccelNum", "ForwardAccel", "ForwardAccelKey", "ForwardAccel"),
        ("ForwardDecelNum", "ForwardDecel", "ForwardDecelKey", "ForwardDecel"),
        ("BackwardAccelNum", "BackwardAccel", "BackwardAccelKey", "BackwardAccel"),
        ("BackwardDecelNum", "BackwardDecel", "BackwardDecelKey", "BackwardDecel"),
        ("BoatForwardAccelNum", "BoatForwardAccel", "BoatForwardAccelKey", "BoatForwardAccel"),
    ):
        rows = _profile_pair_list(lines, section, "Key", "Value")
        values[count_name] = _profile_scalar(lines, count_name, len(rows))
        if values[count_name] > 0:
            values[key_name] = [row[0] for row in rows]
            values[value_name] = [row[1] for row in rows]

    for name in (
        "CrashCompensatePower",
        "DefenseRate",
        "SpeedupCardGenRate",
        "ExtraFuncFlag",
        "EnergyConvert",
        "SuperN2ORate",
        "CollisionLoseRate",
        "NotInterruptDrift",
        "DirUpKeyForceParamA",
        "DirUpKeyForceParamB",
    ):
        values[name] = _profile_scalar(lines, name)
    values["HasSkateParam"] = _profile_scalar(lines, "SkateParaEnabled")
    values["HasBattleModeSkillInfoList"] = _profile_scalar(
        lines, "HasBattleModeSkillInfoList"
    )
    values["AddWeightNum"] = _profile_scalar(lines, "AddWeightNum")
    if values["AddWeightNum"] > 0:
        values["AddWeightTable"] = _profile_simple_list(lines, "AddWeight")
    values["WeightNum"] = _profile_scalar(
        lines, "WeightNum", len(_profile_simple_list(lines, "Weight"))
    )
    if values["WeightNum"] > 0:
        values["WeightTable"] = _profile_simple_list(lines, "Weight")
    anti = _profile_map_values(lines, "AntiCollisionCfg")
    values["HasAntiCollisionCfg"] = _profile_scalar(lines, "HasAntiCollisionCfg")
    values["AntiCollisionNum"] = anti.get("Num", 0)
    if values["AntiCollisionNum"] > 0:
        values["AntiCollisionPosition"] = _profile_simple_list(lines, "Position")
    values["HasBoatParam"] = _profile_scalar(lines, "HasBoatParam")
    boat = _profile_map_values(lines, "BoatParam")
    for input_name, output_name in (
        ("DirKeyForceParamC", "BoatDirKeyForceParamC"),
        ("DirKeyForceParamD", "BoatDirKeyForceParamD"),
        ("DTFLimitAngle", "BoatDTFLimitAngle"),
        ("DTFRatio", "BoatDTFRatio"),
        ("UpKeyVecForce", "BoatUpKeyVecForce"),
        ("UpKeyVecForceParamA", "BoatUpKeyVecForceParamA"),
        ("UpKeyVecForceParamB", "BoatUpKeyVecForceParamB"),
        ("LRKeyVecForce", "BoatLRKeyVecForce"),
        ("LRKeyVecForceParamA", "BoatLRKeyVecForceParamA"),
        ("LRKeyVecForceParamB", "BoatLRKeyVecForceParamB"),
        ("VecForce", "BoatVecForce"),
        ("VecForceParamA", "BoatVecForceParamA"),
        ("VecForceParamB", "BoatVecForceParamB"),
        ("WecEffect", "BoatWecEffect"),
        ("BannerKeyTwist", "BoatBannerKeyTwist"),
        ("BannerKeyTwistParamA", "BoatBannerKeyTwistParamA"),
        ("BannerKeyTwistParamB", "BoatBannerKeyTwistParamB"),
        ("SuaiJianTwist", "BoatSuaiJianTwist"),
        ("BoatHeighRatio", "BoatHeightRatio"),
        ("BannerTwist", "BoatBannerTwist"),
        ("BannerTwistParamA", "BoatBannerTwistParamA"),
        ("DirUpKeyForce", "BoatDirUpKeyForce"),
        ("DirUpKeyForceParamA", "BoatDirUpKeyForceParamA"),
        ("DirUpKeyForceParamB", "BoatDirUpKeyForceParamB"),
        ("DirKeyForce", "BoatDirKeyForce"),
        ("DirKeyForceParamA", "BoatDirKeyForceParamA"),
        ("DirKeyForceParamB", "BoatDirKeyForceParamB"),
        ("AddNO2PerSec", "BoatAddNO2PerSec"),
        ("BoatAirValue", "BoatAirValue"),
        ("ifSlidFricForce", "BoatSlidFricForce"),
    ):
        values[output_name] = boat.get(input_name, 0)
    values["BoatShape"] = _profile_simple_list(lines, "BoatShape")
    values["ProtocolRecord"] = protocol_record
    return values


def parse_server_profile_snapshot(path):
    """读取旧版/服务端 Kart 明文，并转换为导入所需的字段字典。"""
    path = Path(path)
    text = path.read_text(encoding="utf-8-sig")
    lines = _profile_clean_lines(text)
    source = path.name
    for raw in text.splitlines():
        if raw.strip().startswith("# SourceFile:"):
            source = Path(raw.split(":", 1)[1].strip()).name
            break

    records = []
    if "Records:" in lines:
        start = lines.index("Records:") + 1
        current_number = None
        current = []
        for line in lines[start:]:
            if line == "Profile:":
                break
            if line.startswith("- ProtocolRecord:"):
                if current_number is not None:
                    records.append(_parse_profile_record(current, current_number))
                current_number = int(line.split(":", 1)[1].strip())
                current = []
            elif current_number is not None:
                current.append(line[2:] if line.startswith("  ") else line)
        if current_number is not None:
            records.append(_parse_profile_record(current, current_number))
    else:
        profile_index = lines.index("Profile:") if "Profile:" in lines else len(lines)
        records.append(_parse_profile_record(lines[:profile_index], 1))

    if not records:
        raise ValueError("不是完整的服务端明文配置")
    return source, source, records


def _u32(value):
    return int(value) & 0xFFFFFFFF


def _signed(value):
    value &= 0xFFFFFFFF
    return value - 0x100000000 if value & 0x80000000 else value


def _varint(value):
    value = _u32(value)
    result = []
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            byte |= 0x80
        result.append(byte)
        if not value:
            return result


def _format_data_yaml(data: bytes) -> str:
    rows = []
    for pos in range(0, len(data), 16):
        rows.append("  " + ", ".join(f"0x{byte:02X}" for byte in data[pos:pos + 16]))
    return "Data: [\n" + ",\n".join(rows) + "\n]\n"


class Kart551Codec:
    def __init__(self):
        self.emu = Emulator()
        base = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
        snapshot = base / "551_object_init.bin"
        if snapshot.is_file():
            initialized = snapshot.read_bytes()
            if len(initialized) != 2132944:
                raise RuntimeError("551_object_init.bin 长度不正确")
            self.emu.uc.mem_write(OBJECT_BASE, initialized)
        else:
            result, _ = self.emu.call(CONSTRUCTOR, OBJECT_BASE)
            if result != OBJECT_BASE:
                raise RuntimeError(f"551 安全对象初始化失败：{result:#x}")
        self.inverse_tables = {}

    def _try_parse(self, path: Path, data: bytes, payload_start: int):
        self.emu.uc.mem_write(DATA_BASE, b"\0" * min(0x20000, max(len(data) + 32, 0x1000)))
        self.emu.uc.mem_write(DATA_BASE, data)
        self.emu.uc.mem_write(ARG_BASE, struct.pack("<Q", DATA_BASE + payload_start))
        self.emu.uc.mem_write(ARG_BASE + 8, struct.pack("<I", 0))
        self.emu.decode_events.clear()
        self.emu.pending_input = None
        self.emu.trace_enabled = True
        result, _ = self.emu.call(
            PARSER, OBJECT_BASE, ARG_BASE, DATA_BASE + len(data), ARG_BASE + 8
        )
        self.emu.trace_enabled = False
        offset = struct.unpack("<I", self.emu.uc.mem_read(ARG_BASE + 8, 4))[0]
        if (result & 0xFF) != 1:
            return None

        collapsed = []
        for input_pos, object_offset, size, value, rip in self.emu.decode_events:
            if collapsed and collapsed[-1].object_offset == object_offset:
                collapsed[-1].end = input_pos + 1
                collapsed[-1].value = value
            else:
                collapsed.append(Cell(object_offset, input_pos, input_pos + 1, value, rip))
        cells = {cell.object_offset: cell for cell in collapsed}

        records = []
        for base in RECORD_BASES:
            id_cell = cells.get(base + INTERNAL_ID_REL)
            if id_cell is None:
                continue
            values = {}
            for name, rel in SCALAR_FIELDS.items():
                cell = cells.get(base + rel)
                if cell is not None:
                    values[name] = _signed(cell.value) if name in SIGNED_SCALAR_FIELDS else cell.value
            for name, rels in ARRAY_FIELDS.items():
                if all(base + rel in cells for rel in rels):
                    values[name] = [
                        _signed(cells[base + rel].value) if name in SIGNED_ARRAY_FIELDS
                        else cells[base + rel].value
                        for rel in rels
                    ]
            for name, (count_rel, max_count, rels) in VARIABLE_ARRAY_FIELDS.items():
                count_cell = cells.get(base + count_rel)
                if count_cell is None:
                    continue
                count = count_cell.value
                if not 0 < count <= max_count:
                    continue
                active_rels = rels[:count]
                if all(base + rel in cells for rel in active_rels):
                    values[name] = [
                        _signed(cells[base + rel].value) if name in SIGNED_ARRAY_FIELDS
                        else cells[base + rel].value
                        for rel in active_rels
                    ]
            if "SuperJetType" in values:
                values["PhysInfoCount"] = values["SuperJetType"]
            records.append(Record(len(records) + 1, base, id_cell.value, values))
        if not records:
            return None
        return Document(path, data, payload_start, offset, cells, records)

    def read(self, path) -> Document:
        path = Path(path)
        data = load_yaml_data(path)
        if not data:
            raise ValueError("文件中没有 Data 字节")

        starts = []
        if len(data) >= 3 and int.from_bytes(data[:2], "big") == len(data) - 3:
            starts.append(2)
        starts.extend(x for x in (0, 2) if x not in starts)
        for payload_start in starts:
            doc = self._try_parse(path, data, payload_start)
            if doc is not None:
                return doc
        raise ValueError("Top-Kart.dll 拒绝该文件：不是匹配版本的 551 数据或文本格式已损坏")

    def _inverse(self, rip):
        if rip not in self.inverse_tables:
            decoded = self.emu.decoder_table(rip)
            if len(set(decoded)) != 256:
                raise RuntimeError(f"字段字节变换不可逆：{rip:#x}")
            inverse = [0] * 256
            for encoded, plain in enumerate(decoded):
                inverse[plain] = encoded
            self.inverse_tables[rip] = inverse
        return self.inverse_tables[rip]

    @staticmethod
    def _superjet_block_span(doc: Document, record: Record):
        first = doc.cells.get(record.base + SUPERJET_BLOCK_FIRST_REL)
        following = doc.cells.get(record.base + POST_JET_FIELD_REL)
        if first is None or following is None or first.start >= following.start:
            raise ValueError(f"协议记录 {record.index} 的超级喷扩展块不完整")
        return first.start, following.start

    def write(self, doc: Document, record_values: Iterable[dict], output_path) -> Document:
        record_values = list(record_values)
        if len(record_values) != len(doc.records):
            raise ValueError("记录数量不能改变；只允许修改现有记录字段")
        replacements = []
        expected = {}
        for record, values in zip(doc.records, record_values):
            if "InternalKartID" in values:
                cell = doc.cells[record.base + INTERNAL_ID_REL]
                wanted_id = _u32(values["InternalKartID"])
                expected[cell.object_offset] = wanted_id
                if cell.value != wanted_id:
                    inverse = self._inverse(cell.rip)
                    encoded = bytes(inverse[byte] for byte in _varint(wanted_id))
                    replacements.append((cell.start, cell.end, encoded))
            original_type = record.values.get("SuperJetType")
            wanted_type = values.get("SuperJetType", original_type)
            if original_type not in (4, 5) or wanted_type not in (4, 5):
                raise ValueError("SuperJetType 只允许 4（普通赛车）或 5（超级喷赛车）")
            if original_type != wanted_type:
                if wanted_type == 5:
                    insert_at = doc.cells[record.base + POST_JET_FIELD_REL].start
                    replacements.append((insert_at, insert_at, DEFAULT_SUPERJET_BLOCK))
                else:
                    block_start, block_end = self._superjet_block_span(doc, record)
                    replacements.append((block_start, block_end, b""))
            for name, rel in SCALAR_FIELDS.items():
                if name not in values:
                    continue
                cell = doc.cells[record.base + rel]
                wanted = _u32(values[name])
                if name in STRUCTURE_FIELDS and cell.value != wanted:
                    raise ValueError(f"{name} 是条件结构标记/计数，不能脱离协议骨架单独修改")
                expected[cell.object_offset] = wanted
                if cell.value == wanted:
                    continue
                inverse = self._inverse(cell.rip)
                encoded = bytes(inverse[byte] for byte in _varint(wanted))
                replacements.append((cell.start, cell.end, encoded))
            for name, rels in ARRAY_FIELDS.items():
                if name not in values:
                    continue
                if name in STRUCTURE_FIELDS:
                    if values[name] != record.values.get(name):
                        raise ValueError(f"{name} 是结构视图字段，不能直接写入")
                    continue
                items = list(values[name])
                if len(items) != len(rels):
                    raise ValueError(f"{name} 必须正好包含 {len(rels)} 项")
                for rel, value in zip(rels, items):
                    cell = doc.cells[record.base + rel]
                    wanted = _u32(value)
                    expected[cell.object_offset] = wanted
                    if cell.value == wanted:
                        continue
                    inverse = self._inverse(cell.rip)
                    encoded = bytes(inverse[byte] for byte in _varint(wanted))
                    replacements.append((cell.start, cell.end, encoded))
            for name, (count_rel, max_count, rels) in VARIABLE_ARRAY_FIELDS.items():
                if name not in values:
                    continue
                if name in STRUCTURE_FIELDS:
                    if values[name] != record.values.get(name):
                        raise ValueError(f"{name} 是结构视图字段，不能直接写入")
                    continue
                count_cell = doc.cells.get(record.base + count_rel)
                if count_cell is None or not 0 < count_cell.value <= max_count:
                    raise ValueError(f"{name} 在当前协议记录中没有可编辑的条件数组")
                active_rels = rels[:count_cell.value]
                items = list(values[name])
                if len(items) != len(active_rels):
                    raise ValueError(f"{name} 必须保持现有 {len(active_rels)} 项，不能单独增删")
                for rel, value in zip(active_rels, items):
                    cell = doc.cells.get(record.base + rel)
                    if cell is None:
                        raise ValueError(f"{name} 的协议单元不完整：{rel:#x}")
                    wanted = _u32(value)
                    expected[cell.object_offset] = wanted
                    if cell.value == wanted:
                        continue
                    inverse = self._inverse(cell.rip)
                    encoded = bytes(inverse[byte] for byte in _varint(wanted))
                    replacements.append((cell.start, cell.end, encoded))

        result = bytearray(doc.raw_bytes)
        for start, end, encoded in sorted(replacements, reverse=True):
            result[start:end] = encoded
        if doc.has_length_prefix:
            length = len(result) - 3
            if not 0 <= length <= 0xFFFF:
                raise ValueError("编码结果超出 551 两字节长度范围")
            result[:2] = length.to_bytes(2, "big")

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(_format_data_yaml(bytes(result)), encoding="ascii")

        verified = self.read(output_path)
        actual = {offset: cell.value for offset, cell in verified.cells.items()}
        failures = [(offset, value, actual.get(offset)) for offset, value in expected.items()
                    if actual.get(offset) != value]
        if failures:
            output_path.unlink(missing_ok=True)
            raise RuntimeError(f"DLL 回读校验失败：{failures[:3]}")
        return verified

    def reshape(self, source: Document, template_path, source_records,
                target_count: int, output_path) -> Document:
        """借助合法载体重建 1/2/3 形态结构，并用 DLL 回读验证。"""
        if target_count not in (1, 2, 3):
            raise ValueError("形态数量只允许 1、2 或 3")
        template = self.read(template_path)
        if target_count == 2:
            if len(template.records) != 3:
                raise ValueError("生成二形态需要一个三形态协议骨架")
            # 已经客户端实测确认的正式二形态组合是 [0,1,1]：
            # 删除协议槽1（编辑器第3形态），保留槽2、3（编辑器第1、2形态）。
            first_count = template.cells[0xA]
            slot_cells = [cell for offset, cell in template.cells.items()
                          if RECORD_BASES[0] <= offset < RECORD_BASES[0] + RECORD_SIZE]
            if not slot_cells:
                raise ValueError("三形态协议骨架缺少槽1记录")
            record_start = min(cell.start for cell in slot_cells)
            record_end = max(cell.end for cell in slot_cells)
            if record_start != first_count.end:
                raise ValueError("无法确认三形态槽1的协议边界")
            encoded_zero = bytes((self._inverse(first_count.rip)[0],))
            raw = bytearray(template.raw_bytes)
            raw[first_count.start:record_end] = encoded_zero
            if template.has_length_prefix:
                raw[:2] = (len(raw) - 3).to_bytes(2, "big")
            template = self._try_parse(Path(template_path), bytes(raw), template.payload_start)
            if template is None or len(template.records) != 2:
                raise RuntimeError("DLL 拒绝重建后的二形态协议骨架")
        elif len(template.records) != target_count:
            raise ValueError(f"所选协议骨架不是 {target_count} 记录文件")
        if isinstance(source_records, Record):
            source_records = [source_records] * target_count
        else:
            source_records = list(source_records)
        if len(source_records) != target_count:
            raise ValueError(f"目标 {target_count} 形态需要正好 {target_count} 份源形态字段")
        cloned = []
        for source_record in source_records:
            values = copy.deepcopy(source_record.values)
            values["InternalKartID"] = source_record.internal_id
            cloned.append(values)
        return self.write(template, cloned, output_path)


def find_server_encrypt_dir(start=None):
    candidates = []
    if start:
        start = Path(start)
        candidates.extend([start / "EncryptKart", start / "bin" / "EncryptKart"])
    here = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
    candidates.extend([
        here.parent / "QQspeed Mysql" / "bin" / "EncryptKart",
        here.parent / "QQspeed Mysql 9.3" / "bin" / "EncryptKart",
    ])
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    return None
