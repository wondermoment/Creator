# adu-motion-video 安装验证

- 来源：https://github.com/adunext/adu-motion-video
- 固定提交：aba8bf95f8d8ce502af95ec279778e781de51ccd
- 版本：3.14.0-rc.1（上游候选版）
- 路径：D:/Codex/skills/adu-motion-video
- skill-installer 校验、复制完成，836 个源文件复制后摘要一致。
- 对入口、依赖清单及脚本敏感操作进行了静态检查；不是平台安全认证。
- Node 依赖按锁文件安装，禁用安装脚本。
- 独立 Python .venv 已安装依赖，pip check 通过。
- 独立 FFmpeg 9.0.2 下载摘要与 GitHub 发布元数据一致。
- doctor 全部通过；1 秒 1920x1080、30fps 无声 MP4 渲染成功。
- 测试成片：D:/Codex/video-runtime/smoke/adu-motion-smoke.mp4
- 启动入口：D:/Codex/video-runtime/bin/video-adu.ps1
- 未完成真实口播全流程及所有模板验收。

# fal.ai

- 按用户授权将密钥保存到 Windows 用户环境变量 FAL_KEY；本报告不记录密钥。
- 只读查询不存在的任务：无效密钥返回 401，用户密钥返回 404 NOT_FOUND，支持鉴权成功判断。
- 未提交生成任务、未充值，余额及付费模型调用未验证。
- 新启动的 Codex 进程会继承环境变量；现有工具进程可按需从用户环境加载。
