import Link from "next/link";
import { cn, tokens } from "@/lib/theme";

interface PageHeroProps {
  eyebrow: string;
  title: string;
  description: string;
  children?: React.ReactNode;
}

export default function PageHero({
  eyebrow,
  title,
  description,
  children,
}: PageHeroProps) {
  return (
    <section className="relative overflow-hidden border-b border-[var(--page-border)]">
      <div
        className="absolute inset-0 opacity-40"
        style={{
          background:
            "radial-gradient(ellipse at 30% 20%, color-mix(in srgb, var(--accent) 15%, transparent), transparent 60%)",
        }}
      />
      <div className={cn(tokens.container, "relative py-16 md:py-24")}>
        <p className="mb-3 text-xs font-medium uppercase tracking-[0.25em] text-[var(--accent)]">
          {eyebrow}
        </p>
        <h1
          className={cn(
            tokens.heading,
            "mb-5 max-w-3xl text-4xl leading-tight md:text-5xl lg:text-6xl"
          )}
        >
          {title}
        </h1>
        <p className="max-w-2xl text-lg leading-relaxed text-[var(--page-text-muted)]">
          {description}
        </p>
        {children && <div className="mt-8">{children}</div>}
      </div>
    </section>
  );
}

interface ContentSectionProps {
  id?: string;
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  alt?: boolean;
}

export function ContentSection({
  id,
  title,
  subtitle,
  children,
  alt,
}: ContentSectionProps) {
  return (
    <section
      id={id}
      className={cn(
        tokens.section,
        alt && "bg-[var(--page-section-alt)]"
      )}
    >
      <div className={tokens.container}>
        <div className="mb-12 max-w-2xl">
          <h2 className={cn(tokens.heading, "mb-3 text-3xl md:text-4xl")}>
            {title}
          </h2>
          {subtitle && (
            <p className="text-[var(--page-text-muted)]">{subtitle}</p>
          )}
        </div>
        {children}
      </div>
    </section>
  );
}

interface FeatureCardProps {
  title: string;
  description: string;
  action?: { label: string; href: string };
}

export function FeatureCard({ title, description, action }: FeatureCardProps) {
  return (
    <div className="flex h-full flex-col rounded-2xl border border-[var(--page-border)] bg-[var(--page-card)] p-8">
      <h3 className="mb-3 text-xl font-semibold text-[var(--page-text)]">
        {title}
      </h3>
      <p className="flex-1 text-sm leading-relaxed text-[var(--page-text-muted)]">
        {description}
      </p>
      {action && (
        <Link
          href={action.href}
          className="mt-6 inline-flex text-sm font-medium text-[var(--accent)] hover:underline"
        >
          {action.label}
        </Link>
      )}
    </div>
  );
}

export function LearnMoreLink({ href = "#" }: { href?: string }) {
  return (
    <Link
      href={href}
      className="inline-flex items-center gap-1 text-sm font-medium text-[var(--accent)] hover:underline"
    >
      Learn More
    </Link>
  );
}
