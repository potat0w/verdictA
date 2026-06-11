import SiteLayout from "@/components/layout/SiteLayout";
import PageHero from "@/components/layout/PageSections";
import Button from "@/components/ui/Button";
import { cn, tokens } from "@/lib/theme";
import { Clock, Mail, MapPin, Phone } from "lucide-react";

const CONTACT_INFO = [
  {
    icon: Mail,
    label: "Email",
    value: "contact@verdictai.com",
    href: "mailto:contact@verdictai.com",
  },
  {
    icon: Phone,
    label: "Phone",
    value: "+880 123 456 789",
    href: "tel:+880123456789",
  },
  {
    icon: MapPin,
    label: "Location",
    value: "Dhaka, Bangladesh",
  },
  {
    icon: Clock,
    label: "Hours",
    value: "Mon – Fri, 9AM – 6PM",
  },
];

export default function ContactPage() {
  return (
    <SiteLayout>
      <PageHero
        eyebrow="Contact"
        title="Get In Touch"
        description="Schedule a consultation with our legal team. We're here to help with your legal questions and business needs."
      />

      <section className={cn(tokens.section, "bg-[var(--page-section-alt)]")}>
        <div className={tokens.container}>
          <div className="grid gap-12 lg:grid-cols-5">
            <div className="lg:col-span-2">
              <h2 className={cn(tokens.heading, "mb-6 text-2xl")}>
                Contact Information
              </h2>
              <div className="space-y-4">
                {CONTACT_INFO.map((item) => (
                  <div
                    key={item.label}
                    className="flex items-start gap-4 rounded-xl border border-[var(--page-border)] bg-[var(--page-card)] p-5"
                  >
                    <div className={tokens.iconBadge}>
                      <item.icon className="h-5 w-5" />
                    </div>
                    <div>
                      <p className="text-xs font-medium uppercase tracking-wider text-[var(--page-text-muted)]">
                        {item.label}
                      </p>
                      {item.href ? (
                        <a
                          href={item.href}
                          className="text-sm font-medium text-[var(--page-text)] hover:text-[var(--accent)]"
                        >
                          {item.value}
                        </a>
                      ) : (
                        <p className="text-sm font-medium text-[var(--page-text)]">
                          {item.value}
                        </p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="lg:col-span-3">
              <form className="rounded-2xl border border-[var(--page-border)] bg-[var(--page-card)] p-8 md:p-10">
                <h2 className={cn(tokens.heading, "mb-6 text-2xl")}>
                  Send a Message
                </h2>
                <div className="space-y-5">
                  <div className="grid gap-5 md:grid-cols-2">
                    <input
                      type="text"
                      placeholder="Your name"
                      className="rounded-xl border border-[var(--page-border)] bg-[var(--page-input-bg)] px-4 py-3 text-sm text-[var(--page-text)] outline-none focus:border-[var(--accent)]"
                    />
                    <input
                      type="email"
                      placeholder="your@email.com"
                      className="rounded-xl border border-[var(--page-border)] bg-[var(--page-input-bg)] px-4 py-3 text-sm text-[var(--page-text)] outline-none focus:border-[var(--accent)]"
                    />
                  </div>
                  <input
                    type="text"
                    placeholder="Subject"
                    className="w-full rounded-xl border border-[var(--page-border)] bg-[var(--page-input-bg)] px-4 py-3 text-sm text-[var(--page-text)] outline-none focus:border-[var(--accent)]"
                  />
                  <textarea
                    rows={5}
                    placeholder="Describe your legal matter..."
                    className="w-full rounded-xl border border-[var(--page-border)] bg-[var(--page-input-bg)] px-4 py-3 text-sm text-[var(--page-text)] outline-none focus:border-[var(--accent)]"
                  />
                  <Button size="lg" className="w-full md:w-auto">
                    Submit Request
                  </Button>
                </div>
              </form>
            </div>
          </div>
        </div>
      </section>
    </SiteLayout>
  );
}
