# Changelog

本项目的所有重要变更都记录在此文件。

格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### 计划中

- 补充 `NitroRetention` 字段（需先确认安全成员偏移）
- 增加离线字段映射表缓存，减少重复探测耗时
- 补充单元测试与样本脱敏测试夹具

## [1.0.1] - 2026-11-05

### 修复

- 移除 `kart551_backend.py` 中未使用的 `re` 导入
- Ruff 配置：为 `emulate_551.py` 关闭 `F403` / `F405`。unicorn 的寄存器常量有数百个，
  保留官方推荐的 `from unicorn.x86_const import *` 写法，修复 CI lint 任务失败

## [1.0.0] - 2026-11-05

首次开源发布。

### 新增

- 密文编辑器 GUI：读取 551 密文、按形态展示与编辑字段、导出并 DLL 回读校验
- 明文快照编辑器 GUI：免依赖的协作调参工具，输出 `.yml` 与 `.changes.txt`
- `kart551_backend.py`：保留式读写后端，含标量/曲线/碰撞/特殊结构字段映射
- `emulate_551.py`：基于 Unicorn 的 PE 映射与 DLL 函数调用封装
- 字节置换表动态恢复：256 次重放探测自动构造编码映射，含 `mov [mem], reg` 特例识别
- 多形态支持：1 / 2 / 3 形态互转，采用经客户端验证的 `[0,1,1]` 二形态组合
- 超级喷支持：第 5 个喷射配置块的插入与移除
- 批量生成：多快照一次生成，逐份回读校验，失败不中断
- 命令行工具：`validate_551_corpus.py`、`map_551_from_plain.py`、
  `analyze_551_field_xrefs.py`、`analyze_network_phys_debug.py`
- PyInstaller 打包配置（两个 `.spec`）

### 变更

- 开源整理：移除开发机硬编码路径，改为环境变量与命令行参数
- `.spec` 中的依赖路径改为运行时探测，不再写死 `site-packages` 位置

### 验证

- 707 份真实 `EncryptKart` 样本全部解析成功，共 718 条性能记录
- 覆盖 701 份单记录、1 份二记录、5 份三记录文件
- 已验证 32 位负数、VarInt 长度增减、单记录与三记录改写
- 249 条非空配重记录、135 条非空防撞记录读写通过

[Unreleased]: https://github.com/GuiDI-666/top-kart-551-editor/compare/v1.0.1...HEAD
[1.0.1]: https://github.com/GuiDI-666/top-kart-551-editor/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/GuiDI-666/top-kart-551-editor/releases/tag/v1.0.0
