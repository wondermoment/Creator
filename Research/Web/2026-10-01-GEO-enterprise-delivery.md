---
type: research
date: 2026-10-01
tags: [research, GEO, SEO, enterprise-delivery]
ai-first: true
confidence: medium
sources:
  - https://www.tryprofound.com/
  - https://www.scrunch.com/
  - https://peec.ai/
  - https://otterly.ai/
  - https://athenahq.ai/
  - https://ahrefs.com/brand-radar
  - https://github.com/elmohq/elmo
  - https://github.com/cangqiaoGEO/opengeo-platform
  - https://github.com/yaojingang/GEORank
  - https://github.com/Albert-Weasker/niubigeo
  - https://github.com/ai-search-guru/getcito-worlds-first-open-source-aio-aeo-or-geo-tool
  - https://github.com/Auriti-Labs/geo-optimizer-skill
  - https://github.com/StJudeWasHere/seonaut
  - https://github.com/unclecode/crawl4ai
  - https://github.com/DeepSeekGEO/deepseek-geo
  - https://github.com/lorin-code/ai-geo-monitoring
  - https://developers.google.com/search/docs/appearance/ai-features
---

## For future Claude
Research performed on 2026-10-01 for a team planning an enterprise GEO delivery system. Official product pages, GitHub READMEs, license files and selected repository trees were inspected; no systems were deployed or benchmarked. Product capabilities are vendor claims, and architectural recommendations are analyst judgments rather than measured performance rankings.

## 结论与范围

建议定位为企业 GEO 服务交付工作台：客户建档、基线诊断、问题库、AI 回答监测、引用分析、内容审核、发布记录、复测和验收报告。

