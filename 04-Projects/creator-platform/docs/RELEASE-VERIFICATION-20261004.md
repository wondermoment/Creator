# 上线前收口验证 · 2026-10-04

## 已验证
- 后端 `python -m unittest discover -s backend -p "test*.py" -q`：46 项通过。
- 前端 32 个 JavaScript 文件逐个 `node --check`：全部通过。
- 前端回归：表单旧请求隔离、书籍窗口异步隔离、请求错误提示测试均通过。
- 关键资产存在：4 张东方养生 Qiao 原生姿势、6 张长寿运动 Qiao 原生封面、1 张燕麦杯原生图片，共 11 个文件。
- index.html 的关键脚本版本均已指向当前实现：request-errors、book-reader async/error、longevity exercise Qiao covers、coach chat encoding、app form generation。

## 不能据此宣称
运行中的后台未确认加载源码修复；真实浏览器端到端、用户认证/对象权限、多 worker 模型限额、支付商户配置、酒店合作、艺术服务、课程授权、商业图像许可及医学/运动专业签核仍未完成。自动化和合成测试不等于真人专家验收。

## 当前动作
暂停重复微调。下一次有授权重启或明确新缺陷时，按 RELEASE-BLOCKERS.md 先做运行环境恢复和合成账号浏览器流程；不调用付费API，不对外部署，不真实支付，不发送外部消息，不改变已有用户资料。
