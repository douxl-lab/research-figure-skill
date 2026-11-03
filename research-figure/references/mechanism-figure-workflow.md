# 机制图制作 Workflow SOP（实战沉淀版）

> 来源：2026-11-01/02 两轮实战（遥感注意力图重建 142 cells + 贝叶斯道路图复刻 326 cells，位图+矢量结合）+ 三链横评 + pi 双轮评审。权威纪律见全局 AGENTS.md「科研图绘制准则」；本文件是操作级步骤。

## 总流程（八步）

```
1 定规格 → 2 备素材 → 3 通道规划 → 4 面板生成 → 5 合并嵌图
→ 6 AI 自审 → 7 pi 独立检验 → 8 豆哥终审（不过则回 4/6 迭代）
```

## Step 1 · 定规格（SPEC.md）

- 有参考图：Read 参考图 → 面板划分（bounds 表）→ 位图槽位表（id/坐标/raster_reason）→ 矢量清单 → 验收标准
- 从零生成（无参考图）：从论文/公式/代码出发写 FigureSpec（RFS 协议），走 zcode-local-pipeline.md
- 画布坐标与参考图像素系一致（1:1），省换算

## Step 2 · 备素材（位图素材产线三分法）

| 产线 | 用法 | 实测要点 |
|---|---|---|
| 代码渲染优先 | matplotlib 公式直出（曲面/曲线族/热图） | `Agg` 后端、`mathtext.fontset=cm`、透明底、dpi≥200 |
| 生图占位 | `generate_from_prompt.py`（PaperBanana venv） | **--prompt 要文件路径不是文本**；探索期 quality=medium |
| 真实数据 | 实验输出直出 | 红线：生成=伪造 |
| （复刻专属）裁剪 | PIL `Image.crop` 参考图 | 显示坐标×(实际宽/显示宽)换算；裁后拼 contact sheet 逐块 Read 校验 |

## Step 3 · 通道规划（布局阶段做，非画线时）

- 定义坐标时预留线走廊：水平线走区域间固定 y 通道、垂直线走固定 x 通道
- 平行线错开 8–12px；走廊取元素包围盒间隙中点（如圆圈行 y322-346 与下排 y398 → 总线 y=370）
- **规格给子 agent 时走廊坐标显式写出**——"点到点最短"思维必然穿模

## Step 4 · 面板生成（派子 agent，主 agent 定规格+验收）

- 每个面板一个子 agent：Read 参考图 → 循环生成重复图元（EncBlock×4/色格×6/ DWCnv 三列禁手写）→ 产出 panel-*.drawio
- prompt 必含：布局规格+通道坐标+样式常量+自检清单（逐字核对/正交/穿模/文字重叠/数量核对）+"以参考图为准冲突时"
- XML 骨架：mxfile>diagram(id)>mxGraphModel(pageWidth/Height 按面板)>root（id 0/1 前）；diagram 必须有非空 id（validate 会报）
- 工程铁律：改 XML 一律 ElementTree（正则因属性顺序假设必炸）；子 agent 交付后立即 validate（曾出现悬空边、最终写入覆盖主 agent 修复——**验收永远以最终落盘文件为准，重跑清理**）

## Step 5 · 合并嵌图（主 agent 脚本化）

- merge 脚本：读各 panel XML → 去重 id（前缀区分：pl_/pd_/pe_）→ 位图槽位替换为 `shape=image;image=data:image/png,BASE64` → 合入 2304×1279 总图 → ET 解析验证 + 悬空边清理
- 位图保持等比（槽位尺寸按裁剪块宽高比算，避免拉伸变形）

## Step 6 · AI 自审（第①环）

