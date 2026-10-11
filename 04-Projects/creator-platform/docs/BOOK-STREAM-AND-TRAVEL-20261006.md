# 书籍流式正文与旅行结尾 · 2026-10-06

## 用户要求与实现

用户反馈等待17秒仍无正文；随后要求门诊等详情末尾加之前同款back top，并删除截图的“继续阅读官方资料”及资料状态说明。两项已分别完成。

书籍无原文主题交流新增POST /api/coaches/{coach}/chat/stream，通过本机官方Codex app-server stdio协议读取item/agentMessage/delta，NDJSON实时交给前端；不再等整段回答结束才渲染。仍用既有ChatGPT登录/HTTPS provider，无API Key。根据官方文档 https://developers.openai.com/codex/app-server 及本机CLI生成的schema核对字段；初次试验因app-server不支持exec专有的ignore参数失败，修正后成功，未改变用户全局配置。app-server接口属实验性，版本兼容需要回归。

thread/start使用ephemeral、只读sandbox、禁止审批、禁用工具的配置，baseInstructions承载完整既有coach policy，替换无关编程说明；非system历史仍以user数据传入。没有削减医学安全政策，也未换模型或购买优先服务。每请求独立子进程，共用原单实例模型并发槽；结束/失败/断连/超时均尝试终止自有进程树并释放槽。没有常驻跨用户上下文。前端只展示正文delta，不展示reasoning；明确done才提交历史，断流/失败恢复问题，部分正文不作为完成结果。原文问答仍保持原接口与引用核验，不提前暴露未经引用校验的答案；其他教练前端暂未切换流式。

新增local_codex_stream.py、chat-stream.js；coach_chat抽出build_messages使两个接口共用安全上下文。book-reader stream19、chat-stream1。用户先前已授权本地重启，受控停止核验过的旧uvicorn29476，新PID50132监听127.0.0.1:8765，日志.runtime/server-stream-20261006*.log，已实际返回新流式请求。

旅行：抽出travelBackTop共用原小箭头文字按钮，所有门诊及酒店详情结尾复用，目的地原入口仍在。按用户要求仅从门诊正文移除clinicSources展示及c.status段，来源数据仍保留用于编辑核对与咨询上下文；未移除具体医学限制和图片来源。版本travel shared-top6、clinics footer-top5、hotels footer-top20261006。

## 真实验证

- 独立原生流式合成科普问题：7.710秒收到首个文字，10.383秒完成，STREAM-PROBE-20261006.json。
- 完整当前HTTP书籍主题接口，合成《长寿奇点》“最牛观点”：8.166秒首个可见文字，12.240秒完整返回，128个事件；BOOK-STREAM-HTTP-20261006.json保留逐事件时间。采用真实模型，非缓存或模拟。与此前39.048秒不同请求配置/一次样本不可当严格基准或稳定P95，只证明当前真实流式链路可用。
- 真实浏览器一键发送“最牛观点”，日志确认新/stream接口200，正文正确分段/加粗，无裸列表符号；book-stream-live-20261006.png。首次DOM检查已在31.373秒且完成，浏览器本身没有精确捕获首字，因此首字数据引用上述HTTP测试。
- 用户门诊标签已刷新，资料区数量0、back top数量1；门诊及Kamalaya酒店点击后travel-detail.top=0。同款按钮没有额外大容器。截图clinic-clean-footer-20261006.png。第一次立即读位置在平滑滚动中仍为负值，等待后确认0；酒店标题定位初次因名称不是“Kamalaya”精确匹配超时，DOM确认“Kamalaya 苏梅岛”及top=0。

## 自动检查与局限

12项后端：流式4项（增量/完成、完整政策、临时线程、工具拒绝、异常编码、取消释放、HTTP完成/错误/404），既有coach/context/concurrency8项。前端chat-stream验证跨块UTF8、增量与明确完成、断流/错误拒绝；书籍异步、上传异步回归通过。门诊4路/8种咨询上下文检查按用户删除展示更新，来源仍在咨询上下文。相关JS语法通过。

单样本速度不是全体问答承诺；仍需负载/P95、原文流式的保存前证据校验方案及更多真实医疗边界验证。没有真实用户资料/支付/外部部署/消息发送。AI自动验证不是医学专业认证。既有权限、商户、授权、专业签核等上线阻塞仍在。
