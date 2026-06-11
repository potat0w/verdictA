import SiteLayout from "@/components/layout/SiteLayout";
import PageHero, {
  ContentSection,
  FeatureCard,
  LearnMoreLink,
} from "@/components/layout/PageSections";
import { cn, tokens } from "@/lib/theme";
import {
  AlertTriangle,
  Building2,
  Handshake,
  Shield,
  Target,
  User,
  Users,
  Zap,
} from "lucide-react";

const CLIENT_TYPES = [
  {
    icon: User,
    title: "Individuals",
    description:
      "We provide personalized services and exceptional support to individuals, ensuring they receive the attention needed for successful outcomes and lasting relationships.",
  },
  {
    icon: Building2,
    title: "Small Businesses",
    description:
      "Small businesses need legal help to handle regulations. A law firm can assist with contracts and compliance, allowing entrepreneurs to focus on growth.",
  },
  {
    icon: Building2,
    title: "Corporations",
    description:
      "Corporations and law firms collaborate to manage complex legal issues, ensuring regulatory compliance, mitigating risks, managing contracts, and handling litigation effectively.",
  },
];

const FIRM_CULTURE = [
  {
    icon: Zap,
    title: "High-Pressure",
    description: "Committed to excellence and exceptional results.",
  },
  {
    icon: Target,
    title: "Client-Focused",
    description: "Understanding needs and exceeding expectations consistently.",
  },
  {
    icon: Shield,
    title: "Ethical Standards",
    description: "Building trust through ethics and transparency.",
  },
];

export default function ServicesPage() {
  return (
    <SiteLayout>
      <PageHero
        eyebrow="Service"
        title="Legal Solutions for Every Client"
        description="From individuals to corporations, we deliver tailored legal support with collaborative teams and a culture built on excellence."
      />

      <ContentSection
        title="Who We Serve"
        subtitle="Personalized legal services scaled to your needs."
      >
        <div className="grid gap-6 md:grid-cols-3">
          {CLIENT_TYPES.map((client) => (
            <div
              key={client.title}
              className="group rounded-2xl border border-[var(--page-border)] bg-[var(--page-card)] p-8"
            >
              <div className={cn(tokens.iconBadge, "mb-5")}>
                <client.icon className="h-7 w-7" />
              </div>
              <h3 className="mb-3 text-xl font-semibold text-[var(--page-text)]">
                {client.title}
              </h3>
              <p className="mb-6 text-sm leading-relaxed text-[var(--page-text-muted)]">
                {client.description}
              </p>
              <LearnMoreLink href="/contact" />
            </div>
          ))}
        </div>
      </ContentSection>

      <ContentSection
        title="Collaborative Teams"
        subtitle="Working together to create innovative solutions."
        alt
      >
        <div className="grid items-center gap-10 lg:grid-cols-2">
          <div className="rounded-2xl border border-[var(--page-border)] bg-[var(--page-card)] p-8 md:p-10">
            <div className="mb-6 flex items-center gap-3">
              <div className={tokens.iconBadge}>
                <Users className="h-7 w-7" />
              </div>
              <h3 className="text-xl font-semibold">Team Approach</h3>
            </div>
            <p className="text-sm leading-relaxed text-[var(--page-text-muted)]">
              Our collaborative teams bring together diverse expertise to tackle
              complex legal challenges. By combining specialized knowledge across
              practice areas, we develop innovative solutions that address every
              facet of your legal needs.
            </p>
          </div>
          <div className="grid grid-cols-2 gap-4">
            {[
              "Cross-functional expertise",
              "Shared case strategy",
              "Real-time collaboration",
              "Unified client support",
            ].map((item) => (
              <div
                key={item}
                className="flex items-center gap-3 rounded-xl border border-[var(--page-border)] bg-[var(--page-hover)] px-4 py-3"
              >
                <Handshake
                  className="h-4 w-4 shrink-0"
                  style={{ color: "var(--accent)" }}
                />
                <span className="text-sm text-[var(--page-text)]">{item}</span>
              </div>
            ))}
          </div>
        </div>
      </ContentSection>

      <ContentSection title="Firm Culture">
        <div className="grid gap-6 md:grid-cols-3">
          {FIRM_CULTURE.map((item) => (
            <FeatureCard
              key={item.title}
              title={item.title}
              description={item.description}
              action={{ label: "Learn More", href: "/contact" }}
            />
          ))}
        </div>
      </ContentSection>

      <ContentSection
        title="Challenges Faced"
        subtitle="Strategic solutions for complex organizational obstacles."
        alt
      >
        <div className="grid gap-10 lg:grid-cols-2">
          <div>
            <p className="mb-6 text-sm leading-relaxed text-[var(--page-text-muted)]">
              Organizations face numerous complex challenges that can impede
              growth, including regulatory issues, legal risks, rapid
              technological changes, and reputational threats.
            </p>
            <p className="mb-8 text-sm leading-relaxed text-[var(--page-text-muted)]">
              Other struggles include optimizing operations, attracting talent,
              and entering new markets. Recognizing these pressures and having
              expertise in identifying challenges early, offering strategic
              insights, and creating effective solutions enable businesses to
              confidently overcome obstacles and achieve their goals.
            </p>
            <LearnMoreLink href="/contact" />
          </div>

          <div className="grid grid-cols-2 gap-4">
            {[
              "Regulatory compliance",
              "Legal risk mitigation",
              "Technology adaptation",
              "Reputation management",
              "Operational optimization",
              "Market expansion",
            ].map((challenge) => (
              <div
                key={challenge}
                className="flex items-start gap-3 rounded-xl border border-[var(--page-border)] bg-[var(--page-card)] p-4"
              >
                <AlertTriangle
                  className="mt-0.5 h-4 w-4 shrink-0"
                  style={{ color: "var(--accent)" }}
                />
                <span className="text-sm text-[var(--page-text)]">
                  {challenge}
                </span>
              </div>
            ))}
          </div>
        </div>
      </ContentSection>
    </SiteLayout>
  );
}
