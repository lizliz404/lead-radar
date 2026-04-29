const appUrl = process.env.NEXT_PUBLIC_APP_URL || "https://beds-chest-bacterial-anne.trycloudflare.com";

const useCases = [
  "Validate a SaaS idea from Reddit pain points",
  "Find users asking for alternatives or paid help",
  "Turn community posts into a Markdown insight report",
  "Review, tag, and export demand signals",
];

const examples = [
  "Research Shopify sellers struggling with inventory forecasting and cash-flow planning. Look back 7 days and return 20 posts.",
  "Find demand signals from indie hackers looking for better Stripe analytics, churn alerts, or revenue dashboards.",
  "Analyze US pet owners dealing with insurance claims, denied reimbursements, and high vet bills.",
];

const seoLinks = [
  "Reddit demand research tool",
  "Market validation from Reddit",
  "Customer pain point finder",
  "SaaS demand signal scanner",
  "Commercial insight agent",
  "Reddit lead finder",
];

export default function Home() {
  return (
    <main>
      <section className="hero">
        <nav className="nav" aria-label="Primary">
          <a className="brand" href="#top" aria-label="Lead Radar home">
            <span className="brandMark">LR</span>
            <span>Lead Radar</span>
          </a>
          <div className="navLinks">
            <a href="#how">How it works</a>
            <a href="#use-cases">Use cases</a>
            <a href={appUrl}>Open app</a>
          </div>
        </nav>

        <div id="top" className="heroGrid">
          <div className="heroCopy">
            <p className="eyebrow">Reddit market validation · demand signals · commercial insight</p>
            <h1>Turn a market idea into evidence-backed Reddit demand research.</h1>
            <p className="subhead">
              Lead Radar scans public community posts, scores buying intent and pain signals, and gives founders a report they can actually use for product and growth decisions.
            </p>
            <div className="ctaRow">
              <a className="primaryCta" href={appUrl}>Try the live app</a>
              <a className="secondaryCta" href="#examples">View example briefs</a>
            </div>
            <p className="note">The current app runs as a Streamlit workflow behind this SEO-friendly landing page.</p>
          </div>

          <div className="demoCard" aria-label="Product preview">
            <div className="windowBar"><span /><span /><span /></div>
            <p className="label">Market / product brief</p>
            <div className="promptBox">
              Research Shopify sellers struggling with inventory forecasting and cash-flow planning. Look back 7 days and return 20 posts/signals.
            </div>
            <div className="miniGrid">
              <div><strong>20</strong><span>posts</span></div>
              <div><strong>8</strong><span>signals</span></div>
              <div><strong>3</strong><span>strong intent</span></div>
            </div>
            <div className="leadItem"><b>Evidence:</b> “manual spreadsheet forecasting is killing our cash flow…”</div>
            <div className="leadItem"><b>Action:</b> validate willingness to pay before building another dashboard.</div>
          </div>
        </div>
      </section>

      <section id="how" className="section split">
        <div>
          <p className="eyebrow">How it works</p>
          <h2>One brief in. A scan plan and report out.</h2>
        </div>
        <div className="steps">
          <article><span>1</span><h3>Describe the market</h3><p>Write a plain-language brief: user segment, pain, market, timeframe, or number of posts.</p></article>
          <article><span>2</span><h3>Generate scan parameters</h3><p>The app decomposes the brief into keywords, communities, intent phrases, filters, and limits.</p></article>
          <article><span>3</span><h3>Review demand signals</h3><p>Inspect lead cards, source links, confidence, evidence, next actions, CSV, and Markdown report.</p></article>
        </div>
      </section>

      <section id="use-cases" className="section">
        <p className="eyebrow">Use cases</p>
        <h2>Built for early market falsification, not vanity dashboards.</h2>
        <div className="cardGrid">
          {useCases.map((item) => <article key={item} className="plainCard">{item}</article>)}
        </div>
      </section>

      <section id="examples" className="section examples">
        <p className="eyebrow">Example briefs</p>
        <h2>Start with natural language, not a form.</h2>
        <div className="exampleGrid">
          {examples.map((example) => <blockquote key={example}>{example}</blockquote>)}
        </div>
      </section>

      <section className="section seoBlock">
        <p className="eyebrow">SEO surface</p>
        <h2>Search terms this product can own.</h2>
        <div className="chips">
          {seoLinks.map((link) => <span key={link}>{link}</span>)}
        </div>
      </section>

      <section className="finalCta">
        <h2>Stop guessing whether a market wants the thing.</h2>
        <p>Run a small scan, inspect evidence, and decide what to build — or kill — next.</p>
        <a className="primaryCta" href={appUrl}>Open Lead Radar app</a>
      </section>
    </main>
  );
}
