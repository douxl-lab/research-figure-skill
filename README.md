# Research Figure Studio (RFS)

**面向科研论文的 Agent Skills 绘图调度器**。在保持科学结构可核验的前提下，发挥生成式图像模型的设计能力，并使用可复现的代码绘制实验结果；可编辑重建作为独立的按需步骤。

> 仓库名 `research-figure-skill`，安装后的 Skill 目录名为 `research-figure`。这两者是不同的命名层次，`SKILL.md` 中 `name: research-figure` 不应改为仓库名。

## 工作方式

| 路线 | 适合 | 工作内容 |
| --- | --- | --- |
| A · Generative-first | 复杂方法图、模型架构图、Overview | FigureSpec → 专业模型提示词 → 生成与筛选 → 设计锁定 |
| C · Data-driven | 对比实验、消融、训练曲线 | 原始 CSV → Matplotlib → 代码、矢量图及数据来源 |
| B · Native optional | 简单精确的流程图 | 根据已确认结构生成基础 SVG；**不作为复杂科研图的默认视觉路径** |
| Editable reconstruction | 需要 PPTX/draw.io 时 | **实际参考图 + 科学 FigureSpec + 图片锚定的详细文字说明** → 独立后端执行并校验 |

RFS 保留独立的科研事实与数据约束；不让图像生成模型凭视觉自行补造数值，也不把一张位图包装成“可编辑 PPTX”。

## 安装

将本仓库克隆到任意本地目录，安装仓库中的 `research-figure/` 子目录（必须与 `SKILL.md` 的 `name` 一致）：

```bash
git clone https://github.com/douxl-lab/research-figure-skill.git
# 主机可按其 Skill 安装机制引用此仓库根目录，或建立研究专用 Skill 软链接：
# ln -s /absolute/path/research-figure-skill/research-figure ~/.codex/skills/research-figure
python research-figure/scripts/check_skill.py --root research-figure
python research-figure/scripts/rfs.py doctor
```

直接运行脚本不需要外部模型账号。绘制数值图需要 Python 3.10+ 和可选的 Matplotlib：

```bash
python -m pip install -r research-figure/requirements-plot.txt
```

不要只复制 `SKILL.md`：`research-figure/references/`、`research-figure/scripts/` 和 `research-figure/assets/` 均有运行时用途。`research-figure/agents/openai.yaml` 是可选的 Codex Skill 发现元数据，并非开发者本地配置。

## 快速使用

```bash
# 离线校验设计需求与路由
python research-figure/scripts/rfs.py validate --spec research-figure/assets/spec-architecture.json
python research-figure/scripts/rfs.py route --spec research-figure/assets/spec-architecture.json

# 生成式方法图：生成模型专属专业 Prompt + 文字设计草案（此步骤**尚未生图**）
python research-figure/scripts/rfs.py models --provider gemini --priority quality
python research-figure/scripts/rfs.py prompt --spec research-figure/assets/spec-architecture.json \
  --model auto --provider gemini --priority quality --out /path/to/project/F01/draft

# 真实科研数据：替换为自己的 FigureSpec + 实验 CSV（示例数据是合成的）
python research-figure/scripts/rfs.py run --spec research-figure/assets/spec-plot-demo.json \
  --out /path/to/project/synthetic-demo

# 已有确定参考图后，结合科学规格和完成的文字说明构建“重建任务包”；
# 这不是 PPTX 生成成功的证明，仍需可用的 paper-fig / Sivia / draw.io 后端。
python research-figure/scripts/rfs.py reconstruction-package \
  --spec /path/to/project/F01.json \
  --reference /path/to/project/F01/approved.png \
  --design-notes /path/to/project/F01/observed-design-notes.md \
  --backend paper-fig --approved \
  --out /path/to/project/F01/reconstruction
```

更多命令：`python research-figure/scripts/rfs.py --help`。真实图像模型调用、费用和私有科研资料出境需经过用户授权。

