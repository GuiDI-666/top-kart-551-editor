#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""独立的 Top-Kart 551 SchemaVersion 1 明文快照编辑器。"""

from __future__ import annotations

import ast
import copy
import re
import sys
import tkinter as tk
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from tkinter import filedialog, messagebox, ttk


STRUCTURE_FIELDS = {
    "HasSkateParam", "HasBattleModeSkillInfoList", "BattleSkillNum",
    "AddWeightNum", "WeightNum", "HasAntiCollisionCfg", "AntiCollisionNum",
    "PhysInfoCount", "PhysInfoPID", "PhysInfoAffectID", "PhysInfoParam",
    "PhysInfoLifeTime", "PhysInfoCommonParaNum", "AccelStatusCount",
    "CompensateParamCount", "ForwardAccelNum", "ForwardDecelNum",
    "BackwardAccelNum", "BackwardDecelNum", "HasBoatParam",
    "BoatForwardAccelNum",
}

ARRAY_FIELDS = {
    "AccelStatus", "Compensate", "ForwardAccelKey", "ForwardAccel",
    "ForwardDecelKey", "ForwardDecel", "BackwardAccelKey", "BackwardAccel",
    "BackwardDecelKey", "BackwardDecel", "BoatShape", "BoatForwardAccelKey",
    "BoatForwardAccel", "BattleSkillID", "BattleSkillLevel", "AddWeightTable",
    "WeightTable", "AntiCollisionPosition", "PhysInfoPID", "PhysInfoAffectID",
    "PhysInfoParam", "PhysInfoLifeTime", "PhysInfoCommonParaNum",
    "CompensatePercent",
}

SPECIAL_FIELDS = STRUCTURE_FIELDS | {
    "SkateTrackSpeed", "SkateSpeedCoefAirBigJet", "SkateSpeedCoefJump",
    "SkateSpeedCoefAirJetPoint", "SkateSpeedCoefMaxForce", "SkateOntrackAccRef",
    "SkateTrackAccRef", "SkateDashSkill", "BattleSkillID", "BattleSkillLevel",
    "AddWeightTable", "WeightTable", "AntiCollisionPosition",
    "PhysInfoPID", "PhysInfoAffectID", "PhysInfoParam", "PhysInfoLifeTime",
    "PhysInfoCommonParaNum",
}

LABELS = {
    "InternalKartID": "内部赛车 ID", "SuperJetType": "喷射模式（4普通/5超级喷）",
    "NitroPower": "氮气强度", "NitroDuration": "氮气时长",
    "SmallJetPower": "小喷强度", "SmallJetDuration": "小喷时长",
    "CollectEfficiency": "集气效率", "BannerTwist": "漂移转向扭矩",
    "DirKeyTwist": "方向键转向扭矩", "BannerKeyTwist": "漂移方向键转向扭矩",
    "BannerVecForce": "漂移矢量作用力", "DirUpKeyForce": "方向键抬起作用力",
    "TurnRate": "基础转向率", "VolatileTurnRate": "不稳定转向率",
    "SlidFricForce": "滑动摩擦力", "AdditionalLocalZSpeed": "附加本地 Z 速度",
    "Gravity": "重力", "MaxTurnSpeed": "最大转向速度", "MinTurnSpeed": "最小转向速度",
    "BaseAccuRate": "基础累积速率", "MaxAccuTime": "最大累积时间",
    "MaxAffectSpeed": "生效最大速度", "StartVec": "触发最低速度",
    "EndVecFist": "一级中断阈值", "EndVecSecon": "二级退出阈值",
    "DirKeyForce": "方向键作用力", "BannerHeadForce": "车头回正力",
    "RollFricForce": "滚动摩擦力", "StartWec": "接触起始阈值",
    "MaxWec": "接触最大阈值", "SuaiJianTwist": "断位转向扭矩",
    "CollisionBoxLength": "碰撞盒长度", "CollisionBoxWidth": "碰撞盒宽度",
    "CollisionBoxHeight": "碰撞盒高度", "CollisionBoxAdjustOffset": "碰撞盒调整偏移",
    "CollisionBoxAdjustPickGap": "碰撞盒拾取间隙",
    "CollisionBoxAdjustRemoteOffset": "碰撞盒远端调整偏移",
    "CollisionBoxAdjustBevelOffset": "碰撞盒斜面调整偏移",
    "CollisionBoxControllerOffset": "碰撞盒控制器偏移",
    "CarCollisionRadius": "车车碰撞半径", "CarCollisionLength": "车车碰撞长度",
    "CarCollisionWidth": "车车碰撞宽度", "CarCollisionHeight": "车车碰撞高度",
    "CarCollisionLostCtrlTime": "车车碰撞失控时间",
    "CrashCompensatePower": "碰撞补偿强度", "DefenseRate": "防御率",
    "SpeedupCardGenRate": "加速卡生成率", "ExtraFuncFlag": "额外功能标志",
    "EnergyConvert": "能量转换", "SuperN2ORate": "超级氮气率",
    "CollisionLoseRate": "碰撞损失率", "NotInterruptDrift": "漂移不中断",
    "PhysInfoCount": "效果数量（只读）", "PhysInfoPID": "效果 PID（只读）",
    "PhysInfoAffectID": "效果 AffectID（只读）", "PhysInfoParam": "效果参数（只读）",
    "PhysInfoLifeTime": "效果持续时间（只读）",
    "PhysInfoCommonParaNum": "效果 CommonPara 数量（只读）",
    "AccelStatusCount": "平跑加速档位数量（只读）",
    "CompensateParamCount": "落后补偿数量（只读）",
    "CompensatePercent": "落后补偿百分比",
    "ForwardAccelNum": "前进加速数量（只读）",
    "ForwardDecelNum": "前进减速数量（只读）",
    "BackwardAccelNum": "倒车加速数量（只读）",
    "BackwardDecelNum": "倒车减速数量（只读）",
    "HasBoatParam": "船形态参数启用标记（只读）",
    "BoatForwardAccelNum": "船体前进加速数量（只读）",
    "DirUpKeyForceParamA": "抬键作用力参数 A", "DirUpKeyForceParamB": "抬键作用力参数 B",
    "AccelStatus": "多档平跑加速", "Compensate": "落后补偿",
    "ForwardAccelKey": "前进加速速度点", "ForwardAccel": "前进加速值",
    "ForwardDecelKey": "前进减速速度点", "ForwardDecel": "前进减速值",
    "BackwardAccelKey": "倒车加速速度点", "BackwardAccel": "倒车加速值",
    "BackwardDecelKey": "倒车减速速度点", "BackwardDecel": "倒车减速值",
    "HasSkateParam": "滑板参数启用标记（只读）",
    "HasBattleModeSkillInfoList": "对战技能表启用标记（只读）",
    "BattleSkillNum": "对战技能数量（只读）", "BattleSkillID": "对战技能 ID",
    "BattleSkillLevel": "对战技能等级", "AddWeightNum": "附加配重数量（只读）",
    "AddWeightTable": "附加配重表", "WeightNum": "配重数量（只读）",
    "WeightTable": "配重表", "HasAntiCollisionCfg": "防撞配置标记（只读）",
    "AntiCollisionNum": "防撞位置数量（只读）", "AntiCollisionPosition": "防撞位置",
    "SkateTrackSpeed": "滑板轨道速度", "SkateSpeedCoefAirBigJet": "滑板空中大喷系数",
    "SkateSpeedCoefJump": "滑板跳跃速度系数",
    "SkateSpeedCoefAirJetPoint": "滑板空中喷点系数",
    "SkateSpeedCoefMaxForce": "滑板最大作用力系数",
    "SkateOntrackAccRef": "滑板上轨加速度参考", "SkateTrackAccRef": "滑板轨道加速度参考",
    "SkateDashSkill": "滑板冲刺技能参数", "BoatShape": "船体形状",
    "BoatForwardAccelKey": "船体前进加速速度点", "BoatForwardAccel": "船体前进加速值",
}

