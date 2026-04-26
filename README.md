# Lead Radar

> 一个代码优先的“社媒需求信号雷达”：自动从 Reddit 等公开社区抓取帖子，筛出高意图需求信号，生成可行动的 Markdown 线索报告，并按需推送通知。

Lead Radar 不是泛泛的“社媒洞察 Agent”。它的第一性目标很窄：**每天/每次帮你找出一批可能愿意为某类产品、服务或自动化方案付费的真实用户需求信号。**

本项目的 MVP 先聚焦一个场景：

> 找出英文社区里最近是否有人在表达“我想付费/找人/外包/求助，帮我做业务自动化工作流”的需求。

---

## 1. 为什么做这个

这个项目最初从一个 n8n 自动化设想里长出来，但复盘后发现，真正重要的不是编排工具，而是稳定发现真实需求信号。

真正的需求是：

- 不想手刷 Reddit、X、小红书、论坛、Hacker News、Product Hunt 等平台。
- 想快速知道某个主题下有没有真实痛点、付费信号、外包意图、竞品抱怨、内容选题。
- 想让输出结果能直接指导下一步行动，而不是生成一份漂亮但无用的总结。

所以本项目优先使用更直接、可测试、可版本化的代码实现。

---

## 2. MVP 要解决什么

MVP 只回答一个问题：

> 在指定主题、指定社区、指定关键词下，最近有哪些帖子值得我进一步查看或联系？

每条线索必须给出：

- 原帖标题
- 原帖链接
- 来源社区
- 用户痛点
- 是否存在付费/外包/采购/强求助信号
- 为什么值得看
- 推荐下一步行动
- 置信度/优先级

不追求一开始就覆盖所有平台，不追求“智能体人格”，不追求复杂 UI。

---

## 3. 当前交付状态

当前版本包含：

```text
README.md                  项目说明、定位、使用方式
docs/PRD.md                产品需求文档
docs/ARCHITECTURE.md       技术方案与架构决策
config.example.yaml        MVP 主题配置示例
.env.example               环境变量示例
lead_radar/                可运行的 Python MVP 骨架
examples/sample_posts.json 本地 mock 数据
tests/                     评分逻辑测试
```

代码骨架已经按 MVP 的核心链路搭好：

```text
配置主题 → 抓取帖子/读取 mock → 规则过滤与打分 → 生成 Markdown 报告 → 可选通知 → 可选写入 SQLite
```

LLM 分析模块预留为后续扩展点。MVP 先用规则打分和确定性报告跑通核心闭环，避免一开始就把成本和不确定性放进系统。

---

## 4. 为什么选择 Python

### 4.1 Python

选择 Python 的原因不是“流行”，而是它更贴合这个任务：

- 抓取、清洗、打分、SQLite、命令行、定时任务都非常直接。
- 适合后续加上 LLM、向量检索、数据分析、Notebook 复盘。
- 可以用 GitHub Actions、VPS Cron、Docker、Cloudflare Container 等方式部署。
- 比低代码编排更容易测试、版本化、复用和长期维护。

### 4.2 暂不使用 LangChain / Agent 框架

这个项目的核心不是多步智能体推理，而是稳定的数据管道和信号筛选。过早引入 Agent 框架会增加复杂度。

MVP 里 LLM 只需要做两件事：

1. 对 Top N 帖子做结构化分析；
2. 汇总为一份可行动报告。

这不需要复杂 Agent。

## 5. 架构

```text
            ┌─────────────────────┐
            │ config.yaml          │
            │ topic / source / rule│
            └──────────┬──────────┘
                       │
                       ▼
            ┌─────────────────────┐
            │ Collector            │
            │ Reddit / mock / RSS  │
            └──────────┬──────────┘
                       │
                       ▼
            ┌─────────────────────┐
            │ Filter + Scorer      │
            │ rule-first ranking   │
            └──────────┬──────────┘
                       │
                       ▼
            ┌─────────────────────┐
            │ Report Builder       │
            │ Markdown / JSON      │
            └──────┬────────┬─────┘
                   │        │
                   ▼        ▼
          ┌────────────┐  ┌─────────────┐
          │ SQLite     │  │ Notifier    │
          │ history    │  │ notification│
          └────────────┘  └─────────────┘
```

