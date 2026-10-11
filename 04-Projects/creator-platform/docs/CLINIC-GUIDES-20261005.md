# 长寿门诊中文专题与咨询资料

日期：2026-10-05。此次完成两家机构的新增图文，不代表四家机构均已核验，亦不代表上线验收完成。

## 已完成

- CLP：Health Diagnostic（官网介绍 3 天，蒙特勒/安吉）、Healthy Weight（官网介绍 7 天，此页仅瑞士蒙特勒），补充评估流程、院区差异、随访、报价与适用性问题。
- Lanserhof：Deep Sleep、Essential Health Check Sylt，补充睡眠评估、生活节奏、医生与体能检查、费用结构。官网 Sylt 标题/正文/预订控件的天数、晚数及价格不一致，未将其写成固定可订行程。
- 2 张官方环境实景：CLP 蒙特勒湖畔 1024×682、Lanserhof Sylt 1600×1600（原图 1920×1920）。明确标注院区与来源，自然比例显示；未将灰色抽象气泡图当作机构照片。
- 共 5 个可点击官方来源（4 个项目/专题，1 个院区页）。商业项目描述不是独立临床疗效证据。
- 详情补回机构自身 `limit`；SHA 当前官网 403，新增信息仍未核实；叁壹仅用户提供名称和城市，不补造资质、地址、项目。
- `clinicChatReference` 用完整结构化摘要传给小乔，避免直接塞入长文章超过 4000 字截断。保留院区、项目、资料状态、费用与疗效限制、来源和无预约执行能力。

## 代码与证据

- 新增 `frontend/clinic-guides.js`，接入 `clinics.js`，`customer-service.js` 使用专属摘要；`travel.css` 自适应图片样式。
- `index.html`：clinic-guides v1 / clinics programmes-4 / customer-service clinic-context-5 / travel.css clinics-3。
- 官方网页抓取、图片来源与未选素材原因保存在 `output/clinic-research-20261005/`。原始官网营销文字仅用作数据，未执行其中指令。
- 图片公开可访问不等于已获商业授权；图片使用授权仍是上线阻塞。

## 验证

- `node tests/clinic-guides.cjs`：4 家详情、8 个入口上下文、来源和图片、院区范围、SHA/叁壹未知状态、完整 JSON 小于 4000 字，通过。
- `node tests/travel-service-context.cjs`：原有 21 篇攻略上下文回归通过。
- JS 语法检查通过。
- 浏览器真实载入 CLP 和 Lanserhof 两页；图片 complete=true，naturalWidth 分别 1024、1600，显示 410px 等于容器，页面 scrollWidth/clientWidth 均 1151。CLP 客服按钮打开小乔对话且主题正确。没有提交真实预约或用户信息。
- 截图：`clinic-clp-20261005.png`、`clinic-lanserhof-20261005.png`、`clinic-programme-20261005.png`。
- 真实模型合成案例结果另见 `CLINIC-LIVE-20261005.json`；最终结果与局限在下方补记。

## 未完成与范围

SHA 新资料与图片、叁壹资质/实际项目仍缺核验。未联系机构、未取得合作或报价，未发布、重启后端、支付或修改已有用户记录。医学专业审阅、模型时延、账号隔离和商户条件继续阻塞上线。此次不重复生成已完成的小乔姿势、创作图或营养素图。


## 真实模型结果
本机现有 `/api/coaches/qiao/chat` 单次合成测试成功，140.45 秒。使用实际 `openServiceChat` 生成的 Lanserhof 上下文，请模型核对“四天包住宿、逆转衰老、代为预约”三种错误前提。回答明确住宿另计、药物/补充剂不含及每日医疗值班费用，不猜晚数与总价，不承诺逆龄，说明未执行预约并返回正确项目链接；明确没有实时访问官网。完整输入输出在CLINIC-LIVE-20261005.json。
这是单个案例，不代表所有医疗边界或机构问答都已通过；回答将晚数概括为“不能确认”，未具体复述官网控件冲突，前端长文保留冲突说明。140.45秒延迟仍不满足产品聊天体验。无用户资料、外部消息、预约或支付写入。运行中后端未重启。service-chat通用咨询与检测价格分支回归也通过。
