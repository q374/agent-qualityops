# Agent QualityOps

面向 AI 产品经理与智能体团队的轻量级评测、Badcase 复核和发布门禁 MVP。

它不再做“又一个聊天机器人”，而是回答三个上线前问题：

1. 新 Prompt / 模型版本是否真的更好？
2. 失败发生在哪些场景，哪些必须人工复核？
3. 当前证据是否足以允许发布？

> 当前版本是基于公开文档与合成测试问题的离线 MVP，未接入企业生产数据，也未在企业环境部署。

## 已实现范围

- 导入带事实来源的评测集；内置 50 条 Dify / DeerFlow 公开文档用例。
- 配置两个 Prompt 版本并批量运行。
- 记录正确性、依据充分度、任务完成率、安全、延迟、Token 与成本。
- 对比基线与候选版本，形成 Badcase 队列。
- 人工复核可覆盖自动评分，但保留原始判断。
- 按安全、依据、任务完成率和严重回归数生成发布门禁。
- 支持无费用的确定性 `demo` 模式和可选 DeepSeek 真实调用模式。

## 产品边界

- `demo` 模式用于验证产品流程，结果不能写成真实模型质量。
- 真实模型模式必须在本地配置密钥，并受单批次预算和全局预算双重限制。
- 当前未实现登录、租户隔离、生产级审计、异步任务队列或企业密钥管理。
- 自动评分不能覆盖确定性安全失败；高风险失败必须人工复核。

## 快速开始

### 1. 启动后端

```powershell
cd D:\agent-qualityops
python -m pip install -r backend/requirements-dev.txt
python -m uvicorn backend.main:app --reload --port 8000
```

后端首次启动会初始化 SQLite 数据库、导入 50 条评测用例并创建基线/候选 Prompt 版本。

### 2. 启动前端

```powershell
cd D:\agent-qualityops\frontend
npm install
npm run dev
```

访问 `http://localhost:5173`。开发服务器会将 `/api` 代理到 `http://localhost:8000`。

### 3. 真实模型模式（可选）

将 `.env.example` 复制为 `.env`，只在本地填写 `DEEPSEEK_API_KEY`。默认模型为 `deepseek-flash`，预算上限为 5 元。不要将 `.env` 提交到 Git。

## 验证

```powershell
powershell -ExecutionPolicy Bypass -File scripts/verify.ps1
```

脚本会依次运行后端测试、前端类型检查、前端构建，并生成可复现的离线演示证据。详细验收范围见 [评测方案](docs/EVALUATION_PLAN.md)、[演示证据](docs/DEMO_EVIDENCE.json) 和 [演示脚本](docs/DEMO_SCRIPT.md)。

## 文档

- [产品需求文档](docs/PRD.md)
- [架构说明](docs/ARCHITECTURE.md)
- [API 契约](docs/API_CONTRACT.md)
- [评测方案](docs/EVALUATION_PLAN.md)
- [比赛材料](docs/COMPETITION_PACKAGE.md)
- [演示视频设计稿](docs/DEMO_VIDEO_DESIGN.md)
- [静态作品集页面](portfolio/index.html)
- [简历项目描述](docs/RESUME_COPY.md)
- [开源贡献草稿](docs/OPEN_SOURCE_CONTRIBUTION_DRAFT.md)
- [发布候选检查清单](docs/RELEASE_CHECKLIST.md)
- [参与贡献](CONTRIBUTING.md)
- [版本记录](CHANGELOG.md)

## 证据原则

- 报告必须保留用例来源、模型/Prompt 版本、时间、成本和人工判断。
- 公开项目、比赛报名、企业部署、真实用户和指标提升均不得在没有证据时声明。
- 比赛账号注册、正式提交与对外发布不包含在本仓库自动化中。

## License

[MIT](LICENSE)
