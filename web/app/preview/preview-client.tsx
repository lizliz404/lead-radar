"use client";

import { useMemo, useState } from "react";

type Signal = {
  id: string;
  title: string;
  community: string;
  sourceUrl: string;
  score: number;
  status: string;
  quote: string;
  evidence: string;
  nextAction: string;
};

const examples = [
  "Shopify sellers struggling with inventory forecasting and cash-flow planning during Q4.",
  "Indie hackers looking for better Stripe analytics, churn alerts, and revenue dashboards.",
  "Consultants who need AI notes that turn client calls into proposals and follow-up tasks.",
];

const defaultBrief = examples[0];
const reviewStatuses = ["new", "useful", "not useful", "contacted", "replied", "converted"];

function wordsFromBrief(brief: string) {
  const stopWords = new Set([
    "about",
    "after",
    "better",
    "during",
    "find",
    "from",
    "into",
    "looking",
    "need",
    "that",
    "the",
    "their",
    "this",
    "with",
    "who",
  ]);
  return Array.from(new Set(brief.toLowerCase().match(/[a-z][a-z0-9+-]{2,}/g) || []))
    .filter((word) => !stopWords.has(word))
    .slice(0, 8);
}

function buildPlan(brief: string) {
  const keywords = wordsFromBrief(brief);
  const lower = brief.toLowerCase();
  const communities = lower.includes("shopify")
    ? ["r/shopify", "r/ecommerce", "r/smallbusiness", "r/entrepreneur"]
    : lower.includes("stripe") || lower.includes("indie")
      ? ["r/indiehackers", "r/SaaS", "r/startups", "r/Entrepreneur"]
      : ["r/startups", "r/SaaS", "r/smallbusiness", "r/productmanagement"];

  return {
    keywords,
    communities,
    phrases: ["is there a tool", "willing to pay", "alternative to", "too much manual work", "spreadsheet", "recommend"],
    excludes: ["course", "affiliate", "giveaway", "job posting"],
  };
}

function buildSignals(brief: string): Signal[] {
  const plan = buildPlan(brief);
  const niche = plan.keywords.slice(0, 3).join(" ") || "workflow";
  return [
    {
      id: "sig-1",
      title: `Looking for a tool to fix ${niche} before it breaks again`,
      community: plan.communities[0],
      sourceUrl: "https://reddit.com/r/example/comments/simulated_1",
      score: 91,
      status: "new",
      quote: "I would pay for something that catches this before the spreadsheet becomes a mess.",
      evidence: "Tool-seeking language, explicit willingness to pay, repeated workflow pain.",
      nextAction: "Interview 5 users who still use spreadsheets and ask what failure would make them switch this month.",
    },
    {
      id: "sig-2",
      title: `Any ${niche} alternatives that do not require duct-tape automations?`,
      community: plan.communities[1],
      sourceUrl: "https://reddit.com/r/example/comments/simulated_2",
      score: 82,
      status: "new",
      quote: "We have Zapier, Sheets, and a VA checking it manually. It works until it doesn't.",
      evidence: "Workaround stack, manual labor, reliability concern.",
      nextAction: "Turn the workaround into positioning: replace duct-tape automations with reviewed evidence and a next action.",
    },
    {
      id: "sig-3",
      title: `How are people handling ${niche} without hiring another operator?`,
      community: plan.communities[2],
      sourceUrl: "https://reddit.com/r/example/comments/simulated_3",
      score: 74,
      status: "new",
      quote: "I don't need another dashboard. I need to know what to do next and whether this is worth the effort.",
      evidence: "Decision support need; dashboard fatigue; operational cost pressure.",
      nextAction: "Sell the memo, not the dashboard: source links, review status, and kill criteria.",
    },
  ];
}

function buildMarkdown(brief: string, signals: Signal[]) {
  return `# Demand scan preview\n\n## Brief\n${brief}\n\n## Ranked evidence\n${signals
    .map(
      (signal, index) =>
        `${index + 1}. [Score: ${signal.score}] [Review: ${signal.status}] ${signal.title}\n   - Source: ${signal.sourceUrl}\n   - Quote: “${signal.quote}”\n   - Evidence: ${signal.evidence}\n   - Next action: ${signal.nextAction}`,
    )
    .join("\n\n")}\n\n## Limitation\nThis instant preview uses simulated evidence to demonstrate the loop. Paid scans must include real source links and manual review.`;
}

