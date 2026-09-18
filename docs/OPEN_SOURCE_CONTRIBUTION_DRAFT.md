# DeerFlow RFC #4083 产品化补充评论草稿

> 状态：**待核验、未提交**。目标位置：[DeerFlow Issue #4083](https://github.com/bytedance/deer-flow/issues/4083)。提交前必须重新阅读 Issue 最新正文、评论、关联 PR #4070 与贡献规范；若观点已被覆盖，则不重复发送。

## 提交前事实核对

- [ ] 确认 RFC 当前仍在讨论，Issue 未关闭或转移。
- [ ] 核对关联 PR #4070 的状态和最新实现，不评论已解决问题。
- [ ] 验证以下观察仍成立：暂无通用 safety scorer；LLM Judge 被延后且应保持可选／版本化；多轮 schema 与运行行为存在差距；environment fingerprint 尚未覆盖模型、Prompt、Git、工具集和配置摘要；报告支持 JSON／Markdown。
- [ ] 从本地 MVP 截取可复现流程或界面证据；不能只给抽象建议。
- [ ] 评论不声称代表企业用户，不声称本地实现已被上游采用。

## 建议评论标题

Product workflow suggestion: human review, release gates, and version evidence

## 英文评论草稿

I am building a small, independent QualityOps MVP to learn from this RFC rather than proposing a duplicate evaluation platform. The RFC already covers the core runner, schemas, scorers, and JSON/Markdown reporting well. From an AI product workflow perspective, I would like to suggest four additions for consideration:

1. **Human review as a first-class state.** Failed cases and high-risk cases could enter a review queue with `pending / confirmed / overridden` status. An override should preserve the original automatic score, reviewer rationale, and timestamp instead of replacing evidence.

2. **Release gates above aggregate scores.** A run can have a good average while still containing a critical safety failure. A configurable gate could combine hard constraints (for example, zero high-risk safety failures) with quality thresholds and severe regressions versus a baseline. Incomplete runs or unresolved high-risk reviews should fail closed.

3. **Version evidence for reproducibility.** In addition to dataset/report versions, a run fingerprint could include model identifier, prompt hash/version, Git commit, enabled tool set, and a redacted configuration digest. LLM judges should remain optional and versioned, and should not override deterministic failures.

4. **A reviewer-oriented UI flow.** A minimal workflow could be: select baseline and candidate → inspect metric deltas → open a regression → compare input/output/reference/source → submit a review → re-evaluate the release gate → export JSON/Markdown evidence. This would make the RFC usable by product and QA roles, not only by CLI users.

One additional edge case worth clarifying is multi-turn data: if the schema accepts multiple turns but the runner currently executes only the first, the report/UI should mark the case as unsupported or partial rather than silently presenting a complete result.

If this direction is useful, I can first provide a small UI/state proposal or tests around one narrowly scoped behavior after confirming the maintainers' preferred boundary.

## 中文意图说明

- 不提出“新建评测平台”，而是在现有 RFC 上补产品化流程。
- 人工复核不能覆盖或删除自动证据；未复核高风险项默认阻断。
- 门禁优先暴露严重失败，不只看平均分。
- 运行指纹至少能回答“哪份数据、哪个模型、哪个 Prompt、哪次代码、哪些工具和配置”。
- 多轮未完整执行时应显式标记 partial／unsupported，不能按完整通过展示。
- 后续是否提交 PR 由维护者反馈和实际代码范围决定；当前不声称已提交、已接受或已合并。
