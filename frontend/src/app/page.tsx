"use client";

import { useState } from "react";
import { ArrowUpRight, Menu, X } from "lucide-react";
import { useChat } from "@/components/chat/ChatContext";
import SiteLayout from "@/components/layout/SiteLayout";

const steps = [
  [
    "01",
    "Ask naturally",
    "Write your question in Bangla or English, just as you would ask it.",
  ],
  [
    "02",
    "Understand clearly",
    "VerdictAI explains the relevant constitutional principles in plain language.",
  ],
  [
    "03",
    "Read the source",
    "Every answer points you back to the article that grounds it.",
  ],
] as const;

const facts = [
  ["02", "Languages", "Ask in Bangla or English."],
  ["Cite", "Citations", "Every answer names its article."],
  ["01", "Source", "The official constitutional text."],
  ["Text", "Analyze", "Paste a contract and check each clause."],
] as const;

const topics = [
  [
    "Art. 27",
    "Equality",
    "সমতা",
    "All citizens are equal before law.",
    "What does Article 27 of the Constitution of Bangladesh say about equality before the law?",
  ],
  [
    "Art. 32",
    "Life and liberty",
    "জীবন ও স্বাধীনতা",
    "Protection of life and personal liberty.",
    "What does Article 32 say about protection of the right to life and personal liberty in Bangladesh?",
  ],
  [
    "Art. 33",
    "Arrest",
    "গ্রেপ্তার",
    "Safeguards when a person is arrested.",
    "What safeguards does Article 33 of the Constitution of Bangladesh give a person who is arrested?",
  ],
  [
    "Art. 39",
    "Speech",
    "বাক্‌স্বাধীনতা",
    "Thought, conscience, and expression.",
    "What does Article 39 say about freedom of thought, conscience and speech in Bangladesh?",
  ],
  [
    "Art. 41",
    "Religion",
    "ধর্ম",
    "Freedom to profess and practise religion.",
    "What does Article 41 of the Bangladesh Constitution say about freedom of religion?",
  ],
  [
    "Art. 102",
    "Writs",
    "রিট",
    "How the High Court protects rights.",
    "What powers does the High Court Division have under Article 102 to protect fundamental rights in Bangladesh?",
  ],
] as const;

const ticker = [
  "Fundamental rights",
  "Equality",
  "Arrest",
  "Expression",
  "Religion",
  "Citizenship",
  "Property",
  "Writs",
  "মৌলিক অধিকার",
  "সমতা",
  "গ্রেপ্তার",
  "বাক্‌স্বাধীনতা",
];

const faqs = [
  [
    "Is this legal advice?",
    "No. VerdictAI explains the constitutional text in plain language. It is not a lawyer, and it is not a substitute for advice on your own situation.",
  ],
  [
    "Which languages can I use?",
    "Bangla or English. Ask the way you would ask a person, and the reply points back to the article that grounds it.",
  ],
  [
    "Where do the answers come from?",
    "From the Constitution of the People’s Republic of Bangladesh. Each reply is meant to stay tied to that text, with the article named.",
  ],
  [
    "What does Analyze do?",
    "Copy the text from your PDF or TXT file and paste it into the analyzer. File upload is not available. Each clause is checked against retrieved articles.",
  ],
] as const;

