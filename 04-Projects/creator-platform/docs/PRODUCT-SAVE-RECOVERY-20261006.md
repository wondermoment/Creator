# 商品内容保存等待恢复

2026-10-06。先读最新交接。发现商品编辑PUT无等待上限，确认保存成功后还依次等待catalog与commerce snapshot；后者挂起会让已成功的保存窗口一直不可用。

## 修复

productContentWrite补30秒独立Promise截止与AbortController，覆盖请求和响应解析。仅返回相同商品id及提交的status才确认成功；异常回执、网络失败或超时不显示成功。错误保留原服务端信息，补充复制保留修改、关闭后刷新列表核对与商品编号，不把超时说成服务端未处理。

每次编辑窗口最多发起一次保存写请求，未知结果后即使修改表单也不盲目重传；需先核对再重新编辑。缺少revision仍在本地阻止发送，既有乐观并发检查不变。此策略较保守：服务端明确拒绝的校验错误也需关闭重开，未新增HTTP状态分类或可靠幂等回执。

确认保存成功后，catalog和snapshot在后台刷新，不再阻塞showForm关闭和成功反馈。保存未确认时，不触发刷新或迟到成功反馈；共用showForm继续保留当前输入与旧窗口隔离。静态版本save-recovery-7，无后台改动或重启。

## 验证

6套Node通过：product-save-recovery（新增）、product-catalog-recovery、product-image-recovery、product-revision、product-id-escaping、form-async；product-editor语法检查通过。新增测试加载实际showForm与实际productEdit函数，使用合成DOM/传输/时钟，覆盖永久等待、30秒截止、abort及清理、迟到成功、网络/并发冲突错误、错误id/status/空回执、同窗重复提交和修改后重传阻止、保留表单/恢复按钮、两个刷新永久等待时保存仍成功结束。revision测试补充新增函数需要的AbortController及计时器依赖，保留原断言。

运行实例只读GET首页和脚本，版本正确且脚本与本地字节一致，证据PRODUCT-SAVE-RECOVERY-20261006.json。未进行真实浏览器保存或生产本地商品写入；自动测试不能当网络故障实测或正式订单验收。没有模型调用（改动不涉及问答）、新生图、付费API、部署、外发消息、真实支付或已有用户资料变更。

客户端超时不等于服务端取消；跨窗口保存结果恢复/可靠幂等与自动合并未实现。commerce snapshot整体时限/过期数据保护、主图并发替换以及正式身份/对象权限、隐私、商户/医学/素材授权继续待办。本轮不解除上线条件。
