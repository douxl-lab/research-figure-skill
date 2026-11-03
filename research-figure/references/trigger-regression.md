# Trigger Regression Cases（入口触发回归用例）

> 用途：每次新增/合并/修改科研图族入口（SKILL.md description）后，用这组语料逐一检查路由是否正确。人工或 agent 均可执行：读语料 → 判断应进哪个 skill → 与期望对照。来源：2026-11-01 pi 评审建议（P0-2），边界声明见各入口 description。

| # | 触发语料 | 期望入口 | 判定理由 |
|---|---|---|---|
| 1 | "帮我画论文的方法图 / 架构图 / pipeline 图" | research-figure（走本机 local pipeline） | 默认科研图总入口；无黑白/线稿字样，mono-diagram 不得截胡 |
| 2 | "画一张技术路线图，要黑白打印用的线稿" | mono-diagram | 明确黑白 + 打印 + 线稿——mono 的正触发 |
| 3 | "用这组 CSV 画消融实验对比图 / 训练曲线" | academic-plotting（或 RFS Route C） | 数据图走代码绘制路线，禁止生图模型猜测数值 |
| 4 | "把这张已定稿的图做成可编辑 PPTX" | recreate-scientific-figure（协议入口）→ 按后端可用性派发 paper-fig / in-drawio | 已有参考图的重建；无参考图时不得进入 |
| 5 | "给我这个方法做个总览图设计稿就行，不用跑完整流程" | design-scientific-figure | 明确"只要设计方案"；要求完整交付时仍回 RFS |

补充负例（不应发生的行为）：
- mono-diagram 接到语料 1（无黑白要求的彩色方法图）→ 回归失败
- recreate 系接到"从零画一张新图"（无参考图）→ 回归失败
- design 接到语料 4（有参考图的重建）→ 回归失败（应转 recreate）
- 数据图语料进入任何生图路线（Route A / Sivia）→ 回归失败
