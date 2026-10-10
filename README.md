# Research Figure Studio (RFS)

**科研论文图件调度 Skill（Agent Skills）**。复杂方法图用生成式设计，实验图以真实数据与可复现代码绘制；有可编辑需求时，结合**生成图片、可信 FigureSpec、观察图片后的详细文字说明**，交给实际 PPTX/draw.io 后端重建。

## 统一协议与角色

从 v0.4.0 起，**RFS 与 [douxl-lab/PaperBanana](https://github.com/douxl-lab/PaperBanana) 使用相同的 FigureSpec Exchange v1 (`schema_version: "1.0.0"`)**。科学模块、标签、公式、连线、来源、数据及锁定约束由同一协议验证。RFS 是调度与验收方，PaperBanana 保留 Retriever → Planner → Stylist → Visualizer → Critic 多智能体设计引擎；不重复设计/评审循环。

| 路线 | 默认执行 | 实际产物 |
|---|---|---|
| **A · 生成式优先** | 可用时调用 PaperBanana；否则先产出专业 Prompt | 候选图、实际 Prompt、设计说明、完整科学规格及哈希；无模型授权时只是 Prompt |
| **C · 数据优先** | Matplotlib 使用 FigureSpec 中的真实原始数据 | SVG、PDF、PNG + 原始完整数据/科学规格 + 哈希清单 |
| **可编辑重建** | 经审核的候选图 + 原始 FigureSpec + 观察图片后的文字指导 | 严格验收的重建任务包；真正的 PPTX/draw.io 需要另装可编辑后端 |
| **B · 直接原生** | 仅明确指定的简单结构图 | 旧版精确 SVG，不作为复杂方法图的美学默认解 |

## 安装

```bash
git clone https://github.com/douxl-lab/research-figure-skill.git
# Codex 用户：将 research-figure/ 加入自己的 Skills 搜索路径。
python research-figure/scripts/check_skill.py
python research-figure/scripts/rfs.py doctor
```

本机基础调度不需要 API 密钥；canonical FigureSpec v1 和候选包检查需：

```bash
python -m pip install -r research-figure/requirements-exchange.txt
```

真实统计绘图还需：

```bash
python -m pip install -r research-figure/requirements-plot.txt
```

使用 PaperBanana 时，**另行克隆/安装引擎**、配置环境密钥（绝不写入 Git），并将 `PAPERBANANA_ROOT` 指向其仓库。可另设置 `PAPERBANANA_PYTHON` 指向其 Python 环境。RFS 调用前核对双方的协议版本与 Schema/Validator 指纹，不匹配直接拒绝执行，不猜测转换、不重写科学事实。

## Canonical FigureSpec v1：开始使用

```bash
# 例子：完整的 v1 方法图和 v1 原始数据图（都是合成演示，不是论文结果）
FIG=research-figure/assets/figure-spec-v1-example.json
PLOT=research-figure/assets/figure-plot-v1-example.json

python research-figure/scripts/rfs.py validate --spec "$FIG"
python research-figure/scripts/rfs.py route --spec "$FIG"

# 方案 A：不使用付费模型时，先生成专业 Prompt、FigureSpec 和设计意图。
python research-figure/scripts/rfs.py run --spec "$FIG" --out /tmp/rfs-v1-prompt

# PaperBanana 安装且用户授权给模型发送当前科学材料和可能产生费用后：
python research-figure/scripts/rfs.py run --spec "$FIG" \
  --engine paperbanana --allow-external --candidates 2 --out /tmp/rfs-v1-generation

# 方案 C：仅使用原始完整数据，不靠生成式模型猜数值。
python research-figure/scripts/rfs.py run --spec "$PLOT" --out /tmp/rfs-v1-plot

# 检查候选包完整性并保持科学验证状态 PENDING：
python research-figure/scripts/rfs.py audit --spec "$FIG" \
  --artifact /tmp/rfs-v1-generation/request/generated/bundles/ACTUAL_CANDIDATE

# 科学规格 + 实际候选包 + 针对该图片写的文字说明，构成重建交接：
python research-figure/scripts/rfs.py reconstruction-package --spec "$FIG" \
  --bundle /tmp/rfs-v1-generation/request/generated/bundles/ACTUAL_CANDIDATE \
  --design-notes /path/to/observed-design-notes.md \
  --backend paper-fig --approved --out /tmp/rfs-v1-reconstruction
```

`ACTUAL_CANDIDATE` 必须替换成实际输出目录名。只有完整检查结果才能进入重建，图片美观不代表结构可靠；用户批准视觉构图也不意味着科学事实已经验证。`--allow-external` 不应在没有授权时使用。

## 兼容老项目

v0.3.x `schema_version: "0.1.0"` 的 `type`/`diagram` 结构保留为**旧式兼容输入**；旧版例子与测试不被静默转换成新科学事实。**新项目应直接生成 FigureSpec v1**。两种结构不会在同一任务里混用。混合图需拆分方法示意部分和数据部分。

## 源文件与安全

仓库根目录 `README.md` 为公开安装说明；`research-figure/SKILL.md` 是自动发现入口；`research-figure/references/` 属于必需的公开运行规则。用户论文、API Key、IDE/Agent 本地配置、运行输出、评审草稿与内部文档不纳入版本控制。`.gitignore` 与 CI 中的 `check_repository.py` 双重检查，但对已泄露历史记录不能代替密钥轮换。发布用例均为明确标记的 synthetic fixtures。

**验证边界：** 离线协议、完整性检查与合成测试不等于真实模型出图效果、科学正确性或 PPTX 原生重建成功。相关项未验证时报告 PENDING，不能宣称完成。

## 许可与上游声明

自主调度代码采用 [MIT](LICENSE)。迁入 `research-figure/protocol/` 的 PaperBanana FigureSpec v1 校验/编译与互操作代码按其原有 **Apache-2.0** 许可保留版权，详见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) 和随附许可。Sivia 与 paper-fig 仅为可选外部后端，不再分发其受限内容。