- [[2026-10-01-GEO-enterprise-delivery#Elmo|Elmo]]：优先评估的国际引擎监测底座。
- [[2026-10-01-GEO-enterprise-delivery#OpenGEO|OpenGEO]]：中文引擎与内容交付流程的重点候选，但需要验证稳定性。
- [[2026-10-01-GEO-enterprise-delivery#GEORank|GEORank]]：中文诊断、售前方案和拓词工作台的参考。
- [[2026-10-01-GEO-enterprise-delivery#交付设计|交付设计]]：自研重点放在客户、任务、证据、验收和成本管理。

用户尚未明确国内或出海市场，因此保留两条路线。默认研究脚本只有 2/6 个来源返回结果，通用搜索覆盖不足；本报告主要依据随后直接读取的官方页面和 GitHub 资料，并非全市场穷尽调查。

## 商业产品

以下均为 2026-10-01 官方页面披露的功能，未登录付费后台验证；不采信其营销增长比例作为效果证据。

| 产品与来源 | 公开能力 | 对交付系统的参考价值 |
|---|---|---|
| [Profound](https://www.tryprofound.com/) | Answer Engine Insights、Prompt Volumes、Agent Analytics、Context Manager、营销与内容 Agents | 从监测、需求研究到内容执行的企业产品架构 |
| [Scrunch](https://www.scrunch.com/) | Monitoring & Citations、Agent Traffic、Site Optimization、Agent Pages | 把 AI 回答监测与网站可访问性、爬虫访问数据连接 |
| [Peec AI](https://peec.ai/) | Visibility、Position、Sentiment、问题管理、信源分析、API | 客户能读懂的监测看板、问题分组和竞品报告 |
| [Otterly.AI](https://otterly.ai/) | Prompt Research、AI Search Analytics、内容审计、优化建议、Agency 方案 | 研究、监测、内容诊断组成标准化服务包 |
| [AthenaHQ](https://athenahq.ai/) | AI 可见度、引用来源、内容缺口、行动建议、企业与机构方案 | 让诊断结果进入执行任务，而非停留在图表 |
| [Ahrefs Brand Radar](https://ahrefs.com/brand-radar) | 预采集 AI 可见度索引、Custom Prompts、品牌提及和引用、搜索需求关联 | SEO 与 GEO 的同一问题体系；区分行业索引和客户自定义样本 |

这些是产品设计与采购候选，不意味着可以买源码、可白标或可转售。API、导出、品牌数、采样频率、地区覆盖和代理商授权需要逐项核对，不能只比最低月费。

## Elmo

2026-10-01 核查：[elmohq/elmo](https://github.com/elmohq/elmo)，404 stars，最新推送 2026-09-29；[LICENSE.md](https://github.com/elmohq/elmo/blob/main/LICENSE.md) 实际为 MIT。统计只代表当天快照。

- README 提供品牌和问题管理、定时 worker、回答与引用来源、竞品比较、分享报告和 REST API。
- 技术栈包括 TypeScript、TanStack Start、PostgreSQL、Drizzle、pg-boss。
- 仓库树实际存在组织管理、报告 API、Provider 模块、跨租户测试文件；测试文件存在不等于测试已通过。
- 同时使用消费者界面采集供应商和直接模型 API，应分开显示两类结果。
- 推荐用途：自托管监测底座的第一轮 POC。白标、SSO 与托管套餐的边界应另行核查，不能从 MIT 推导全部商业配套都免费。

## OpenGEO

2026-10-01 核查：[cangqiaoGEO/opengeo-platform](https://github.com/cangqiaoGEO/opengeo-platform)，2 stars，最新推送 2026-09-25，MIT。

- README 明确它源自 Elmo；不是独立从零实现的第三套监测引擎。
- 在监测台之外增加 Studio：品牌事实库、素材、模板、内容生成、审核、导出发布包、发布 URL 回收。
- 中文接入声明包括火山方舟、DashScope、DeepSeek API、腾讯 TokenHub。API 接入不能直接证明其输出等于对应消费者 App，尤其应核对腾讯通道实际模型与元宝产品之间的关系。
- 仓库树能看到 Studio、中文 Provider、相关测试和租户模块；未实际调用验证。
- 推荐用途：国内交付流程原型的重点候选。优先核验中文来源提取、任务失败恢复、租户隔离、内容事实校验，以及跟进上游修复的机制。
- README 对是否继续跟进上游的表述并不完全一致，维护策略需要向维护者确认。

## GEORank

2026-10-01 核查：[yaojingang/GEORank](https://github.com/yaojingang/GEORank)，487 stars，最新推送 2026-09-16，软件 Apache-2.0。

- README 披露网站诊断、问答、30/60/90 天方案、拓词、JSON-LD、知识库草稿和后台管理。
- 技术栈是 Next.js/静态前端、FastAPI、Celery、PostgreSQL、Redis，并包含更多可选数据服务；前端处于静态版本与 Next.js 迁移并存阶段。
- 更适合售前诊断与方案工作台参考；不能由名称推断已实现完整的消费者 AI 排名追踪。
- [DATA_LICENSE.md](https://github.com/yaojingang/GEORank/blob/main/DATA_LICENSE.md) 对专家资料、商标、肖像和首页素材另有边界，软件许可证不等于素材授权。

## 其他开源候选

以下状态与许可证均按 2026-10-01 读取的信息记录。

| 项目 | 判断 | 关键边界 |
|---|---|---|
| [NiubiGEO](https://github.com/Albert-Weasker/niubigeo) | Apache-2.0；适合域名诊断、竞品发现、关键词测试、原始回答留证和定时测试 | README 明确为 Provider API 观测，非消费者聊天界面；完整竞品及关键词监测看板计划在 2026 年 10 月下旬，未包含于 v0.2.1 |
| [GetCito](https://github.com/ai-search-guru/getcito-worlds-first-open-source-aio-aeo-or-geo-tool) | 品牌、任务、引用、报告和白标功能候选 | 实际 LICENSE.md 声明为 Elmo 衍生作品、MIT；GitHub 自动识别为 NOASSERTION，不能只看徽标；应先与 Elmo 比较增量 |
| [geo-optimizer-skill](https://github.com/Auriti-Labs/geo-optimizer-skill) | MIT；CLI/Python/MCP 审计与部分引用测试，可嵌入诊断 worker | 主要衡量网站输入端准备度，工具评分不是 AI 推荐效果，不是完整企业 SaaS |
| [SEOnaut](https://github.com/StJudeWasHere/seonaut) | MIT；Go/MySQL，网站爬取、坏链、重定向、Meta、标题结构等审计 | 技术 SEO 模块，不替代 AI 回答监测 |
| [Crawl4AI](https://github.com/unclecode/crawl4ai) | Apache-2.0；官网和引用页面内容采集组件 | 爬虫基础组件，需要自建诊断规则、任务调度及交付界面 |
| [geo-aeo-tracker](https://github.com/danishashko/geo-aeo-tracker) | MIT；Next.js、多面板、Bright Data 采集，适合参考看板或演示 | 默认本地 IndexedDB，可选云同步；多 workspace 不能直接视为企业级租户隔离 |
| [Notra](https://github.com/usenotra/notra) | AGPL-3.0；监测、内容缺口、brief、API、流量 SDK 参考 | 修改后网络服务涉及 AGPL 义务；README 提示空数据库初始化有迁移边界 |
| [超算 GEO 前端](https://github.com/DeepSeekGEO/deepseek-geo) | MIT；中文管理台和浏览器插件模式参考 | README 明确仓库为前端源码，仍需托管或自建后端；不能认定完整系统已开源 |
| [ai-geo-monitoring](https://github.com/lorin-code/ai-geo-monitoring) | README 有 Next.js + Express、任务、会员额度、豆包与 DeepSeek 接入 | GitHub 元数据未识别许可证；需确认授权后再用于商业二开；名称不能证明与海外同名产品有关联 |

## 交付设计

本节为方案建议，不是上述项目现成功能的声明。

| 模块 | 必备能力 | 客户交付物 |
|---|---|---|
| 客户与品牌档案 | 组织隔离、角色、产品、地域、竞品、品牌别名 | 服务范围与目标清单 |
| 品牌事实库 | 官方参数、案例、证据 URL、审批人、有效期 | 审核通过的可引用事实资产 |
| 问题库 | 搜索意图、购买阶段、地区、平台、版本；品牌词与非品牌词分离 | 固定测评问题集 |
| 基线与复测 | 平台/渠道适配、调度、限流、重试、模型与搜索模式记录 | 原始回答、来源链接、采样条件和基线报告 |
| SEO/GEO 诊断 | 抓取、索引、网站结构、实体信息、内容缺口、引用页面分析 | 有优先级、负责人和验收条件的修复单 |
| 内容与发布 | 基于事实生成、人工审核、CMS 或人工发布、URL 与版本回收 | 内容包、发布台账、审核记录 |
| 报告与验收 | 固定问题复测、趋势、竞品、来源变化、执行记录 | 月度报告和可复查的证据包 |
| 经营管理 | 客户套餐、调用成本、工时、预算上限、续费提醒 | 项目利润与交付进度 |

建议的数据关系：客户 -> 品牌 -> 问题集版本 -> 采样运行 -> 原始回答 -> 提及/推荐/引用证据 -> 优化任务 -> 内容版本 -> 发布 URL -> 复测 -> 报告。

### 测量口径

- 品牌提及率 = 提及品牌的有效回答数 / 有效回答总数。
- 推荐率单独定义为明确推荐的有效回答占比；提到品牌不等于推荐。
- 自有域引用率 = 引用客户自有域的有效回答数 / 有效回答总数；另记第三方提到品牌的引用。
- SoV 可定义为品牌提及事件数 / 选定品牌与竞品的提及事件总数；在产品内固定去重与竞争集合口径，不能与提及率混用。
- 失败和超时不记作未提及；同时报告成功率、覆盖量和有效样本数。
- 保存问题、地区、语言、账号状态、渠道、模型版本、是否联网、时间；API、消费者网页/App 和人工采样分别统计。
- 对重点问题重复采样、按周聚合；单次排名或百分比波动不能直接宣称效果提升。
- 固定基线问题集，新增探索问题另外分组。前后对比是相关证据，不自动证明因果。
- 业务结果另看有来源标记的询盘、CRM 和可识别的引荐流量；无法完整识别所有 AI 带来的访问。

### 路线与 POC

出海优先：Elmo 监测 + SEOnaut/抓取组件 + 自研客户交付层。

国内优先：OpenGEO 做 POC、评估能否采用其中文适配和 Studio；以 Elmo 作为上游对照。若中文通道不能达到要求，则保留自建适配层并导入人工网页/App 抽样证据。GEORank 主要参考中文诊断与方案流程，不建议三套数据库和登录系统直接拼接。

建议先用 3 家同一行业客户做试点，每家约 50 个非品牌核心问题，选 2-3 个目标平台。跑通基线、修复、审核发布、复测、报告的一个周期，然后再决定是否做大规模 SaaS。

POC 必须验收：新环境部署、真实调用与引用解析、两个客户之间的数据隔离、限流失败重试、模型变更后的可比性、报告回溯原始证据、导出与恢复，以及单位客户实际成本。

成本计算采用调用数量而非只看 token：50 问题 × 3 平台 × 每天 1 次 × 30 天 = 4,500 次采样/客户/月；10 家即 45,000 次，重复 3 轮则 135,000 次，尚未计失败重试、搜索、内容抓取和分析。API 与网页采集应分别计价。

## SEO 与 GEO 的关系

2026-10-01 读取 [Google 官方 AI features 文档](https://developers.google.com/search/docs/appearance/ai-features)：SEO 最佳实践仍适用于 AI Overviews 和 AI Mode，没有额外特殊优化要求。该结论限于 Google 对其产品的说明，不能直接推广为所有平台的实现机制。

因此应先做好可抓取、可索引、准确的实体与产品信息、可靠证据和清晰内容结构。llms.txt 或某个自定评分只能是辅助检查，不能作为验收的最终效果指标。

## 待确认

- 首批客户以国内、出海还是双市场为主？目标行业是什么？
- 现有开发团队技术栈，以及客户数量和月度采样预算？
- 交付模式是内部代运营工作台、客户可登录 SaaS，还是客户私有化部署？
- 所有候选仍需运行验证；本次没有证明其线上 SLA、模型覆盖效果或安全性。
