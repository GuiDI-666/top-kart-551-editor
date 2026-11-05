from __future__ import annotations

from collections import defaultdict
import os
from pathlib import Path
import re
import sys

from kart551_backend import Kart551Codec, RECORD_SIZE, find_server_encrypt_dir


def _resolve_plain_dir() -> Path:
    """定位明文配置目录：优先 PLAIN_KART_DIR 环境变量，其次 EncryptKart 的同级 Kart 目录。"""
    configured = os.environ.get("PLAIN_KART_DIR")
    if configured:
        return Path(configured)
    encrypted = find_server_encrypt_dir()
    if encrypted is not None:
        return encrypted.parent / "Kart"
    return Path(__file__).resolve().parent / "Kart"


PLAIN_DIR = _resolve_plain_dir()
SCALAR_PATHS = {
    "BaseTurnRate": ("BaseTurnRate",),
    "VolatileTurnRate": ("VolatileTurnRate",),
    "MaxTurnSpeed": ("MaxTurnSpeed",),
    "MinTurnSpeed": ("MinTurnSpeed",),
    "MaxAccuTime": ("MaxAccuTime",),
    "BaseAccuRate": ("BaseAccuRate",),
    "MaxAffectSpeed": ("MaxAffectSpeed",),
    "Gravity": ("Gravity",),
    "AdditionalLocalZSpeed": ("AdditionalLocalZSpeed",),
    "StartVec": ("StartVec",),
    "EndVecFist": ("EndVecFist",),
    "EndVecSecon": ("EndVecSecon",),
    "DirKeyForce": ("DirKeyForce",),
    "DirKeyTwist": ("DirKeyTwist",),
    "BannerTwist": ("BannerTwist",),
    "BannerKeyTwist": ("BannerKeyTwist",),
    "BannerVecForce": ("BannerVecForce",),
    "BannerHeadForce": ("BannerHeadForce",),
    "SlidFricForce": ("SlidFricForce",),
    "RollFricForce": ("RollFricForce",),
    "StartWec": ("StartWec",),
    "MaxWec": ("MaxWec",),
    "SuaiJianTwist": ("SuaiJianTwist",),
    "DirUpKeyForce": ("DirUpKeyForce",),
    "CrashCompensatePower": ("CrashCompensatePower",),
    "DefenseRate": ("DefenseRate",),
    "SpeedupCardGenRate": ("SpeedupCardGenRate",),
    "ExtraFuncFlag": ("ExtraFuncFlag",),
    "EnergyConvert": ("EnergyConvert",),
    "SuperN2ORate": ("SuperN2ORate",),
    "CollisionLoseRate": ("CollisionLoseRate",),
    "NotInterruptDrift": ("NotInterruptDrift",),
    "DirUpKeyForceParamA": ("DirUpKeyForceParamA",),
    "DirUpKeyForceParamB": ("DirUpKeyForceParamB",),
}
for group in ("CollisionBoxParam", "CarToCarCollisionParam"):
    for field in (
        "BoxLength", "BoxWidth", "BoxHeight", "AdjustOffset", "AdjustPickGap",
        "AdjustRemoteOffset", "AdjustBevelOffset", "ControllerOffset",
        "CollisionRadius", "CollisionLength", "CollisionWidth", "CollisionHeight",
        "CollisionLostCtrlTime",
    ):
        SCALAR_PATHS[f"{group}.{field}"] = (group, field)
for field in (
    "DirKeyForceParamC", "DirKeyForceParamD", "DTFLimitAngle", "DTFRatio",
    "UpKeyVecForce", "UpKeyVecForceParamA", "UpKeyVecForceParamB",
    "LRKeyVecForce", "LRKeyVecForceParamA", "LRKeyVecForceParamB",
    "VecForce", "VecForceParamA", "VecForceParamB", "WecEffect",
    "BannerKeyTwist", "BannerKeyTwistParamA", "BannerKeyTwistParamB",
    "SuaiJianTwist", "BoatHeighRatio", "BannerTwist", "BannerTwistParamA",
    "DirUpKeyForce", "DirUpKeyForceParamA", "DirUpKeyForceParamB",
    "DirKeyForce", "DirKeyForceParamA", "DirKeyForceParamB",
    "AddNO2PerSec", "BoatAirValue", "SlidFricForce",
):
    SCALAR_PATHS[f"BoatParam.{field}"] = ("BoatParam", field)


def nested(config, path):
    value = config
    for part in path:
        if not isinstance(value, dict) or part not in value:
            return None
        value = value[part]
    return value if isinstance(value, int) else None


def load_plain_scalars(path):
    result = {}
    section = None
    for raw in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        match = re.match(r"^(\s*)([A-Za-z][A-Za-z0-9_]*):\s*(-?\d+)?\s*$", raw)
        if not match:
            continue
        indent, key, text = match.groups()
        if not indent:
            section = key if text is None else None
            if text is not None:
                result[key] = int(text)
        elif section and text is not None:
            result.setdefault(section, {})[key] = int(text)
    return result


def main(limit=250):
    encrypted_dir = find_server_encrypt_dir()
    if encrypted_dir is None:
        raise RuntimeError("找不到 EncryptKart")
    codec = Kart551Codec()
    samples = []
    files = sorted(encrypted_dir.glob("*.yml"), key=lambda p: p.name)
    for encrypted in files:
        plain = PLAIN_DIR / encrypted.name
        if not plain.is_file():
            continue
        doc = codec.read(encrypted)
        if len(doc.records) != 1:
            continue
        config = load_plain_scalars(plain)
        record = doc.records[0]
        cells = {
            offset - record.base: cell.value & 0xFFFFFFFF
            for offset, cell in doc.cells.items()
            if record.base <= offset < record.base + RECORD_SIZE
        }
        samples.append((config, cells))
        if len(samples) >= limit:
            break

    print(f"samples={len(samples)}")
    for name, path in SCALAR_PATHS.items():
        usable = [(nested(config, path), cells) for config, cells in samples]
        usable = [(value & 0xFFFFFFFF, cells) for value, cells in usable if value is not None]
        if not usable:
            continue
        nonzero = [(value, cells) for value, cells in usable if value != 0]
        if nonzero:
            usable = nonzero
        scores = defaultdict(int)
        for value, cells in usable:
            for rel, decoded in cells.items():
                if decoded == value:
                    scores[rel] += 1
        ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))[:5]
        diversity = len({value for value, _ in usable})
        rendered = ", ".join(f"{rel:#06x}:{hits}/{len(usable)}" for rel, hits in ranked)
        print(f"{name:42} distinct={diversity:3}  {rendered}")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 250)
