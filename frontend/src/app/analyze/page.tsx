"use client";

import { FormEvent, useMemo, useState } from "react";
import SiteLayout from "@/components/layout/SiteLayout";
import InnerPage from "@/components/layout/InnerPage";
import {
  AnalysisReport,
  ClauseReport,
  analyzeDocument,
} from "@/lib/api";

const CATEGORY_LABEL: Record<string, string> = {
  POTENTIAL_CONTRADICTION: "Potential contradiction",
  POTENTIAL_RIGHTS_VIOLATION: "Potential rights concern",
  POTENTIALLY_UNFAIR: "Potentially unfair",
  AMBIGUOUS: "Ambiguous",
  NO_CLEAR_ISSUE: "No Clear Issue Found",
};

const RISK_RANK: Record<string, number> = {
  HIGH: 0,
  MEDIUM: 1,
  LOW: 2,
};

const FLAG_LABEL: Record<string, string> = {
  hc_dec2024_declared_void:
    "High Court Division (17 Dec 2024) declared this article void.",
  source_is_bdlaws_consolidation_through_2018:
    "Source text is the bdlaws consolidation through 2018.",
};

export default function AnalyzePage() {
  return (
    <SiteLayout>
      <InnerPage title="Document analyzer">
        <Analyzer />
      </InnerPage>
    </SiteLayout>
  );
}

function Analyzer() {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [report, setReport] = useState<AnalysisReport | null>(null);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!file || loading) return;
    setLoading(true);
    setError(null);
    try {
      const result = await analyzeDocument(file);
      setReport(result);
    } catch (err) {
      setReport(null);
      setError(err instanceof Error ? err.message : "Analysis failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="analyzer">
      <p>
        Upload an English contract in PDF, DOCX, or TXT. Each clause is checked
        against retrieved articles of the Constitution of Bangladesh. Phase 1
        does not read scanned PDFs.
      </p>

      <form className="analyze-form" onSubmit={onSubmit}>
        <label className="analyze-file">
          <span>Document</span>
          <input
            type="file"
            accept=".pdf,.docx,.txt,application/pdf,text/plain"
            onChange={(event) => {
              setFile(event.target.files?.[0] ?? null);
              setError(null);
            }}
          />
        </label>
        <button
          className="analyze-submit"
          type="submit"
          disabled={!file || loading}
        >
          {loading ? "Analyzing…" : "Analyze document"}
        </button>
      </form>

      {error && (
        <p className="analyze-error" role="alert">
          {error}
        </p>
      )}

      {report && <ReportView report={report} />}
    </div>
  );
}

function ReportView({ report }: { report: AnalysisReport }) {
  const ordered = useMemo(() => {
    return [...report.clauses].sort((a, b) => {
      const risk = (RISK_RANK[a.risk_level] ?? 9) - (RISK_RANK[b.risk_level] ?? 9);
      return risk || a.original_index - b.original_index;
    });
  }, [report.clauses]);

  const categories = Object.entries(report.summary.categories).filter(
    ([, count]) => count > 0
  );

  return (
    <div className="analyze-report">
      <p className="analyze-disclaimer">{report.disclaimer}</p>

      <div className="summary-grid">
        <SummaryCard label="Clauses" value={String(report.summary.total_clauses)} />
        <SummaryCard label="High" value={String(report.summary.risk_levels.HIGH ?? 0)} />
        <SummaryCard label="Medium" value={String(report.summary.risk_levels.MEDIUM ?? 0)} />
        <SummaryCard label="Low" value={String(report.summary.risk_levels.LOW ?? 0)} />
      </div>

      {report.summary.truncated && (
        <p className="analyze-note">
          The document was truncated after 60 clauses.
        </p>
      )}

      {categories.length > 0 && (
        <ul className="category-counts">
          {categories.map(([category, count]) => (
            <li key={category}>
              {CATEGORY_LABEL[category] ?? category}: {count}
            </li>
          ))}
        </ul>
      )}

      <p className="analyze-note">
        Higher-risk clauses are listed first. Original position is shown on each card.
      </p>

      <div className="clause-list">
        {ordered.map((clause) => (
          <ClauseCard key={clause.clause_id} clause={clause} />
        ))}
      </div>
    </div>
  );
}

function SummaryCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="summary-card">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function ClauseCard({ clause }: { clause: ClauseReport }) {
  const category =
    clause.category === "NO_CLEAR_ISSUE"
      ? "No Clear Issue Found"
      : CATEGORY_LABEL[clause.category] ?? clause.status;

  return (
    <article className="clause-card">
      <header className="clause-card-head">
        <span className="clause-id">
          {clause.clause_id}
          {clause.heading ? ` · ${clause.heading}` : ""}
          {` · position ${clause.original_index + 1}`}
        </span>
        <span className="badge-row">
          <span className={`badge risk-${clause.risk_level.toLowerCase()}`}>
            {clause.risk_level}
          </span>
          <span className="badge">{category}</span>
        </span>
      </header>

      <h2>Original clause</h2>
      <div className="analyze-clause-text">{clause.original_text}</div>

      {clause.related_articles.length > 0 && (
        <div className="article-list">
          <h2>Related articles</h2>
          {clause.related_articles.map((article) => (
            <div className="article-block" key={article.article_key}>
              <p className="article-key">
                Article {article.display_number || article.article_key}
              </p>
              {article.quote && <blockquote>{article.quote}</blockquote>}
              {article.legal_status_flags.length > 0 && (
                <ul className="flag-list">
                  {article.legal_status_flags.map((flag) => (
                    <li
                      key={flag}
                      className={
                        flag === "hc_dec2024_declared_void" ? "flag-warning" : undefined
                      }
                    >
                      {FLAG_LABEL[flag] ?? flag}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          ))}
        </div>
      )}

      {clause.why_flagged && (
        <>
          <h2>Why it was flagged</h2>
          <p>{clause.why_flagged}</p>
        </>
      )}

      {clause.analysis && (
        <>
          <h2>Analysis</h2>
          <p>{clause.analysis}</p>
        </>
      )}

      {clause.recommendation && (
        <>
          <h2>Recommendation</h2>
          <p>{clause.recommendation}</p>
        </>
      )}

      {clause.scope_note && <p className="analyze-note">{clause.scope_note}</p>}
    </article>
  );
}
