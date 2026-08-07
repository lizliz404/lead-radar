import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { getReport, reports } from "../reports";

type PageProps = {
  params: Promise<{ slug: string }>;
};

export function generateStaticParams() {
  return reports.map((report) => ({ slug: report.slug }));
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { slug } = await params;
  const report = getReport(slug);
  if (!report) return {};

  return {
    title: { absolute: `${report.title} — sample · Lead Radar` },
    description: `Simulated Lead Radar report for ${report.title}: ranked Reddit demand signals, pain clusters, evidence slots, and review-status format.`,
    alternates: { canonical: `/examples/${report.slug}` },
  };
}

export default async function ExampleReportPage({ params }: PageProps) {
  const { slug } = await params;
  const report = getReport(slug);
  if (!report) notFound();

  return (
    <main className="examplePage">
      <section className="container exampleHero reportHero">
        <Link href="/examples" className="backLink">← All sample reports</Link>
        <p className="eyebrow">Simulated Reddit demand report</p>
        <h1>{report.title}</h1>
        <p className="subhead">{report.summary}</p>
        <p className="note">Format sample only. This page uses simulated evidence to show the artifact shape; real reports should include source links and review status.</p>
        <div className="reportStats heroStats">
          <span>{report.scanned}</span>
          <span>{report.signals}</span>
          <span>{report.highIntent}</span>
        </div>
      </section>

      <section className="container reportLayout">
        <aside className="reportAside">
          <h2>Scan context</h2>
          <p>{report.market}</p>
          <h3>Communities</h3>
          <ul>
            {report.communities.map((community) => <li key={community}>{community}</li>)}
          </ul>
        </aside>

        <article className="reportBody">
          <section>
            <p className="eyebrow">1. Top pain clusters</p>
            {report.painClusters.map((cluster) => (
              <div className="painCluster" key={cluster.text}>
                <strong>[Severity: {cluster.severity}]</strong>
                <p>{cluster.text}</p>
              </div>
            ))}
          </section>

          <section>
            <p className="eyebrow">2. Ranked evidence</p>
            {report.evidence.map((item) => (
              <div className="evidenceBlock" key={item.quote}>
                <div className="evidenceTopline">
                  <span>{item.label}</span>
                  <strong>Intent: {item.intent}</strong>
                </div>
                <blockquote>“{item.quote}”</blockquote>
                <p><b>Next action:</b> {item.action}</p>
              </div>
            ))}
          </section>

          <section>
            <p className="eyebrow">3. Suggested positioning</p>
            <ul className="positioningList">
              {report.positioning.map((item) => <li key={item}>{item}</li>)}
            </ul>
          </section>

          <section className="reportCta">
            <h2>Want this for your market?</h2>
            <p>Use this format as the decision artifact: if the evidence is weak, kill the idea early; if it is strong, take the exact language into customer interviews.</p>
            <Link className="button buttonPrimary" href="/">Back to Lead Radar</Link>
          </section>
        </article>
      </section>
    </main>
  );
}
