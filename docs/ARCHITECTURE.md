# Architecture：Lead Radar 技术方案

## 1. 架构原则

Lead Radar 的技术架构遵守五个原则：

1. **代码优先**：核心逻辑必须可测试、可版本化、可迁移。
2. **数据源可插拔**：Reddit 只是 MVP 数据源，不应该绑死系统。
3. **规则先行**：全量数据先用规则筛，LLM 只处理少量高价值候选。
4. **证据闭环**：所有洞察必须保留原始链接和命中证据。
5. **低运维成本**：MVP 能用本地 CLI / cron / GitHub Actions 运行。

---

## 2. 模块划分

```text
lead_radar/
  cli.py          CLI 入口
  config.py       YAML 配置加载与校验
  models.py       数据模型
  reddit.py       Reddit 数据源适配器
  scoring.py      规则过滤与评分
  report.py       Markdown 报告生成
  storage.py      SQLite 存储
  feishu.py       飞书 webhook 推送
```

### 2.1 Config

职责：

- 读取 `config.yaml`；
- 校验 topic 是否存在；
- 为后续模块提供结构化配置。

### 2.2 Collector

职责：

- 从 Reddit / mock / 后续 RSS 等数据源取帖子；
- 统一转换为 `RawPost`；
- 不做复杂业务判断。

### 2.3 Scorer

职责：

- 按 topic 规则计算分数；
- 输出 `LeadSignal`；
- 保留 evidence；
- 控制 Top N。

### 2.4 Report Builder

职责：

- 将 `LeadSignal` 转成 Markdown；
- 输出可读的摘要和行动建议；
- 后续可接 LLM 优化摘要。

### 2.5 Storage

职责：

- 保存 scan run；
- 保存 post；
- 保存 signal；
- 保存 report path；
- 做基础去重。

### 2.6 Notifier

职责：

- 将报告摘要推送到飞书；
- MVP 先发文本；
- V1 可升级为交互式卡片。

---

## 3. 数据流

```text
1. 用户运行 CLI
2. CLI 加载 config.yaml
3. 选择 topic
4. 数据源适配器抓取 RawPost
5. Scorer 过滤、打分、排序
6. Report Builder 生成 Markdown
7. Storage 写入 SQLite
8. Notifier 可选推送飞书
```

---

## 4. 为什么不一开始做 LLM 全自动判断

LLM 的价值在于语义总结，不在于替代所有过滤。

如果一开始把所有帖子都丢给 LLM，会带来：

- 成本浪费；
- 速度变慢；
- 结果不可控；
- Prompt 调试复杂；
- 误判难以定位。

因此 MVP 采用：

```text
全量帖子 → 规则粗筛 → Top N → 后续 LLM 深分析
```

LLM 后续只处理 Top 10/20，而不是处理几百条噪音。

---

## 5. 数据模型

### RawPost

代表原始帖子，跨平台统一。

核心字段：

- `source`
- `source_id`
- `url`
- `title`
- `body`
- `author`
- `community`
- `created_at`
- `upvotes`
- `num_comments`

### LeadSignal

代表经过评分后的线索。

核心字段：

- `post`
- `score`
- `buying_intent`
- `confidence`
- `evidence`
- `pain_summary`
- `recommended_action`
- `tags`

---

## 6. 扩展点

### 6.1 新增数据源

新增一个数据源时，只需要实现：

```python
class SourceClient:
    def fetch(self, topic: TopicConfig) -> list[RawPost]:
        ...
```

候选数据源：

- RSS
- Hacker News Algolia API
- Product Hunt API
- GitHub Issues Search API
- 合规中文平台数据接口

### 6.2 新增 LLM 分析

新增 LLM 模块时，建议只处理 `LeadSignal` 的 Top N。

输出结构：

```json
{
  "pain_summary": "...",
  "buying_intent": "strong|medium|weak|none",
  "opportunity": "...",
  "recommended_action": "...",
  "confidence": 0.0
}
```

### 6.3 新增推送渠道

Notifier 可以扩展为：

- Feishu
- Slack
- Email
- Telegram
- Notion
- Airtable

---

## 7. 部署方案

### 7.1 本地手动运行

适合 MVP 验证。

```bash
lead-radar run --config config.yaml --topic n8n_paid_workflow_demand
```

### 7.2 GitHub Actions Cron

适合每日自动推送。

```yaml
on:
  schedule:
    - cron: "0 0 * * *"
```

### 7.3 VPS Cron

适合长期稳定运行。

```bash
0 8 * * * cd /app/lead-radar && lead-radar run --config config.yaml --topic n8n_paid_workflow_demand --send-feishu
```

---

## 8. 安全与合规

- API key 只通过环境变量读取；
- 不提交 `.env`；
- 不长期保存不必要个人数据；
- 尊重平台删除内容和数据保留要求；
- 不做自动骚扰和批量私信；
- 输出报告作为人工判断辅助。

---

## 9. 后续架构升级

当 MVP 证明有价值后，再考虑升级：

```text
SQLite → Postgres / Supabase
CLI → API Service
Markdown → Dashboard
Text webhook → Interactive cards
Rule scoring → Rule + LLM + feedback learning
Single topic → Multi-topic workspace
```

每次升级都必须回答：

> 这个复杂度是否能提高线索质量、降低人工复核成本，或提升稳定性？

如果不能，就不做。
