# 内容复用、SEO 与 GEO 开源参考核查

2026-10-03。通过 GitHub API 和固定提交原文研究，没有运行仓库安装器、复制整套后台、申请试用或调用第三方诊断服务。原文保存在 `outputs/github-reference-research/`。仓库描述不等于本机验证结果。

| 固定版本 | 许可及核查范围 | 采用 / 未采用 |
| --- | --- | --- |
| [AIWriteX](https://github.com/iniwap/AIWriteX/tree/1abed0cb47a0a8923a3e26470c139389ebc01998) | Apache-2.0；README，相关场景功能未实测 | 分场景、开篇、节奏、结尾；不采用阅读量承诺、规避检测、自动发布 |
| [autoclip](https://github.com/zhouxiaoka/autoclip/tree/ae87864fc36e87d137e2f161771dd4579fb1b920) | MIT；大纲、推荐理由提示原文 | 字幕主题分段与时间依据；未接下载/转录/剪辑，不把启发式分数当传播事实 |
| [youtube-digest](https://github.com/zarazhangrui/youtube-digest/tree/bb2f7b1aedb6b50c261c0cf35b0acc7ed631d833) | MIT；analysis 提示原文 | 覆盖全文开中结尾，短引语溯源；Supadata 未接入 |
| [MimicThem](https://github.com/zhanchey/MimicThem/tree/8e34b22492c8a188023abd7c33f989619a1c2db0) | 许可元数据缺失；README 的 MIT 与非商用说明有歧义 | 仅研究来源→分析→素材库流程，不复制代码或提示原文 |
| [SEOnaut](https://github.com/StJudeWasHere/seonaut/tree/880b312c28fab8b0bf7fe4f9449dc4746dbb82ff) | MIT；indexability.go、images.go | 问题证据/优先级/行动/复测；未集成全站爬虫，空 alt 需人工区分装饰图 |
| [marketingskills](https://github.com/coreyhaines31/marketingskills/tree/13c3832512b629bcf0226c99036ab434f53ff5b0) | MIT；seo-audit、ai-seo Skill | 搜索准入→技术→页面→内容及静态检查边界；不沿用无证据引擎规则或效果百分比 |
| [mmld-yuanbao-skill](https://github.com/dengyuanxing953-eng/mmld-yuanbao-skill/tree/a25b54f96845ed92aaa56a720cde0ab7f0b7e148) | MIT；SKILL.md | 第三方餐饮内容生成 Skill，不能认定为腾讯官方企业诊断；仅借鉴事实来源意识，不采用排名、重复关键词或数字配额 |
| [Chinese-Geo](https://github.com/qingqingpi/Chinese-Geo/tree/5b70b2052c5f461800d03ee9bc808f05e1bd832b) | MIT；monitor、audit Skill | 不带品牌的固定问题，App/API/网站证据分开；不套用分数阈值或增幅承诺 |
| [geo-skill](https://github.com/zen7-duze/geo-skill/tree/28554ca3c1d24908fcc92a3da71f1a709307ad5b) | Apache-2.0；vigilath-mention Skill | 原话、时间、失败透明；依赖外部 Vigilath 服务，未登录/领额度/充值，不能当成本地独立能力 |

## 本机落地与边界

- 爆款复刻：文章/字幕→模型八维拆解→短引语校验→企业方法库→标签/备注版本管理→专家引用。链接仅保存出处；时间码只有和引语同行时保留，SRT 跨行时间关联尚未实现。
- SEO：静态 HTML 八项检查→失败项加入清单→负责人和处理说明→同 URL 新检查通过才可验证。未检查收录、HTTP robots 响应头、全站、速度或脚本渲染。
- GEO：仅基于本企业人工录入回答分析，人工来源未自动核验；示例与 API 观测不混入。
- 外部内容不成为企业事实或操作指令。实现独立编写，外部原文只归档研究。

## 设计决策

沿用现有蓝白企业界面，使用 Refero 的研究先行与交互细节方法，未调用在线 Refero 服务。主线采用用户指定流程：输入和下一步并列、分析后入库、任务靠近证据、无证据不填假分数。保留算力充值入口并如实标明计费待接入。
