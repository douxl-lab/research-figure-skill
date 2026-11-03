# ZCode 本机编排（Local Pipeline）— RFS 在无云端凭证环境的适配

> 2026-11-01 由 `research-figure-zcode` skill 并入。**机制图（位图+矢量结合）的完整制作 SOP 见 [mechanism-figure-workflow](mechanism-figure-workflow.md)（八步流程+素材产线+踩坑速查，2026-11 两轮实战沉淀）。**本机 PaperBanana 的多 agent 文本侧**没有云端 API 凭证**（2026-10-11 拍板：不接 API，ZCode 做文本侧）。本流程把 Planner/Critic 的职责交给 ZCode，PaperBanana 只负责生图。生图走 image2-api 中转链（happyevering · gpt-image-2.5-sunburst），已实测出图。**本机科研图任务默认走本流程。**

## 固定路径与环境

- RFS skill：`~/.agents/skills/research-figure`（python 用 `/c/ProgramData/chocolatey/bin/python3.13`，**勿用 MSYS2 python3**）
- PaperBanana：`E:\skills\PaperBanana`（venv 已建，凭证在 `.env`，生图入口 `scripts/generate_from_prompt.py`）
- 环境变量（.bashrc 已配）：`PAPERBANANA_ROOT`、`PAPERBANANA_PYTHON`、`RFS_PAPERFIG_SKILL`、`RFS_SIVIA_SKILL`
- 产物目录建议：当前项目 `figures/<图名>/`

## 流程九步

1. **起草 FigureSpec**：按 `~/.agents/skills/research-figure/assets/figure-spec-v1-example.json` 的 v1 schema 写 spec（科学模块、标签、公式、连线、来源、锁定约束）。豆哥给论文/方法描述时，先通读材料再写 spec，不要只凭摘要。
2. **校验**：`python3.13 ~/.agents/skills/research-figure/scripts/rfs.py validate --spec <spec.json>`
3. **编译 prompt 包**：`python3.13 .../rfs.py run --spec <spec.json> --out <dir>`（prompt-only 模式，产出 `prompt.txt` + `design-intent.md` + `figure-spec.json` + `manifest.json`）
4. **审校 prompt（ZCode 文本侧核心职责）**：逐项核对 prompt.txt——科学标签与原文一致、公式无误、布局描述可执行、图像资产规划合理（参考 `research-figure/references/journal-mechanism-style.md` 的排版规范：独立图默认不加图内大标题和 A/B/C 标签）。发现问题直接改 prompt.txt 并在对话里说明改了什么。
5. **生图**（脚本在本 skill 的 `scripts/` 下，引擎定位走 `PAPERBANANA_ROOT` 环境变量，默认 `E:\skills\PaperBanana`）：
   `E:/skills/PaperBanana/.venv/Scripts/python.exe ~/.agents/skills/research-figure/scripts/generate_from_prompt.py --prompt <dir>/prompt.txt --out <dir>/candidates --candidates 2 --size 1536x1024 --quality high`（探索期用 low/medium，定稿用 high+；链路健康检查用同目录 `image2api_smoke.py`）
6. **视觉评审（Critic 职责）**：**派 `vision` 子代理** Read 每张 candidate（不要用 CDN URL 喂视觉 MCP——反斜杠路径会静默幻觉，见 memory）。检查：文字渲染准确（科学标签错字=硬伤）、布局与 spec 一致、无编造元素。选一张最优，其余留档。
7. **程序验收**（v1 spec 直调 audit_file，绕开 rfs.py 的 canonical bundle 分支——ZCode 编排不产 PaperBanana 全流程 bundle）：
   ```bash
   cd ~/.agents/skills/research-figure/scripts && /c/ProgramData/chocolatey/bin/python3.13 -c "
   import sys, json; sys.path.insert(0, '.')
   from auditing import audit_file
   T = '<产物目录>'
   spec = json.load(open(T + '/figure-spec.json', encoding='utf-8'))
   r = audit_file(spec, T + '/figure-spec.json', T + '/candidates/candidate-N.png')
   print({k: v['status'] for k, v in r['checks'].items()})"
   ```
   `artifact_exists` 与 `artifact_format` 应为 PASS；科学各项 PENDING 是设计常态。
