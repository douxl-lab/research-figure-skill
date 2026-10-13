# Research Figure Studio (RFS)

**科研论文图件调度 Skill（Agent Skills）**。复杂方法图用生成式设计，实验图以真实数据与可复现代码绘制；有可编辑需求时，结合**生成图片、可信 FigureSpec、观察图片后的详细文字说明**，交给实际 PPTX/draw.io 后端重建。

## 科研图默认排版规范

新增 [真实论文与期刊规范调研的机制图风格](research-figure/references/journal-mechanism-style.md)：独立图默认**不在图内加大标题、阶段 1–6 或 A/B/C 标签**；总架构、Router 内部机制、Evidential Fusion 内部机制应在有足够内容时分别成为三张可独立引用的图。避免海报化信息卡片和无效空白，让每个科学术语、算子、公式及连线都有来源。期刊明确要求组合子图时仍遵守其 panel 标记规则。该风格是默认偏好，不会覆盖具体论文的科学证据或投稿要求。

## 统一协议与角色

从 v0.4.0 起，**RFS 与 [douxl-lab/PaperBanana](https://github.com/douxl-lab/PaperBanana) 使用相同的 FigureSpec Exchange v1 (`schema_version: "1.0.0"`)**。科学模块、标签、公式、连线、来源、数据及锁定约束由同一协议验证。RFS 是调度与验收方，PaperBanana 保留 Retriever → Planner → Stylist → Visualizer → Critic 多智能体设计引擎；不重复设计/评审循环。

| 路线 | 默认执行 | 实际产物 |
|---|---|---|
| **A · 生成式优先** | 可用时调用 PaperBanana；否则先产出专业 Prompt | 候选图、实际 Prompt、设计说明、完整科学规格及哈希；无模型授权时只是 Prompt |
| **T · 精密矢量（显式选择）** | FigureSpec v1 + 安全转义 + TikZ/XeLaTeX/Poppler，本地绘制公式、时序和结构图 | 可复现的 .tex、PDF、SVG、PNG、完整 FigureSpec 和 SHA-256 验收记录 |
| **C · 数据优先** | Matplotlib 使用 FigureSpec 中的真实原始数据 | SVG、PDF、PNG + 原始完整数据/科学规格 + `plot-reproduce.py` + 哈希清单 |
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

## TikZ 本地矢量后端（新增，显式选用）

默认的生成式方法图仍优先使用 PaperBanana；需要精确数学公式、流程/时序布局和可复现代码的**纯示意图**时，才选 `--engine tikz`。新路线与 PaperBanana 共享 FigureSpec v1 的科学数据与指纹，不更改 schema、validator 或双方互通协议，也不会在未授权时调用任何外部 API。

先安装 XeLaTeX（含 TikZ/standalone/fontspec/amsmath）与 Poppler 的 `pdftocairo`。中文最好提供 Noto Sans CJK SC；编译环境缺失时明确报错而不是伪造矢量文件。

```bash
FIG=research-figure/assets/figure-spec-v1-example.json
python research-figure/scripts/rfs.py route --spec "$FIG" --engine tikz
python research-figure/scripts/rfs.py run --spec "$FIG" --engine tikz --out /tmp/rfs-encoder-tikz
python research-figure/scripts/rfs.py audit --spec "$FIG" --artifact /tmp/rfs-encoder-tikz
```

交付文件包含 `figure.tex`、`figure.pdf`、`figure.svg`、`figure.png`、`figure-spec.json`、`manifest.json`。数学公式只接受安全白名单命令，所有自由文本自动 TeX 转义，默认禁止 shell escape；这仍不是对恶意 TeX 的完整沙箱，陌生输入应在受限容器中执行。有限的自动布局不保证复杂图避免所有交叉，必须实际渲染并检查。

**PaperBanana 适配：** 已选中的候选图可由 PaperBanana 的 `skill/exchange.py vector-handoff` 导出经过哈希验证的图片、设计说明和同源 FigureSpec，供 TikZ 独立重绘时作视觉参考；不得宣称位图与 TikZ 输出一一像素一致。详见 [TikZ 工作流](research-figure/references/tikz-workflow.md)。

## 原生可编辑 PPTX / draw.io 验收

新版 `native-audit` 用于**检查已经由真实后端生成并保存的原生文件**，不会把一张 PNG 伪装成 PPTX，也不会自动重绘批准的复杂构图。它核对可编辑文字、对象数量、连接线以及可选的稳定对象 ID。推荐在原生对象命名时使用 `rfs-node:<FigureSpec ID>` 和 `rfs-edge:<FigureSpec ID>`，并保留连接线的实际起终点和箭头。

```bash
python research-figure/scripts/rfs.py native-audit \
  --spec /project/figure-spec.json --native-file /project/rebuilt.pptx

# 对可信 PPTX 明确选择真正的 LibreOffice 导入/导出，并与批准的图片做诊断性比较：
python research-figure/scripts/rfs.py native-audit \
  --spec /project/figure-spec.json --native-file /project/rebuilt.pptx \
  --render-with-libreoffice --reference /project/approved.png \
  --render-out /project/rebuilt-actual-render.png

# draw.io：结构校验支持普通或压缩 XML；渲染需实际可用的 draw.io 应用：
python research-figure/scripts/rfs.py native-audit \
  --spec /project/figure-spec.json --native-file /project/rebuilt.drawio
```

纯对象检查基于 Python 标准库；PPTX 文件生成与渲染验收的本地测试工具见 `research-figure/requirements-native-qa.txt`。启用实际渲染还需要系统 LibreOffice；不可将它当成对不可信文件的安全沙箱。像素差异分数只是排查线索，**不是高保真证明**；字体、遮挡、构图、科学内容和完整编辑性仍需人工核查。无原生文件或无实际渲染时保持 PENDING。

## 兼容老项目

v0.3.x `schema_version: "0.1.0"` 的 `type`/`diagram` 结构保留为**旧式兼容输入**；旧版例子与测试不被静默转换成新科学事实。**新项目应直接生成 FigureSpec v1**。两种结构不会在同一任务里混用。混合图需拆分方法示意部分和数据部分。

## 源文件与安全

仓库根目录 `README.md` 为公开安装说明；`research-figure/SKILL.md` 是自动发现入口；`research-figure/references/` 属于必需的公开运行规则。用户论文、API Key、IDE/Agent 本地配置、运行输出、评审草稿与内部文档不纳入版本控制。`.gitignore` 与 CI 中的 `check_repository.py` 双重检查，但对已泄露历史记录不能代替密钥轮换。发布用例均为明确标记的 synthetic fixtures。

**验证边界：** 离线协议、完整性检查与合成测试不等于真实模型出图效果、科学正确性或 PPTX 原生重建成功。相关项未验证时报告 PENDING，不能宣称完成。

## 许可与上游声明

自主调度代码采用 [MIT](LICENSE)。迁入 `research-figure/protocol/` 的 PaperBanana FigureSpec v1 校验/编译与互操作代码按其原有 **Apache-2.0** 许可保留版权，详见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) 和随附许可。Sivia 与 paper-fig 仅为可选外部后端，不再分发其受限内容。