function downloadText(filename: string, text: string, type: string) {
  const blob = new Blob([text], { type });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

export function PreviewClient({ operatorAppUrl }: { operatorAppUrl: string }) {
  const [brief, setBrief] = useState(defaultBrief);
  const [signals, setSignals] = useState<Signal[]>([]);
  const plan = useMemo(() => buildPlan(brief), [brief]);
  const markdown = useMemo(() => buildMarkdown(brief, signals), [brief, signals]);

  function runPreview() {
    setSignals(buildSignals(brief));
  }

  function updateStatus(id: string, status: string) {
    setSignals((items) => items.map((item) => (item.id === id ? { ...item, status } : item)));
  }

  return (
    <main className="previewPage">
      <section className="previewHero">
        <div className="container previewGrid">
          <div>
            <a className="backLink" href="/">← Back to landing</a>
            <p className="eyebrow">Instant preview · no Streamlit wait</p>
            <h1>Run the loop before you trust the product.</h1>
            <p className="subhead">
              This page replaces the slow public Streamlit jump with an instant browser-native preview of the actual loop: brief → scan plan → ranked evidence → review status → Markdown export.
            </p>
          </div>
          <div className="previewNotice">
            <strong>Reality check</strong>
            <p>
              This is not pretending to be live Reddit evidence. It is a fast UX harness. The operator console and Python scanner can stay backstage until the delivery flow is worth productionizing.
            </p>
            {operatorAppUrl ? <a className="textLink" href={operatorAppUrl} target="_blank" rel="noreferrer">Open Streamlit operator console →</a> : null}
          </div>
        </div>
      </section>

      <section className="section previewWorkspace">
        <div className="container previewWorkspaceGrid">
          <div className="previewPanel">
            <label className="previewLabel" htmlFor="brief">Market brief</label>
            <textarea id="brief" value={brief} onChange={(event) => setBrief(event.target.value)} />
            <div className="previewExamples">
              {examples.map((example) => (
                <button key={example} type="button" onClick={() => setBrief(example)}>
                  {example}
                </button>
              ))}
            </div>
            <button className="button buttonPrimary previewRun" type="button" onClick={runPreview} disabled={!brief.trim()}>
              Run instant preview
            </button>
          </div>

          <div className="previewPanel">
            <p className="eyebrow">Generated scan plan</p>
            <div className="planList">
              <span>Communities</span>
              <p>{plan.communities.join(", ")}</p>
              <span>Keywords</span>
              <p>{plan.keywords.join(", ") || "manual workflow, recommendation, alternative"}</p>
              <span>Intent phrases</span>
              <p>{plan.phrases.join(", ")}</p>
              <span>Exclude</span>
              <p>{plan.excludes.join(", ")}</p>
            </div>
          </div>
        </div>
      </section>

      {signals.length ? (
        <section className="section previewResults">
          <div className="container">
            <div className="sectionIntro narrow">
              <p className="eyebrow">Evidence preview</p>
              <h2>Ranked signals with review status.</h2>
              <p>Simulated source links keep this honest: the production value is not the mock data, it is the review/export loop.</p>
            </div>
            <div className="signalReviewGrid">
              {signals.map((signal) => (
                <article key={signal.id} className="signalReviewCard">
                  <div className="evidenceTopline">
                    <span>{signal.community}</span>
                    <span>Score {signal.score}</span>
                  </div>
                  <h3>{signal.title}</h3>
                  <blockquote>“{signal.quote}”</blockquote>
                  <p><strong>Evidence:</strong> {signal.evidence}</p>
                  <p><strong>Next action:</strong> {signal.nextAction}</p>
                  <div className="reviewRow">
                    <a href={signal.sourceUrl} target="_blank" rel="noreferrer">Source</a>
                    <select value={signal.status} onChange={(event) => updateStatus(signal.id, event.target.value)}>
                      {reviewStatuses.map((status) => <option key={status}>{status}</option>)}
                    </select>
                  </div>
                </article>
              ))}
            </div>
            <div className="exportBar">
              <button className="button buttonPrimary" type="button" onClick={() => downloadText("lead-radar-preview.md", markdown, "text/markdown;charset=utf-8")}>Download Markdown</button>
              <button className="button buttonSecondary" type="button" onClick={() => downloadText("lead-radar-preview.csv", signals.map((signal) => `${signal.id},${signal.score},${signal.status},${JSON.stringify(signal.title)}`).join("\n"), "text/csv;charset=utf-8")}>Download CSV</button>
            </div>
          </div>
        </section>
      ) : null}
    </main>
  );
}
