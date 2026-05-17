import type { Metadata } from "next";
import { PreviewClient } from "./preview-client";

export const metadata: Metadata = {
  title: "Instant Preview",
  description: "Try the Lead Radar brief-to-evidence workflow without waiting for the Streamlit operator console.",
  alternates: { canonical: "/preview" },
};

export default function PreviewPage() {
  return <PreviewClient operatorAppUrl={process.env.NEXT_PUBLIC_OPERATOR_APP_URL || ""} />;
}