逐条：语义逐字（模块名/下标/张量标注 vs 参考图）｜正交纪律（XML 全局 grep curved/spline=0）｜穿模（程序化：每条边折线段 vs 不透明顶点 bbox 相交检测）｜位图 gate（数量+位置+无变形）｜数量核对（EncBlock/DBCIM/Decoder 等系列模块数）｜文字重叠（label bbox 两两相交）
→ validate 零错误 + 程序化检查 + 渲染 PNG 目视三重验证，缺陷如实列表

## Step 7 · pi 独立检验（第②环）

- `pi-delegate` review 模式，**chcp 65001 包裹**（Windows GBK 编码崩溃的解法）+ `--task-file`（中文长文本）+ 后台跑（--timeout 1500）
- 简报含：参考图/成品路径（XML 为准）、五项验收标准逐项判、已知差异清单（验证是否属实）、选型三问
- FAIL → 修 v(n+1) 回 Step 6

## Step 8 · 豆哥终审（第③环）

- 交付三件套+.drawio 源 + PPTX 版（按需）+ 已知差异清单 + 待替换位图槽位表
- 豆哥反馈进下一轮迭代

## 导出与交付（链路选型矩阵）

| 目标 | 链路 | 命令/工具 |
|---|---|---|
| 预览 PNG | drawio CLI | `drawio_export format=png width=2200` |
| 矢量 SVG/PDF | drawio CLI | `drawio_export format=svg/pdf`（论文投稿用 PDF） |
| 可编辑 PPTX | drawio→DOM→html-to-pptx | `drawio_to_dom_html.py` → `run.sh input.html -o out.pptx`（`figures/recreate-demo/html-pptx-v2/drawio_to_dom_html.py`） |

已知短板与对策：PPTX 线段栅格化（改线回 .drawio 再转，单一源头）；drawio 3D 盒无渐变（PPTX 链渲染质感更好，终稿可换链）；drawio-live 弃用（CDP 不稳）。

## pi 检验沉淀的链路增强项（2026-11-02 二轮检验建议，待实践）

1. **跨导出端一致性测试**：同一 .drawio 自动导 PNG/PDF/PPTX → 渲 PPTX 视觉回归，检查字体替换/上下标/虚线/透明度/图片裁剪/z-order——"对象可编辑数量"不是充分指标
2. **素材 provenance 规范**：代码渲染的合成曲线/曲面标 `schematic/simulated`（代码生成≠真实数据）；生图占位进独立目录+manifest `placeholder=true`，最终导出发现占位素材应阻断交付；参考图裁片标 `reference-derived` 不升格为真实测量；真实数据记录原图哈希+变换链
3. **导出质量门槛**：自动检查缺图、可见性、宽高比、有效 DPI——防"源文件有图、成品没图"（pi 曾因小图误判曲面缺失，放大复核流程固化：争议项裁局部放大人工+XML 双验）
4. **交付边界声明**：PPTX 版注明"模块+文字可编辑，连线需回 .drawio 源改"——不宣传全元素可编辑
5. **线段原生 connector**（中期）：drawio→DOM 时同时输出线段元数据，PPTX 侧直生原生连接线替代栅格小图

## 踩坑速查（两天实战全记录）

1. drawio-live 三次断连 → 全后台管线
2. 主 agent 长上下文手写大批 cell 规格 → 三次损坏 → 派子 agent
3. 正则改 XML 属性顺序假设 → ElementTree
4. update_cells 改不了 waypoints（geometry 非 style）→ ET 脚本
5. 色格小间距自动路由绕圈 → 显式 waypoints + 直连方向
6. cmd //c 引号吃参数、heredoc 截断长脚本 → Write 工具/task-file
7. pi 中文 GBK 崩溃 → chcp 65001 包裹
8. MCP 生图 30s 超时 → CLI 链（PaperBanana venv）
9. matplotlib pane API 3.14 改名 → set_pane_color
10. 子 agent 最终写入覆盖主 agent 中途修复 → 落盘后重新验收
11. Agent subagent_type 拼错 → 直接报错重派
12. 微信临时图路径会清 → 先拷入工作区
