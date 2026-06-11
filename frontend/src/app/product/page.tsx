import SiteLayout from "@/components/layout/SiteLayout";
import PageHero, {
  ContentSection,
  FeatureCard,
  LearnMoreLink,
} from "@/components/layout/PageSections";
import { cn, tokens } from "@/lib/theme";
import {
  BookOpen,
  Globe,
  Leaf,
  Receipt,
  Sparkles,
} from "lucide-react";

const EXPERTISE_AREAS = [
  { icon: Sparkles, label: "Intellectual Property" },
  { icon: Receipt, label: "Tax Law" },
  { icon: Leaf, label: "Environmental Regulations" },
  { icon: Globe, label: "International Trade Law" },
];

const MARKETING_ITEMS = [
  { label: "Brand Recognition", value: 20 },
  { label: "Client Acquisition", value: 20 },
  { label: "Digital Presence", value: 20 },
  { label: "Market Analysis", value: 20 },
  { label: "Ethical Outreach", value: 20 },
];

const CHART_DATA = [
  { item: "Item 1", s1: 35, s2: 28, s3: 22 },
  { item: "Item 2", s1: 42, s2: 30, s3: 18 },
  { item: "Item 3", s1: 28, s2: 38, s3: 25 },
  { item: "Item 4", s1: 45, s2: 22, s3: 32 },
];

