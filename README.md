# Research Figure Studio · v0.8.0

**一个科研绘图入口，内置设计内核、版式素材和真实执行适配。**

`research-figure-skill` 是仓库名，安装入口为 `research-figure/SKILL.md`。
常规调用使用我们的内部职责名，不需要用户逐个点名第三方项目。
原始项目名称、许可证和版本保留在来源记录中，绝不冒充全部原创。

## 包含什么

| 内部模块 | 职责 | 是否在包内 |
| --- | --- | --- |
| `design` | 检索、规划、风格、生图协调、评审；宿主或经授权的 Provider 路径 | 47 个源文件，含五阶段代码、协议和样式指引 |
| `layout` | 模板/图库检索、布局、SVG/PPTX/VSDX 导出、文件审计 | 83 个文件，含 16 个 YAML 模板与 19 张参考预览 |
| `vector` | 明确要求的 TikZ / 精确数学矢量表达 | RFS 渲染器；XeLaTeX/Poppler 是环境依赖 |
| `plot` | 真实数据图与可复现代码 | RFS Matplotlib 适配器 |
| `reconstruction` / `audit` | 已批准图片的可编辑重建交接、原生对象和导出验收 | 规范/交接/审计在包内；特定编辑器仍需实际可用 |

安装**完整的 `research-figure/` 目录**，不要只复制 `SKILL.md`。
源码、参考模板和图片均真实内置；普通解压安装不需要递归子模块或额外 clone。
安装不等于有模型权限：真正生图仍须宿主生图工具，或已授权且配置正确的外部服务。

## 使用

用户只需说：“用 research-figure，根据这份代码画科研机制图。”
主入口会主动选择本地参考原型、启动设计阶段、执行可用工具，再检查实际产物。
实测数据图不进入生成模型；明确 TikZ 请求直接走矢量路线。

```bash
RFS=/installed/research-figure
python "$RFS/scripts/workflow.py" doctor
python "$RFS/scripts/upstreams.py" verify
python "$RFS/scripts/library.py" --query attention
python "$RFS/scripts/workflow.py" plan --spec /project/figure-spec.json --host-image-tool ACTUAL_AVAILABLE_TOOL
python "$RFS/scripts/workflow.py" run --spec /project/figure-spec.json --host-image-tool ACTUAL_AVAILABLE_TOOL --out /project/figures/F01
```

`HOST_ACTION_REQUIRED` 表示宿主必须继续执行返回的阶段，**不是已经画完**。
`kernel.py design next/record/verify` 管理真实阶段回执；协调脚本本身不调用生图模型。
不使用外部凭证的宿主生图，与通过中转服务的 API 生图是两件事。
中转同样需要披露/费用授权，不会因端点在本地就跳过。

```bash
# 版式内核：单独审校 layout YAML，不能把 FigureSpec 当成上游 YAML
python "$RFS/scripts/workflow.py" run --spec /project/figure-spec.json --mode layout \
  --layout-spec /project/layout.yaml --out /project/figures/F01-vector
# 精确矢量源文件
python "$RFS/scripts/workflow.py" run --spec /project/figure-spec.json --mode tikz --out /project/figures/F02
```

旧 `rfs.py`、旧引擎名称和环境变量保留兼容；新默认路径是包内内核。
明确设置无效外部路径时会报错，不会悄悄换到另一引擎。

## 上游更新：可审查的 pull

```bash
# 先查看变更，不修改内核
python "$RFS/scripts/upstreams.py" check --kernel layout --allow-network
# 拉取选择范围，更新源码及 commit / 哈希锁
python "$RFS/scripts/upstreams.py" pull --kernel layout --allow-network
python "$RFS/scripts/upstreams.py" verify
python -m unittest discover -s "$RFS/tests" -q
```

支持 `--ref <commit>` 固定版本，以及 `--source /local/upstream --kernel design`
离线 Git 镜像。它只读取 Git 对象，不执行下载代码、不安装依赖、不自动 push。
存在本地修改、额外文件、符号链接或并发更新时停止，绝不直接覆盖。
许可证变化必须单独审查并显式接受。一个内核的替换和锁更新具备失败回退；
多个内核顺序更新的已完成状态会如实报告。提交后的撤销使用 `git revert`。
详见 [维护指南](research-figure/references/upstream-maintenance.md)。

上游来源为 PaperBanana / CVPR-Figure；日常能力名与第三方来源名分离。
确切版本和每个文件的哈希见
[upstreams.lock.json](research-figure/assets/upstreams.lock.json)，许可证见
[THIRD_PARTY_NOTICES](research-figure/THIRD_PARTY_NOTICES.md)。

## 本地贡献整合

PR #1 的分层 doctor、本地单点生图、协议 bundle 交接、位图/矢量机制图 SOP
保留并通用化。固定 Windows 路径、自动 `.env` 搜索和机器专用默认被移除。
单点生图明确要求 `--config`、`--allow-external`；provider/model、精确 prompt、
科学规范、候选图片哈希一起绑定，解决原生成器和 bundle 发射器字段/路径不一致。
不因本地回执或哈希一致就声称科研正确、用户批准或原生可编辑。

- [设计内核](research-figure/references/design-core.md)
- [版式素材库](research-figure/references/layout-library.md)
- [本地单点链路](research-figure/references/local-image-pipeline.md)
- [机制图八步 SOP](research-figure/references/mechanism-figure-workflow.md)
- [期刊机制图规范](research-figure/references/journal-mechanism-style.md)

## 验证与分发

```bash
python -m pip install -r research-figure/requirements-exchange.txt \
  -r research-figure/requirements-plot.txt -r research-figure/requirements-native-qa.txt
python research-figure/scripts/check_skill.py
python research-figure/scripts/upstreams.py verify
python research-figure/scripts/check_repository.py --root . --tracked
python -m unittest discover -s research-figure/tests -q
python research-figure/scripts/build_package.py --out /tmp/research-figure-0.8.0.zip
```

Provider 全流程另需设计内核声明的依赖和对应服务授权；单点 API 适配需 OpenAI
兼容 SDK，YAML 配置另需 PyYAML。版式 SVG/PPTX/VSDX 引擎使用 Python 标准库；
PDF/PNG 转换、PDF 审计使用其声明的可选转换器。实际模型能力由宿主核实。

测试使用明确标注的合成夹具与离线源码；不是科研结果或收费生图验收。
图库仅用于设计参考，不能当本研究观测数据。私有论文、凭证、实际产物、字体
文件及开发工作区不得进入公开仓库/安装包。GitHub 更新不自动替换旧客户端安装。