详见 [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)。

---

## 6. 快速开始

### 6.1 安装

推荐使用 `uv`：

```bash
uv sync --extra dev
```

或者使用普通虚拟环境：

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

### 6.2 复制配置

```bash
cp .env.example .env
cp config.example.yaml config.yaml
```

### 6.3 使用 mock 数据跑通 MVP

```bash
lead-radar run --config config.yaml --topic paid_demand_signals --mock
```

输出文件会生成在：

```text
reports/
```

### 6.4 使用真实 Reddit 数据

推荐配置 Reddit app 的 client id / secret，让程序自动换取短期 access token：

```bash
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
REDDIT_USER_AGENT="lead-radar/0.1 by your_reddit_username"
```

也可以临时传入已有 bearer token：

```bash
REDDIT_ACCESS_TOKEN=your_access_token
```

但 Reddit access token 会过期，长期运行更建议使用 `REDDIT_CLIENT_ID` / `REDDIT_CLIENT_SECRET`。

然后运行：

```bash
lead-radar run --config config.yaml --topic paid_demand_signals
```

程序会通过 Reddit OAuth 获取 token，然后请求 `https://oauth.reddit.com` 的搜索接口。Reddit Data API 有速率限制；本项目 MVP 默认低频运行，避免高频抓取。参考 Reddit 官方 Data API 文档：<https://support.reddithelp.com/hc/en-us/articles/16160319875092-Reddit-Data-API-Wiki>。

### 6.5 推送通知

通知只是提醒你回来看 Markdown 报告，不承载完整复核体验。个人使用可以优先用 Telegram；团队场景可以用飞书。

配置 Telegram：

```bash
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

运行：

```bash
lead-radar run --config config.yaml --topic paid_demand_signals --mock --notify telegram
```

配置飞书：

配置 `.env`：

```bash
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/xxx
```

运行：

```bash
lead-radar run --config config.yaml --topic paid_demand_signals --mock --notify feishu
```

当前版本里，Telegram 会直接发送完整 Markdown 报告；如果报告超过 Telegram 单条消息长度限制，会自动分段发送。飞书仍推送文本摘要和 Markdown 报告路径。后续可以升级为交互式卡片或通用 webhook。

### 6.6 可选 LLM 二次筛选

默认流程是规则评分，不调用大模型。如果需要在规则粗筛后让大模型做第二轮筛选和排序，配置 OpenAI-compatible API：

```bash
LEAD_RADAR_LLM_API_KEY=your_api_key
LEAD_RADAR_LLM_BASE_URL=https://your-provider.example/v1
LEAD_RADAR_LLM_MODEL=your_model
```

运行：

```bash
lead-radar run --config config.yaml --topic paid_demand_signals --mock --llm-rerank
```

这一步只处理规则筛出的候选集，不把全量帖子直接丢给 LLM。

如果需要让大模型按战略摘要 prompt 生成最终 Markdown 报告，增加：

```bash
lead-radar run --config config.yaml --topic paid_demand_signals --mock --llm-report
```

### 6.7 GitHub Actions 定时运行

项目内置 `.github/workflows/lead-radar.yml`，支持手动运行和每日定时运行。需要在 GitHub repository secrets 配置：

```text
REDDIT_CLIENT_ID
REDDIT_CLIENT_SECRET
REDDIT_USER_AGENT
TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID
```

如果使用飞书或 LLM，再补：

```text
FEISHU_WEBHOOK_URL
LEAD_RADAR_LLM_API_KEY
LEAD_RADAR_LLM_BASE_URL
LEAD_RADAR_LLM_MODEL
```

默认 workflow 会运行 `paid_demand_signals` 并推送 Telegram。手动触发时可以把 `notify` 改成 `feishu` 或 `none`。

---

## 7. 配置示例

```yaml
topics:
  - name: paid_demand_signals
    description: 找公开社区里带有付费、外包、采购或强求助意图的需求信号
    sources:
      reddit:
        subreddits:
          - automation
          - smallbusiness
          - entrepreneur
          - SaaS
          - Zapier
          - NoCode
          - selfhosted
    keywords:
      - "need automation"
      - "automate my workflow"
      - "looking for help"
      - "Zapier alternative"
      - "manual work"
      - "hire someone"
      - "workflow consultant"
      - "willing to pay"
      - "paid help"
    include_phrases:
      - "looking for help"
      - "can someone build"
      - "willing to pay"
      - "hire"
      - "freelancer"
      - "consultant"
      - "too much manual work"
    exclude_phrases:
      - "i am selling"
      - "course"
      - "affiliate"
      - "job posting"
    lookback_hours: 72
    max_posts_per_source: 30
    min_comments: 0
    min_upvotes: 0
    output_top_n: 10
