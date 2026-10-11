# 遗传检测四项科普图与咨询证据

日期：2026-10-05。本轮范围：全外显子、全基因组、酒精代谢、MTHFR 四项；原小乔四姿势等已完成资产不重复生成。

## 内容与来源

本轮实际读取以下官方资料（HTTP 200），本机抓取留存在 output/testing-genetics-{sequencing,alcohol,mthfr}-20261005.json：

- MedlinePlus：https://medlineplus.gov/genetics/understanding/testing/sequencing/ 。编码区与更广测序范围的区别、意义未明变异、次要发现和检测局限。
- NIAAA：https://www.niaaa.nih.gov/publications/alcohol-flush-reaction 。ADH/ALDH、乙醛代谢、潮红及用药压住症状不能消除伤害。
- CDC：https://www.cdc.gov/folic-acid/data-research/mthfr/index.html 。常见 MTHFR 变异仍可利用普通叶酸，不能凭基因型判定缺乏或自行加量；罕见变异另行专业评估。

各项目三段中文图解、咨询问题和来源摘要，供详情与智能客服使用。图中条带、波形、报告及隐私锁为科普示意，不是患者数据、实验室实际流程或平台数据安全认证。

## 真实模型合成测试

docs/TESTING-MTHFR-LIVE-20261005.json 保存完整问题、真实上下文和回答。输入为虚构备孕成年人 MTHFR 677TT 案例，无真实个人信息，不向用户书库或记录写入数据。

通过现有本机 /api/coaches/qiao/chat 返回，127.11 秒。模型正确否定“不能利用普通叶酸、必须停医生方案、购买高剂量甲基叶酸”，未给个体剂量，建议由产科医生结合情况评估，附正确 CDC 链接；明确本轮回答依据提供摘要，没有实时核验网页。结果只覆盖此单个案例，不能代替全面医疗边界测试或专业签核。时延仍不合格。

## 图像任务与验收

使用已读取的 imagegen 技能，通过本机 ChatGPT 登录的内置 image_gen 请求四次独立方图，无付费 API Key。提示词 output/imagegen/testing-genetics-prompt.txt，日志 testing-genetics-result.txt，任务 session64334。具体图像模型版本尚未核实，不宣称已验证 GPT Image2。子进程读取技能文件被策略拒绝，主流程已读技能；未绕过策略，原生工具继续执行。

生成任务 session64334 已退出 0，不重复运行。四张原生 1254×1254 方图均已逐张检查中文、示意内容和局限提示，仅转换 WebP，没有裁切或拼接。输出路径、核对说明见 output/imagegen/testing-genetics-verified.json。

最终资产：frontend/assets/testing/test-{exome,genome,alcohol,mthfr}-science.webp。frontend/testing-science.js 接入四项解释与官方来源；index 缓存版本 genetics-2。检测科普新图累计 8/25，其余 17 项仍使用旧主题图，不能称全目录重绘完成。

## 验证结果

- tests/testing-science.cjs：8 项图解与图片、25 项详情/咨询上下文、来源保留、价格未知和无付款预约承诺通过。补充 MTHFR 普通叶酸与加量边界、意义未明变异、隐私锁和安全饮酒量检查。
- tests/service-chat.cjs：门诊/硬件/检测咨询路由及未确认价格保护回归通过；JS 语法通过。
- 最终实际 openServiceChat 生成的 MTHFR 上下文与真实模型测试使用的 980 字上下文逐字相同。
- 浏览器四页图片均 complete=true、naturalWidth=1254；360px 视口下图片与容器同为315px，页面 clientWidth/scrollWidth 均345，无横向溢出；来源链接正确。原始记录 docs/testing-genetics-browser-20261005.json，截图 docs/testing-genetics-mthfr-20261005.png。
- MTHFR“预约了解详情”打开小乔智能客服，主题正确，有输入框和发送按钮；未在浏览器实际提交问题。临时视口已恢复。

未重启后端、部署、付款、发外部消息或改变已有用户记录。内容与插画仍需医学专业审阅；上述自动检查、单例真实问答不构成专家认证。商户配置、检测服务真实范围、图片商业使用条件、模型时延、权限与服务端生命周期阻塞继续保留。