8. **写观察笔记**：`<dir>/observed-design-notes.md`——覆盖至少三个维度（layout / objects+text / connectors / visual style），写给重建后端看：精确描述选中图的布局、各对象位置关系、连线走向、配色字号。这一步是重建质量的杠杆，要写细。
9. **重建交接（可选，豆哥要求可编辑 PPTX 时）**：**走协议正门产出正式重建包**（2026-11-01 打通，冒烟全过；旧版"手工组织 handoff 包"的做法已废弃）：
   ```bash
   cd ~/.agents/skills/research-figure/scripts
   # a) 组装 bundle（payload 全部来自本流程真实产物，脚本当场跑 interop.verify_result 自验）
   python emit_bundle.py --dir <产物目录> --candidate <选中编号>
   # b) 出正式重建包（rfs-native-handoff/1.0 回执，READY_NOT_EXECUTED）
   python rfs.py reconstruction-package --spec <产物目录>/figure-spec.json \
     --bundle <产物目录>/bundle --design-notes <产物目录>/observed-design-notes.md \
     --out <产物目录>/pkg --backend paper-fig
   ```
   之后按 handoff 包做原生重建：优先 paper-fig v2 的 rfs_consumer（读 `~/.agents/skills/paper-fig/rfs_consumer/README.md`）；若其私有 runtime（@oai/artifact-tool）不可用，走 html-to-pptx 替代链（见 memory：箭头用 CSS 形状、转换后删垫底整页图）。handoff 优先级规则不变：① FigureSpec 与已验证科学事实管辖节点/边拓扑、公式、精确标签，绝不从位图"补全"事实；② 批准的参考图管辖构图、比例、视觉层级与配色；③ 设计笔记解决图像歧义细节；④ 来源冲突时标 BLOCKED/PENDING 请豆哥裁决，不擅自折中；⑤ 尽量用原生可编辑文字/模块/连接器；⑥ 交付前对实际保存的 PPTX/draw.io 重开渲染审计对象清单，"看着一样的 PNG"不是可编辑性证明。

## 交付清单与完成状态（所有路线统一，2026-11-01 定）

每条路线（AI 生图链 / Sivia 原生 / Route C 数据图 / 重建）交付时记录同一份清单，禁止各路线自解释"完成"：

| 字段 | 说明 |
|---|---|
| spec 版本与 scientific_fingerprint | 协议锚点，贯穿全链 |
| 来源 | 论文/代码/CSV 及引用位置 |
| 生产者及版本 | 如 image2api-relay + 模型名 / Sivia v1.3.0 (douxl-lab fork) / matplotlib 版本 |
| 选中产物 | candidate 编号或文件路径；落盘字节为准（图床 URL 不算产物） |
| 审批状态 | 豆哥终审记录（第 6 步视觉评审 ≠ 科学验证） |
| 设计笔记 | observed-design-notes.md（重建质量的杠杆） |
| 原生文件 | 实际保存的 PPTX/draw.io/SVG/PDF；重开渲染审计后才是交付 |
| 审计结果 | bundle verify_result / audit_file / figureguard 各自的 PASS-FAIL-PENDING |
| 未决项 | 全部 PENDING 与 BLOCKED 显式列出，不许静默 |

完成状态语义（沿用协议既有词汇，不得发明新状态）：
- `PROMPT_READY_NOT_RENDERED`：prompt 包产出但未生图——不是图，不得当交付
- `READY_NOT_EXECUTED`（rfs-native-handoff/1.0 回执）：重建包就绪但未执行——不是可编辑文件
- 科学项 `PENDING` 是诚实状态：AI 视觉输出未经科学验证，科学正确性靠 spec 锁定 + 豆哥终审
- 严禁：把预览 PNG/SVG 称作可编辑 PPTX；把"看着一样"当重开审计

## 边界与红线

- **不要**用 `--engine paperbanana`（会拉起无凭证的多 agent 文本流程，直接失败）；生图只用 generate_from_prompt.py。
- 数据图（柱状/折线/真实实验数据）不走本流程的生图侧——用 `rfs.py run --spec <plot-spec>` 的 plot-matplotlib 路线（数据可复现），或 academic-plotting skill。
- 生图模型的视觉输出未经科学验证（audit 各项保持 PENDING 属正常）；科学正确性靠 spec 锁定 + 豆哥终审。
- 定稿候选的 metadata（generation-metadata.json）与 handoff 包一起归档，保证溯源。
- 已知现象：中转生图尺寸会略放大（要 1024 给 ~1254），不影响使用；图床 URL 有时效，生成后立即落盘（脚本已处理）。
