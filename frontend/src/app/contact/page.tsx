"use client";

import SiteLayout from "@/components/layout/SiteLayout";
import InnerPage from "@/components/layout/InnerPage";

export default function ContactPage() {
  return (
    <SiteLayout>
      <InnerPage title="Contact">
        <p>
          Reach us for questions about VerdictAI. For constitutional questions,
          open the chat — that is what we built for.
        </p>
        <p style={{ marginTop: 24 }}>
          <a href="mailto:hello@verdictai.bd">hello@verdictai.bd</a>
          <br />
          Dhaka, Bangladesh
        </p>
      </InnerPage>
    </SiteLayout>
  );
}