SECTIONS = ("身份", "模式", "动力", "漂移", "物理", "碰撞", "扩展", "特殊结构", "数组", "船形态", "其他")


def section_for(name: str) -> str:
    if name == "InternalKartID": return "身份"
    if name == "SuperJetType": return "模式"
    if name.startswith("Boat"): return "船形态"
    if name in SPECIAL_FIELDS: return "特殊结构"
    if name in ARRAY_FIELDS: return "数组"
    if name.startswith("CollisionBox") or name.startswith("CarCollision"): return "碰撞"
    if name in {"NitroPower", "NitroDuration", "SmallJetPower", "SmallJetDuration", "CollectEfficiency"}: return "动力"
    if name in {"BannerTwist", "DirKeyTwist", "BannerKeyTwist", "BannerVecForce", "DirUpKeyForce", "TurnRate", "VolatileTurnRate"}: return "漂移"
    if name in {"SlidFricForce", "AdditionalLocalZSpeed", "Gravity"}: return "物理"
    if name in {"CrashCompensatePower", "DefenseRate", "SpeedupCardGenRate", "ExtraFuncFlag", "EnergyConvert", "SuperN2ORate", "CollisionLoseRate", "NotInterruptDrift", "DirUpKeyForceParamA", "DirUpKeyForceParamB"}: return "扩展"
    return "其他"


def value_range(name: str):
    if name == "SuperJetType": return 4, 5
    if name == "InternalKartID": return 0, 0xFFFFFFFF
    if name in {"BattleSkillID"}: return -32768, 32767
    if name == "PhysInfoCount": return 0, 10
    if name in {"ForwardAccelNum", "ForwardDecelNum", "BackwardAccelNum", "BackwardDecelNum", "BoatForwardAccelNum"}: return 0, 30
    if name == "CompensateParamCount": return 0, 20
    if name == "AccelStatusCount": return 0, 6
    if name == "HasBoatParam": return 0, 1
    if name in {"PhysInfoPID", "PhysInfoAffectID"}: return 0, 0xFFFFFFFF
    if name in {"PhysInfoParam", "PhysInfoLifeTime"}: return -0x80000000, 0xFFFFFFFF
    if name == "PhysInfoCommonParaNum": return 0, 10
    if name in STRUCTURE_FIELDS or name in {"BattleSkillLevel", "AddWeightTable", "WeightTable", "NotInterruptDrift"}: return 0, 255
    if name in {"SuperN2ORate", "CollisionLoseRate"}: return 0, 65535
    return -0x80000000, 0xFFFFFFFF


@dataclass
class SnapshotRecord:
    protocol_record: int
    fields: OrderedDict
    common_para: list[list[int]] = field(default_factory=list)


@dataclass
class Snapshot:
    path: Path
    source_file: str
    carrier_file: str
    source_format: str
    records: list[SnapshotRecord]


def parse_snapshot(path) -> Snapshot:
    path = Path(path)
    text = path.read_text(encoding="utf-8-sig")
    if not any(line.strip().startswith("SchemaVersion:") for line in text.splitlines()):
        return parse_server_profile(path, text)
    schema = None; source = None; carrier = None; source_format = ""
    records = []; current = None
    for line_no, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#") or line == "Records:": continue
        if line.startswith("SchemaVersion:"):
            schema = int(line.split(":", 1)[1].strip()); continue
        if line.startswith("SourceFile:"):
            source = Path(line.split(":", 1)[1].strip()).name; continue
        if line.startswith("CarrierFile:"):
            carrier = Path(line.split(":", 1)[1].strip()).name; continue
        if line.startswith("SourceFormat:"):
            source_format = line.split(":", 1)[1].strip(); continue
        if line.startswith("- ProtocolRecord:"):
            number = int(line.split(":", 1)[1].strip())
            current = SnapshotRecord(number, OrderedDict()); records.append(current); continue
        if current is None or ":" not in line:
            raise ValueError(f"第 {line_no} 行不属于任何协议记录：{line}")
        name, text = (part.strip() for part in line.split(":", 1))
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
            raise ValueError(f"第 {line_no} 行字段名无效：{name}")
        if name in current.fields: raise ValueError(f"第 {line_no} 行字段重复：{name}")
        try: value = ast.literal_eval(text)
        except (ValueError, SyntaxError) as exc: raise ValueError(f"第 {line_no} 行数值格式错误：{name}") from exc
        if isinstance(value, bool) or not isinstance(value, (int, list)):
            raise ValueError(f"第 {line_no} 行只允许整数或整数数组：{name}")
        if isinstance(value, list) and any(isinstance(item, bool) or not isinstance(item, int) for item in value):
            raise ValueError(f"第 {line_no} 行数组包含非整数：{name}")
        current.fields[name] = value
    if schema != 1 or not source or not carrier or not records:
        raise ValueError("不是完整的 SchemaVersion 1 明文快照")
    return Snapshot(path, source, carrier, source_format, records)


