# 参与贡献

感谢关注 Agent QualityOps。当前仓库是企业智能体质量运营的离线 MVP，贡献应优先提升证据可追溯性、失败可解释性和发布决策可靠性。

## 本地开发

```powershell
python -m pip install -r backend/requirements-dev.txt
cd frontend
npm ci
cd ..
powershell -ExecutionPolicy Bypass -File scripts/verify.ps1
```

## 贡献边界

- 新增用例必须标注公开来源或明确标注为合成数据，不提交企业内部数据和个人信息。
- 不提交 `.env`、API 密钥、真实用户数据、数据库文件或本地交付产物。
- Demo Provider 的结果只能证明流程可运行，不得描述为真实模型效果。
- 修改评分、人工复核或发布门禁逻辑时，必须增加或更新回归测试。
- 确定性安全失败不能被 LLM Judge 或人工复核覆盖为通过。

## 提交前检查

1. 后端测试通过。
2. 前端类型检查和生产构建通过。
3. `docs/DEMO_EVIDENCE.json` 可以重新生成。
4. 文档明确区分已验证事实、假设和后续计划。
5. 没有新增密钥、数据库、日志、视频或其他大体积本地产物。

## Issue 建议格式

- 用户问题与影响范围
- 最小复现步骤
- 当前行为与期望行为
- 验收标准
- 数据来源与真实性边界
