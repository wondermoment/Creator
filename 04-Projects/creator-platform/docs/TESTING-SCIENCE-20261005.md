# 检测科普图重绘：首批四项

日期：2026-10-05。用户要求图铺满版面并增强科普感；原25项用9种通用主题图，本轮选择端粒、甲基化年龄、食物IgG、食物IgE，生成4张独立原理科普图。其余21项继续原主题图，不能称全目录已重绘。

## 生成与内容

使用imagegen技能和本机Codex ChatGPT登录内置image_gen，一图一调用，无付费API Key。提示词output/imagegen/testing-science-prompt.txt；生成日志testing-science-result.txt；来源与尺寸逐项记录testing-science-verified.json。具体图像模型版本无法从结果确认，不宣称已核实GPT Image2。图片包含三组科普视角，不是实际机构采样流程、真实病例或疗效数据，不是拼接替代生成。

配套testing-science.js给每图三段解读及咨询问题，保留指标局限；IgG尤其说明不能用于过敏/不耐受诊断，不按阳性表忌口。IgE说明需结合反应史，不能自行食物激发；急症先联系当地急救。

已实际读取AAAAI官方《The Myth of IgG Food Panel Testing》，HTTP200，原文抓取output/testing-science-source-20261005.json。来源：https://www.aaaai.org/tools-for-the-public/conditions-library/allergies/igg-food-test 。说明IgG可为接触正常反应，IgG4可与耐受相关，不建议用IgG诊断食物过敏或不耐受。该来源随详情和客服上下文传递，无实时检索或已读书籍全文声明。

原图不覆盖，新增*-science.webp。最终页面整合、浏览器验收与测试结果在下方补记。

## 局限

图片与科普仍需专业审阅；本轮不改变检测资质、机构与价格待核实状态，不开通购买或预约。不进行真实付款、发消息、重启后端或修改用户记录。绘图是真实生成，客服问答回归为合成请求；不把它们当医学认证或真实问答提速。原小乔四姿势、创作图及营养素图已完成，不重复生成。


## 完成与验收

绘图任务session9664退出0，四张均1254×1254，全部目检并转换WebP（仅格式转换，无裁切/拼接）。原生来源保留在testing-science-verified.json；不要重跑已完成任务。

最终资产：
- frontend/assets/testing/test-telomere-science.webp
- frontend/assets/testing/test-methylation-science.webp
- frontend/assets/testing/test-igg-science.webp
- frontend/assets/testing/test-ige-science.webp

集成：testingArtwork按ID使用4张新图，列表/详情统一宽100%、自然高度、contain；其余主题图保留。alt与图下注明局限，详情有三段图解和咨询问题；IgG追加AAAAI来源链接。customer-service检测上下文加入相同解释和来源，价格未知状态及未开通购买/预约能力保持。

版本：testing-science v1、testing-catalog science-3、customer-service testing-science-6。

自动测试：tests/testing-science.cjs检验25目录/详情/咨询上下文（完整JSON<4000字符）、4图文件与三段解释、IgG来源保留、价格不外泄、无付款承诺。service-chat、clinic-guides、travel-service-context回归通过，JS语法通过。首次整合脚本引号语法错误，图片尚未接入时新测试正确失败；修正脚本后通过，不是图生成失败。

浏览器：四页均complete=true、naturalWidth1254，360px视口下实际内容315px等于父容器。IgG/IgE document宽与scroll宽均345，无横向溢出；IgG预约了解详情进入小乔智能客服且主题正确。截图testing-science-igg-20261005.png、testing-science-ige-20261005.png。临时视口已恢复，没有发送问题/购买/预约记录。

本轮4次真实原生绘图；没有新增客服真实模型对话，自动测试不能替代问答端到端或医学审阅。生成子进程读取其技能文件曾被策略拒绝；主流程已读取本机技能，未修改策略，内置绘图继续成功。具体模型版本依旧未证实。最近真实问答140.45秒时延未变。