export default function ProductPage() {
  return (
    <SiteLayout>
      <PageHero
        eyebrow="Product"
        title="Legal Expertise"
        description="Our legal team excels in specialized knowledge across various areas of law, delivering informed advice and precision representation."
      />

      <ContentSection
        title="Specialized Knowledge"
        subtitle="Deep expertise across complex legal domains."
      >
        <div className="grid gap-10 lg:grid-cols-2">
          <div className="rounded-2xl border border-[var(--page-border)] bg-[var(--page-card)] p-8 md:p-10">
            <div className="mb-6 flex items-center gap-3">
              <div className={tokens.iconBadge}>
                <BookOpen className="h-7 w-7" />
              </div>
              <h3 className="text-xl font-semibold">Our Expertise</h3>
            </div>
            <p className="mb-6 text-sm leading-relaxed text-[var(--page-text-muted)]">
              Our expertise encompasses intellectual property, tax law,
              environmental regulations, and international trade law. Our lawyers
              are adept at handling complex legal issues, delivering informed
              advice, and representing clients in specialized legal matters with
              precision.
            </p>
            <p className="mb-8 text-sm leading-relaxed text-[var(--page-text-muted)]">
              We prioritize staying current with the latest changes and
              developments within these fields to provide accurate and effective
              guidance. Our commitment to specialization often involves obtaining
              additional certifications and engaging in continuous education to
              maintain the highest level of proficiency.
            </p>
            <LearnMoreLink href="/services" />
          </div>

          <div className="grid grid-cols-2 gap-4">
            {EXPERTISE_AREAS.map(({ icon: Icon, label }) => (
              <div
                key={label}
                className="flex flex-col items-center justify-center rounded-2xl border border-[var(--page-border)] bg-[var(--page-card)] p-6 text-center"
              >
                <div className={cn(tokens.iconBadge, "mb-3 h-14 w-14")}>
                  <Icon className="h-6 w-6" />
                </div>
                <span className="text-sm font-medium text-[var(--page-text)]">
                  {label}
                </span>
              </div>
            ))}
          </div>
        </div>
      </ContentSection>

      <ContentSection
        title="Marketing Strategies"
        subtitle="Robust, ethically-driven strategies to enhance your brand and drive growth."
        alt
      >
        <div className="grid gap-10 lg:grid-cols-2">
          <div>
            <p className="mb-6 text-sm leading-relaxed text-[var(--page-text-muted)]">
              We create robust, ethically-driven marketing strategies to enhance
              your brand and drive growth. Our process starts with analyzing
              market trends and your business goals, followed by tailored
              strategies based on data-driven insights.
            </p>
            <p className="mb-8 text-sm leading-relaxed text-[var(--page-text-muted)]">
              Whether aiming to boost brand recognition, attract clients, or
              optimize your digital presence, our expert team delivers
              comprehensive, customized solutions while upholding integrity and
              professionalism.
            </p>
            <LearnMoreLink href="/contact" />

            <div className="mt-10 space-y-3">
              {MARKETING_ITEMS.map((item) => (
                <div key={item.label}>
                  <div className="mb-1 flex justify-between text-xs text-[var(--page-text-muted)]">
                    <span>{item.label}</span>
                    <span>{item.value}%</span>
                  </div>
                  <div className="h-2 overflow-hidden rounded-full bg-[var(--page-hover)]">
                    <div
                      className="h-full rounded-full"
                      style={{
                        width: `${item.value}%`,
                        background: "var(--accent)",
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-2xl border border-[var(--page-border)] bg-[var(--page-card)] p-8">
            <p className="mb-6 text-xs font-medium uppercase tracking-wider text-[var(--page-text-muted)]">
              Performance Overview
            </p>
            <div className="mb-6 flex justify-center gap-6">
              {MARKETING_ITEMS.slice(0, 5).map((item, i) => (
                <div key={item.label} className="flex flex-col items-center gap-2">
                  <div
                    className="h-16 w-16 rounded-full border-4"
                    style={{
                      borderColor: `color-mix(in srgb, var(--accent) ${80 - i * 12}%, transparent)`,
                      background: `color-mix(in srgb, var(--accent) ${20 + i * 8}%, transparent)`,
                    }}
                  />
                  <span className="text-[10px] text-[var(--page-text-muted)]">
                    {item.label.split(" ")[0]}
                  </span>
                </div>
              ))}
            </div>

            <div className="space-y-4">
              <div className="flex gap-4 text-[10px] text-[var(--page-text-muted)]">
                <span className="flex items-center gap-1">
                  <span
                    className="h-2 w-2 rounded-full"
                    style={{ background: "var(--accent)" }}
                  />
                  Series 1
                </span>
                <span className="flex items-center gap-1">
                  <span className="h-2 w-2 rounded-full bg-[var(--page-text-muted)]" />
                  Series 2
                </span>
                <span className="flex items-center gap-1">
                  <span className="h-2 w-2 rounded-full bg-[var(--page-border)]" />
                  Series 3
                </span>
              </div>
              {CHART_DATA.map((row) => (
                <div key={row.item} className="flex items-end gap-2">
                  <span className="w-12 shrink-0 text-[10px] text-[var(--page-text-muted)]">
                    {row.item}
                  </span>
                  <div className="flex flex-1 items-end gap-1">
                    {[row.s1, row.s2, row.s3].map((val, i) => (
                      <div
                        key={i}
                        className="flex-1 rounded-t-sm"
                        style={{
                          height: `${val * 2}px`,
                          background:
                            i === 0
                              ? "var(--accent)"
                              : i === 1
                                ? "color-mix(in srgb, var(--accent) 50%, var(--page-text-muted))"
                                : "var(--page-hover)",
                        }}
                      />
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </ContentSection>

      <ContentSection title="Why Choose Our Product">
        <div className="grid gap-6 md:grid-cols-3">
          <FeatureCard
            title="Precision Advice"
            description="Specialized legal guidance tailored to your unique situation and industry requirements."
            action={{ label: "Learn More", href: "/services" }}
          />
          <FeatureCard
            title="Continuous Learning"
            description="Our team maintains certifications and stays updated on the latest legal developments."
            action={{ label: "Learn More", href: "/services" }}
          />
          <FeatureCard
            title="Ethical Marketing"
            description="Brand growth strategies built on integrity, professionalism, and data-driven insights."
            action={{ label: "Learn More", href: "/contact" }}
          />
        </div>
      </ContentSection>
    </SiteLayout>
  );
}
