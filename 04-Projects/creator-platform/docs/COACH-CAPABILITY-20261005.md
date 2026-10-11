# 研究知识库与教练能力边界验证 · 2026-10-05

## 本轮交付
- 正念教练专项流程从旧“生成作品/海报影片”转为短时觉察、自然呼吸、睁眼替代和日记文字草稿；允许退出与转交，不强迫感恩、闭眼、深呼吸或回忆创伤。
- 七教练每轮上下文明确当前只有文字回复能力，不能声称已经保存、计时、导出媒体、预约或购买；界面快捷提问只填草稿。
- frontend/skill-quality.js、coach-chat.js及后台coach_knowledge.json同步；后台未重启，运行实例仍可能含旧系统任务。前端上下文已带新任务，后台生效不能冒称完成。

## 验证
- tests/coach-skill-flow.cjs：实际7教练×6轮，路由、完整专项任务、能力边界保留及快捷提问不自动发送，通过。
- tests/research-chat-flow.cjs：4研究者×6轮，来源摘要及分析框架保留，通过。
- coach-async、skills.test通过，均为合成回归，无真实用户数据改变。
- 实际本机模型：RESEARCH-KNOWLEDGE-LIVE-20261005.json。Sinclair误导问题“NMN恢复视力”收到正确区分小鼠OSK研究与口服NMN、动物与人体证据，引用真实DOI，明确未检索全文。135.0秒。只证明此单例，不代表全面医学/引用评估。

## 延迟诊断与失败
- 既有原生日志nutrient-science-result.txt记录连续5次重连后“Falling back from WebSockets to HTTPS transport. request timed out”。是明确延迟线索，不证明所有时延都来自传输。
- 读取当前CLI features list，responses_websockets/v2均标removed，不尝试已移除开关。
- 官方main配置schema含ModelProviderInfo.supports_websockets。单次隔离诊断尝试model_providers.openai.supports_websockets=false，CLI在0.27秒拒绝：内置provider ID不可覆盖。没有模型结果，RESEARCH-TRANSPORT-TEST-20261005.json记录。
- 未修改配置、provider、认证、网络安全或审批参数；未绕过校验，未重启服务。当前CLI版本的受支持传输控制仍待确认。

## 后续
需继续浏览器验收快捷提问/来源展示、更多真实模型场景、响应延迟处理和后台加载一致性。其他内容欠项以HANDOFF-LATEST末尾为准，不重复生成已完成图片。
