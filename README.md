# Research Figure Studio

面向科研论文的统一绘图 Skill：从可核对的方法、代码或真实数据出发，组织设计、版式、矢量绘制、原生重建和产物验收。

**一个入口，按任务主动选择内部能力。** 设计内核、模板与参考图库已随包提供；用户不需要逐个点名第三方工具。`research-figure-skill` 是仓库名，实际安装入口是 [`research-figure/SKILL.md`](research-figure/SKILL.md)。

## 0.9.0：生图模型优先，SVG 按需

**默认由生图模型完成整张机制图，再看图审查与局部编辑。** 不再默认把 AI 限制为局部素材生产，也不要求先用代码搭出整图。少字多图，用特征、Token、Glyph 和信息流解释机制；公式只在确有必要时出现。

优先使用实际可用的宿主生图工具；在本地/API 环境中，可以接入单独安装的 [image2-api](https://github.com/techdou/image2-api)。新适配器使用其生成与编辑 CLI，默认 PNG，支持多参考图和蒙版，保留提示词、源规范、版本图片与审查状态。不硬编码某个最新模型，不自动重试或切换服务商。干跑不调用 API，也不能当作出图成功。

明确要求可编辑 SVG 时，优先由宿主 LLM 撰写 SVG 源码并实际渲染检查；无需为 SVG 默认调用生图 API。`llm-svg` 是宿主任务交接，不是 CLI 自行调用另一个 LLM。真实实验曲线和观测图仍由真实数据生成。

```bash
# 在项目目录准备 figure-spec.json、mechanism-prompt.txt 和私有 image-provider 配置
python research-figure/scripts/workflow.py run --mode image2-api \
  --image2-root /installed/image2-api --image2-config /project/image-provider.json \
  --spec /project/figure-spec.json --prompt /project/mechanism-prompt.txt \
  --dry-run --out /project/figures/F01-dry

# 审查服务、数据与费用授权后：移除 --dry-run，加 --allow-external，并改用全新输出目录。
# 仅在明确要求 SVG 时：
python research-figure/scripts/workflow.py run --mode llm-svg \
  --spec /project/figure-spec.json --out /project/figures/F01-svg
```

配置、真实调用、参考图/蒙版编辑和边界见[生图适配指引](research-figure/references/local-image-pipeline.md)；完整制作流程见[机制图 SOP](research-figure/references/mechanism-figure-workflow.md)。发布包更新不等于客户端安装副本已更新；离线测试不证明真实模型的视觉质量。

## 能力与边界

| 模块 | 职责 | 运行条件 |
| --- | --- | --- |
| `design` | 方法图、机制图、架构图的检索、规划、风格、生图协调与评审 | 包内协调代码；实际生图需要宿主工具或已授权的模型服务 |
| `layout` | 本地素材检索、模板布局、SVG / 原生 PPTX / VSDX 导出与审计 | 包内代码与素材；基础矢量导出使用 Python 标准库 |
| `vector` | 按需由宿主 LLM 撰写 SVG，或使用 TikZ 精确矢量表达 | RFS 渲染器及 XeLaTeX / Poppler 等对应工具 |
| `plot` | 真实实验数据图与可复现绘图代码 | Matplotlib 与完整输入数据 |
| `reconstruction` / `audit` | 已批准图片的原生重建交接、对象检查与导出检查 | 实际可用的编辑器、导出器及审计依赖 |

实测曲线、遥感观测和预测结果不得由生成模型代替。生成图片不等于科学正确；插入 PNG 的幻灯片不等于原生可编辑。模板和图库只提供设计参考，不作为研究证据。

## 目录规范

```text
research-figure-skill/
├── .github/workflows/ci.yml       # 只读验证与安装包构建
├── .gitattributes                # 文本与来源快照的字节规则
├── .gitignore                    # 私密内容默认排除，运行文件显式例外
├── README.md                     # 公开使用说明
├── LICENSE
├── THIRD_PARTY_NOTICES.md
└── research-figure/              # 必须整体安装的 Skill
    ├── SKILL.md
    ├── agents/                  # 公开的 Skill 展示元数据；不是个人 Agent 配置
    ├── assets/                  # 公开 schema、合成夹具、样式及上游锁文件
    ├── kernels/
    │   ├── design/              # 固定版本的设计源码快照
    │   └── layout/              # 固定版本的版式源码、模板与图库
    ├── protocol/                # FigureSpec 与产物交换协议
    ├── references/              # Skill 执行必需的公开指引
    ├── scripts/                 # 编排、适配、校验、更新与打包入口
    └── tests/                   # 离线回归与合成测试夹具
```

内部文档、开发计划、审查记录、运行状态和真实项目资料不属于这个目录树。工作目录与安装目录分离，建议在仓库外保存论文、配置、实验数据及生成结果。不要将临时文件放入 `references/` 或 `assets/` 规避排除规则。

## 安装与环境

需要 Python 3.10+。安装**完整的 `research-figure/` 目录**，不要只复制 `SKILL.md`。包内源码和素材无需额外 clone 或递归初始化子模块；Python 库、系统工具、编辑器和模型访问权限不随安装包提供。

从仓库根目录安装离线协议与审计依赖：

```bash
python -m pip install -r research-figure/requirements-exchange.txt -r research-figure/requirements-plot.txt -r research-figure/requirements-native-qa.txt
python research-figure/scripts/check_skill.py
python research-figure/scripts/upstreams.py verify
python research-figure/scripts/workflow.py doctor
```

上述命令同样适用于已经配置 `python` 的 PowerShell。Provider 全流程需要设计内核声明的额外依赖；单点 API 适配需要兼容 SDK，读取 YAML 配置另需 PyYAML。PDF / PNG 转换按实际选择的后端安装对应转换器，参见其运行指引。

`doctor` 只报告已观察到的状态：路径存在不证明调用成功，配置存在不证明授权有效。更新仓库或生成 ZIP 不会自动替换客户端已经安装的旧副本。

## 快速开始

普通使用直接向宿主提出任务，例如：

> 用 research-figure，根据这份模型代码绘制科研机制图；保留可核对的数据流和标签，交付图片及所需源文件。

以下命令均从仓库根目录运行。将 `/project/` 替换为仓库外的项目路径；将 `ACTUAL_AVAILABLE_TOOL` 替换为宿主实际提供的生图工具名称，不得虚构工具能力。

```bash
# 检索包内参考素材（无需联网）
python research-figure/scripts/library.py --query attention

# 校验科学规范、规划路线；不会生成图片
python research-figure/scripts/rfs.py validate --spec /project/figure-spec.json
python research-figure/scripts/workflow.py plan --spec /project/figure-spec.json --host-image-tool ACTUAL_AVAILABLE_TOOL

# 启动设计协调，宿主继续执行返回的阶段任务
python research-figure/scripts/workflow.py run --spec /project/figure-spec.json --host-image-tool ACTUAL_AVAILABLE_TOOL --out /project/figures/F01
```

`HOST_ACTION_REQUIRED` 表示宿主仍需执行任务，**不是图片已经生成**。`kernel.py design next/record/verify` 用于阶段推进与回执核对；真实图片、科学核对、视觉评审和用户批准分别记录。

按输出要求选择其他路线：

```bash
# 版式 YAML 必须单独审校，不能用 FigureSpec JSON 直接替代
python research-figure/scripts/workflow.py run --spec /project/figure-spec.json --mode layout --layout-spec /project/layout.yaml --out /project/figures/F02

# 明确要求的 TikZ 矢量输出
python research-figure/scripts/workflow.py run --spec /project/figure-spec.json --mode tikz --out /project/figures/F03
```

实测数据图自动走 `plot-matplotlib`；已有图片的小修或原生重建不应重新开始概念设计。旧引擎名与环境变量保留兼容，新接口使用内部模块名。显式指定的外部路径无效时会报错，不会静默改用其他后端。

## 凭据、配置与发布范围

**不得提交 API 密钥、令牌、私钥、真实服务配置或私密研究内容，私有仓库也不例外。** 密钥从任务明确指定的环境变量读取；本地服务配置保存在仓库外。不要在命令行、URL、源码、示例、FigureSpec、提示词、日志或公开 issue 中粘贴真实密钥。公开配置模板只能含占位符和环境变量名称。

通过中转服务或本地代理调用外部模型，仍需要相应的数据披露与费用授权。`--allow-external` 只表达调用条件，不会自动取得授权，也不会因为发现一个 key 就更换服务。

| 可以提交 | 不可以提交 |
| --- | --- |
| 源码、离线测试、公开合成夹具、schema、版本锁与 CI | 真实论文、数据、实验结果、生成文件、会话及运行回执 |
| README、许可证、`SKILL.md` 和显式列入公开清单的执行指引 | 内部文档、TODO / 计划 / 评审报告、开发状态与个人笔记 |
| 来源锁定的上游代码、必要指引、参考图库和组件 | 未经审查的上游新增文件、字体、SDK 二进制与模型权重 |
| `research-figure/agents/openai.yaml` 等公开 Skill 元数据 | `.vscode/`、`.idea/`、`.cursor/`、`.claude/`、`.codex/`、`.agents/` 及其他个人工具配置 |

`.gitignore` 默认排除文档与私密目录；仅精确放行运行必需的文档及已审查素材。`check_repository.py` 同时检查 **Git 暂存区实际 blob 与已跟踪工作区文件**，拒绝禁止的路径、来源哈希偏移和配置规则识别出的敏感值。检查报告不回显匹配值。

新增公开运行指引或上游素材时，必须审查内容并同步公开清单 / 忽略例外；不要使用 `git add -f` 绕过规则。安装包构建复用同一发布检查，存在未批准文件时失败，而不是悄悄带入安装包。

`.gitignore` 不影响已跟踪文件，也不能清除 Git 历史。如果发现误入库的私密文件，应先停止发布；确认本地副本保留后从索引移除，再处理已发布影响。泄漏凭据须先撤销或轮换，之后再协调历史清理；不能把删除最新文件视为已经消除泄漏。相关依据：[Git 忽略规则](https://git-scm.com/docs/gitignore)、[GitHub 敏感信息移除指南](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository)。静态扫描不是“绝无泄漏”的保证，提交前仍需人工审查 diff。

## 更新与回滚

在工作树干净且远端设置正确时，获取本项目发布的新版本：

```bash
git pull --ff-only
```

包内上游源码使用受控更新。**设计内核的默认检查源已更正为原作者 `original_upstream`，不再误将我们的 Fork 当作原作者上游。** 因为我们保留了 FigureSpec、native-host 和隐私保护扩展，禁止原作者源码直接覆盖内核；先在我们的维护 Fork 适配并通过测试，再显式同步：

```bash
# 核查原作者当前 main：仅读取、不写入
python research-figure/scripts/upstreams.py check --kernel design --allow-network

# 适配并提交到维护 Fork 后，更新已审查的内核快照
python research-figure/scripts/upstreams.py pull --kernel design --source-role maintained --ref FULL_FORK_COMMIT_SHA --allow-network
python research-figure/scripts/upstreams.py verify

# 无独立 Fork 的版式内核仍走直接检查与受控更新
python research-figure/scripts/upstreams.py check --kernel layout --allow-network
python research-figure/scripts/upstreams.py pull --kernel layout --allow-network
```

支持 `--ref <commit>` 锁定版本和 `--source <local-repository>` 离线读取 Git 对象。存在本地改动、符号链接、许可证变更或并发操作时拒绝覆盖；不执行下载代码、不自动安装依赖，也不会自动 commit/push。具体双源策略见维护指南。

更新后检查 diff、公开文件清单和完整回归，再显式提交。已发布提交使用 `git revert` 回滚，避免改写协作者历史。完整说明见[上游维护指南](research-figure/references/upstream-maintenance.md)。

## 验证、提交与分发

```bash
python research-figure/scripts/check_skill.py
python research-figure/scripts/upstreams.py verify
python -m unittest discover -s research-figure/tests -q
python research-figure/scripts/smoke_kernels.py

# 明确暂存本次文件后，检查暂存区与工作区，再审查最终 diff
python research-figure/scripts/check_repository.py --root . --tracked
git diff --cached --check
git diff --cached --stat
```

离线测试使用标注的合成夹具，不代表真实生图质量、科研正确性或宿主自动匹配率。CI 检查 Python 3.10 / 3.12 / 3.13；环境相关跳过项必须单独查看，不能表述为已验证。

提交采用 `type(scope): summary`，例如 `fix(security): validate staged publication inputs`。测试通过后推送到约定分支；不覆盖远端新增提交、不强制推送，不提交内部验收报告、计划或打包产物。

```bash
python research-figure/scripts/build_package.py --out /outside-repo/research-figure.zip
```

构建输出必须为安装目录外的全新路径。安装整个目录或将 ZIP 交给支持该格式的宿主；打包完成与宿主安装成功是不同状态。

## 运行指引

[设计内核](research-figure/references/design-core.md) · [版式素材](research-figure/references/layout-library.md) · [期刊机制图规范](research-figure/references/journal-mechanism-style.md) · [制作 SOP](research-figure/references/mechanism-figure-workflow.md) · [单点生图](research-figure/references/local-image-pipeline.md) · [原生重建](research-figure/references/reconstruction.md)

## 许可证与来源

RFS 自有编排与适配代码使用 [MIT](LICENSE)。内置 `design` 来源于维护的 PaperBanana 分支，保留 Apache-2.0；`layout` 来源于 CVPR-Figure，保留 MIT。内部名称不替代原作者署名，也不表示全部代码原创。

确切上游仓库、commit 和逐文件 SHA-256 见 [`upstreams.lock.json`](research-figure/assets/upstreams.lock.json)；完整归属及其他依赖边界见 [THIRD_PARTY_NOTICES](research-figure/THIRD_PARTY_NOTICES.md)。第三方图片、字体、论文和服务可能有各自的使用限制。
