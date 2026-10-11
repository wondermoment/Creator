---
title: Creator 智能流项目入口
description: 旧资料续接、可运行版本、开发边界与下一步
tags: [creator, project, health]
updated: 2026-09-28
---

# Creator 智能流

本项目继续使用原来的 `04-Projects/creator-platform`。定位：为长寿诊所建立连接客户关系、健康数据、人工决策和服务复盘的经营与健管系统。

## 旧资料库已续接

- [原始架构规划](./ARCHITECTURE.md)：保留历史版本；其中模型、自动接入、收益和效率描述属于规划或假设，并非已实现能力或已验证结果。
- [用户提供的历史对话全文](./sources/2026-09-28-历史对话.txt)：本次原样归档，避免依赖打不开的旧聊天。
- [本轮产品与架构收敛](./PRODUCT.md)：新一轮实现边界。
- [旧业务枚举](./backend/app/models/enums.py)：保留内容渠道、私域、客户阶段和审批状态定义。
- [旧数据库配置](./backend/app/core/database.py)、[旧基础模型](./backend/app/models/base.py)、[旧容器草案](./docker-compose.yml)：保留，尚未接入新演示版本。

本轮检索主要知识目录，仅找到原有架构笔记；旧 `frontend/mobile` 为空目录。无法据此恢复未落盘的历史代码，也没有恢复原聊天窗口。

## 运行

在本目录执行（Python 3.12）：

```powershell
python -m pip install -r backend/requirements-demo.txt
./start.ps1
```

访问 http://127.0.0.1:8765 ，API 文档位于 http://127.0.0.1:8765/docs 。启动脚本仅监听本机。手机排版可在浏览器窄窗口预览；手机实机访问需后续提供受保护的网络部署。

当前实现为 FastAPI + 原生 HTML/CSS/JavaScript + SQLite，本机即可启动。沿用旧规划的 FastAPI；为先验证闭环，本轮没有引入 Next.js 构建链，也未启用 PostgreSQL、Redis、pgvector。原 docker-compose 缺少 Dockerfile，不能作为本版运行入口。

## 可操作功能

- 客户端：首页、六类指标与 7/14/30 天趋势、报告档案、任务复盘和事件时间线。
- 健管师：客户检索与切换、规则建议复核、驳回留因、批准创建任务、完成任务并记录反馈。
- 健康数据：来源、单位、带时区的测量时间；数值与时间输入校验。
- 报告：PDF/PNG/JPEG 上传、本机存储、下载；待人工解读。
- 持久化：`.runtime/creator.db`，首次启动创建三名虚构客户和示例数据；重启保留用户操作。
- 建议审批、任务创建与事件写入使用同一事务；重复审批不会重复创建任务。

当前没有登录、租户隔离、真实设备接入、OCR、LLM 或经临床验证的预测算法。角色切换是演示导航，不是权限控制；请只使用演示资料。

## 验证

```powershell
python -m unittest backend.test_workflow -v
node --check frontend/app.js
```

集成测试使用临时数据库，验证输入校验、录入、建议去重、批准/驳回、任务完成、报告往返和重启持久化。实际代码见 [API](./backend/app/main.py)、[前端](./frontend/app.js)、[工作流测试](./backend/test_workflow.py)。

## 下一开发顺序

1. PostgreSQL 迁移、账号与租户、服务端角色权限、客户授权和审计访问；再接真实客户。
2. CSV 导入与字段映射、报告指标人工复核、基线和干预周期。
3. 按已获授权与实际厂商能力接企业微信、设备 API；个人微信先以人工录入和合规导出承接。
4. 引入可追溯的 AI 建议，记录模型、版本、依据和人工结果；不自动修改医疗方案。
5. 验证首家诊所效果后，将字段、关系、规则和工作流提炼为版本化行业模板，不复制客户个人健康数据。
