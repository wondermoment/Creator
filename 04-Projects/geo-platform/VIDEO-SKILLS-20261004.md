# AI 视频 Skills 来源与接入记录

2026-10-04。GitHub 公开仓库检索 video generation skill、ai video skills、ffmpeg skill、seedance skill，每组读取前6项候选；这不是全 GitHub 的穷尽清单。核对6个仓库的元数据/树/Skill正文，安装4个互补 Skill，复用已有视频能力。不执行下载仓库的脚本，不开通服务或上传客户素材。

## 新安装（Codex 下一轮可发现）

| Skill | 来源与固定提交 | 许可 | 本站状态 |
|---|---|---|---|
| heygen-avatar | [HeyGen官方](https://github.com/heygen-com/skills/tree/1bd5e4d33a028dfed3abf504c5e3dd644fb9ea8a/heygen-avatar) | MIT | 制作方案；未接数字人生成 |
| heygen-video | [HeyGen官方](https://github.com/heygen-com/skills/tree/1bd5e4d33a028dfed3abf504c5e3dd644fb9ea8a/heygen-video) | MIT | 构图/口播规划；未接视频生成 |
| heygen-translate | [HeyGen官方](https://github.com/heygen-com/skills/tree/1bd5e4d33a028dfed3abf504c5e3dd644fb9ea8a/heygen-translate) | MIT | 双语稿；未接视频翻译/口型同步 |
| seedance-prompt-zh | [dexhunter](https://github.com/dexhunter/seedance2-skill/tree/516284d5bab58361bfdfed3cc96cee3e837d4c44/zh) | MIT | 分镜、素材角色、画面提示词；未调用Seedance |

通过官方 skill-installer 脚本 --method download --ref 固定提交安装到 D:/Codex/skills。根目录MIT许可副本已放进各安装目录；未执行 heygen-video/scripts/update-check.sh。

## 复用与未安装

- 本机 Remotion、HyperFrames、video-use、videocut、muapi-seedance-2 已存在，未重复覆盖。产品只吸收分镜/时间线/字幕方法，不通过网页执行这些Skill的CLI。
- remotion-dev/skills：提交0b5db9daae40f42c73544d1cc0a8c733bd530eaa，GitHub未给出仓库许可；已有本机版本，不新增搬运。Remotion商业运行时许可仍须单独核对。
- kajisho5/ffmpeg-skill：MIT，但根库包含大量非视频开发规则，本轮不整库安装。
- CrunTeam/crun-agent-skills：MIT，919ced2949cc29feb539e7904a681c1620c9ced7。又一个付费媒体聚合服务，目前无授权服务配置，避免重复接入。
- Vincentwei1021/video-shotcraft：本机已有，但当前GitHub返回404，不用其远程内容作可验证新来源。
- 搜索到但未采纳：OpenMontage为AGPL-3.0的完整系统，未把其源码并入本站；其他无明确许可或同类提示词仓库不机械复制。

## 产品实施与设计依据

沿用一鱼多吃已有的选择原稿→勾选任务→生成→修改流程。用户指定视频卡片放在原“视频制作准备”处，桌面一排四个；窄屏改为两列/一列。

参照 Refero Design bundled craft-details.md 的表单焦点和状态反馈，以及 copywriting.md 的“目的、产出、条件”表达；保持当前白色面板、有限绿色选择态、简洁数字顺序，不增加新导航。没有使用在线Refero截图，以上为本机参考。

6项任务：导演分镜、Seedance画面提示词、数字人口播、剪辑动效、配音字幕、多语言文案。产品后端 repurpose.py 的简明创作指引为原创整合，不把下载的SKILL.md指令直接注入模型或公开给客户。复用现有企业模型、来源快照、执行记录、保存草稿和审核门禁。SRT无音轨时只是预估。

## 成片缺口

需管理员选择并授权视频/数字人服务账号与额度，确定素材与人物/声音授权；实现上传、异步任务、回执、失败重试、成片验收。当前既未宣称接通，也未调用第三方媒体API。
