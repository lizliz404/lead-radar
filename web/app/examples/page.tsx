import type { Metadata } from "next";
import Link from "next/link";
import { reports } from "./reports";

export const metadata: Metadata = {
  title: "Simulated Demand Report Formats",
  description:
    "Read simulated Lead Radar report formats showing ranked Reddit demand signals, pain clusters, evidence slots, review status, and positioning notes.",
  alternates: { canonical: "/examples" },
};

export default function ExamplesPage() {
  return (
    <main className="examplePage">
      <section className="container exampleHero">
        <Link href="/" className="backLink">← Back to Lead Radar</Link>
        <p className="eyebrow">Sample reports</p>
        <h1>Inspect the artifact before you run the agent.</h1>
        <p className="subhead">
          These are simulated examples, not live Reddit scan outputs. They show the report structure Lead Radar is designed to produce: market summary, pain clusters, source-linked evidence slots, review status, and next actions.
        </p>
      </section>

      <section className="container reportList">
        {reports.map((report) => (
          <Link className="reportListCard" href={`/examples/${report.slug}`} key={report.slug}>
            <div>
              <p className="eyebrow">{report.market}</p>
              <h2>{report.title}</h2>
              <p>{report.summary}</p>
            </div>
            <div className="reportStats">
              <span>{report.scanned}</span>
              <span>{report.signals}</span>
              <span>{report.highIntent}</span>
            </div>
          </Link>
        ))}
      </section>
    </main>
  );
}
