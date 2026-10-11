# 对话延迟定位与修复 · 2026-10-05

原本每次本机Codex请求先反复尝试无法连接的WebSocket，随后才回退HTTPS；此前合成真实模型问答约127–140秒。修改backend/app/local_codex.py为本次子进程指定独立chatgpt_https provider，仍使用官方ChatGPT登录与https://chatgpt.com/backend-api/codex，禁用此provider的WebSocket。未写全局配置、未读取或输出登录凭证、未引入API Key；原有只读沙盒和工具限制保留。

依据官方Codex schema及model-provider-info源码，CLI0.158.0。诊断记录CHAT-HTTPS-DIAGNOSTIC-20261005.json：12.22秒，无重连/回退。实际导入coach chat完整路径的合成菜谱请求CHAT-HTTPS-COACH-LIVE-20261005.json：18.45秒。后者回复仍有较多追问；一个样本不能证明整体P95、并发性能或医疗质量。

backend.test_codex_encoding、backend.test_coach_chat共5项和backend.test_model_concurrency2项通过；新增断言检查同一登录、HTTPS、不含API Key和只读沙盒。

运行中的8765服务尚未重启，不能声称用户页面已提速。此前自动审批拒绝过重启；本轮已向用户发出明确的重启确认问题，当前未收到答复。不可反复请求或自行视作通过。得到明确授权后重新核对PID/进程，再受控重启并做合成真实HTTP验证。已有真实用户数据不得改动。
