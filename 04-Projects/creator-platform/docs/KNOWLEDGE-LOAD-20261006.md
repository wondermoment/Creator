# 知识库服务端收藏读取恢复 · 2026-10-06

代码审查发现loadKnowledge直接接受API结果，无等待上限、无结构校验或请求代次控制；首次读取失败仍显示“还没有收藏”。收藏书籍编号直接拼接到属性，正文没有复用已有的排版功能。

## 修改与验证

portal.js增加15秒截止并传AbortSignal、请求代次隔离；新读取取消旧请求，旧成功或失败不改新结果。验证列表、合法book编号、assistant角色/saved标记及readingMessage/source结构后才替换内存快照。失败保留旧快照并明确非最新；首次失败不说列表为空。刷新时显示读取状态，结束恢复按钮，离页不重绘其他板块。

复用chatAnswer/readingReferenceHtml显示分段、加粗及出处，属性值转义。页面说明更新为：摘录及公开交流笔记在当前浏览器，原文回答收藏在本机服务，无跨设备同步。

新增tests/knowledge-load.cjs覆盖首次失败与空列表区别、旧快照保留、非法来源和书籍编号、连续刷新旧结果隔离、传输忽略Abort时的截止、迟到结果不覆盖、离页不重绘及本地笔记保留。第一次测试因合成环境未提供travelStored失败，补齐合成笔记读取后通过，非产品回归被删除。

5套前端检查通过：knowledge-load、knowledge-notes、book-reader-async、reading-format、book-public-sources；portal.js语法通过。输出见KNOWLEDGE-LOAD-CHECKS-20261006.json。运行只读GET首页与portal.js，确认knowledge-load-4版本及字节一致。

## 局限与边界

无真实浏览器故障注入或服务端收藏记录读取；全部异常/竞争验证为合成传输。不宣称收藏与知识库全链路真实浏览器验收。没有模型调用、后台重启、用户记录写入或删除、外发、部署、支付、API Key、生图。现有本地笔记完整性/备份、跨设备同步、正式权限/隐私及专业签核等条件保留。本轮只改善已有收藏的读取，不新增数据归属能力。
