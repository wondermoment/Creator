# 激素相关检测科普图与咨询资料

日期：2026-10-05。本轮范围test-stress、test-estrogen，补足现有15项缺图中的两项，不重复已完成的小乔与检测资产。

## 来源与内容边界

实际读取MedlinePlus两篇官方科普（HTTP200）：
- https://medlineplus.gov/lab-tests/cortisol-test/ ：皮质醇的昼夜变化、不同样本/采样安排、压力运动用药影响及单一检测不足以确定异常原因。
- https://medlineplus.gov/lab-tests/estrogen-levels-test/ ：E1/E2/E3、不同生理阶段与检测目的、用药告知和不自行停药。

抓取文件output/testing-endocrine-{cortisol,estrogen}-source-20261005.json。客户端使用原创中文摘要，非全文复制。特别区分普通激素科普和未核实套餐：皮质醇仅是例子，不代表目录“抗压力荷尔蒙评估”确认包含它；E1/E2/E3不是目录“雌激素代谢分析”的已核实清单，激素水平和代谢物/比值不是同一回事。来源不作为排毒、疗效或套餐临床价值认证。

## 生成与计划验证

已使用imagegen技能，通过本机Codex ChatGPT登录请求内置image_gen各生成独立方图，禁止付费API Key、拼接或SVG代替原生生成。提示词output/imagegen/testing-endocrine-prompt.txt，生成日志testing-endocrine-result.txt，进程81935。具体图像模型版本未验证，不宣称GPT Image2已核实。

图片拟在目检后以新文件接入测试列表与详情；三段图解、来源、局限和两条快捷问题随客服咨询保留。最终资产与验证待下方补记，不能把启动任务当已完成。

本轮不新增真实问答模型调用：前几轮真实问答已有约127秒时延证据，重复相同测试不会解决延迟。本轮自动交互测试使用合成数据，不是医学专业签核。无重启、部署、付款、外部消息或真实用户数据修改。

## 完成与验收

生成任务81935退出0，不重复运行。两张独立1254×1254方图均逐张目检，中文标签正确；压力图页脚多一个句号，不影响语义，未为此重绘。压力曲线只表变化、不表达具体峰值或参考范围；雌激素图E1/E2/E3为水平检测例子，不是代谢通路。主流程已读取技能；生成子进程读取技能文件被策略拒绝，未改变策略，内置图像工具仍完成。具体模型版本仍未核实。

仅转WebP，无裁切/拼接。资产frontend/assets/testing/test-stress-science.webp、test-estrogen-science.webp；原生文件路径与检查说明output/imagegen/testing-endocrine-verified.json。testing-science.js新增两项图解/来源/快捷问题；index版本endocrine-4，客服已有机制直接承接，无需后端重启。

自动验证：testing-science通过12图、25目录/详情/咨询上下文，新增确认“皮质醇只是例子”“来源不验证代谢物套餐”及不自行骤停/调激素。testing-chat-flow 25×7轮合成传输测试通过，来源和局限超过历史窗口仍保留，快捷不自动发送；JS语法通过。不是175次真实模型问答。

浏览器：两图complete=true、naturalWidth1254，360×780视口下图片/容器均315px，document宽/scroll宽均345，无横溢；来源链接正确。雌激素咨询窗口主题正确，快捷“正在用激素，检测前需要自行停药吗？”只填草稿、chatQuestions=0；展开来源显示MedlinePlus及非实时检索。无发送，临时视口已恢复。记录testing-endocrine-browser-20261005.json，截图testing-endocrine-20261005.png。

现累计12/25检测新图完成，余13：chronic、nad、organic-acids、gut、oral、family、apoe、male、female、liver、immune、environment、elements（均test-前缀）。套餐采样/指标/资质/价格未核实、医学审阅、模型时延和权限等上线阻塞未解除。
