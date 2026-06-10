"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Send,
  Bot,
  User,
  Loader2,
  Scale,
  BookOpen,
  Shield,
  FileText,
  Building2,
  Gavel,
  ArrowRight,
  Star,
  Mail,
  Phone,
  MapPin,
  ChevronRight,
  Quote,
  Target,
  TrendingUp,
  Briefcase,
  Heart,
} from "lucide-react";
import { FaGavel } from "react-icons/fa";
import { askLegalQuestion, clearToken, getToken } from "@/lib/api";
import { cn, tokens } from "@/lib/theme";
import Button from "@/components/ui/Button";
import Card from "@/components/ui/Card";
import Image from "next/image";

interface Message {
  id: string;
  content: string;
  role: "user" | "assistant";
  timestamp: Date;
}

const NAV_LINKS = [
  { href: "#services", label: "Services" },
  { href: "#about", label: "About" },
  { href: "#team", label: "Team" },
  { href: "#contact", label: "Contact" },
] as const;

const SERVICES = [
  {
    name: "Contract Law",
    icon: FileText,
    description: "Drafting, reviewing, and negotiating contracts",
  },
  {
    name: "Property Law",
    icon: Building2,
    description: "Real estate transactions and property disputes",
  },
  {
    name: "Criminal Law",
    icon: Gavel,
    description: "Criminal defense and legal representation",
  },
  {
    name: "Business Law",
    icon: Briefcase,
    description: "Corporate legal services and compliance",
  },
  {
    name: "Family Law",
    icon: Heart,
    description: "Divorce, custody, and family matters",
  },
  {
    name: "Civil Litigation",
    icon: Scale,
    description: "Dispute resolution and court representation",
  },
] as const;

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "1",
      content:
        "Hello! I'm VerdictAI, your legal assistant. I can help you with legal questions using my knowledge of legal texts and regulations. What would you like to know?",
      role: "assistant",
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [showChat, setShowChat] = useState(false);
  const [hasToken, setHasToken] = useState(false);

  useEffect(() => {
    setHasToken(!!getToken());
    const onStorage = () => setHasToken(!!getToken());
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      content: input.trim(),
      role: "user",
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    try {
      const data = await askLegalQuestion(input.trim());

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: data.answer,
        role: "assistant",
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch {
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        content:
          "I apologize, but I'm having trouble connecting to my legal database right now. Please try again in a moment.",
        role: "assistant",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  if (showChat) {
    return (
      <div className={cn("flex flex-col h-screen", tokens.bg.gradient)}>
        {/* Header */}
        <header className="bg-[rgba(15,28,36,0.9)] shadow-sm">
          <div
            className={cn(
              tokens.container,
              "py-4 flex items-center justify-between"
            )}
          >
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2">
                <FaGavel className="text-2xl text-[var(--primary-gold)]" />
                <h1 className="text-xl font-bold">VerdictAI</h1>
              </div>
              <div className="flex items-center gap-1 text-sm text-white/70">
                <BookOpen className="w-4 h-4" />
                <span>Legal Assistant</span>
              </div>
            </div>
            <button
              onClick={() => setShowChat(false)}
              className="text-white/80 hover:text-white"
            >
              ← Back to Home
            </button>
          </div>
        </header>

        {/* Chat Container */}
        <div className="flex-1 overflow-hidden">
          <div className={cn(tokens.container, "h-full flex flex-col")}>
            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {messages.map((message) => (
                <div
                  key={message.id}
                  className={cn(
                    "flex gap-3",
                    message.role === "user" ? "justify-end" : "justify-start"
                  )}
                >
                  <div
                    className={cn(
                      "flex gap-3 max-w-[80%]",
                      message.role === "user" ? "flex-row-reverse" : "flex-row"
                    )}
                  >
                    <div
                      className={cn(
                        "flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center",
                        message.role === "user"
                          ? "bg-[#1E5A47] text-white"
                          : "bg-[rgba(200,171,127,0.18)] text-[var(--primary-gold)]"
                      )}
                    >
                      {message.role === "user" ? (
                        <User className="w-4 h-4" />
                      ) : (
                        <Bot className="w-4 h-4" />
                      )}
                    </div>
                    <div
                      className={cn(
                        "rounded-2xl px-4 py-3",
                        message.role === "user"
                          ? "bg-[#1E5A47] text-white"
                          : "bg-[rgba(15,28,36,0.85)]"
                      )}
                    >
                      <p className="text-sm leading-relaxed whitespace-pre-wrap">
                        {message.content}
                      </p>
                      <p
                        className={cn(
                          "text-xs mt-2",
                          message.role === "user"
                            ? "text-white/70"
                            : "text-white/60"
                        )}
                      >
                        {message.timestamp.toLocaleTimeString([], {
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </p>
                    </div>
                  </div>
                </div>
              ))}

              {isLoading && (
                <div className="flex gap-3 justify-start">
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-[rgba(200,171,127,0.18)] flex items-center justify-center">
                    <Bot className="w-4 h-4 text-[var(--primary-gold)]" />
                  </div>
                  <div className="bg-[rgba(15,28,36,0.85)] rounded-2xl px-4 py-3">
                    <div className="flex items-center gap-2">
                      <Loader2 className="w-4 h-4 animate-spin text-[var(--primary-gold)]" />
                      <span className="text-sm text-white/80">
                        Analyzing legal documents...
                      </span>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Input Form */}
            <div className="bg-[rgba(15,28,36,0.9)] p-4">
              <form onSubmit={handleSubmit} className={tokens.container}>
                <div className="flex gap-3">
                  <div className="flex-1 relative">
                    <input
                      type="text"
                      value={input}
                      onChange={(e) => setInput(e.target.value)}
                      placeholder="Ask me about legal matters, regulations, or case law..."
                      className="w-full px-4 py-3 pr-12 rounded-2xl bg-[#0e1a22] text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-[var(--primary-gold)] focus:border-transparent"
                      disabled={isLoading}
                    />
                    <button
                      type="submit"
                      disabled={!input.trim() || isLoading}
                      className="absolute right-3 top-1/2 -translate-y-1/2 rounded-lg bg-[var(--primary-gold)] text-[#0f1c24] hover:brightness-110 p-2.5 border-none transition-all focus:outline-none focus:ring-2 focus:ring-[var(--primary-gold)] disabled:opacity-50"
                      aria-label="Send message"
                    >
                      <Send className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </form>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      {/* Navigation */}
      <nav className="bg-[rgba(15,28,36,0.9)] backdrop-blur-md sticky top-0 z-50">
        <div className={tokens.container}>
          <div className="flex justify-between items-center py-4">
            <div className="flex items-center gap-3">
              <FaGavel className="text-3xl text-[var(--primary-gold)]" />
              <div>
                <h1 className="text-2xl font-bold">VerdictAI</h1>
                <p className="text-xs text-[var(--primary-gold)]">
                  advocate & law firm
                </p>
              </div>
            </div>
            <div className="hidden md:flex items-center gap-8 text-white/80">
              {NAV_LINKS.map((link) => (
                <a
                  key={link.href}
                  href={link.href}
                  className="hover:text-[var(--primary-gold)] transition-colors"
                >
                  {link.label}
                </a>
              ))}
            </div>
            <div className="flex items-center gap-3">
              {hasToken ? (
                <>
                  <Link
                    href="/profile"
                    className="text-white/80 hover:text-[var(--primary-gold)]"
                  >
                    Profile
                  </Link>
                  <Button
                    variant="outline"
                    onClick={() => {
                      clearToken();
                      setHasToken(false);
                    }}
                  >
                    Logout
                  </Button>
                </>
              ) : (
                <>
                  <Link
                    href="/login"
                    className="text-white/80 hover:text-[var(--primary-gold)]"
                  >
                    Log in
                  </Link>
                  <Link href="/signup">
                    <Button variant="outline">Sign up</Button>
                  </Link>
                </>
              )}
            </div>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className={cn("relative overflow-hidden", tokens.section)}>
        <div className={tokens.container}>
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <div className="text-center lg:text-left">
              <h1
                className={cn(
                  tokens.heading,
                  "text-5xl md:text-6xl mb-6 leading-tight"
                )}
              >
                Specifically Designed For{" "}
                <span className={tokens.text.gold}>Law Firm</span>
              </h1>
              <p className="text-xl md:text-2xl text-white/80 mb-8 max-w-2xl">
                Our AI-powered legal assistant provides customer-centric advice
                to corporations and individuals, backed by comprehensive legal
                knowledge.
              </p>
              <div className="flex flex-col sm:flex-row gap-4 justify-center lg:justify-start">
                <Button
                  onClick={() => setShowChat(true)}
                  size="lg"
                  className="gap-2 bg-[var(--primary-gold)] text-[#0f1c24] hover:brightness-110 px-6 py-3 rounded-lg font-semibold transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--primary-gold)] border-none"
                >
                  Ask Legal Question
                  <ArrowRight className="w-5 h-5" />
                </Button>
              </div>
            </div>
            <div className="relative">
              <div className="relative w-full aspect-[4/3] rounded-2xl overflow-hidden shadow-2xl">
                <Image
                  src="/hero.jpg"
                  alt="Law firm hero"
                  fill
                  priority
                  className="object-cover"
                />
              </div>
            </div>
          </div>
        </div>

        {/* Background Pattern */}
        <div className="absolute inset-0 -z-10">
          <div className="absolute inset-0 bg-gradient-to-r from-black/30 to-black/10"></div>
          <div className="absolute top-0 left-0 w-full h-full opacity-10">
            <div className="absolute top-20 left-20 w-32 h-32 border border-[rgba(200,171,127,0.3)] rounded-full"></div>
            <div className="absolute top-40 right-20 w-24 h-24 border border-[rgba(200,171,127,0.2)] rounded-full"></div>
            <div className="absolute bottom-20 left-1/4 w-16 h-16 border border-[rgba(200,171,127,0.25)] rounded-full"></div>
          </div>
        </div>
      </section>

      {/* Services Section */}
      <section id="services" className={cn(tokens.section, "bg-black/20")}>
        <div className={tokens.container}>
          <div className="text-center mb-16">
            <h2 className={cn(tokens.heading, "text-4xl mb-4 pt-5")}>
              Our Popular Services
            </h2>
            <p className="text-xl text-white/80">
              Comprehensive legal solutions for every need
            </p>
          </div>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
            {SERVICES.map((service) => (
              <Card key={service.name} interactive className="p-6">
                <div className={tokens.iconBadge}>
                  <service.icon className="w-7 h-7" />
                </div>
                <h3 className="text-xl font-semibold mt-4 mb-2">
                  {service.name}
                </h3>
                <p className="text-white/70 mb-4">{service.description}</p>
                <button className="text-[var(--primary-gold)] hover:text-white transition-colors inline-flex items-center gap-2">
                  Learn More <ChevronRight className="w-4 h-4" />
                </button>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* About Section */}
      <section id="about" className={tokens.section}>
        <div className={tokens.container}>
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <div className="relative">
              <div className="relative w-full aspect-[4/3] rounded-2xl overflow-hidden shadow-2xl">
                <Image
                  src="/hero1.jpg"
                  alt="Law firm hero"
                  fill
                  priority
                  className="object-cover"
                />
              </div>
            </div>
            <div>
              <h2 className={cn(tokens.heading, "text-4xl mb-6")}>
                Trusted Legal Advisor
              </h2>
              <p className="text-xl text-white/80 mb-8">
                Our AI-powered legal assistant provides comprehensive legal
                guidance backed by extensive knowledge of laws, regulations, and
                case precedents.
              </p>
              <div className="grid grid-cols-2 gap-6">
                {[
                  { value: "18+", label: "Years Experience" },
                  { value: "265+", label: "Cases Handled" },
                  { value: "24/7", label: "Availability" },
                  { value: "99%", label: "Success Rate" },
                ].map((stat) => (
                  <div key={stat.label} className="text-center">
                    <div className="text-3xl font-bold text-[var(--primary-gold)] mb-2">
                      {stat.value}
                    </div>
                    <div className="text-white/70">{stat.label}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Statistics Section */}
      <section className={tokens.section}>
        <div className={tokens.container}>
          <div className="grid md:grid-cols-3 gap-8">
            {[
              {
                icon: Target,
                value: "81%",
                title: "Legal Methods",
                desc: "Advanced legal analysis techniques",
              },
              {
                icon: TrendingUp,
                value: "68%",
                title: "Remote Advice",
                desc: "Digital legal consultation services",
              },
              {
                icon: Shield,
                value: "79%",
                title: "Strong Cases",
                desc: "Robust legal case preparation",
              },
            ].map((item) => (
              <Card key={item.title} className="p-8 text-center">
                <div className={cn(tokens.iconBadge, "mx-auto mb-4")}>
                  <item.icon className="w-7 h-7" />
                </div>
                <div className="text-3xl font-bold text-[var(--primary-gold)] mb-2">
                  {item.value}
                </div>
                <h3 className="text-xl font-semibold mb-2">{item.title}</h3>
                <p className="text-white/70">{item.desc}</p>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Contact Section */}
      <section id="contact" className={cn(tokens.section, "bg-black/20")}>
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-16">
            <h2 className={cn(tokens.heading, "text-4xl mb-4 pt-6")}>
              Appointment Event
            </h2>
            <p className="text-xl text-white/80">
              Get personalized legal assistance
            </p>
          </div>
          <form className="space-y-6">
            <div className="grid md:grid-cols-2 gap-6">
              <div>
                <label className="block mb-2 font-semibold">Name</label>
                <input
                  type="text"
                  className="w-full px-4 py-3 rounded-lg bg-[#0e1a22]/80 text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-[var(--primary-gold)]"
                  placeholder="Your full name"
                />
              </div>
              <div>
                <label className="block mb-2 font-semibold">Email</label>
                <input
                  type="email"
                  className="w-full px-4 py-3 rounded-lg bg-[#0e1a22]/80 text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-[var(--primary-gold)]"
                  placeholder="your@email.com"
                />
              </div>
            </div>
            <div>
                <label className="block mb-2 font-semibold">Phone</label>
                <input
                  type="tel"
                  className="w-full px-4 py-3 rounded-lg bg-[#0e1a22]/80 text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-[var(--primary-gold)]"
                  placeholder="Your phone number"
                />
              </div>
            <div>
              <label className="block mb-2 font-semibold">Message</label>
              <textarea
                rows={4}
                className="w-full px-4 py-3 rounded-lg bg-[#0e1a22]/80 text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-[var(--primary-gold)]"
                placeholder="Describe your legal matter..."
              ></textarea>
            </div>
            <div className="text-center">
             <Button className="h-12 px-8 text-xl rounded-xl">
  Submit
</Button>

            </div>
          </form>
        </div>
      </section>

      {/* Testimonials */}
      <section className={tokens.section}>
        <div className={tokens.container}>
          <div className="text-center mb-16">
            <h2 className={cn(tokens.heading, "text-4xl mb-4 pt-8 mt-3")}>
              What Our Clients Say
            </h2>
            <p className="text-xl text-white/80">
              Trusted by businesses and individuals
            </p>
          </div>
          <div className="grid md:grid-cols-2 gap-8">
            {[
              "VerdictAI provided me with clear, actionable legal guidance that saved me thousands in potential legal fees. The AI's knowledge is impressive and the responses are always professional.",
              "The best legal tool I've used. Fast, accurate, and affordable. The AI understands complex legal questions and provides practical solutions.",
            ].map((quote, idx) => (
              <Card key={idx} className="p-8">
                <div className="flex items-center gap-2 mb-4">
                  {Array.from({ length: 5 }).map((_, i) => (
                    <Star
                      key={i}
                      className="w-5 h-5 text-[var(--primary-gold)] fill-current"
                    />
                  ))}
                </div>
                <Quote className="w-8 h-8 text-[var(--primary-gold)] mb-4" />
                <p className="text-white/80 mb-6 text-lg">
                  &ldquo;{quote}&rdquo;
                </p>
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 bg-[rgba(200,171,127,0.12)] rounded-full" />
                  <div>
                    <p className="font-semibold">
                      {idx === 0 ? "Sarah M." : "Ahmed K."}
                    </p>
                    <p className="text-white/60 text-sm">
                      {idx === 0 ? "Business Owner" : "Legal Consultant"}
                    </p>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-[#0e1a22] py-12">
        <div className={tokens.container}>
          <div className="grid md:grid-cols-4 gap-8">
            <div>
              <div className="flex items-center gap-3 mb-4">
                <FaGavel className="text-2xl text-[var(--primary-gold)]" />
                <div>
                  <h3 className="text-xl font-bold">VerdictAI</h3>
                  <p className="text-xs text-[var(--primary-gold)]">
                    advocate & law firm
                  </p>
                </div>
              </div>
              <p className="text-white/70">
                AI-powered legal assistance for everyone.
              </p>
            </div>
            <div>
              <h4 className="font-semibold mb-4">Services</h4>
              <ul className="space-y-2 text-white/70">
                {SERVICES.slice(0, 4).map((s) => (
                  <li key={s.name}>
                    <a
                      href="#"
                      className="hover:text-[var(--primary-gold)] transition-colors"
                    >
                      {s.name}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <h4 className="font-semibold mb-4">Company</h4>
              <ul className="space-y-2 text-white/70">
                {[
                  "About Us",
                  "Privacy Policy",
                  "Terms of Service",
                  "Disclaimer",
                ].map((label) => (
                  <li key={label}>
                    <a
                      href="#"
                      className="hover:text-[var(--primary-gold)] transition-colors"
                    >
                      {label}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <h4 className="font-semibold mb-4">Contact</h4>
              <ul className="space-y-2 text-white/70">
                <li className="flex items-center gap-2">
                  <Mail className="w-4 h-4" />
                  <a
                    href="mailto:contact@verdictai.com"
                    className="hover:text-[var(--primary-gold)] transition-colors"
                  >
                    contact@verdictai.com
                  </a>
                </li>
                <li className="flex items-center gap-2">
                  <Phone className="w-4 h-4" />
                  <a
                    href="tel:+880123456789"
                    className="hover:text-[var(--primary-gold)] transition-colors"
                  >
                    +880 123 456 789
                  </a>
                </li>
                <li className="flex items-center gap-2">
                  <MapPin className="w-4 h-4" />
                  <span>Dhaka, Bangladesh</span>
                </li>
              </ul>
            </div>
          </div>
          <div className="mt-8 pt-8 text-center text-white/70">
            <p>&copy; 2024 VerdictAI. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </div>
  );
}
