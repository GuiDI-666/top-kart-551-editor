# Top-Kart 551 赛车属性编辑器

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey.svg)](#环境要求)
[![CI](https://github.com/GuiDI-666/top-kart-551-editor/actions/workflows/ci.yml/badge.svg)](https://github.com/GuiDI-666/top-kart-551-editor/actions/workflows/ci.yml)

一个基于**原版 DLL 语义**的 551 协议赛车参数编辑器。

不逆向猜偏移、不重写加密算法、不破坏未知字段——所有读写都以原厂解析函数为准，导出后强制回读校验。

---

## 目录

- [简介](#简介)
- [核心特性](#核心特性)
- [工作原理](#工作原理)
- [环境要求](#环境要求)
- [安装](#安装)
- [快速开始](#快速开始)
- [项目结构](#项目结构)
- [命令行工具](#命令行工具)
- [字段支持范围](#字段支持范围)
- [已知限制](#已知限制)
- [常见问题](#常见问题)
- [参与贡献](#参与贡献)
- [许可证](#许可证)
- [免责声明](#免责声明)

## 简介

`551` 是《QQ飞车》赛车物理参数的二进制协议格式。每条记录编码了转向、加速、漂移、
氮气、碰撞、形态等数百个整数与整数数组，其中大部分字段使用**逐字段字节置换 + VarInt**
混合编码。

本项目的做法与常见的"硬编码结构体偏移"工具不同：

- **读取**：把原版 `Top-Kart.dll` 映射进 Unicorn 模拟器，直接调用 DLL 内部的安全协议
  解析函数 `CSSafeCNotifyKartPhysParamPara` / `CSSafeSTKartPhysParam`，得到与游戏客户端
  完全一致的解释结果。
- **写入**：只替换已确认字段对应的编码字节，逐字节保留未映射数据。
- **校验**：每次导出后重新用同一个 DLL 解析输出，逐字段比对；不一致就报错而不是静默写坏文件。

因为解析逻辑直接来自原厂二进制，所以不需要为每个新字段手工推导偏移，也不会因为
协议小版本变动而整体错位。

项目包含两个工具：

| 工具 | 用途 | 依赖 |
| --- | --- | --- |
| **密文编辑器**（`551密文编辑器_tk.py`） | 完整功能：读密文、改字段、增删形态、导出并校验 | 需要 `Top-Kart.dll` |
| **明文快照编辑器**（`551明文快照编辑器_tk.py`） | 协作调参：只编辑 `.yml` 明文快照，不接触加密 | 纯 Python，可分发给他人 |

## 核心特性

- **原厂语义解析**：Unicorn + PE 映射直接执行 DLL 代码，解释结果与客户端一致。
- **动态恢复字节置换表**：运行时逐字节重放解析路径，自动构造 256 项编码→解码映射，
  无需静态分析置换算法。
- **保留式改写**：LoginID、UserID、未知字段、扩展结构逐字节原样保留。
- **强制回读校验**：导出后由 DLL 二次解析，结构或字段任一不符即判定失败。
- **多形态支持**：单记录 / 二形态 / 三形态互转，使用同版本合法协议骨架，经客户端实测的
  `[0,1,1]` 组合作为正式二形态方案。
- **明文快照协作流**：主编辑器导出 `.yml` 快照 → 他人用免依赖的快照编辑器改值 →
  回传后由主编辑器合并生成密文。
- **批量生成**：一次选择多份快照，逐份执行 DLL 回读，失败不中断其余文件。

## 工作原理

### 1. PE 映射与模拟执行

`pefile` 读取 `Top-Kart.dll` 的节表，按 `ImageBase = 0x180000000` 把各节写入 Unicorn
的虚拟内存，再单独映射栈、对象区、数据区、参数区和哨兵页。调用时把返回地址压成
`SENTINEL`（`0x340000000`，内容为 `nop; nop; ret`），函数返回即触发 `emu_stop`。

```text
0x180000000  IMAGE_BASE   DLL 映像
0x300000000  STACK_BASE   调用栈
0x310000000  OBJECT_BASE  物理参数对象（0x300000，约 2.1 MB 有效）
0x320000000  DATA_BASE    551 密文数据
0x330000000  ARG_BASE     调用参数
0x340000000  SENTINEL     返回哨兵
```

### 2. 动态恢复字节置换表

551 协议里每个受保护字段都经过一次单字节双射替换。直接静态还原这张表成本很高，
本项目的做法是**让 DLL 自己告诉我们**：

1. 打开 hook，捕获 1 字节的输入读取与随后的对象写入；
2. 记录该写入指令 `rip` 处的完整上下文（寄存器、栈页快照）；
3. 对该输入位置逐一重放 `0x00`–`0xFF`，恢复到同一 `rip` 时读取目标寄存器；
4. 256 次探测的结果就是这张置换表的**反查表**，写入时直接查表编码。

对少数直接 `mov [mem], reg` 的单字节字段（如 `SuperJetType`），代码会识别这种模式
并改用直接取寄存器的方式，不依赖后续的 `test` 指令。

### 3. 保留式改写与回读校验

改写只发生在已确认字段的字节区间上，VarInt 长度变化会就地伸缩，未映射区域保持原样。
导出后重新解析输出文件，逐字段比对；任何差异都会阻止写入磁盘。

## 环境要求

- **操作系统**：Windows（需要读取原版 PE 文件；DLL 依赖 Windows 调用约定）
- **Python**：3.10 及以上
- **依赖**：`pefile`、`capstone`、`unicorn`
- **游戏文件**：需要自备与目标协议版本一致的 `Top-Kart.dll`

> 仓库**不包含**任何游戏原始文件、协议模板或运营数据。这些文件版权归原厂所有，
> 请自行从你合法持有的客户端中获取。

## 安装

```bash
git clone https://github.com/GuiDI-666/top-kart-551-editor.git
cd top-kart-551-editor
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

把 `Top-Kart.dll` 放到项目根目录，或设置环境变量指向它：

```powershell
$env:TOP_KART_DLL = "C:\path\to\Top-Kart.dll"
```

## 快速开始

### 密文编辑器

```bash
python 551密文编辑器_tk.py
```

1. 启动后工具会尝试自动定位 `EncryptKart` 目录，也可手动选择；
2. 左侧选文件，中间按页签显示单记录或三个形态；
3. 双击"数值"列编辑，改动会实时反映到形态对比页；
4. 点"导出并 DLL 校验"，结果写入程序目录下的 `551输出/`，源文件不会被覆盖。

### 明文快照编辑器

```bash
python 551明文快照编辑器_tk.py
```

打开快照目录或单个 `.yml`，改完点"另存贡献稿"，会在 EXE 旁生成 `.yml` 与同名
`.changes.txt` 修改清单，把两者一起回传给管理者即可。

详细说明见 [`docs/editor.md`](docs/editor.md) 与 [`docs/snapshot-editor.md`](docs/snapshot-editor.md)。

## 项目结构

```text
top-kart-551-editor/
├── 551密文编辑器_tk.py            # 主编辑器 GUI（发布版）
├── 551明文快照编辑器_tk.py        # 协作版快照编辑器 GUI（免依赖）
├── kart551_backend.py             # 核心：读取、字段提取、保留式改写、回读校验
├── emulate_551.py                 # 核心：PE 映射、Unicorn 调用、置换表动态恢复
├── validate_551_corpus.py         # 批量语料解析验证
├── map_551_from_plain.py          # 明文配置与密文字段的相关性比对
├── analyze_551_field_xrefs.py     # 静态交叉引用分析
├── analyze_network_phys_debug.py  # Network.dll 调试输出 schema 分析
├── Top-Kart-551-Editor.spec       # PyInstaller 打包配置（主编辑器）
├── Top-Kart-551-Snapshot-Editor.spec
├── docs/
│   ├── editor.md                  # 主编辑器使用说明
│   └── snapshot-editor.md         # 快照编辑器使用说明
├── requirements.txt
├── CHANGELOG.md
├── CONTRIBUTING.md
├── SECURITY.md
└── LICENSE
```

## 命令行工具

```bash
# 校验一批 EncryptKart 是否能全部解析
python validate_551_corpus.py <EncryptKart目录>

# 查看某个样本的解码轨迹（需要 Top-Kart.dll）
python emulate_551.py samples/100047.yml out

# 明文与密文字段相关性分析（需要明文 Kart 目录）
python map_551_from_plain.py 250

# 分析 Network.dll 的物理调试 schema
python analyze_network_phys_debug.py Network.dll
```

> `validate_551_corpus.py` 与 `map_551_from_plain.py` 支持用环境变量
> `TOP_KART_DLL`、`PLAIN_KART_DIR` 指定路径。

## 字段支持范围

已开放并可写回的字段类别：

- **基础物理**：转向速率、最大/最小转弯速度、聚气时间、加速度、重力、附加纵向速度
- **输入曲线**：前进/后退加速与减速的 Key/Value 曲线
- **漂移与喷射**：方向键力/扭力、横幅力/扭力、头部力、滑行摩擦、翻滚摩擦、超级氮气率
- **碰撞**：碰撞盒长宽高、四项调整参数、控制器偏移、车车碰撞半径/长/宽/高、失控时间
- **扩展性能**：碰撞补偿、防御率、加速卡生成率、能量转换、碰撞损失率、漂移不中断
- **特殊结构**：滑板参数（8 项）、对战技能（最多 10 项）、附加配重与配重（各最多 9 项）、
  防撞位置（最多 12 项）
- **形态**：1 / 2 / 3 形态互转，含超级喷标志与第 5 个喷射配置块的增删

完整字段清单与验证结论见 [`docs/editor.md`](docs/editor.md)。

## 已知限制

- `NitroRetention` 未开放：现有样本中没有非零值，无法证明其对应的安全成员，工具不猜偏移。
- 明文快照只包含已确认字段，**不是** 551 对象的无损文本序列化；重新生成密文时仍需
  对应的原密文作为载体，以保留未知字段。
- 形态转换依赖同版本的合法协议骨架文件；形态数量变化时，未开放结构来自所选骨架。
- 滑板、对战技能、附加配重等结构仅在原文件已编码的元素上编辑，不能凭计数凭空创建。
- 仅在 Windows + Python 3.10 环境验证，其他版本未测试。

## 常见问题

**Q：为什么必须提供 `Top-Kart.dll`？**
A：解析逻辑就是 DLL 里的原厂函数。没有它，工具无法保证解释结果与客户端一致，
也无法做导出回读校验。这是本项目的设计前提，不是可选项。

**Q：能打包成给不装 Python 的人用吗？**
A：可以，用仓库里的 `.spec` 执行 `pyinstaller Top-Kart-551-Editor.spec`。
快照编辑器是纯 Python 实现，打包后不需要 DLL，适合分发给协作调参的人。

**Q：为什么二形态用 `[0,1,1]` 而不是 `[1,1,0]`？**
A：三个形态槽由三个独立的安全数组计数控制。`[0,1,1]` 是经客户端变形测试确认的
正式组合，旧的 `[1,1,0]` 方案已不再生成。

**Q：导出失败了怎么办？**
A：先看报错里的字段名与偏移。失败意味着 DLL 回读结果与编辑值不一致，此时**不要**
继续沿用输出文件。多数情况是载体文件与目标样本不匹配（`CarrierFile` 指错）。

## 参与贡献

欢迎提交 Issue 和 Pull Request。请先阅读 [`CONTRIBUTING.md`](CONTRIBUTING.md)。

提交前请确认：

- 不包含任何游戏原始文件、协议模板或运营数据；
- 不包含服务器地址、账号、密钥等敏感信息；
- 新增字段必须附带验证依据（DLL 函数、样本对比或客户端实测），不接受"猜偏移"。

## 许可证

本项目采用 [MIT License](LICENSE) 开源。

## 免责声明

- 本项目为**技术研究与学习**用途，与腾讯公司及《QQ飞车》官方无任何关联，非官方工具。
- 仓库仅包含自行编写的源代码，**不包含**任何游戏客户端/服务端文件、美术资源、
  协议模板或运营数据。使用者需自行合法获取相关文件。
- 请勿将本工具用于任何违反游戏用户协议、法律法规或损害他人权益的场景。
- 使用本工具产生的一切后果由使用者自行承担，作者不承担任何责任。

---

如果这个项目帮你理解了二进制协议解析或模拟执行，欢迎点个 Star。
