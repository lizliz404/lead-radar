export type ExampleReport = {
  slug: string;
  title: string;
  market: string;
  summary: string;
  scanned: string;
  signals: string;
  highIntent: string;
  communities: string[];
  painClusters: { severity: "High" | "Medium"; text: string }[];
  evidence: { label: string; quote: string; intent: "High" | "Very high" | "Medium"; action: string }[];
  positioning: string[];
};

export const reports: ExampleReport[] = [
  {
    slug: "shopify-inventory-forecasting",
    title: "Shopify Inventory Forecasting",
    market: "Shopify sellers managing cash flow, reorder points, and stockouts",
    summary:
      "The strongest commercial signal is not demand for a full ERP. It is demand for a focused reorder and forecasting layer that replaces fragile spreadsheets without forcing merchants into enterprise inventory software.",
    scanned: "Simulated: 40 posts across 2 communities",
    signals: "12 demand signals",
    highIntent: "5 high-intent threads",
    communities: ["r/shopify", "r/ecommerce"],
    painClusters: [
      { severity: "High", text: "Manual spreadsheet forecasting creates cash-flow mistakes and late reorders." },
      { severity: "High", text: "Multi-warehouse stock counts are hard to sync before Q4 spikes." },
      { severity: "Medium", text: "Existing inventory tools feel too expensive or too complex for small teams." },
    ],
    evidence: [
      {
        label: "Spreadsheet pain",
        quote:
          "We are doing 2M/yr and still using Google Sheets for forecasting. I'd happily pay $100/mo for something that tells me exactly when to reorder based on 30-day velocity.",
        intent: "Very high",
        action: "Validate willingness to pay around stockout prevention and trapped cash recovery.",
      },
      {
        label: "Paid solution request",
        quote: "Does anyone know a paid app that just handles reorder points accurately without becoming a full ERP?",
        intent: "High",
        action: "Position against spreadsheets first, not against enterprise ERPs.",
      },
    ],
    positioning: [
      "Lead with 'prevent stockouts without buying an ERP.'",
      "Anchor pricing against recovered cash flow, not dashboard convenience.",
      "Use spreadsheet replacement copy: fewer formulas, fewer emergency reorders, fewer dead-stock surprises.",
    ],
  },
  {
    slug: "stripe-analytics-for-indie-hackers",
    title: "Stripe Analytics for Indie Hackers",
    market: "Solo founders and tiny SaaS teams tracking churn, trials, revenue, and alerts",
    summary:
      "The market does not need another generic analytics dashboard. It wants lightweight revenue alerts and founder-readable explanations for churn, failed payments, and trial conversion problems.",
    scanned: "Simulated: 35 posts across 3 communities",
    signals: "9 demand signals",
    highIntent: "3 high-intent threads",
    communities: ["r/indiehackers", "r/SaaS", "r/startups"],
    painClusters: [
      { severity: "High", text: "Stripe data is available, but turning it into decisions still takes manual work." },
      { severity: "High", text: "Founders miss churn/failure events until revenue already moved." },
      { severity: "Medium", text: "Existing analytics tools feel priced and packaged for larger teams." },
    ],
    evidence: [
      {
        label: "Alerting gap",
        quote: "I don't need a giant BI tool. I need Slack to tell me when MRR drops and why it probably happened.",
        intent: "High",
        action: "Test a narrow alert-first MVP before building a dashboard suite.",
      },
      {
        label: "Founder-readable insight",
        quote: "Stripe has the data, but I still end up exporting CSVs every Monday to understand what changed.",
        intent: "Medium",
        action: "Emphasize weekly revenue briefings rather than charts.",
      },
    ],
    positioning: [
      "Sell 'Monday revenue brief' before 'analytics dashboard.'",
      "Target founders below the threshold where Baremetrics-style tools feel worth the subscription.",
      "Start with churn, failed payments, and trial conversion alerts.",
    ],
  },
  {
    slug: "pet-insurance-claims",
    title: "Pet Insurance Claims",
    market: "US pet owners dealing with denied claims, reimbursement delays, and surprise vet bills",
    summary:
      "The repeated pain is not discovering insurance. It is understanding policy exclusions, predicting reimbursement outcomes, and fighting confusing claim decisions after a stressful vet visit.",
    scanned: "Simulated: 45 posts across 4 communities",
    signals: "14 demand signals",
    highIntent: "4 high-intent threads",
    communities: ["r/dogs", "r/cats", "r/personalfinance", "r/Insurance"],
    painClusters: [
      { severity: "High", text: "Owners cannot predict whether expensive procedures will be reimbursed." },
      { severity: "High", text: "Denied claims create anger because policy language is hard to interpret." },
      { severity: "Medium", text: "Comparison shopping is confusing because coverage details differ by provider." },
    ],
    evidence: [
      {
        label: "Denied claim frustration",
        quote: "I paid premiums for years and still have no idea why this emergency visit was considered pre-existing.",
        intent: "High",
        action: "Test a claim-explanation assistant before a full insurance marketplace.",
      },
      {
        label: "Pre-purchase uncertainty",
        quote: "Is there any way to know what they will actually reimburse before I pick a plan?",
        intent: "High",
        action: "Position around reimbursement clarity, not just cheaper quotes.",
      },
    ],
    positioning: [
      "Lead with 'understand what your policy will actually cover.'",
      "Avoid sounding like another insurance comparison affiliate page.",
      "Build trust with plain-English explanations and examples, not generic savings claims.",
    ],
  },
];

export function getReport(slug: string) {
  return reports.find((report) => report.slug === slug);
}
