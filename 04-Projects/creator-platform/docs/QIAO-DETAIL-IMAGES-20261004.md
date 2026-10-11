# 运动详情配图更新

- 椅子坐站三步图、靠墙俯卧撑屈肘图、扶椅提踵两步图均通过本机 Codex ChatGPT 登录的内置 image_gen 生成，无付费 API Key。
- 三张原始图在 geo-platform/.runtime/codex-local/generated_images 下，各自会话为 01a1063c-e052-70f3-bb7e-bf3d11fe8ffb、01a1064a-2648-7e13-8572-d35b54b2649e、01a1064b-a387-7742-b6ca-80498d5f2e1a。
- 已保存本项目 frontend/assets/exercise 下 chair-sequence-qiao.webp、wall-pose-qiao.webp、heel-sequence-qiao.webp，替换对应 NHS 静态图。保留原视频，图注明确 AI 插画。
- row/walk/break 详情原本未引用已生成的同主题封面，现已引用；不是新生成的步骤分解。划船图人物转头看镜头，说明强调实际练习时目光朝前。
- 已目检图像；JS 语法通过，五项本地图片引用验证通过，浏览器确认久坐详情出现图片。未据此宣称教练或医疗专家认证，视频未做完整播放验收。
- 正在生成八段锦8式双姿态图与抱拳礼4格图，会话01a1064c-ba7c-7ae3-a0fd-99a1eddb30c3；完成后逐张检查再接入。

## 东方步骤图完成
八式各1张双姿态图及抱拳礼4格图，9次内置image_gen生成成功；抱拳礼原图按四格裁开，不是拼接生成。落盘 frontend/assets/eastern/baduan-{1..8}-steps.webp、kungfu-step-{1..4}.webp。提示词 output/imagegen/eastern-steps-prompt.txt；生成路径映射 eastern-steps-result.txt。
前端 eastern-steps.js 提供八式独立卡片及抱拳四步，eastern.js接入；已验证8+4图片存在，JS语法通过，浏览器确认两栏目步骤与图片可见，手机版截图 docs/baduan-step-preview-20261004.png。
局限：第4/5图生成方向与提示词相反，页面采用向一侧、换侧的中性文案；第5/6/8为降低幅度版本，页面明确说明。AI插画不是标准整套教学/专业认证；央视视频未完成接入（官方旧链接打开未显示正文，不能声称能播放）。未付费API、未重启、未真实写用户数据。