def _strip_comment(line: str) -> str:
    return line.split("#", 1)[0].rstrip()


def _clean_lines(text: str):
    return [_strip_comment(line) for line in text.splitlines() if _strip_comment(line).strip()]


def _scalar(lines, key, default=0):
    prefix = key + ":"
    for line in lines:
        if line.startswith(prefix):
            text = line.split(":", 1)[1].strip()
            if text in ("true", "True"): return 1
            if text in ("false", "False"): return 0
            return int(text) if text else default
    return default


def _section(lines, key):
    marker = key + ":"
    for index, line in enumerate(lines):
        if line.strip() == marker:
            result = []
            for item in lines[index + 1:]:
                if item and not item.startswith(" ") and not item.startswith("- "):
                    break
                result.append(item)
            return result
    return []


def _simple_list(lines, key):
    return [int(line.strip()[2:].strip()) for line in _section(lines, key) if line.strip().startswith("- ")]


def _map_values(lines, key):
    values = {}
    for line in _section(lines, key):
        stripped = line.strip()
        if ":" in stripped and not stripped.startswith("- "):
            name, text = (part.strip() for part in stripped.split(":", 1))
            if not text:
                continue
            values[name] = int(text)
    return values


def _pair_list(lines, key, first_name, second_name):
    rows = []
    current = None
    for line in _section(lines, key):
        stripped = line.strip()
        if stripped.startswith(f"- {first_name}:"):
            current = [int(stripped.split(":", 1)[1].strip()), 0]
            rows.append(current)
        elif current is not None and stripped.startswith(f"{second_name}:"):
            current[1] = int(stripped.split(":", 1)[1].strip())
    return rows


def _phys_infos(lines):
    rows = []
    current = None
    in_common = False
    for line in _section(lines, "PhysInfo"):
        stripped = line.strip()
        if stripped.startswith("- PID:"):
            current = {"PID": int(stripped.split(":", 1)[1].strip()), "CommonPara": []}
            rows.append(current)
            in_common = False
        elif current is not None and stripped.startswith(("AffectID:", "Param:", "LifeTime:", "CommonParaNum:")):
            name, text = (part.strip() for part in stripped.split(":", 1))
            current[name] = int(text)
            in_common = False
        elif current is not None and stripped == "CommonPara:":
            in_common = True
        elif current is not None and in_common and stripped.startswith("- "):
            current["CommonPara"].append(int(stripped[2:].strip()))
    return rows


