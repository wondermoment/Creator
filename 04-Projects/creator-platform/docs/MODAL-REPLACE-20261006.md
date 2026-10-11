# 共享窗口替换时取消旧流 · 2026-10-06

## 复现与修复

此前直接调用showForm/openCoach/openReadingChat替换已打开窗口，只会移除旧内容，不触发dialog.close。教练/公共书籍问答只监听close，因此旧流式请求仍可能占用模型。阅读窗口的reading-fullscreen样式也只在close清除，会遗留到普通窗口。

新增tests/modal-stream-replace.cjs，运行实际showForm与教练/书籍函数，DOM与传输为合成。修复前在coach→coach的旧signal未取消断言失败（exit 1）；不是仅凭代码猜测。

showForm在替换内容前发出formreplace事件；教练和书籍流式问答监听该事件并abort，finally清理close/formreplace监听。阅读样式在关闭或替换时同步移除并解除两类监听，避免旧清理影响新书籍窗口。没有伪造close事件或关闭后重新打开共享dialog。

## 验证结果

六种实际函数组合（coach/book分别切coach/book/form）通过：旧流signal取消、定时器释放、迟到delta不绘制、新草稿不改变、新流仍可完成、阅读样式随新窗口类型正确设置。

8套自动回归全部通过：modal-stream-replace、form-async、coach-stream-ui、coach-async、book-reader-async、book-upload-async、chat-stream、chat-stream-cancel。3个修改JS语法通过。book-reader-async原关闭后残留1个样式监听的期望改为0，其他断言保留。详细输出见MODAL-REPLACE-CHECKS-20261006.json。

运行服务只读GET确认首页缓存版本与3个JS文件字节和磁盘一致：app modal-replace-7、coach-chat replace-cancel-15、book-reader replace-cancel-22。没有后台重启，最近PID78640仍为交接记录；没有读取私人记录或更改现有用户数据。

## 范围限制

本轮验证为合成DOM/流式传输和只读HTTP，没有真实浏览器切窗或新真实模型请求。中止浏览器请求不等于云端推理立即停止，服务端资源释放精确时延及多实例限额仍待验证。上传和已上传原文的同步问答仍没有完整取消能力；本次没有声称一并修好。

原62例全板块审核和2例菜单时间真实样本不重复调用。医学签核、供应商授权、权限隔离、商户配置、全文Skill、严格菜单时间等上线条件保留。无新生图、付费API Key、部署、外部消息或支付。
