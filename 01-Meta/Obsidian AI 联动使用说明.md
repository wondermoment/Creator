# Obsidian AI 联动使用说明

## 已安装内容

### Obsidian 社区插件

- Git：提交、查看和回滚 Vault 改动。
- Templater：用模板创建日报、项目笔记和会议记录。
- Calendar：按日期打开或创建每日笔记。
- Text Generator：在 Obsidian 内调用 AI；公司资料优先配置 Ollama 或局域网模型。
- Excalidraw：绘制知识图谱、流程图和草图。

### Agent Skills

当前 Vault 已安装 Anthropic Skills、Obsidian 官方 Skills、Obsidian Second Brain、ctx、compabob、obsidian-ai-setup 和相关安全 Skills。Skills 位于 `.agents/skills`，Claude、Codex 等 Agent 会按任务自动读取。

Open Knowledge 已通过项目级 MCP 接入 Claude、Cursor、Codex、OpenCode 和 Pi，配置文件由 `ok init` 生成：

- `.mcp.json`
- `.cursor/mcp.json`
- `.codex/config.toml`
- `opencode.json`
- `.pi/extensions/open-knowledge.ts`

## 第一次使用

1. 重启 Obsidian，以及正在使用的 Claude/Codex/Cursor 等 Agent 会话。
2. 先在 Vault 根目录创建一次 Git 检查点：

   ```powershell
   git add -A
   git commit -m "vault checkpoint before ai edit"
   ```

3. 在 Agent 中先要求只读检查，不要一上来允许批量修改：

   ```text
   先只读检查当前 Obsidian Vault，告诉我有哪些目录、笔记和待整理问题。
   不要修改或删除文件。
   ```

## 常用 Agent 提示词

### 收集资料

```text
把下面这段内容整理成一篇 Obsidian Markdown 笔记：
1. 保存到 00-Inbox；
2. 添加简洁的 YAML frontmatter；
3. 抽取 3-7 个关键词；
4. 只引用已有笔记，不要臆造链接；
5. 先给我预览，确认后再写入。
```

### 整理已有笔记

```text
扫描 00-Inbox，只处理未归档的 Markdown。
请先列出每篇笔记准备移动到哪里、会新增哪些 wikilink、会修改哪些内容。
不要删除原文，等我确认后再执行。
```

### 写日报

```text
根据今天的工作记录创建一篇日报，保存到 02-Daily。
结构包括：完成事项、进行中、阻塞、明日计划、相关项目链接。
不要编造没有出现在 Vault 中的事实。
```

### 建知识图谱

```text
从 03-Knowledge 中找出与“主题名”相关的概念，
先给出候选 wikilink 和关系说明；确认后再创建或更新一张 Excalidraw/Canvas 图。
```

### 定期维护

```text
检查 Vault 的断链、重复标题、缺少 frontmatter 的笔记和孤立笔记。
输出报告即可，不要自动删除或合并。
```

## Obsidian 内的插件入口

- Git：左侧 Git 图标，或命令面板搜索 `Git: Create`、`Git: Commit`、`Git: Checkout`。
- Calendar：左侧日历图标；建议把 Daily notes 文件夹设为 `02-Daily`。
- Templater：设置模板目录后，在命令面板运行 `Templater: Create new note from template`。
- Text Generator：在设置里选择模型和 API；涉及公司手册时不要默认使用公网 API。
- Excalidraw：命令面板运行 `Excalidraw: Create new drawing`。

## Open Knowledge 命令

这些命令在 Vault 根目录的终端运行：

```powershell
ok preview
ok lint
ok start
ok ui
```

- `ok preview`：只读查看会被知识库跟踪的 Markdown。
- `ok lint`：检查 Markdown 问题。
- `ok start`：启动本地知识库服务。
- `ok ui`：启动本地 Web 编辑界面。

Agent 通过项目级 MCP 连接 Open Knowledge；一般不需要手动运行 `ok mcp`。

## 安全习惯

- 每次让 Agent 批量改 Vault 前先提交 Git。
- 第一次只给“读取”和“生成预览”权限；确认后再允许写入。
- 不要把 API Key、公司账号、Cookie 或 `.env` 内容复制进 Vault。
- Text Generator 使用公网模型时，输入内容可能离开本机；公司手册优先使用本地 Ollama 或内网模型。
- 删除、批量移动、批量重命名前，要求 Agent 先输出变更清单。
- 回滚时优先用 Git 插件或普通 Git 命令，不要直接删除整个 Vault。

## 推荐工作流

```text
剪藏/收集
   ↓
00-Inbox
   ↓  Agent 提取摘要、标签和 wikilink
03-Knowledge / 04-Projects
   ↓
日报、项目复盘、Canvas/Excalidraw 图谱
   ↓
Git 提交检查点
```
