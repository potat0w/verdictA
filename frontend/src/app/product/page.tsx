"use client";

import SiteLayout from "@/components/layout/SiteLayout";
import InnerPage from "@/components/layout/InnerPage";

export default function ProductPage() {
  return (
    <SiteLayout>
      <InnerPage title="Product">
        <p>
          VerdictAI is a bilingual constitutional companion. Ask in Bangla or
          English and receive answers grounded in the official text of the
          Constitution of Bangladesh.
        </p>
      </InnerPage>
    </SiteLayout>
  );
}
