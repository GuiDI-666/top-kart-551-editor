# 贡献指南

感谢你愿意改进这个项目。这份文档说明参与方式与硬性红线。

## 行为准则

参与本项目即表示同意遵守 [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)。

## 可以贡献什么

- **Bug 修复**：解析失败、字段错位、导出校验不通过
- **新字段支持**：前提是能提供验证依据
- **文档改进**：错别字、表述不清、缺失的使用说明
- **工具链**：测试、CI、打包脚本、代码质量

## 硬性红线

以下内容**一律不接受**，PR 会被直接关闭：

1. **任何游戏原始文件**——`Top-Kart.dll`、`Network.dll`、`.bin`、协议模板、
   `EncryptKart` 数据、明文配置。版权不属于本项目。
2. **任何运营数据**——服务器地址、账号、密钥、玩家数据、日志。
3. **猜出来的字段偏移**——没有 DLL 函数、样本对比或客户端实测支撑的字段，
   即使"看起来对"也不合并。这个项目的价值就在于不猜。
4. **破坏保留式改写的改动**——任何会丢失未知字段、覆盖原始字节的实现。
5. **移除回读校验的改动**——校验是这个工具能安全使用的前提。

## 开发环境

```bash
git clone https://github.com/GuiDI-666/top-kart-551-editor.git
cd top-kart-551-editor
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
```

环境变量：

| 变量 | 用途 |
| --- | --- |
| `TOP_KART_DLL` | 指定 `Top-Kart.dll` 路径 |
| `NETWORK_DLL` | 指定 `Network.dll` 路径（仅分析脚本用） |
| `PLAIN_KART_DIR` | 指定明文 `Kart` 配置目录（仅比对脚本用） |

## 提交前自检

```bash
# 语法检查
python -m compileall -q .

# 代码规范
ruff check .

# 确认没有把私有路径带进来
grep -rnE "[A-Za-z]:[\\/]" --include=*.py --include=*.spec .
```

最后一条必须无输出。任何形如 `D:\...`、`C:\Users\...` 的绝对路径都不能提交。

## 新增字段的流程

1. **找依据**：在 DLL 里定位该字段的转换函数或安全成员，或找到可对比的样本；
2. **写映射**：在 `kart551_backend.py` 的对应字段表中登记偏移与类型；
3. **说明验证**：在 PR 描述里写清楚依据来源（函数地址、反汇编片段、样本对比结果）；
4. **补限制**：若只能读不能安全写，请加入 `UNVERIFIED_FIELDS` 并在文档说明。

不要为了让功能"看起来完整"而开放未验证的字段。

## 提交信息规范

采用 [Conventional Commits](https://www.conventionalcommits.org/zh-hans/)：

```text
<type>(<scope>): <subject>

type:  feat | fix | docs | refactor | test | chore | perf
scope: backend | gui | emulator | docs | ci（可省略）
```

示例：

```text
feat(backend): 开放 SuspensionCompress 字段写回
fix(emulator): 修正 VarInt 跨页读取时的栈快照缺失
docs: 补充二形态 [0,1,1] 的验证过程
```

## Pull Request 流程

1. Fork 仓库并从 `main` 切出分支：`feat/xxx` 或 `fix/xxx`；
2. 提交改动，确保 `ruff check .` 与 `compileall` 通过；
3. 按模板填写 PR 描述，说明动机、改动点、验证方式；
4. 等待 review。涉及字段映射的改动需要提供可复现的验证依据。

## 版本与发布

- 版本号遵循语义化版本：破坏兼容的协议变动 → major，新功能 → minor，修复 → patch；
- 每次发布更新 `CHANGELOG.md` 与 `VERSION`，并打 annotated tag；
- 不重写已发布的 tag，不回退历史。

## 许可证

你的贡献将以 [MIT License](LICENSE) 发布。提交 PR 即表示同意此条款。