## PaperBanana 与其他可选后端

- **PaperBanana**：优先使用 [`douxl-lab/PaperBanana`](https://github.com/douxl-lab/PaperBanana) 作为生成式五智能体引擎。设置 `PAPERBANANA_ROOT` 指向已安装的源码位置，然后运行 `python research-figure/scripts/rfs.py doctor` 检查环境。`rfs.py run --engine paperbanana --allow-external` 需要明确授权。
- **academic-plotting**：这里独立实现了有限的 Matplotlib 数据绘图路径，不复制上游 Skill。
- **paper-fig / Sivia**：仅在对应绘图后端真实安装且用户需要可编辑输出时调用。RFS 能准备三源任务包，**不承诺单独生成 PPTX/draw.io**。

**接口现状（重要）：** PaperBanana 升级后的 RFS Exchange v1（`schema_version: 1.0.0`）与本 Skill 的 FigureSpec v0.1（`schema_version: 0.1.0`）当前不同。内置 PaperBanana 调用使用科学文字摘要而非直接传入可验证的同构 JSON；尚未完成跨项目的科学不变量与任务包验收测试。不要将两份结构化协议视为无缝互换。参见 [外部接入规则](research-figure/references/integrations.md)。

## 目录规范

```text
research-figure-skill/
├── README.md                       # 仅公开的使用文档
├── .gitignore                      # 私密文件/本地状态屏蔽
├── .github/workflows/ci.yml       # 跨版本持续集成及安全检查
├── LICENSE / THIRD_PARTY_NOTICES.md
└── research-figure/                # 与 SKILL.md name 严格一致
    ├── SKILL.md                    # Agent Skills 主入口
    ├── agents/openai.yaml
    ├── references/                 # 运行时需读取的公开参考规范
    ├── scripts/                    # 调度、Prompt、数据图和审查
    ├── assets/                     # 公开样例，不含私有数据
    ├── tests/                      # 单元/回归/安全测试
    └── requirements-plot.txt
```

`README.md`、`research-figure/SKILL.md` 和 `research-figure/references/*.md` 是**公开运行时/使用文档**，必须随 Skill 版本控制；**内部文档、草稿、测试产物、开发笔记与任务状态**一律放在忽略目录，不能提交到 GitHub。`.gitignore` 无法保护已经追踪或被 `git add -f` 强制加入的文件，因此 CI 额外执行 `research-figure/scripts/check_repository.py --root . --tracked` 检查提交内容。

## 测试与安全

```bash
python research-figure/scripts/check_skill.py
python research-figure/scripts/check_repository.py --root . --tracked
python -m unittest discover -s research-figure/tests -q
```

- 无需联网的测试用于验证本地流程，不意味着真实模型 API 可用或科研图质量已达投稿要求。
- 密钥仅从本地环境变量或第三方后端独立配置读取，**不得写入源码、FigureSpec、公开示例、生成 Prompt 或日志**。
- 项目数据、论文 PDF、运行缓存、PNG/PPTX 成果必须存放在此仓库之外；不要把未发表内容复制进 `assets/`。
- `.gitignore`、内容扫描和平台 Secret Scanning 只是多道防线，不是保密担保。对外公开仓库前检查 Git 历史；泄露过的密钥必须轮换，单纯删除文件无效。
- 不允许把 Sivia 的非商业代码/模板或 paper-fig 的受限第三方材料复制进本仓库。详见 [第三方声明](THIRD_PARTY_NOTICES.md)。

## 版本与许可

- **v0.3.2**：仓库发布与隐私保护整理（基于上一版 v0.3.1 CLI/Skill，未宣称新的模型质量验证）。
- 本项目自行实现的代码按 [MIT](LICENSE) 发布；外部模型服务、依赖和参考仓库分别遵守其许可与平台条款。
- [Agent Skills 官方范式](https://agentskills.io/specification)。