```

---

## 8. 报告输出示例

```markdown
# Lead Radar Report: paid_demand_signals

## 今日判断

发现 3 条值得人工复核的需求信号，其中 1 条存在较强外包/付费意图。

## Top Leads

### 1. Need help automating client onboarding

- Source: r/automation
- Score: 18.5
- Buying intent: strong
- Pain: onboarding 手动步骤多，跨表格/邮件/CRM 重复录入。
- Evidence: “willing to pay someone to set this up”
- Recommended action: 回复提供 15 分钟诊断，询问现有工具栈和触发条件。
- URL: https://reddit.com/...
```

---

## 9. 质量标准

这个项目不以“抓到多少帖子”为成功标准，而以“抓到多少可行动信号”为标准。

MVP 阶段的验收标准：

- 每次运行能稳定输出 Top 10 或更少的高信号帖子；
- 每条结果必须有原帖链接；
- 结果能解释“为什么值得看”；
- 人工复核时间从 1-2 小时降到 10-20 分钟；
- 至少 30% 的 Top 10 结果值得点开原帖查看；
- 不长期囤积不必要的用户原文和个人信息。

---

## 10. 路线图

### MVP：规则优先的 Reddit 需求雷达

- [x] 配置文件定义主题、社区、关键词、过滤规则
- [x] mock 数据运行
- [x] Reddit API 抓取骨架
- [x] 规则打分
- [x] Markdown 报告
- [x] SQLite 存储
- [x] 飞书 webhook 推送
- [x] Telegram bot 推送
- [x] GitHub Actions 定时任务
- [ ] LLM 结构化分析 Top N 帖子

### V1：真正可用的个人工作流

- [ ] 每日定时运行
- [ ] 多主题配置
- [ ] 报告历史对比
- [ ] 去重与已读状态
- [ ] Feishu 交互式卡片
- [ ] 简单的人工反馈：有用/无用

### V2：可产品化的需求情报系统

- [ ] RSS / Hacker News / Product Hunt / GitHub Issues 数据源
- [ ] 小红书/知乎等平台的合规数据接入方案
- [ ] LLM 自动聚类痛点
- [ ] 竞品监控
- [ ] 线索 CRM 化
- [ ] Prompt 和评分规则 A/B 测试

---

## 11. 合规与边界

- 只抓取公开内容或已授权内容。
- 遵守各平台 API 条款、速率限制和数据保留要求。
- 不做隐私信息聚合，不做用户画像贩卖。
- 不自动骚扰用户，不自动批量私信。
- 报告只作为人工判断辅助，不直接替代商业决策。

---

## 12. 项目原则

1. **窄场景优先**：先把一个高价值主题做穿，不做泛化大而全。
2. **规则先于 AI**：先用硬规则过滤，再把少量高价值数据交给 LLM。
3. **证据优先**：所有洞察必须能回到原始链接。
4. **低复杂度优先**：能用 CLI + cron 解决，就不要先造大系统。
5. **输出服务行动**：报告的终点不是“看起来聪明”，而是“下一步该做什么”。