function LandingPage() {
  const { openChat } = useChat();
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <main className="site-shell">
      <header className="site-nav" aria-label="Main navigation">
        <a className="wordmark" href="#top" aria-label="VerdictAI home">
          verdict<span>ai</span>
        </a>
        <nav className="desktop-nav" aria-label="Primary">
          <button type="button" onClick={() => openChat()}>
            Chat
          </button>
          <a href="/analyze">Analyze</a>
          <a href="#topics">Topics</a>
          <a href="#contact">Contact</a>
        </nav>
        <button type="button" className="nav-cta" onClick={() => openChat()}>
          Open chat <ArrowUpRight size={14} strokeWidth={1.5} />
        </button>
        <button
          className="mobile-menu"
          type="button"
          aria-label="Open navigation"
          onClick={() => setMobileOpen((v) => !v)}
        >
          {mobileOpen ? <X size={20} strokeWidth={1.5} /> : <Menu size={20} strokeWidth={1.5} />}
        </button>
      </header>

      {mobileOpen && (
        <div className="mobile-nav-panel">
          <button
            type="button"
            onClick={() => {
              openChat();
              setMobileOpen(false);
            }}
          >
            Chat
          </button>
          <a href="/analyze" onClick={() => setMobileOpen(false)}>
            Analyze
          </a>
          <a href="#topics" onClick={() => setMobileOpen(false)}>
            Topics
          </a>
          <a href="#contact" onClick={() => setMobileOpen(false)}>
            Contact
          </a>
        </div>
      )}

      <section id="top" className="hero" aria-labelledby="hero-title">
        <div
          className="hero-image"
          role="img"
          aria-label="Constitutional paper in soft afternoon light"
        />
        <div className="hero-copy">
          <p className="eyebrow">
            A constitutional companion / সংবিধানের সঙ্গী
          </p>
          <h1 id="hero-title">
            Your Constitution,
            <br />
            <em>explained.</em>
          </h1>
          <p className="hero-intro">
            A calm, careful way to understand the Constitution of Bangladesh —
            in Bangla or English.
          </p>
          <button type="button" className="button button-dark" onClick={() => openChat()}>
            Ask a question <ArrowUpRight size={16} strokeWidth={1.5} />
          </button>
          <ul className="hero-points">
            <li>Bangla + English</li>
            <li>Cited articles</li>
            <li>Plain language</li>
          </ul>
        </div>
        <p className="hero-note">
          Dhaka / Bangladesh
          <br />
          বাংলা · English
        </p>
      </section>

      <div className="topic-ticker" aria-hidden="true">
        <div className="topic-ticker-track">
          {[...ticker, ...ticker].map((item, index) => (
            <span key={`${item}-${index}`}>{item}</span>
          ))}
        </div>
      </div>

      <section className="facts-band" aria-label="What VerdictAI offers">
        {facts.map(([mark, title, body]) => (
          <div className="fact" key={title}>
            <strong>{mark}</strong>
            <span>{title}</span>
            <p>{body}</p>
          </div>
        ))}
      </section>

      <section className="steps-section" aria-labelledby="steps-title">
        <div className="section-heading">
          <p className="section-label">01 / How it works</p>
          <h2 id="steps-title">
            Three steps
            <br />
            <em>to clarity.</em>
          </h2>
        </div>
        <div className="steps-list">
          {steps.map(([number, title, body]) => (
            <article className="step" key={number}>
              <span className="step-number">{number}</span>
              <div>
                <h3>{title}</h3>
                <p>{body}</p>
              </div>
              <ArrowUpRight className="step-arrow" size={18} strokeWidth={1.5} />
            </article>
          ))}
        </div>
      </section>

      <section className="chat-section" id="chat" aria-labelledby="chat-title">
        <div className="section-heading">
          <p className="section-label">02 / A small example</p>
          <h2 id="chat-title">
            Questions deserve
            <br />
            <em>good answers.</em>
          </h2>
        </div>
        <article className="sample-answer">
          <p className="sample-question">
            “Assume that the agreement between Rahim and Karim was never
            registered. Karim has paid Tk. 5,00,000 in advance but has not
            deposited the remaining consideration in court. Can Karim still
            obtain a decree for specific performance under Bangladeshi law?
            Identify the exact statutory provision and explain the legal
            requirements.”
          </p>
          <h3>Direct answer</h3>
          <p>
            Karim cannot obtain a decree for specific performance because the
            statutory conditions for enforcing a contract for the sale of
            immovable property have not been satisfied.
          </p>
          <div className="sample-law">
            <h3>What the law says</h3>
            <p>
              <strong>Section 7 of the Specific Relief Act, 1877</strong>{" "}
              provides that “no contract for sale of any immovable property can
              be specifically enforced unless – (a) the contract is in writing
              and <strong>registered</strong> under the Registration Act, 1908,
              whether or not the transferee has taken possession of the
              property or any part thereof; and (b) the balance amount of
              consideration of the contract is{" "}
              <strong>deposited in the court</strong> at the time of filing the
              suit for specific performance of the contract.”
            </p>
            <p>
              <strong>Section 24 of the Specific Relief Act, 1877</strong>{" "}
              further bars specific performance “in favour of a person … who
              has become incapable of performing, or violates, any essential
              term of the contract … or who has <strong>not deposited</strong>{" "}
              the balance consideration as required by Section 7.”
            </p>
          </div>
        </article>
        <button type="button" className="button button-outline" onClick={() => openChat()}>
          Open the conversation <ArrowUpRight size={16} strokeWidth={1.5} />
        </button>
      </section>

      <section className="ways-section" aria-labelledby="ways-title">
        <div className="section-heading">
          <p className="section-label">03 / Two ways in</p>
          <h2 id="ways-title">
            A question,
            <br />
            <em>or a document.</em>
          </h2>
        </div>
        <div className="ways-grid">
          <article className="way way-chat">
            <p className="section-label">Chat</p>
            <h3>Ask in your own words.</h3>
            <p>
              Write the question as you would say it. VerdictAI answers from
              the Constitution and names the article.
            </p>
            <button type="button" className="button button-dark" onClick={() => openChat()}>
              Open chat <ArrowUpRight size={16} strokeWidth={1.5} />
            </button>
          </article>
          <article className="way way-analyze">
            <p className="section-label">Analyze</p>
            <h3>Check a contract.</h3>
            <p>
              Copy the text from a PDF or TXT file and paste it in. Each clause
              is read against the articles that may bear on it.
            </p>
            <a className="button button-line" href="/analyze">
              Open analyzer <ArrowUpRight size={16} strokeWidth={1.5} />
            </a>
          </article>
        </div>
      </section>

      <section className="trust-section" aria-label="Trust and source">
        <p className="section-label">04 / The source</p>
        <blockquote>
          “Built on the official text
          <br />
          of the <em>Bangladesh Constitution.</em>”
        </blockquote>
        <div className="trust-meta">
          <p>
            Answers are grounded in the Constitution of the People&apos;s
            Republic of Bangladesh — with references to specific articles, in
            both languages.
          </p>
          <span>
            Established 2026
            <br />
            Dhaka, BD
          </span>
        </div>
      </section>

      <section className="topics-section" id="topics" aria-labelledby="topics-title">
        <div className="section-heading">
          <p className="section-label">05 / What you can ask</p>
          <h2 id="topics-title">
            Start with
            <br />
            <em>a right.</em>
          </h2>
        </div>
        <div className="topic-grid">
          {topics.map(([article, title, bangla, body, query]) => (
            <button
              type="button"
              className="topic-card"
              key={article}
              onClick={() => openChat(query)}
            >
              <span className="topic-kicker">
                {article}
                <span lang="bn">{bangla}</span>
              </span>
              <h3>{title}</h3>
              <p>{body}</p>
              <span className="topic-ask">
                Ask this <ArrowUpRight size={14} strokeWidth={1.5} />
              </span>
            </button>
          ))}
        </div>
      </section>

      <section className="faq-section" aria-labelledby="faq-title">
        <div className="section-heading">
          <p className="section-label">06 / Before you ask</p>
          <h2 id="faq-title">
            A few
            <br />
            <em>plain answers.</em>
          </h2>
        </div>
        <div className="faq-list">
          {faqs.map(([question, answer]) => (
            <details className="faq-item" key={question}>
              <summary>
                {question}
                <span aria-hidden="true" />
              </summary>
              <p>{answer}</p>
            </details>
          ))}
        </div>
      </section>

      <footer id="contact" className="site-footer">
        <div className="footer-top">
          <div className="footer-brand">
            <a className="wordmark" href="#top">
              verdict<span>ai</span>
            </a>
            <p>Constitutional clarity, in two languages.</p>
          </div>
          <div className="footer-links">
            <button type="button" onClick={() => openChat()}>
              Chat
            </button>
            <a href="/analyze">Analyze</a>
            <a href="mailto:hello@verdictai.bd">hello@verdictai.bd</a>
          </div>
        </div>
        <div className="footer-bottom">
          <span>© 2026 VerdictAI</span>
          <span>Made for Bangladesh</span>
        </div>
      </footer>
    </main>
  );
}

export default function Home() {
  return (
    <SiteLayout>
      <LandingPage />
    </SiteLayout>
  );
}