def _server_record(record_lines, protocol_record):
    fields = OrderedDict()
    fields["InternalKartID"] = _scalar(record_lines, "KartID")
    phys = _phys_infos(record_lines)
    fields["PhysInfoCount"] = _scalar(record_lines, "PhysInfoCount", len(phys))
    fields["PhysInfoPID"] = [item.get("PID", 0) for item in phys]
    fields["PhysInfoAffectID"] = [item.get("AffectID", 0) for item in phys]
    fields["PhysInfoParam"] = [item.get("Param", 0) for item in phys]
    fields["PhysInfoLifeTime"] = [item.get("LifeTime", 0) for item in phys]
    fields["PhysInfoCommonParaNum"] = [item.get("CommonParaNum", len(item.get("CommonPara", []))) for item in phys]
    common_para = [item.get("CommonPara", []) for item in phys]

    compensate = _pair_list(record_lines, "CompensateParam", "Percent", "Value")
    fields["CompensateParamCount"] = _scalar(record_lines, "CompensateParamCount", len(compensate))
    fields["CompensatePercent"] = [row[0] for row in compensate]
    fields["Compensate"] = [row[1] for row in compensate]

    for key, name in {
        "BoxLength": "CollisionBoxLength", "BoxWidth": "CollisionBoxWidth", "BoxHeight": "CollisionBoxHeight",
        "AdjustOffset": "CollisionBoxAdjustOffset", "AdjustPickGap": "CollisionBoxAdjustPickGap",
        "AdjustRemoteOffset": "CollisionBoxAdjustRemoteOffset", "AdjustBevelOffset": "CollisionBoxAdjustBevelOffset",
        "ControllerOffset": "CollisionBoxControllerOffset",
    }.items():
        fields[name] = _map_values(record_lines, "CollisionBoxParam").get(key, 0)
    for key, name in {
        "CollisionRadius": "CarCollisionRadius", "CollisionLength": "CarCollisionLength",
        "CollisionWidth": "CarCollisionWidth", "CollisionHeight": "CarCollisionHeight",
        "CollisionLostCtrlTime": "CarCollisionLostCtrlTime",
    }.items():
        fields[name] = _map_values(record_lines, "CarToCarCollisionParam").get(key, 0)

    for key, name in (
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
        fields[name] = _scalar(record_lines, key)

    fields["AccelStatusCount"] = _scalar(record_lines, "AccelStatusCount", len(_simple_list(record_lines, "AccelStatus")))
    fields["AccelStatus"] = _simple_list(record_lines, "AccelStatus")
    for count_name, section, key_name, value_name in (
        ("ForwardAccelNum", "ForwardAccel", "ForwardAccelKey", "ForwardAccel"),
        ("ForwardDecelNum", "ForwardDecel", "ForwardDecelKey", "ForwardDecel"),
        ("BackwardAccelNum", "BackwardAccel", "BackwardAccelKey", "BackwardAccel"),
        ("BackwardDecelNum", "BackwardDecel", "BackwardDecelKey", "BackwardDecel"),
        ("BoatForwardAccelNum", "BoatForwardAccel", "BoatForwardAccelKey", "BoatForwardAccel"),
    ):
        rows = _pair_list(record_lines, section, "Key", "Value")
        fields[count_name] = _scalar(record_lines, count_name, len(rows))
        fields[key_name] = [row[0] for row in rows]
        fields[value_name] = [row[1] for row in rows]

    for name in ("CrashCompensatePower", "DefenseRate", "SpeedupCardGenRate", "ExtraFuncFlag",
                 "EnergyConvert", "SuperN2ORate", "CollisionLoseRate", "NotInterruptDrift",
                 "DirUpKeyForceParamA", "DirUpKeyForceParamB"):
        fields[name] = _scalar(record_lines, name)
    fields["HasSkateParam"] = _scalar(record_lines, "SkateParaEnabled")
    fields["HasBattleModeSkillInfoList"] = _scalar(record_lines, "HasBattleModeSkillInfoList")
    fields["AddWeightNum"] = _scalar(record_lines, "AddWeightNum")
    fields["AddWeightTable"] = _simple_list(record_lines, "AddWeight")
    fields["WeightNum"] = _scalar(record_lines, "WeightNum", len(_simple_list(record_lines, "Weight")))
    fields["WeightTable"] = _simple_list(record_lines, "Weight")
    anti = _map_values(record_lines, "AntiCollisionCfg")
    fields["HasAntiCollisionCfg"] = _scalar(record_lines, "HasAntiCollisionCfg")
    fields["AntiCollisionNum"] = anti.get("Num", 0)
    fields["AntiCollisionPosition"] = _simple_list(record_lines, "Position")
    fields["HasBoatParam"] = _scalar(record_lines, "HasBoatParam")
    boat = _map_values(record_lines, "BoatParam")
    for key, name in (
        ("DirKeyForceParamC", "BoatDirKeyForceParamC"), ("DirKeyForceParamD", "BoatDirKeyForceParamD"),
        ("DTFLimitAngle", "BoatDTFLimitAngle"), ("DTFRatio", "BoatDTFRatio"),
        ("UpKeyVecForce", "BoatUpKeyVecForce"), ("UpKeyVecForceParamA", "BoatUpKeyVecForceParamA"),
        ("UpKeyVecForceParamB", "BoatUpKeyVecForceParamB"), ("LRKeyVecForce", "BoatLRKeyVecForce"),
        ("LRKeyVecForceParamA", "BoatLRKeyVecForceParamA"), ("LRKeyVecForceParamB", "BoatLRKeyVecForceParamB"),
        ("VecForce", "BoatVecForce"), ("VecForceParamA", "BoatVecForceParamA"),
        ("VecForceParamB", "BoatVecForceParamB"), ("WecEffect", "BoatWecEffect"),
        ("BannerKeyTwist", "BoatBannerKeyTwist"), ("BannerKeyTwistParamA", "BoatBannerKeyTwistParamA"),
        ("BannerKeyTwistParamB", "BoatBannerKeyTwistParamB"), ("SuaiJianTwist", "BoatSuaiJianTwist"),
        ("BoatHeighRatio", "BoatHeightRatio"), ("BannerTwist", "BoatBannerTwist"),
        ("BannerTwistParamA", "BoatBannerTwistParamA"), ("DirUpKeyForce", "BoatDirUpKeyForce"),
        ("DirUpKeyForceParamA", "BoatDirUpKeyForceParamA"), ("DirUpKeyForceParamB", "BoatDirUpKeyForceParamB"),
        ("DirKeyForce", "BoatDirKeyForce"), ("DirKeyForceParamA", "BoatDirKeyForceParamA"),
        ("DirKeyForceParamB", "BoatDirKeyForceParamB"), ("AddNO2PerSec", "BoatAddNO2PerSec"),
        ("BoatAirValue", "BoatAirValue"), ("ifSlidFricForce", "BoatSlidFricForce"),
    ):
        fields[name] = boat.get(key, 0)
    fields["BoatShape"] = _simple_list(record_lines, "BoatShape")
    return SnapshotRecord(protocol_record, fields, common_para)


def parse_server_profile(path, text) -> Snapshot:
    path = Path(path)
    lines = _clean_lines(text)
    source = path.name
    for raw in text.splitlines():
        if raw.strip().startswith("# SourceFile:"):
            source = Path(raw.split(":", 1)[1].strip()).name
            break
    records = []
    if any(line == "Records:" for line in lines):
        start = lines.index("Records:") + 1
        current_number = None
        current = []
        for line in lines[start:]:
            if line == "Profile:": break
            if line.startswith("- ProtocolRecord:"):
                if current_number is not None:
                    records.append(_server_record(current, current_number))
                current_number = int(line.split(":", 1)[1].strip())
                current = []
            elif current_number is not None:
                current.append(line[2:] if line.startswith("  ") else line)
        if current_number is not None:
            records.append(_server_record(current, current_number))
    else:
        profile_index = lines.index("Profile:") if "Profile:" in lines else len(lines)
        records.append(_server_record(lines[:profile_index], 1))
    if not records:
        raise ValueError("不是完整的服务端明文配置")
    return Snapshot(path, source, source, "ServerProfile551", records)


def validate_snapshot(snapshot: Snapshot):
    if not 1 <= len(snapshot.records) <= 3: raise ValueError("快照只能包含 1～3 条协议记录")
    expected_numbers = list(range(1, len(snapshot.records) + 1))
    if [record.protocol_record for record in snapshot.records] != expected_numbers:
        raise ValueError("ProtocolRecord 必须从 1 开始连续编号")
    relations = {
        "BattleSkillNum": ("BattleSkillID", "BattleSkillLevel"),
        "AddWeightNum": ("AddWeightTable",), "WeightNum": ("WeightTable",),
        "AntiCollisionNum": ("AntiCollisionPosition",),
        "PhysInfoCount": ("PhysInfoPID", "PhysInfoAffectID", "PhysInfoParam", "PhysInfoLifeTime", "PhysInfoCommonParaNum"),
        "CompensateParamCount": ("CompensatePercent",),
    }
    for record in snapshot.records:
        if "InternalKartID" not in record.fields: raise ValueError(f"记录 {record.protocol_record} 缺少 InternalKartID")
        for name, value in record.fields.items():
            low, high = value_range(name)
            items = value if isinstance(value, list) else [value]
            if any(not low <= item <= high for item in items):
                raise ValueError(f"记录 {record.protocol_record} 的 {name} 超出范围 {low}～{high}")
        for count_name, array_names in relations.items():
            if count_name not in record.fields: continue
            count = record.fields[count_name]
            for array_name in array_names:
                if array_name in record.fields and len(record.fields[array_name]) != count:
                    raise ValueError(f"记录 {record.protocol_record}：{array_name} 项数必须等于 {count_name}={count}")


def render_snapshot(snapshot: Snapshot) -> str:
    if snapshot.source_format == "ServerProfile551":
        return render_server_profile(snapshot)
    validate_snapshot(snapshot)
    lines = ["SchemaVersion: 1", f"SourceFile: {snapshot.source_file}",
             f"CarrierFile: {snapshot.carrier_file}", f"SourceFormat: {snapshot.source_format}", "Records:"]
    for record in snapshot.records:
        lines.append(f"  - ProtocolRecord: {record.protocol_record}")
        for name, value in record.fields.items():
            rendered = "[" + ", ".join(map(str, value)) + "]" if isinstance(value, list) else str(value)
            lines.append(f"    {name}: {rendered}")
    lines += ["", "# 此文件由 Top-Kart 551 明文快照编辑器保存。",
              "# 重新生成密文仍需要 CarrierFile 指定的原密文载体。"]
    return "\n".join(lines) + "\n"


def _ys(value):
    if isinstance(value, bool): return "true" if value else "false"
    return str(value)


def _rs(lines, key, value, indent=0):
    lines.append(f"{' ' * indent}{key}: {_ys(value)}")


def _rl(lines, key, values, indent=0):
    lines.append(f"{' ' * indent}{key}:")
    for value in values:
        lines.append(f"{' ' * indent}- {_ys(value)}")


def _rpair(lines, key, first, second, left, right, indent=0):
    lines.append(f"{' ' * indent}{key}:")
    for a, b in zip(left, right):
        lines.append(f"{' ' * indent}- {first}: {_ys(a)}")
        lines.append(f"{' ' * (indent + 2)}{second}: {_ys(b)}")


def _render_server_record(record: SnapshotRecord, include_profile=True, indent=0):
    f = record.fields
    lines = []
    _rs(lines, "KartID", f.get("InternalKartID", 0), indent)
    _rs(lines, "PhysInfoCount", f.get("PhysInfoCount", len(f.get("PhysInfoPID", []))), indent)
    lines.append(f"{' ' * indent}PhysInfo:")
    count = f.get("PhysInfoCount", len(f.get("PhysInfoPID", [])))
    for i in range(count):
        lines.append(f"{' ' * indent}- PID: {f.get('PhysInfoPID', [0] * count)[i]}")
        lines.append(f"{' ' * (indent + 2)}AffectID: {f.get('PhysInfoAffectID', [0] * count)[i]}")
        lines.append(f"{' ' * (indent + 2)}Param: {f.get('PhysInfoParam', [0] * count)[i]}")
        lines.append(f"{' ' * (indent + 2)}LifeTime: {f.get('PhysInfoLifeTime', [0] * count)[i]}")
        common_nums = f.get("PhysInfoCommonParaNum", [0] * count)
        common = record.common_para[i] if i < len(record.common_para) else []
        lines.append(f"{' ' * (indent + 2)}CommonParaNum: {common_nums[i] if i < len(common_nums) else len(common)}")
        if common:
            lines.append(f"{' ' * (indent + 2)}CommonPara:")
            for value in common:
                lines.append(f"{' ' * (indent + 2)}- {value}")
        else:
            lines.append(f"{' ' * (indent + 2)}CommonPara: []")

    _rs(lines, "CompensateParamCount", f.get("CompensateParamCount", len(f.get("Compensate", []))), indent)
    _rpair(lines, "CompensateParam", "Percent", "Value", f.get("CompensatePercent", []), f.get("Compensate", []), indent)

    lines.append(f"{' ' * indent}CollisionBoxParam:")
    for key, name in {
        "BoxLength": "CollisionBoxLength", "BoxWidth": "CollisionBoxWidth", "BoxHeight": "CollisionBoxHeight",
        "AdjustOffset": "CollisionBoxAdjustOffset", "AdjustPickGap": "CollisionBoxAdjustPickGap",
        "AdjustRemoteOffset": "CollisionBoxAdjustRemoteOffset", "AdjustBevelOffset": "CollisionBoxAdjustBevelOffset",
        "ControllerOffset": "CollisionBoxControllerOffset",
    }.items():
        _rs(lines, key, f.get(name, 0), indent + 2)
    lines.append(f"{' ' * indent}CarToCarCollisionParam:")
    for key, name in {
        "CollisionRadius": "CarCollisionRadius", "CollisionLength": "CarCollisionLength",
        "CollisionWidth": "CarCollisionWidth", "CollisionHeight": "CarCollisionHeight",
        "CollisionLostCtrlTime": "CarCollisionLostCtrlTime",
    }.items():
        _rs(lines, key, f.get(name, 0), indent + 2)

    for key, name in (
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
        _rs(lines, key, f.get(name, 0), indent)

    _rs(lines, "AccelStatusCount", f.get("AccelStatusCount", len(f.get("AccelStatus", []))), indent)
    _rl(lines, "AccelStatus", f.get("AccelStatus", []), indent)
    for count_name, section, key_name, value_name in (
        ("ForwardAccelNum", "ForwardAccel", "ForwardAccelKey", "ForwardAccel"),
        ("ForwardDecelNum", "ForwardDecel", "ForwardDecelKey", "ForwardDecel"),
        ("BackwardAccelNum", "BackwardAccel", "BackwardAccelKey", "BackwardAccel"),
        ("BackwardDecelNum", "BackwardDecel", "BackwardDecelKey", "BackwardDecel"),
    ):
        _rs(lines, count_name, f.get(count_name, len(f.get(value_name, []))), indent)
        _rpair(lines, section, "Key", "Value", f.get(key_name, []), f.get(value_name, []), indent)

    for name in ("CrashCompensatePower", "DefenseRate", "SpeedupCardGenRate", "ExtraFuncFlag",
                 "EnergyConvert", "SuperN2ORate", "CollisionLoseRate", "NotInterruptDrift"):
        _rs(lines, name, f.get(name, 0), indent)
    _rs(lines, "SkateParaEnabled", f.get("HasSkateParam", 0), indent)
    _rs(lines, "HasBattleModeSkillInfoList", f.get("HasBattleModeSkillInfoList", 0), indent)
    _rs(lines, "AddWeightNum", f.get("AddWeightNum", 0), indent)
    _rl(lines, "AddWeight", f.get("AddWeightTable", []), indent)
    _rs(lines, "WeightNum", f.get("WeightNum", len(f.get("WeightTable", []))), indent)
    _rl(lines, "Weight", f.get("WeightTable", []), indent)
    _rs(lines, "HasAntiCollisionCfg", f.get("HasAntiCollisionCfg", 0), indent)
    lines.append(f"{' ' * indent}AntiCollisionCfg:")
    _rs(lines, "Num", f.get("AntiCollisionNum", len(f.get("AntiCollisionPosition", []))), indent + 2)
    _rl(lines, "Position", f.get("AntiCollisionPosition", []), indent + 2)

    _rs(lines, "HasBoatParam", f.get("HasBoatParam", 0), indent)
    lines.append(f"{' ' * indent}BoatParam:")
    for key, name in (
        ("DirKeyForceParamC", "BoatDirKeyForceParamC"), ("DirKeyForceParamD", "BoatDirKeyForceParamD"),
        ("DTFLimitAngle", "BoatDTFLimitAngle"), ("DTFRatio", "BoatDTFRatio"),
        ("UpKeyVecForce", "BoatUpKeyVecForce"), ("UpKeyVecForceParamA", "BoatUpKeyVecForceParamA"),
        ("UpKeyVecForceParamB", "BoatUpKeyVecForceParamB"), ("LRKeyVecForce", "BoatLRKeyVecForce"),
        ("LRKeyVecForceParamA", "BoatLRKeyVecForceParamA"), ("LRKeyVecForceParamB", "BoatLRKeyVecForceParamB"),
        ("VecForce", "BoatVecForce"), ("VecForceParamA", "BoatVecForceParamA"),
        ("VecForceParamB", "BoatVecForceParamB"), ("WecEffect", "BoatWecEffect"),
        ("BannerKeyTwist", "BoatBannerKeyTwist"), ("BannerKeyTwistParamA", "BoatBannerKeyTwistParamA"),
        ("BannerKeyTwistParamB", "BoatBannerKeyTwistParamB"), ("SuaiJianTwist", "BoatSuaiJianTwist"),
        ("BoatHeighRatio", "BoatHeightRatio"), ("BannerTwist", "BoatBannerTwist"),
        ("BannerTwistParamA", "BoatBannerTwistParamA"), ("DirUpKeyForce", "BoatDirUpKeyForce"),
        ("DirUpKeyForceParamA", "BoatDirUpKeyForceParamA"), ("DirUpKeyForceParamB", "BoatDirUpKeyForceParamB"),
        ("DirKeyForce", "BoatDirKeyForce"), ("DirKeyForceParamA", "BoatDirKeyForceParamA"),
        ("DirKeyForceParamB", "BoatDirKeyForceParamB"), ("AddNO2PerSec", "BoatAddNO2PerSec"),
        ("BoatAirValue", "BoatAirValue"), ("ifSlidFricForce", "BoatSlidFricForce"),
    ):
        _rs(lines, key, f.get(name, 0), indent + 2)
    _rl(lines, "BoatShape", f.get("BoatShape", []), indent + 2)
    _rs(lines, "BoatForwardAccelNum", f.get("BoatForwardAccelNum", len(f.get("BoatForwardAccel", []))), indent)
    _rpair(lines, "BoatForwardAccel", "Key", "Value", f.get("BoatForwardAccelKey", []), f.get("BoatForwardAccel", []), indent)
    _rs(lines, "DirUpKeyForceParamA", f.get("DirUpKeyForceParamA", 0), indent)
    _rs(lines, "DirUpKeyForceParamB", f.get("DirUpKeyForceParamB", 0), indent)
    return lines


def render_server_profile(snapshot: Snapshot) -> str:
    lines = ["# Generated from EncryptKart 551 data for mode28346=3.", f"# SourceFile: {snapshot.source_file}"]
    if len(snapshot.records) > 1:
        lines += ["SkateParaEnabled: 0", "HasBattleModeSkillInfoList: 0", "Records:"]
        for record in snapshot.records:
            lines.append(f"- ProtocolRecord: {record.protocol_record}")
            lines.extend(_render_server_record(record, include_profile=False, indent=2))
        base_id = snapshot.records[0].fields.get("InternalKartID", 0)
    else:
        lines.extend(_render_server_record(snapshot.records[0], include_profile=False, indent=0))
        base_id = snapshot.records[0].fields.get("InternalKartID", 0)
    lines.append("Profile:")
    _rs(lines, "Version", 1, 2)
    lines.append("  Mode: FinalWithRefitAndPet")
    _rs(lines, "Account", 10001, 2)
    _rs(lines, "BaseKartID", base_id, 2)
    _rs(lines, "SkinID", 0, 2)
    _rs(lines, "IncludesRefit", True, 2)
    _rs(lines, "IncludesPet", True, 2)
    return "\n".join(lines) + "\n"


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Top-Kart 551 明文快照编辑器（协作版）")
        self.geometry("1320x860"); self.minsize(980, 650)
        self.app_dir = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
        default = self.app_dir / "551明文导出"
        self.source_dir = default if default.is_dir() else None
        self.output_dir = self.app_dir / "快照编辑输出"
        self.files = []; self.filtered = []; self.current = None; self.original = None
        self.trees = {}; self.compare_tree = None; self.dirty = False
        self._list_mouse_down = False; self._list_load_after = None
        self._ui()
        if self.source_dir: self.reload_files()
        self.protocol("WM_DELETE_WINDOW", self.close_app)

    def _ui(self):
        top = ttk.Frame(self, padding=6); top.pack(fill="x")
        for text, command in (("打开快照目录", self.choose_dir), ("打开单个快照", self.open_one),
                              ("重新载入", self.reload_current), ("另存贡献稿", self.save_copy),
                              ("覆盖当前快照", self.overwrite), ("导出修改清单", self.export_changes)):
            ttk.Button(top, text=text, command=command).pack(side="left", padx=3)
        self.status = tk.StringVar(value="就绪"); ttk.Label(top, textvariable=self.status).pack(side="right", padx=8)
        pane = ttk.Panedwindow(self, orient="horizontal"); pane.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        left = ttk.Frame(pane, padding=4); right = ttk.Frame(pane, padding=4); pane.add(left, weight=1); pane.add(right, weight=4)
        self.dir_label = ttk.Label(left, text="未选择快照目录", wraplength=280); self.dir_label.pack(fill="x", pady=3)
        self.search = tk.StringVar(); self.search.trace_add("write", lambda *_: self.filter_files())
        ttk.Entry(left, textvariable=self.search).pack(fill="x", pady=3)
        list_frame = ttk.Frame(left); list_frame.pack(fill="both", expand=True)
        self.listbox = tk.Listbox(list_frame, exportselection=False, font=("Microsoft YaHei UI", 10))
        bar = ttk.Scrollbar(list_frame, orient="vertical", command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=bar.set); self.listbox.pack(side="left", fill="both", expand=True); bar.pack(side="right", fill="y")
        self.listbox.bind("<ButtonPress-1>", self.list_press, add="+")
        self.listbox.bind("<ButtonRelease-1>", self.list_release, add="+")
        self.listbox.bind("<<ListboxSelect>>", self.select_file)
        self.count = ttk.Label(left, text="0 个文件"); self.count.pack(fill="x", pady=3)
        self.info = ttk.Label(right, text="请选择一份 SchemaVersion 1 快照", wraplength=920); self.info.pack(fill="x", pady=5)
        self.tabs = ttk.Notebook(right); self.tabs.pack(fill="both", expand=True)
        ttk.Label(right, text="协作版只修改明文字段；结构标记和数量只读。另存贡献稿不会覆盖原快照。",
                  foreground="#9a5a00").pack(fill="x", pady=5)

    def choose_dir(self):
        folder = filedialog.askdirectory(title="选择 551明文导出 目录")
        if folder:
            if not self.confirm_leave(): return
            self.source_dir = Path(folder); self.reload_files()

    def open_one(self):
        path = filedialog.askopenfilename(title="打开明文快照", filetypes=(("YAML 快照", "*.yml"), ("所有文件", "*.*")))
        if path and self.confirm_leave(): self.load(Path(path))

    def reload_files(self):
        self.files = sorted(self.source_dir.glob("*.yml"), key=lambda p: p.name.lower())
        self.dir_label.configure(text=str(self.source_dir)); self.filter_files()

    def filter_files(self):
        query = self.search.get().strip().lower()
        self.filtered = [path for path in self.files if query in path.name.lower()]
        self.listbox.delete(0, "end")
        for path in self.filtered: self.listbox.insert("end", path.name)
        self.count.configure(text=f"{len(self.filtered)} / {len(self.files)} 个文件")

    def list_press(self, _event=None):
        self._list_mouse_down = True
        if self._list_load_after is not None: self.after_cancel(self._list_load_after); self._list_load_after = None

    def list_release(self, _event=None): self._list_mouse_down = False; self.select_file()

    def select_file(self, _event=None):
        if self._list_mouse_down: return
        if self._list_load_after is not None: self.after_cancel(self._list_load_after)
        self._list_load_after = self.after(250, self.load_selected)

    def load_selected(self):
        self._list_load_after = None; selected = self.listbox.curselection()
        if selected and self.confirm_leave(): self.load(self.filtered[selected[0]])

    def load(self, path):
        try:
            snapshot = parse_snapshot(path); validate_snapshot(snapshot)
            self.current = snapshot; self.original = copy.deepcopy(snapshot); self.dirty = False
            self.build_tabs(); ids = ", ".join(str(r.fields["InternalKartID"]) for r in snapshot.records)
            self.info.configure(text=f"{path.name}　记录 {len(snapshot.records)}　内部 ID {ids}　SourceFile={snapshot.source_file}　CarrierFile={snapshot.carrier_file}")
            self.status.set("快照解析成功")
        except Exception as exc: messagebox.showerror("快照解析失败", f"{path}\n\n{exc}"); self.status.set("解析失败")

    def shape_number(self, index):
        if len(self.current.records) == 3: return {1: 3, 2: 1, 3: 2}[index]
        return index

    def display_records(self): return sorted(self.current.records, key=lambda record: self.shape_number(record.protocol_record))

    def all_names(self):
        result = []
        for record in self.current.records:
            for name in record.fields:
                if name not in result: result.append(name)
        return result

    def values_for(self, name, index):
        values = []
        for record in self.display_records():
            value = record.fields.get(name)
            if value is None or (index >= 0 and (not isinstance(value, list) or index >= len(value))): values.append("—")
            else: values.append(value[index] if index >= 0 else value)
        return values

    @staticmethod
    def compare_text(values):
        if len(values) == 1: return "单记录"
        if len(set(values)) == 1: return f"相同: {values[0]}"
        return " / ".join(f"形{i + 1}:{value}" for i, value in enumerate(values))

    def build_tabs(self):
        for tab in self.tabs.tabs(): self.tabs.forget(tab)
        self.trees = {}; self.compare_tree = None
        records = self.display_records()
        if len(records) > 1: self.build_compare(records)
        for record in records:
            shape = self.shape_number(record.protocol_record); title = f"第{shape}形态" if len(records) > 1 else "车辆参数"
            page = ttk.Frame(self.tabs, padding=6); self.tabs.add(page, text=title)
            ttk.Label(page, text=f"{title} = ProtocolRecord {record.protocol_record}　双击数值编辑",
                      foreground="#1565c0").pack(fill="x", pady=(0, 6))
            frame = ttk.Frame(page); frame.pack(fill="both", expand=True)
            tree = ttk.Treeview(frame, columns=("section", "field", "item", "value", "status"), show="headings", selectmode="browse")
            for column, text, width in (("section", "分类", 90), ("field", "字段", 330), ("item", "数组项", 75),
                                        ("value", "数值（双击编辑）", 170), ("status", "形态对比", 150)):
                tree.heading(column, text=text); tree.column(column, width=width, anchor="w" if column == "field" else "center")
            bar = ttk.Scrollbar(frame, orient="vertical", command=tree.yview); tree.configure(yscrollcommand=bar.set)
            tree.pack(side="left", fill="both", expand=True); bar.pack(side="right", fill="y")
            tree.tag_configure("same", background="#ffffff"); tree.tag_configure("array", background="#eef6ff")
            tree.tag_configure("different", background="#fff1bf"); tree.tag_configure("readonly", background="#eeeeee", foreground="#666666")
            for section in SECTIONS:
                for name, value in record.fields.items():
                    if section_for(name) != section: continue
                    label = LABELS.get(name, name)
                    indexes = range(len(value)) if isinstance(value, list) else (-1,)
                    for index in indexes:
                        item_value = value[index] if index >= 0 else value; comparison = self.values_for(name, index)
                        readonly = name in STRUCTURE_FIELDS
                        status = "结构只读" if readonly else self.compare_text(comparison)
                        tag = "readonly" if readonly else ("different" if len(set(comparison)) > 1 else ("array" if index >= 0 else "same"))
                        tree.insert("", "end", iid=f"{name}:{index}", values=(section, f"{label} ({name})", index + 1 if index >= 0 else "-", item_value, status), tags=(tag,))
            tree.bind("<Double-1>", lambda event, rec=record, widget=tree: self.begin_edit(event, rec, widget))
            self.trees[record.protocol_record] = tree

    def build_compare(self, records):
        page = ttk.Frame(self.tabs, padding=6); self.tabs.add(page, text=f"{len(records)}形态对比")
        ttk.Label(page, text="黄色表示该项在各形态之间不同", foreground="#1565c0").pack(fill="x", pady=(0, 6))
        frame = ttk.Frame(page); frame.pack(fill="both", expand=True)
        shape_columns = tuple(f"shape{i+1}" for i in range(len(records)))
        tree = ttk.Treeview(frame, columns=("section", "field", "item") + shape_columns + ("result",), show="headings")
        defs = [("section", "分类", 85), ("field", "字段", 300), ("item", "数组项", 70)]
        defs += [(column, f"第{i+1}形态", 110) for i, column in enumerate(shape_columns)]; defs += [("result", "对比", 80)]
        for column, text, width in defs: tree.heading(column, text=text); tree.column(column, width=width, anchor="w" if column == "field" else "center")
        bar = ttk.Scrollbar(frame, orient="vertical", command=tree.yview); tree.configure(yscrollcommand=bar.set)
        tree.pack(side="left", fill="both", expand=True); bar.pack(side="right", fill="y")
        tree.tag_configure("same", background="#ffffff"); tree.tag_configure("different", background="#ffe59a")
        for section in SECTIONS:
            for name in self.all_names():
                if section_for(name) != section: continue
                present = [record.fields.get(name) for record in records]; sample = next(value for value in present if value is not None)
                indexes = range(max(len(value) for value in present if isinstance(value, list))) if isinstance(sample, list) else (-1,)
                for index in indexes:
                    values = self.values_for(name, index); differs = len(set(values)) > 1
                    tree.insert("", "end", iid=f"{name}:{index}", values=(section, f"{LABELS.get(name, name)} ({name})", index + 1 if index >= 0 else "-", *values, "不同" if differs else "相同"), tags=("different" if differs else "same",))
        self.compare_tree = tree

    def begin_edit(self, event, record, tree):
        if tree.identify_region(event.x, event.y) != "cell" or tree.identify_column(event.x) != "#4": return
        item = tree.identify_row(event.y)
        if not item: return
        name, index_text = item.rsplit(":", 1); index = int(index_text)
        if name in STRUCTURE_FIELDS: return
        box = tree.bbox(item, "value")
        if not box: return
        current = record.fields[name]; old = current[index] if index >= 0 else current
        edit = ttk.Entry(tree); edit.insert(0, str(old)); edit.select_range(0, "end"); edit.focus_set(); edit.place(x=box[0], y=box[1], width=box[2], height=box[3])
        done = {"value": False}
        def commit(_event=None):
            if done["value"]: return
            done["value"] = True
            try:
                value = int(edit.get()); low, high = value_range(name)
                if not low <= value <= high: raise ValueError(f"允许范围 {low}～{high}")
            except ValueError as exc: messagebox.showwarning("数值无效", f"{name}: {exc}"); edit.destroy(); return
            if index >= 0: record.fields[name][index] = value
            else: record.fields[name] = value
            self.dirty = True; self.build_tabs(); self.status.set("存在尚未保存的修改"); edit.destroy()
        edit.bind("<Return>", commit); edit.bind("<FocusOut>", commit); edit.bind("<Escape>", lambda _e: edit.destroy())

    def changes(self):
        if not self.current or not self.original: return []
        result = []
        for current, original in zip(self.current.records, self.original.records):
            names = list(dict.fromkeys(list(original.fields) + list(current.fields)))
            for name in names:
                before = original.fields.get(name); after = current.fields.get(name)
                if before == after: continue
                if isinstance(before, list) and isinstance(after, list):
                    for index, (old, new) in enumerate(zip(before, after), 1):
                        if old != new: result.append((current.protocol_record, name, index, old, new))
                else: result.append((current.protocol_record, name, None, before, after))
        return result

    def report_text(self):
        rows = self.changes(); lines = [f"SourceFile: {self.current.source_file}", f"CarrierFile: {self.current.carrier_file}", f"修改项数: {len(rows)}", ""]
        for protocol, name, index, old, new in rows:
            shape = self.shape_number(protocol); suffix = f"[{index}]" if index is not None else ""
            lines.append(f"第{shape}形态\t{name}{suffix}\t{old} -> {new}")
        if not rows: lines.append("没有数值修改。")
        return "\n".join(lines) + "\n"

    def save_to(self, output):
        output = Path(output); output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(render_snapshot(self.current), encoding="utf-8-sig")
        report = output.with_suffix(".changes.txt"); report.write_text(self.report_text(), encoding="utf-8-sig")
        return report

    def save_copy(self):
        if not self.current: return
        self.output_dir.mkdir(exist_ok=True)
        default = self.output_dir / self.current.path.name
        output = filedialog.asksaveasfilename(title="另存贡献稿", initialdir=str(default.parent), initialfile=default.name, defaultextension=".yml", filetypes=(("YAML 快照", "*.yml"),))
        if not output: return
        if Path(output).resolve() == self.current.path.resolve():
            messagebox.showwarning("禁止覆盖", "“另存贡献稿”不能覆盖当前原快照。\n如确实需要覆盖，请使用“覆盖当前快照”。")
            return
        try:
            report = self.save_to(output); self.dirty = False; self.status.set("贡献稿保存成功")
            messagebox.showinfo("保存成功", f"贡献稿：\n{output}\n\n修改清单：\n{report}\n\n原快照未覆盖。")
        except Exception as exc: messagebox.showerror("保存失败", str(exc))

    def overwrite(self):
        if not self.current or not messagebox.askyesno("确认覆盖", f"确定覆盖当前快照？\n\n{self.current.path}"): return
        try:
            report = self.save_to(self.current.path); self.original = copy.deepcopy(self.current); self.dirty = False; self.status.set("已覆盖保存")
            messagebox.showinfo("保存成功", f"已覆盖：\n{self.current.path}\n\n修改清单：\n{report}")
        except Exception as exc: messagebox.showerror("保存失败", str(exc))

    def export_changes(self):
        if not self.current: return
        output = filedialog.asksaveasfilename(title="导出修改清单", initialfile=self.current.path.stem + ".changes.txt", defaultextension=".txt", filetypes=(("文本文件", "*.txt"),))
        if output:
            Path(output).write_text(self.report_text(), encoding="utf-8-sig"); messagebox.showinfo("已导出", output)

    def reload_current(self):
        if self.current and self.confirm_leave(): self.load(self.current.path)

    def confirm_leave(self):
        return not self.dirty or messagebox.askyesno("放弃修改", "当前修改尚未保存，确定放弃吗？")

    def close_app(self):
        if self.confirm_leave(): self.destroy()


if __name__ == "__main__":
    App().mainloop()
