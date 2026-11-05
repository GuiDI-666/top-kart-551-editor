#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""无需 Qt 的 Top-Kart 551 密文可视化编辑器。"""

import copy
import ast
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

from kart551_backend import (
    Kart551Codec, LEGACY_FIELD_ALIASES, STRUCTURE_FIELDS,
    find_server_encrypt_dir, format_server_profile, parse_server_profile_snapshot,
)


INFO = {
    "SuperJetType": ("喷射模式（4普通/5超级喷）", 4, 5, "模式"),
    "NitroPower": ("氮气强度", 0, 16383, "动力"), "SmallJetPower": ("小喷强度", 0, 16383, "动力"),
    "CollectEfficiency": ("集气效率", 0, 2097151, "动力"), "NitroDuration": ("氮气时长", 0, 16383, "动力"),
    "SmallJetDuration": ("小喷时长", 0, 16383, "动力"), "BannerTwist": ("漂移转向扭矩", 0, 16383, "漂移"),
    "DirKeyTwist": ("方向键转向扭矩", 0, 16383, "漂移"), "BannerKeyTwist": ("漂移方向键转向扭矩", 0, 16383, "漂移"),
    "BannerVecForce": ("漂移矢量作用力", 0, 16383, "漂移"), "DirUpKeyForce": ("方向键抬起作用力", 0, 16383, "漂移"),
    "TurnRate": ("基础转向率", 0, 16383, "漂移"), "VolatileTurnRate": ("不稳定转向率", 0, 16383, "漂移"),
    "SlidFricForce": ("滑动摩擦力", 0, 16383, "物理"), "AdditionalLocalZSpeed": ("附加本地 Z 速度（平衡）", -2147483648, 2147483647, "物理"),
    "Gravity": ("重力（悬挂）", -2147483648, 2147483647, "物理"), "MaxTurnSpeed": ("最大转向速度", 0, 16383, "高级漂移"),
    "MinTurnSpeed": ("最小转向速度", 0, 16383, "高级漂移"), "BaseAccuRate": ("基础累积速率", 0, 16383, "高级漂移"),
    "MaxAccuTime": ("最大累积时间", 0, 16383, "高级漂移"), "MaxAffectSpeed": ("生效最大速度", 0, 2097151, "高级漂移"),
    "StartVec": ("触发最低速度", 0, 2097151, "高级漂移"), "EndVecFist": ("一级中断阈值", 0, 2097151, "高级漂移"),
    "EndVecSecon": ("二级退出阈值", 0, 2097151, "高级漂移"), "DirKeyForce": ("方向键作用力", 0, 16383, "高级漂移"),
    "BannerHeadForce": ("车头回正力", 0, 16383, "高级漂移"), "RollFricForce": ("滚动摩擦力", 0, 16383, "高级漂移"),
    "StartWec": ("接触起始阈值", 0, 16383, "高级漂移"), "MaxWec": ("接触最大阈值", 0, 16383, "高级漂移"),
    "SuaiJianTwist": ("断位转向扭矩", 0, 16383, "高级漂移"), "AccelStatus": ("多档平跑加速", 0, 4294967295, "数组"),
    "CollisionBoxLength": ("碰撞盒长度", 0, 4294967295, "碰撞"), "CollisionBoxWidth": ("碰撞盒宽度", 0, 4294967295, "碰撞"), "CollisionBoxHeight": ("碰撞盒高度", 0, 4294967295, "碰撞"),
    "CollisionBoxAdjustOffset": ("碰撞盒调整偏移", 0, 4294967295, "碰撞"), "CollisionBoxAdjustRemoteOffset": ("碰撞盒远端调整偏移", 0, 4294967295, "碰撞"),
    "CollisionBoxAdjustPickGap": ("碰撞盒拾取间隙", 0, 4294967295, "碰撞"), "CollisionBoxAdjustBevelOffset": ("碰撞盒斜面调整偏移", 0, 4294967295, "碰撞"),
    "CollisionBoxControllerOffset": ("碰撞盒控制器偏移", -2147483648, 2147483647, "碰撞"), "CarCollisionRadius": ("车车碰撞半径", 0, 4294967295, "碰撞"),
    "CarCollisionLength": ("车车碰撞长度", 0, 4294967295, "碰撞"), "CarCollisionWidth": ("车车碰撞宽度", 0, 4294967295, "碰撞"),
    "CarCollisionHeight": ("车车碰撞高度", 0, 4294967295, "碰撞"), "CarCollisionLostCtrlTime": ("车车碰撞失控时间", 0, 4294967295, "碰撞"),
    "CrashCompensatePower": ("碰撞补偿强度", -2147483648, 2147483647, "扩展"), "DefenseRate": ("防御率", -2147483648, 2147483647, "扩展"),
    "SpeedupCardGenRate": ("加速卡生成率", -2147483648, 2147483647, "扩展"), "ExtraFuncFlag": ("额外功能标志", 0, 4294967295, "扩展"),
    "EnergyConvert": ("能量转换", -2147483648, 2147483647, "扩展"), "SuperN2ORate": ("超级氮气率", 0, 65535, "扩展"),
    "CollisionLoseRate": ("碰撞损失率", 0, 65535, "扩展"), "NotInterruptDrift": ("漂移不中断", 0, 255, "扩展"),
    "DirUpKeyForceParamA": ("抬键作用力参数 A", -2147483648, 2147483647, "扩展"), "DirUpKeyForceParamB": ("抬键作用力参数 B", -2147483648, 2147483647, "扩展"),
    "PhysInfoCount": ("效果数量（只读）", 0, 10, "特殊结构"),
    "PhysInfoPID": ("效果 PID（只读）", 0, 4294967295, "特殊结构"),
    "PhysInfoAffectID": ("效果 AffectID（只读）", 0, 4294967295, "特殊结构"),
    "PhysInfoParam": ("效果参数（只读）", -2147483648, 2147483647, "特殊结构"),
    "PhysInfoLifeTime": ("效果持续时间（只读）", -2147483648, 2147483647, "特殊结构"),
    "PhysInfoCommonParaNum": ("效果 CommonPara 数量（只读）", 0, 10, "特殊结构"),
    "AccelStatusCount": ("平跑加速档位数量（只读）", 0, 6, "特殊结构"),
    "CompensateParamCount": ("落后补偿数量（只读）", 0, 20, "特殊结构"),
    "CompensatePercent": ("落后补偿百分比", 0, 4294967295, "数组"),
    "ForwardAccelNum": ("前进加速数量（只读）", 0, 30, "特殊结构"),
    "ForwardDecelNum": ("前进减速数量（只读）", 0, 30, "特殊结构"),
    "BackwardAccelNum": ("倒车加速数量（只读）", 0, 30, "特殊结构"),
    "BackwardDecelNum": ("倒车减速数量（只读）", 0, 30, "特殊结构"),
    "HasBoatParam": ("船形态参数启用标记（只读）", 0, 1, "特殊结构"),
    "BoatForwardAccelNum": ("船体前进加速数量（只读）", 0, 30, "特殊结构"),
    "HasSkateParam": ("滑板参数启用标记（只读）", 0, 255, "特殊结构"),
    "SkateTrackSpeed": ("滑板轨道速度", -2147483648, 2147483647, "特殊结构"),
    "SkateSpeedCoefAirBigJet": ("滑板空中大喷速度系数", -2147483648, 2147483647, "特殊结构"),
    "SkateSpeedCoefJump": ("滑板跳跃速度系数", -2147483648, 2147483647, "特殊结构"),
    "SkateSpeedCoefAirJetPoint": ("滑板空中喷点速度系数", -2147483648, 2147483647, "特殊结构"),
    "SkateSpeedCoefMaxForce": ("滑板最大作用力速度系数", -2147483648, 2147483647, "特殊结构"),
    "SkateOntrackAccRef": ("滑板上轨加速度参考", -2147483648, 2147483647, "特殊结构"),
    "SkateTrackAccRef": ("滑板轨道加速度参考", -2147483648, 2147483647, "特殊结构"),
    "SkateDashSkill": ("滑板冲刺技能参数", -2147483648, 2147483647, "特殊结构"),
    "HasBattleModeSkillInfoList": ("对战技能表启用标记（只读）", 0, 255, "特殊结构"),
    "BattleSkillNum": ("对战技能数量（只读）", 0, 10, "特殊结构"),
    "BattleSkillID": ("对战技能 ID", -32768, 32767, "特殊结构"),
    "BattleSkillLevel": ("对战技能等级", 0, 255, "特殊结构"),
    "AddWeightNum": ("附加配重数量（只读）", 0, 9, "特殊结构"),
    "AddWeightTable": ("附加配重表", 0, 255, "特殊结构"),
    "WeightNum": ("配重数量（只读）", 0, 9, "特殊结构"),
    "WeightTable": ("配重表", 0, 255, "特殊结构"),
    "HasAntiCollisionCfg": ("防撞配置启用标记（只读）", 0, 255, "特殊结构"),
    "AntiCollisionNum": ("防撞位置数量（只读）", 0, 12, "特殊结构"),
    "AntiCollisionPosition": ("防撞位置", -2147483648, 2147483647, "特殊结构"),
    "Compensate": ("落后补偿", 0, 16383, "数组"), "ForwardAccelKey": ("前进加速速度点", 0, 4294967295, "数组"),
    "ForwardAccel": ("前进加速值", 0, 16383, "数组"), "ForwardDecelKey": ("前进减速速度点", 0, 4294967295, "数组"),
    "ForwardDecel": ("前进减速值", -2147483648, 2147483647, "数组"), "BackwardAccelKey": ("倒车加速速度点", 0, 4294967295, "数组"),
    "BackwardAccel": ("倒车加速值", -2147483648, 2147483647, "数组"), "BackwardDecelKey": ("倒车减速速度点", 0, 4294967295, "数组"),
    "BackwardDecel": ("倒车减速值", -2147483648, 2147483647, "数组"),
    "BoatSlidFricForce": ("船体滑动摩擦力", -2147483648, 2147483647, "船形态"), "BoatAirValue": ("船体空气值", -2147483648, 2147483647, "船形态"),
    "BoatLRKeyVecForce": ("船体左右键矢量力", -2147483648, 2147483647, "船形态"), "BoatLRKeyVecForceParamA": ("船体左右键矢量参数 A", -2147483648, 2147483647, "船形态"),
    "BoatBannerKeyTwist": ("船体漂移方向扭矩", -2147483648, 2147483647, "船形态"), "BoatBannerKeyTwistParamA": ("船体漂移方向参数 A", -2147483648, 2147483647, "船形态"),
    "BoatBannerKeyTwistParamB": ("船体漂移方向参数 B", -2147483648, 2147483647, "船形态"), "BoatUpKeyVecForce": ("船体抬键矢量力", -2147483648, 2147483647, "船形态"),
    "BoatUpKeyVecForceParamA": ("船体抬键矢量参数 A", -2147483648, 2147483647, "船形态"), "BoatLRKeyVecForceParamB": ("船体左右键矢量参数 B", -2147483648, 2147483647, "船形态"),
    "BoatVecForce": ("船体矢量力", -2147483648, 2147483647, "船形态"), "BoatVecForceParamA": ("船体矢量力参数 A", -2147483648, 2147483647, "船形态"),
    "BoatVecForceParamB": ("船体矢量力参数 B", -2147483648, 2147483647, "船形态"), "BoatHeightRatio": ("船体高度比例", -2147483648, 2147483647, "船形态"),
    "BoatDTFLimitAngle": ("船体 DTF 限制角", -2147483648, 2147483647, "船形态"), "BoatDTFRatio": ("船体 DTF 比例", -2147483648, 2147483647, "船形态"),
    "BoatDirUpKeyForce": ("船体方向键抬起作用力", -2147483648, 2147483647, "船形态"), "BoatDirUpKeyForceParamB": ("船体抬键作用力参数 B", -2147483648, 2147483647, "船形态"),
    "BoatDirKeyForce": ("船体方向键作用力", -2147483648, 2147483647, "船形态"), "BoatDirKeyForceParamA": ("船体方向键作用力参数 A", -2147483648, 2147483647, "船形态"),
    "BoatDirKeyForceParamC": ("船体方向键作用力参数 C", -2147483648, 2147483647, "船形态"), "BoatDirKeyForceParamD": ("船体方向键作用力参数 D", -2147483648, 2147483647, "船形态"),
    "BoatDirKeyForceParamB": ("船体方向键作用力参数 B", -2147483648, 2147483647, "船形态"), "BoatWecEffect": ("船体接触效果", -2147483648, 2147483647, "船形态"),
    "BoatSuaiJianTwist": ("船体断位转向扭矩", -2147483648, 2147483647, "船形态"), "BoatBannerTwist": ("船体漂移转向扭矩", -2147483648, 2147483647, "船形态"),
    "BoatUpKeyVecForceParamB": ("船体抬键矢量参数 B", -2147483648, 2147483647, "船形态"), "BoatAddNO2PerSec": ("船体每秒增加氮气", -2147483648, 2147483647, "船形态"),
    "BoatBannerTwistParamA": ("船体漂移转向参数 A", -2147483648, 2147483647, "船形态"), "BoatDirUpKeyForceParamA": ("船体抬键作用力参数 A", -2147483648, 2147483647, "船形态"),
    "BoatShape": ("船体形状", -2147483648, 2147483647, "船形态"), "BoatForwardAccelKey": ("船体前进加速速度点", -2147483648, 2147483647, "船形态"),
    "BoatForwardAccel": ("船体前进加速值", -2147483648, 2147483647, "船形态"),
}
SECTIONS = ("模式", "动力", "漂移", "物理", "高级漂移", "碰撞", "扩展", "特殊结构", "数组", "船形态")
SUPERJET_LABELS = {4: "普通赛车", 5: "超级喷赛车"}
SUPERJET_VALUES = {label: value for value, label in SUPERJET_LABELS.items()}


