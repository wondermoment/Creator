# 肝脏与APOE检测科普补齐

2026-10-05。本轮延续已完成12项检测图，新增两项，累计14/25。乔小乔四种姿势已完成，未重复生成。

## 内容与图片

肝脏评估：解释不同指标用途、症状和用药背景、综合判断；明确常规肝功能检查只是科普示例，不证明本套餐包含哪些项目，不把转氨酶读数当排毒能力评分。不自行停药、不推荐排毒补充剂。目录中“截图未列明”改为客户可理解的价值与范围介绍。

APOE：解释脂质运输、ε2/ε3/ε4、风险与诊断的区别；没有ε4也不能排除疾病，不能替代血脂或认知问题的临床评估。补充遗传咨询、知情同意、家族影响与数据使用问题，不按基因型自行用药。

两项各三段图解、两条快捷问题和官方来源传入现有咨询上下文。列表与详情共用新图；图片不是机构实际采样流程、个人结果或疗效证明。

本机Codex ChatGPT登录内置image_gen两次独立生成，无API Key；具体图像模型版本未核实。session 68030退出0，生成会话01a10bf9-6c25-7380-98cb-193a9da3f6af。技能读取子进程曾被策略阻止，未绕过；主会话已读取imagegen技能，后续原生生图成功。

- frontend/assets/testing/test-liver-science.webp
- frontend/assets/testing/test-apoe-science.webp
- 提示词：output/imagegen/testing-liver-apoe-prompt.txt
- 原始路径、尺寸和SHA256：output/imagegen/testing-liver-apoe-verified.json

原图均1254×1254，逐张目检标题、三栏和边界文字；仅转WebP，未拼接、重画或覆盖文字。肝图器官为简化示意，APOE图无确定发病预测或疗效承诺。

## 来源与验证

实际读取以下官方页面，均HTTP200；正文保留于output/testing-liver-apoe-{liver,apoe}-source-20261005.json。

- https://medlineplus.gov/lab-tests/liver-function-tests/
- https://medlineplus.gov/genetics/gene/apoe/

tests/testing-science.cjs通过：14个科普资源、25条目录/详情/咨询映射，来源、限制、费用未知及不承诺支付预约。tests/testing-chat-flow.cjs通过：25×7轮合成传输/DOM，来源和边界跨历史截断保留，快捷问题仅填草稿。两个JS文件语法检查通过。

浏览器375px窄屏两张图均naturalWidth1254，展示宽330px等于容器宽；document.scrollWidth360，未横溢。两项真实页面咨询来源正确、快捷问题填入输入框而未发送。无模型调用或用户记录写入。截图docs/testing-liver-20261005.png、testing-apoe-20261005.png；尺寸记录testing-liver-apoe-browser-20261005.json。临时视口已恢复。

index版本testing-science liver-apoe-5、testing-catalog science-4。不是医学专业审查或模型医学能力验收；本轮未新增真实问答，此前127.11秒模型延迟未改善。无重启、部署、外部消息、支付、既有用户数据修改。

## 剩余

剩11项检测图：chronic、nad、organic-acids、gut、oral、family、male、female、immune、environment、elements。实际套餐/机构/采样/费用核实、医学签核、身份权限、运行后台待加载、23本精准微信读书链接等既有阻塞继续保留。
