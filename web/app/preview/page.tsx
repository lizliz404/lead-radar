import type { Metadata } from "next";
import { PreviewClient } from "./preview-client";

export const metadata: Metadata = {
  title: "Instant Preview",
  description:
    "Paste a market brief, see ranked Reddit-style demand signals and review status, and test the evidence workflow before you pay for a full scan.",
  alternates: { canonical: "/preview" },
};

export default function PreviewPage() {
  return <PreviewClient operatorAppUrl={process.env.NEXT_PUBLIC_OPERATOR_APP_URL || ""} />;
}