class ScrollFrame(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        canvas = tk.Canvas(self, highlightthickness=0)
        bar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        self.body = ttk.Frame(canvas)
        window = canvas.create_window((0, 0), window=self.body, anchor="nw")
        self.body.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(window, width=e.width))
        canvas.configure(yscrollcommand=bar.set)
        canvas.pack(side="left", fill="both", expand=True); bar.pack(side="right", fill="y")


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Top-Kart 551 密文编辑器（DLL 回读校验版）")
        self.geometry("1320x860")
        self.minsize(980, 650)
        self.codec = None
        self.source_dir = find_server_encrypt_dir()
        self.output_dir = Path(sys.executable if getattr(sys, "frozen", False) else __file__).resolve().parent / "551输出"
        self.files = []; self.filtered = []; self.current = None
        self.edit_values = {}; self.record_trees = {}; self.mode_combos = {}; self.compare_tree = None; self.dirty = False
        self._list_load_after = None
        self._list_mouse_down = False
        self._ui()
        if self.source_dir: self.reload_files()
        self.protocol("WM_DELETE_WINDOW", self.close_app)

    def _ui(self):
        top = ttk.Frame(self, padding=6); top.pack(fill="x")
        for text, command in (("打开 EncryptKart", self.choose_dir), ("重新加载", self.reload_current),
                              ("导出并 DLL 校验", self.save), ("导出服务端明文", self.export_plain),
                              ("从快照生成密文（可多选）", self.import_plain), ("增删形态", self.manage_shapes),
                              ("验证当前原文件", self.verify)):
            ttk.Button(top, text=text, command=command).pack(side="left", padx=3)
        self.status = tk.StringVar(value="就绪")
        ttk.Label(top, textvariable=self.status).pack(side="right", padx=8)

        pane = ttk.Panedwindow(self, orient="horizontal"); pane.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        left = ttk.Frame(pane, padding=4); right = ttk.Frame(pane, padding=4); pane.add(left, weight=1); pane.add(right, weight=4)
        self.dir_label = ttk.Label(left, text="未选择服务端目录", wraplength=280); self.dir_label.pack(fill="x", pady=3)
        self.search = tk.StringVar(); self.search.trace_add("write", lambda *_: self.filter_files())
        ttk.Entry(left, textvariable=self.search).pack(fill="x", pady=3)
        list_frame = ttk.Frame(left); list_frame.pack(fill="both", expand=True)
        self.listbox = tk.Listbox(list_frame, exportselection=False, font=("Microsoft YaHei UI", 10))
        list_bar = ttk.Scrollbar(list_frame, orient="vertical", command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=list_bar.set)
        self.listbox.pack(side="left", fill="both", expand=True); list_bar.pack(side="right", fill="y")
        self.listbox.bind("<ButtonPress-1>", self.list_mouse_press, add="+")
        self.listbox.bind("<ButtonRelease-1>", self.list_mouse_release, add="+")
        self.listbox.bind("<<ListboxSelect>>", self.select_file)
        self.count = ttk.Label(left, text="0 个文件"); self.count.pack(fill="x", pady=3)
        self.info = ttk.Label(right, text="请选择一个 551 文件", wraplength=900); self.info.pack(fill="x", pady=5)
        self.tabs = ttk.Notebook(right); self.tabs.pack(fill="both", expand=True)
        ttk.Label(right, text="源文件只读；输出写入 551输出。LoginID/UserID、扩展结构和未知字段逐字节保留。",
                  foreground="#9a5a00").pack(fill="x", pady=5)

    def busy(self, text):
        self.status.set(text); self.configure(cursor="watch"); self.update()

    def idle(self, text="就绪"):
        self.status.set(text); self.configure(cursor=""); self.update()

    def ensure_codec(self):
        if self.codec: return True
        self.busy("首次初始化 Top-Kart.dll，约需 20 秒……")
        try:
            self.codec = Kart551Codec(); return True
        except Exception as exc:
            messagebox.showerror("初始化失败", str(exc)); return False
        finally: self.idle()

    def choose_dir(self):
        folder = filedialog.askdirectory(title="选择服务端 EncryptKart 目录")
        if folder: self.source_dir = Path(folder); self.reload_files()

    def reload_files(self):
        self.files = sorted(self.source_dir.glob("*.yml"), key=lambda p: p.name.lower())
        self.dir_label.configure(text=str(self.source_dir)); self.filter_files()

    def filter_files(self):
        q = self.search.get().strip().lower() if hasattr(self, "search") else ""
        self.filtered = [p for p in self.files if q in p.name.lower()]
        self.listbox.delete(0, "end")
        for path in self.filtered: self.listbox.insert("end", path.name)
        self.count.configure(text=f"{len(self.filtered)} / {len(self.files)} 个文件")

    def list_mouse_press(self, _event=None):
        self._list_mouse_down = True
        if self._list_load_after is not None:
            self.after_cancel(self._list_load_after); self._list_load_after = None

    def list_mouse_release(self, _event=None):
        self._list_mouse_down = False
        self.select_file()

    def select_file(self, _event=None):
        # Listbox 在按住鼠标滑动时会连续改变 selection。等鼠标松开或
        # 键盘选择稳定后再解析，避免把经过的每个文件依次交给 DLL。
        if self._list_mouse_down:
            return
        if self._list_load_after is not None:
            self.after_cancel(self._list_load_after)
        self._list_load_after = self.after(350, self.load_selected_file)

    def load_selected_file(self):
        self._list_load_after = None
        selected = self.listbox.curselection()
        if not selected: return
        if self.dirty and not messagebox.askyesno("尚未导出", "当前修改尚未导出，仍要切换吗？"): return
        self.load(self.filtered[selected[0]])

    def load(self, path):
        if not self.ensure_codec(): return
        self.busy(f"DLL 正在解析 {path.name}……")
        try:
            self.current = self.codec.read(path); self.dirty = False; self.build_tabs()
            ids = ", ".join(str(r.internal_id) for r in self.current.records)
            diff_names = []
            if len(self.current.records) > 1:
                for name in self.current.records[0].values:
                    if any(r.values.get(name) != self.current.records[0].values[name] for r in self.current.records[1:]):
                        diff_names.append(name)
            diff_text = f"　形态差异字段 {len(diff_names)} 个：{', '.join(diff_names)}" if diff_names else ""
            self.info.configure(text=f"{path.name}　{self.current.format_name}　协议记录 {len(self.current.records)}　内部ID {ids}　{len(self.current.raw_bytes)} 字节{diff_text}")
            self.idle("解析成功")
        except Exception as exc:
            messagebox.showerror("解析失败", f"{path}\n\n{exc}"); self.idle("解析失败")

    def shape_number(self, record):
        """三形态沿用游戏映射；二形态按两个协议数组的顺序显示。"""
        if len(self.current.records) == 3:
            return {1: 3, 2: 1, 3: 2}[record.index]
        return record.index

    def build_tabs(self):
        for tab in self.tabs.tabs(): self.tabs.forget(tab)
        self.edit_values = {r.base: copy.deepcopy(r.values) for r in self.current.records}
        self.record_trees = {}
        self.mode_combos = {}
        self.compare_tree = None
        different = set()
        if len(self.current.records) > 1:
            names = set.intersection(*(set(r.values) for r in self.current.records))
            for name in names:
                first = self.current.records[0].values[name]
                if any(r.values[name] != first for r in self.current.records[1:]):
                    different.add(name)

        display_records = sorted(self.current.records, key=self.shape_number)
        if len(display_records) > 1:
            self.build_comparison_tab(display_records)
        for record in display_records:
            shape = self.shape_number(record)
            title = f"第{shape}形态" if len(self.current.records) > 1 else "车辆参数"
            page = ttk.Frame(self.tabs, padding=6)
            self.tabs.add(page, text=title)
            ttk.Label(
                page,
                text=(f"{title} = 协议记录 {record.index}　对象基址 {record.base:#x}　"
                      f"内部赛车 ID {record.internal_id}（只读）"),
                foreground="#1565c0",
            ).pack(fill="x", pady=(0, 6))
            mode_bar = ttk.Frame(page); mode_bar.pack(fill="x", pady=(0, 6))
            ttk.Label(mode_bar, text="赛车喷射模式：").pack(side="left")
            mode_combo = ttk.Combobox(mode_bar, state="readonly", width=16,
                                      values=tuple(SUPERJET_VALUES))
            mode_combo.set(SUPERJET_LABELS.get(self.edit_values[record.base].get("SuperJetType"), "未知模式"))
            mode_combo.pack(side="left")
            ttk.Label(mode_bar, text="（切换后需“导出并 DLL 校验”才会生成新文件）",
                      foreground="#9a5a00").pack(side="left", padx=8)
            tree_frame = ttk.Frame(page); tree_frame.pack(fill="both", expand=True)
            tree = ttk.Treeview(
                tree_frame, columns=("section", "field", "item", "value", "status"),
                show="headings", selectmode="browse",
            )
            headings = (("section", "分类", 90), ("field", "字段", 300),
                        ("item", "数组项", 80), ("value", "数值（双击编辑）", 170),
                        ("status", "形态对比", 130))
            for column, text, width in headings:
                tree.heading(column, text=text); tree.column(column, width=width, anchor="center" if column != "field" else "w")
            bar = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
            tree.configure(yscrollcommand=bar.set)
            tree.pack(side="left", fill="both", expand=True); bar.pack(side="right", fill="y")
            tree.tag_configure("different", background="#fff1bf")
            tree.tag_configure("same", background="#ffffff")
            tree.tag_configure("array", background="#eef6ff")
            tree.tag_configure("readonly", background="#eeeeee", foreground="#666666")
            for section in SECTIONS:
                for name, value in record.values.items():
                    if INFO[name][3] != section: continue
                    label = INFO[name][0]
                    if isinstance(value, list):
                        for index, item in enumerate(value):
                            comparison = self.comparison_values(display_records, name, index)
                            row_diff = len(set(comparison)) > 1
                            readonly = name in STRUCTURE_FIELDS
                            tag = "readonly" if readonly else ("different" if row_diff else "array")
                            status = "结构只读" if readonly else self.comparison_text(comparison)
                            tree.insert("", "end", iid=f"{name}:{index}",
                                        values=(section, f"{label} ({name})", index + 1, item, status), tags=(tag,))
                    else:
                        comparison = self.comparison_values(display_records, name, -1)
                        row_diff = len(set(comparison)) > 1
                        tag = "readonly" if name in STRUCTURE_FIELDS else ("different" if row_diff else "same")
                        status = "结构只读" if name in STRUCTURE_FIELDS else self.comparison_text(comparison)
                        tree.insert("", "end", iid=f"{name}:-1",
                                    values=(section, f"{label} ({name})", "-", value, status), tags=(tag,))
            tree.bind("<Double-1>", lambda event, r=record, t=tree: self.begin_tree_edit(event, r, t))
            self.record_trees[record.base] = tree
            self.mode_combos[record.base] = mode_combo
            mode_combo.bind("<<ComboboxSelected>>",
                            lambda _event, r=record, t=tree, c=mode_combo: self.set_superjet_mode(r, t, c.get()))

    def set_superjet_mode(self, record, tree, label):
        value = SUPERJET_VALUES.get(label)
        if value is None:
            return
        item = "SuperJetType:-1"
        if self.edit_values[record.base].get("SuperJetType") == value:
            return
        self.edit_values[record.base]["SuperJetType"] = value
        if tree.exists(item):
            row = list(tree.item(item, "values")); row[3] = value
            tree.item(item, values=row)
        self.refresh_comparison_row("SuperJetType", -1)
        self.dirty = True

    def comparison_values(self, display_records, name, index):
        result = []
        for record in display_records:
            value = self.edit_values[record.base].get(name)
            if value is None or (index >= 0 and (not isinstance(value, list) or index >= len(value))):
                result.append("—")
            else:
                result.append(value[index] if index >= 0 else value)
        return result

    @staticmethod
    def comparison_text(values):
        if len(values) == 1:
            return "单记录"
        if len(set(values)) == 1:
            return f"相同: {values[0]}"
        return " / ".join(f"形{i + 1}:{value}" for i, value in enumerate(values))

    def build_comparison_tab(self, display_records):
        shape_count = len(display_records)
        page = ttk.Frame(self.tabs, padding=6)
        self.tabs.add(page, text=f"{shape_count}形态对比")
        ttk.Label(page, text=f"{shape_count}形态并排对比（黄色仅表示这一项的数值不同）", foreground="#1565c0").pack(fill="x", pady=(0, 6))
        frame = ttk.Frame(page); frame.pack(fill="both", expand=True)
        shape_columns = tuple(f"shape{i + 1}" for i in range(shape_count))
        tree = ttk.Treeview(frame, columns=("section", "field", "item") + shape_columns + ("result",),
                            show="headings", selectmode="browse")
        definitions = [("section", "分类", 85), ("field", "字段", 290), ("item", "数组项", 70)]
        definitions += [(column, f"第{i + 1}形态", 110) for i, column in enumerate(shape_columns)]
        definitions += [("result", "对比", 90)]
        for column, text, width in definitions:
            tree.heading(column, text=text); tree.column(column, width=width, anchor="center" if column != "field" else "w")
        bar = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=bar.set); tree.pack(side="left", fill="both", expand=True); bar.pack(side="right", fill="y")
        tree.tag_configure("different", background="#ffe59a")
        tree.tag_configure("same", background="#ffffff")
        for section in SECTIONS:
            for name, field_info in INFO.items():
                if field_info[3] != section: continue
                present = [self.edit_values[record.base].get(name) for record in display_records]
                if not any(value is not None for value in present):
                    continue
                value = next(value for value in present if value is not None)
                label = INFO[name][0]
                if isinstance(value, list):
                    indexes = range(max(len(item) for item in present if isinstance(item, list)))
                else:
                    indexes = (-1,)
                for index in indexes:
                    values = self.comparison_values(display_records, name, index)
                    differs = len(set(values)) > 1
                    tree.insert("", "end", iid=f"{name}:{index}",
                                values=(section, f"{label} ({name})", index + 1 if index >= 0 else "-",
                                        *values, "不同" if differs else "相同"),
                                tags=("different" if differs else "same",))
        self.compare_tree = tree

    def refresh_comparison_row(self, name, index):
        if len(self.current.records) < 2:
            return
        item = f"{name}:{index}"
        display_records = sorted(self.current.records, key=self.shape_number)
        values = self.comparison_values(display_records, name, index)
        differs = len(set(values)) > 1
        status = self.comparison_text(values)

        if self.compare_tree is not None and self.compare_tree.exists(item):
            row = list(self.compare_tree.item(item, "values"))
            row[3:3 + len(values)] = values; row[3 + len(values)] = "不同" if differs else "相同"
            self.compare_tree.item(item, values=row, tags=("different" if differs else "same",))

        # 同步刷新三个形态页的对比文字和逐项高亮，避免编辑后其它页仍显示旧状态。
        for record in display_records:
            tree = self.record_trees.get(record.base)
            if tree is None or not tree.exists(item):
                continue
            row = list(tree.item(item, "values")); row[4] = status
            same_tag = "array" if index >= 0 else "same"
            tree.item(item, values=row, tags=("different" if differs else same_tag,))

    def begin_tree_edit(self, event, record, tree):
        if tree.identify_region(event.x, event.y) != "cell" or tree.identify_column(event.x) != "#4":
            return
        item = tree.identify_row(event.y)
        if not item: return
        box = tree.bbox(item, "value")
        if not box: return
        name, index_text = item.rsplit(":", 1); index = int(index_text)
        if name in STRUCTURE_FIELDS:
            return
        if name == "SuperJetType":
            current = self.edit_values[record.base][name]
            combo = self.mode_combos[record.base]
            combo.set(SUPERJET_LABELS[5 if current == 4 else 4])
            self.set_superjet_mode(record, tree, combo.get())
            return
        old = self.edit_values[record.base][name]
        old = old[index] if index >= 0 else old
        edit = ttk.Entry(tree)
        edit.insert(0, str(old)); edit.select_range(0, "end"); edit.focus_set()
        edit.place(x=box[0], y=box[1], width=box[2], height=box[3])
        done = {"value": False}

        def commit(_event=None):
            if done["value"]: return
            done["value"] = True
            try:
                value = int(edit.get())
                low, high = INFO[name][1:3]
                if not low <= value <= high:
                    raise ValueError(f"允许范围 {low}～{high}")
            except ValueError as exc:
                messagebox.showwarning("数值无效", f"{name}: {exc}")
                edit.destroy(); return
            if index >= 0: self.edit_values[record.base][name][index] = value
            else: self.edit_values[record.base][name] = value
            row = list(tree.item(item, "values")); row[3] = value; tree.item(item, values=row)
            self.refresh_comparison_row(name, index)
            self.dirty = True; edit.destroy()

        edit.bind("<Return>", commit); edit.bind("<FocusOut>", commit)
        edit.bind("<Escape>", lambda _e: edit.destroy())

    def values(self):
        return [copy.deepcopy(self.edit_values[record.base]) for record in self.current.records]

    def save(self):
        if not self.current: return
        try: values = self.values()
        except Exception as exc: messagebox.showwarning("字段错误", str(exc)); return
        output = self.output_dir / self.current.path.name; self.busy("编码并调用 DLL 回读校验……")
        try:
            self.current = self.codec.write(self.current, values, output); self.dirty = False; self.build_tabs()
            messagebox.showinfo("成功", f"已导出：\n{output}\n\nDLL 回读校验通过，源文件未修改。")
            self.idle("导出并校验成功")
        except Exception as exc: messagebox.showerror("导出失败", str(exc)); self.idle("导出失败")

    def export_plain(self):
        if not self.current: return
        folder = self.output_dir.parent / "551明文导出"; folder.mkdir(exist_ok=True); output = folder / self.current.path.name
        values = [self.edit_values[record.base] for record in self.current.records]
        output.write_text(format_server_profile(self.current, values), encoding="utf-8")
        messagebox.showinfo("已导出", str(output))

    @staticmethod
    def parse_plain_snapshot(path):
        path = Path(path)
        text = path.read_text(encoding="utf-8-sig")
        if not any(line.strip().startswith("SchemaVersion:") for line in text.splitlines()):
            return parse_server_profile_snapshot(path)

        source_file = None; carrier_file = None; schema = None; records = []; current = None
        for raw in text.splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or line == "Records:":
                continue
            if line.startswith("SchemaVersion:"):
                schema = int(line.split(":", 1)[1].strip()); continue
            if line.startswith("SourceFile:"):
                source_file = Path(line.split(":", 1)[1].strip()).name; continue
            if line.startswith("CarrierFile:"):
                carrier_file = Path(line.split(":", 1)[1].strip()).name; continue
            if line.startswith("- ProtocolRecord:"):
                current = {"ProtocolRecord": int(line.split(":", 1)[1].strip())}
                records.append(current); continue
            if current is None or ":" not in line:
                continue
            name, text = (part.strip() for part in line.split(":", 1))
            name = LEGACY_FIELD_ALIASES.get(name, name)
            if name == "InternalKartID" or name in INFO:
                try: current[name] = ast.literal_eval(text)
                except (ValueError, SyntaxError): raise ValueError(f"快照字段格式错误：{name}")
        if schema != 1 or not source_file or not records:
            raise ValueError("不是本工具导出的 SchemaVersion 1 明文快照")
        return source_file, carrier_file or source_file, records

    def generate_snapshot_file(self, snapshot, carrier_cache, allow_carrier_prompt=False):
        source_name, carrier_name, snapshot_records = self.parse_plain_snapshot(snapshot)
        carrier = self.source_dir / carrier_name if self.source_dir else None
        if carrier is None or not carrier.is_file():
            if not allow_carrier_prompt:
                raise FileNotFoundError(f"找不到载体：{carrier_name}")
            chosen = filedialog.askopenfilename(title=f"选择快照对应的原密文载体（建议 {carrier_name}）",
                                                filetypes=(("551 YAML", "*.yml"),))
            if not chosen:
                raise RuntimeError("用户取消选择密文载体")
            carrier = Path(chosen)
        carrier = carrier.resolve()
        doc = carrier_cache.get(carrier)
        if doc is None:
            doc = self.codec.read(carrier)
            carrier_cache[carrier] = doc
        if len(doc.records) != len(snapshot_records):
            raise ValueError(f"快照有 {len(snapshot_records)} 条记录，载体有 {len(doc.records)} 条记录")
        values = []
        for record, snap in zip(doc.records, snapshot_records):
            edited = copy.deepcopy(record.values)
            if "InternalKartID" in snap:
                edited["InternalKartID"] = int(snap["InternalKartID"])
            for name in INFO:
                if name in snap:
                    edited[name] = copy.deepcopy(snap[name])
            values.append(edited)
        output = self.output_dir / source_name
        self.codec.write(doc, values, output)
        return output, source_name, carrier_name

    def import_plain(self):
        snapshots = filedialog.askopenfilenames(title="选择一个或多个明文快照",
                                                filetypes=(("YAML 快照", "*.yml"), ("所有文件", "*.*")))
        if not snapshots or not self.ensure_codec(): return
        snapshots = [Path(path) for path in snapshots]
        carrier_cache = {}
        successes = []
        failures = []
        targets = {}
        self.busy(f"正在批量生成密文：0 / {len(snapshots)}……")
        try:
            for index, snapshot in enumerate(snapshots, 1):
                self.status.set(f"正在批量生成密文：{index} / {len(snapshots)}　{snapshot.name}")
                self.update_idletasks()
                try:
                    source_name, _carrier_name, _records = self.parse_plain_snapshot(snapshot)
                    key = source_name.lower()
                    if key in targets:
                        raise ValueError(f"输出目标与 {targets[key]} 重复：{source_name}")
                    targets[key] = snapshot.name
                    output, source_name, carrier_name = self.generate_snapshot_file(
                        snapshot, carrier_cache, allow_carrier_prompt=len(snapshots) == 1
                    )
                    successes.append((snapshot.name, source_name, carrier_name, output))
                except Exception as exc:
                    failures.append((snapshot.name, str(exc)))
            if len(snapshots) == 1 and successes:
                output = successes[0][3]
                self.load(output)
                messagebox.showinfo("生成成功", f"已根据明文快照生成：\n{output}\n\nDLL 回读校验通过。")
                return
            report = self.output_dir / "批量生成报告.txt"
            lines = [f"快照总数：{len(snapshots)}", f"成功：{len(successes)}", f"失败：{len(failures)}", "", "成功项目："]
            lines += [f"{snap}\t=> {target}\t载体 {carrier}" for snap, target, carrier, _output in successes]
            lines += ["", "失败项目："] + [f"{snap}\t{reason}" for snap, reason in failures]
            report.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")
            summary = f"批量处理完成：成功 {len(successes)}，失败 {len(failures)}。\n\n报告：\n{report}"
            if failures:
                summary += "\n\n前几项错误：\n" + "\n".join(f"{name}: {reason}" for name, reason in failures[:5])
                messagebox.showwarning("批量生成完成", summary)
            else:
                messagebox.showinfo("批量生成完成", summary)
            self.idle(f"批量生成完成：成功 {len(successes)}，失败 {len(failures)}")
        except Exception as exc:
            messagebox.showerror("批量生成失败", str(exc)); self.idle("批量生成失败")

    def shape_template(self, target_count):
        required_count = 3 if target_count in (2, 3) else 1
        app_dir = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
        name = "三形态模板.yml" if required_count == 3 else "单形态模板.yml"
        internal = app_dir / "协议模板" / name
        if internal.is_file():
            if len(self.codec.read(internal).records) != required_count:
                raise ValueError(f"内置协议模板记录数不正确：{internal}")
            return internal
        chosen = filedialog.askopenfilename(title=f"选择一个 {required_count} 记录的551协议骨架",
                                            filetypes=(("551 YAML", "*.yml"),))
        if not chosen: return None
        path = Path(chosen)
        if len(self.codec.read(path).records) != required_count:
            raise ValueError(f"所选文件不是 {required_count} 记录协议骨架")
        return path

    def manage_shapes(self):
        if not self.current or not self.ensure_codec(): return
        current_count = len(self.current.records)
        target_count = simpledialog.askinteger("设置形态数量", "生成几个形态？（1～3）", minvalue=1, maxvalue=3,
                                               initialvalue=current_count)
        if target_count is None: return
        if target_count == current_count:
            messagebox.showinfo("无需转换", f"当前已经是 {current_count} 形态"); return
        display_records = sorted(self.current.records, key=self.shape_number)
        live_records = []
        for record in display_records:
            live = copy.deepcopy(record)
            live.values = copy.deepcopy(self.edit_values[record.base])
            live_records.append(live)
        template = None
        if current_count == 3 and target_count == 2:
            # 正式二形态组合：[0,1,1]。直接使用当前三形态文件为骨架，
            # 删除编辑器第3形态并原样保留第1、第2形态的未知结构。
            source_records = live_records[:2]
            template = self.current.path
            prompt = "删除编辑器第3形态，保留第1、第2形态并生成正式二形态？"
        elif target_count == 1 and current_count > 1:
            shape = simpledialog.askinteger("选择源形态", f"以第几个形态的字段为模板？（1～{current_count}）",
                                            minvalue=1, maxvalue=current_count, initialvalue=1)
            if shape is None: return
            source_records = [live_records[shape - 1]]
            prompt = f"仅保留第 {shape} 形态并转换为单形态？"
        elif current_count == 2 and target_count == 3:
            shape = simpledialog.askinteger("新增第3形态", "新第3形态复制第几个现有形态？（1～2）",
                                            minvalue=1, maxvalue=2, initialvalue=2)
            if shape is None: return
            # 三形态协议物理顺序为 [第3, 第1, 第2]。
            source_records = [live_records[shape - 1], live_records[0], live_records[1]]
            prompt = f"保留现有第1、第2形态，并复制第 {shape} 形态作为新第3形态？"
        else:
            source_records = [live_records[0]] * target_count
            prompt = f"把当前形态复制并重建为 {target_count} 形态？"
        if not messagebox.askyesno("确认形态转换",
                                   f"{prompt}\n\n"
                                   "未开放结构来自协议骨架；输出会经过 DLL 校验，源文件不会修改。"):
            return
        try:
            if template is None:
                template = self.shape_template(target_count)
            if template is None: return
            output = self.output_dir / self.current.path.name
            self.busy("正在重建形态结构并调用 DLL 校验……")
            self.codec.reshape(self.current, template, source_records, target_count, output)
            self.load(output)
            messagebox.showinfo("形态转换成功", f"已生成：\n{output}\n\n当前为 {target_count} 记录结构，DLL 回读校验通过。")
        except Exception as exc:
            messagebox.showerror("形态转换失败", str(exc)); self.idle("形态转换失败")

    def verify(self):
        if not self.current: return
        self.busy("DLL 正在重新验证原文件……")
        try:
            doc = self.codec.read(self.current.path); messagebox.showinfo("验证通过", f"成功解析 {len(doc.records)} 条协议记录。")
            self.idle("验证通过")
        except Exception as exc: messagebox.showerror("验证失败", str(exc)); self.idle("验证失败")

    def reload_current(self):
        if self.current: self.load(self.current.path)

    def close_app(self):
        if self.dirty and not messagebox.askyesno("尚未导出", "修改尚未导出，确定退出吗？"): return
        self.destroy()


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "--self-test":
        tested = Kart551Codec().read(Path(sys.argv[2]))
        if not tested.records:
            raise SystemExit(2)
        raise SystemExit(0)
    App().mainloop()
