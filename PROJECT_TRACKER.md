# 项目跟踪（Project Tracker）

> 这是本项目的长期记忆文档。请持续更新，记录目标、方案、进展、重复问题与解决方案。

## 当前目标（Now）
- 建立近 3 年 Nature/Science/Cell 论文清单与 DOI 索引。
- 扩展到 CNS 全刊与 Nature 子刊的论文清单与 DOI 索引。
- 形成 GitHub 发现与筛选规则（能找到 figure 作图代码）。
- 定义图类型 taxonomy 与数据库字段。

## 方案摘要（Plan Snapshot）
- 数据获取：期刊官网/聚合数据库拉取论文列表。
- 仓库发现：论文页面、补充材料、README、Issue、引用等线索。
- 代码筛选：优先包含 figure 生成脚本、绘图配置或复现说明的仓库。
- 数据入库：结构化字段统一，记录可复现性与样式信息。
- 技能/多智能体：检索 -> 选型 -> 复用代码 -> 统一样式 -> 输出。

## 数据源与抓取策略（Sources & Harvesting）
- 期刊官网：按年/卷/期抓取论文目录与 DOI。
- Crossref：按期刊与年份批量拉取 DOI 与元数据。
- OpenAlex：补充论文元数据与外部链接。
- GitHub 发现：论文页面、补充材料、README、Issue、引用文献、作者主页。
- 规则：优先标注含 `fig`/`figure`/`plot`/`visualization` 的仓库或脚本。

## 进展记录（Progress Log）
- 2026-03-17：初始化跟踪文档与设计蓝图。
- 2026-03-17：新增图类型 taxonomy 初稿与数据库 MVP 结构。
- 2026-03-17：新增统一风格指南与技能/多智能体流程文档。
- 2026-03-17：新增论文清单抓取脚本与抓取计划文档。
- 2026-03-17：新增 GitHub 发现与可复现性判定细则文档。
- 2026-03-17：新增统一配色与字体配置表。
- 2026-03-17：完成 Crossref 三刊论文清单抓取并生成仓库发现样例表。
- 2026-03-17：新增可复现性验证模板（Markdown+CSV）。
- 2026-03-17：完成首批 18 篇论文的在线检索，更新 GitHub 链接与状态标注。
- 2026-03-17：新增 Nature.com 期刊索引解析脚本与 Nature 子刊列表（含系列分类）。
- 2026-03-17：从 Nature Portfolio 期刊指标页面提取 2024 JIF，生成 IF>10 子刊清单，并启动 Crossref 批量抓取。
- 2026-03-17：完成 IF>10 Nature 子刊 Crossref 抓取 54/63，本轮缺失期刊：
  Nature Sustainability；npj Clean Water；npj Computational Materials；
  npj Digital Medicine；npj Flexible Electronics。
- 2026-03-17：完成 CNS（Nature/Science/Cell）近三年 12,959 篇论文批量页面抓取与可用性标注，队列 pending=0；新增 `code_availability` 字段与 `github_found_web/code_available_non_github/no_code_availability_found/fetch_failed` 状态。
- 2026-03-17：启动 IF>10 Nature 子刊近三年批量页面抓取（后台任务，日志见 `logs/nature_if_gt10_scan.log`）。
- 2026-03-17：暂停子刊抓取，切换到 CNS GitHub 仓库的 figure 代码与图像抽取（脚本：`scripts/github_figure_miner.py`，日志：`logs/cns_github_figure_miner.log`）。
- 2026-03-17：完成 CNS 成功仓库的 figure 文件规范化与自动分类，生成初版数据库 `data/metadata/cns_figure_db.csv` 与类型统计 `data/metadata/cns_figure_type_summary.csv`。
- 2026-03-17：细分图类型分类规则，新增 L1/L2 类别并消除 `Other/Uncategorized`；拆分 CNS 数据库为 `papers/repositories/figures/scripts/outputs` 五张表（`data/metadata/cns_tables/`）。
- 2026-03-17：生成脚本-图像启发式匹配表 `data/metadata/cns_tables/script_output_links.csv`，并建立可复现性队列 `data/metadata/reproducibility_queue.csv`（状态 pending）。
- 2026-03-17：静态富集可复现性队列，填充依赖文件与运行命令（`ready_for_run=2020`，`needs_manual=288`）。
- 2026-03-17：启动 CNS 复现批量执行（后台运行 `scripts/run_reproducibility_queue.py`）。
- 2026-03-17：增强脚本-图像匹配规则（结合 README 与日志关键词），重建 `script_output_links.csv`。
- 2026-03-17：新增复现失败修复队列生成器 `scripts/build_failure_fix_queue.py` 与修复手册 `docs/repro_failure_playbook.md`。
- 2026-03-17：新增统一风格 wrapper（Python/R/Matlab）与 styled 队列 `data/metadata/reproducibility_queue_styled.csv`。
- 2026-03-17：新增最小 CLI（`scripts/pfc_cli.py`）用于 figure 类型推荐与 styled 渲染。
- 2026-03-17：新增增量更新与回归脚本（`scripts/run_incremental_update.sh`、`scripts/run_reproducibility_regression.sh`）。
- 2026-03-17：新增并启用并行复现执行器 `scripts/run_reproducibility_queue_parallel.py`（支持批量刷写进度）。
- 2026-03-18：运行自动修复与依赖补齐（`scripts/apply_auto_fixes.py`、`scripts/install_missing_python_deps.py`），更新复现队列与失败修复队列。
- 2026-03-18：新增脚本内输出路径提取规则，增强脚本-图像映射评分，重建 `data/metadata/cns_tables/script_output_links.csv`。
- 2026-03-18：新增失败日志解析脚本 `scripts/analyze_failure_logs.py`，生成细分失败统计 `data/metadata/repro_failure_detail_summary.csv`。
- 2026-03-18：缺失依赖自动安装后，复现成功数从 122 提升至 125，并将可重试项批量重跑（`scripts/mark_ready_after_dep_install.py`）。
- 2026-03-18：新增 nbconvert 自动补全 `--to` 选项与含空格/括号路径自动加引号规则（`scripts/apply_auto_fixes.py`），并对相关失败项进行重跑。
- 2026-03-19：使用 GitHub 全量压缩包恢复 AutoMorph 完整仓库，修复离线权重下载与多进程权限问题，CPU 跑通完整流程并生成 `Results/` 输出。
- 2026-03-19：将 AutoMorph 输出文件追加进 `data/metadata/cns_repo_figure_files.csv` 并重建 `cns_figure_db.csv` 与 `cns_figure_type_summary.csv`。
- 2026-03-19：重建 CNS 规范化表（`data/metadata/cns_tables/`）以包含 AutoMorph outputs。

## 重复问题与解决方案（Recurring Issues & Fixes）
- 待记录。

## 决策与假设（Decisions & Assumptions）
- 仅收集公开 GitHub 仓库。
- 以“能复现 figure”为筛选标准。

## 待办（Next Actions）
- 基于样例表补充 GitHub 仓库链接（若 Crossref 未提供）。
- 按样例表挑选可复现的 figure 代码并录入数据库。
- 运行 OpenAlex 补充元数据（需要 API key）。
- 使用 Nature 子刊列表与批量抓取脚本扩展 Crossref 数据。

## 更新规则
- 每次新增数据源、变更流程、修复问题后，都在“进展记录”与“重复问题与解决方案”中更新。
- 用简洁短句描述，避免冗长叙述。
