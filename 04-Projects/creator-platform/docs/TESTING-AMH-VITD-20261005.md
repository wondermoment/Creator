# AMH与维生素D检测科普及咨询

日期：2026-10-05。本轮只补 test-amh、test-vitd 两项检测科普图与解释；原小乔姿势、营养素维生素D图及前8项检测图不重复生成。

## 内容依据

实际读取 MedlinePlus 官方两篇科普，HTTP200，抓取保存在 output/testing-hormone-{amh,vitamin-d}-source-20261005.json：

- https://medlineplus.gov/lab-tests/anti-mullerian-hormone-test/ ：AMH与卵巢储备、辅助生殖反应的关系；不能表示卵子质量、单独预测受孕、准确预测绝经时间或独立诊断PCOS。
- https://medlineplus.gov/lab-tests/vitamin-d-test/ ：常规状态评估使用25(OH)D，与活性维生素D用途不同；并非人人需要常规筛查，过量补充有风险，说明现有用药但不自行停药。

采用中文原创摘要，不复制文章全文到客户端。每项三段图解、解释边界及咨询问题随详情和客服上下文传递。AMH目录原名“卵巢年龄评估”保留为供应目录名称，正文明确其不是卵巢年龄计算器。

## 图像与互动

imagegen技能，本机Codex ChatGPT登录原生image_gen，一图一调用，无API Key/付费图像API/拼接替代。提示词 output/imagegen/testing-amh-vitd-prompt.txt，日志 testing-amh-vitd-result.txt，进程session42150。图像模型具体版本未核实，不能宣称已核实GPT Image2。

检测咨询中有已核对来源的项目展示可展开来源；两个新项目分别提供2条快捷问题，只填草稿，不自动发送。来源标明公开科普、核对日期与非实时检索。换到其他服务不沿用上一检测的来源或问题。

## 本轮局限与运行记录

仅合成传输/DOM自动测试，不新增真实模型对话；最近真实模型案例为MTHFR，127.11秒，不能推广为AMH/维D已真实验收。无医学专业签核，无法解除聊天延迟、机构资质、真实价格/采样范围、支付/预约及数据权限阻塞。没有重启后端、发布、真实支付、外部消息或改动用户记录。

抓取先遇Windows stdout GBK无法显示一个Unicode空格，改为UTF-8后读取已缓存的AMH结果，没有重抓；维D一次TLS连接中断，正常重试HTTP200，未关闭TLS校验。初次合并补丁因目标行不完整未应用，改为精确匹配后成功。生成子进程读取技能文件被策略拒绝，主流程已读取技能，未绕策略，原生工具继续生成。

## 完成与验证

生成进程42150退出0，不重跑。两张1254×1254原生图已逐张目检，仅转换WebP、无裁切拼接。AMH卵泡周围细胞与血样/综合评估、维D的25(OH)D标签和背景器官均作简化科普；仍需专业审阅。来源manifest：output/imagegen/testing-amh-vitd-verified.json。

资产：frontend/assets/testing/test-amh-science.webp、test-vitd-science.webp。testing-science.js追加两项，index版本amh-vitd-3；customer-service.js加可见来源与快捷草稿，版本testing-sources-7。现10/25检测新科普图完成，15项待绘。

验证结果：
- tests/testing-science.cjs通过10图、25目录/详情/上下文及新AMH/维D解释边界。
- 新增tests/testing-chat-flow.cjs通过25项×7轮，超过历史截断窗口仍保留每项名称/解释/局限/来源、价格未知与急症提示；验证显示来源、快捷问题仅填草稿和切换其他咨询时不残留上个项目内容。回复由合成传输返回，不能当真实模型能力测试。
- tests/service-chat.cjs价格/路由回归与两文件JS语法通过。
- 浏览器两图complete=true、naturalWidth1254；360×640视口图片与容器均315px，document宽和scroll宽均345，无横溢。记录testing-amh-vitd-browser-20261005.json，截图testing-vitd-20261005.png。
- 维D咨询快捷问题填入文本框，chatQuestions=0，无自动提交。展开MedlinePlus来源链接及非实时检索说明。资料展开后对话框内容需纵向滚动（scrollHeight772/clientHeight574），键盘移到发送按钮后scrollTop198，发送底部583<640，可以访问；不把需要滚动描述为全部内容首屏可见。截图testing-sources-chat-20261005.png与testing-chat-input-20261005.png。没有点击发送，临时视口已恢复。

来源读取与绘图是真实操作；本轮对话测试仅合成自动测试，未调用真实问答模型，不改变之前127秒延迟结论。
