#!/usr/bin/env python3
"""Fair gold retrieval eval — no LLM, no answer memorization.

Matches /ask context building: hybrid fuse, then fused top-k (no keyword /
issue filters). Scores gold Article keys at fuse and at LLM context so you
can see ranker misses vs top-k truncation.

Scoring labels from gold_eval.txt are used only AFTER each stage. They are
never injected into the query, filters, or ranker.

From backend/ (venv on):
  ./venv/bin/python eval_retrieval_gold.py
  ./venv/bin/python eval_retrieval_gold.py --limit 4
  ./venv/bin/python eval_retrieval_gold.py --language bn
  ./venv/bin/python eval_retrieval_gold.py --json-out gold_retrieval_report.json
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

from dotenv import load_dotenv

from gold_eval_cases import DEFAULT_GOLD_PATH, GoldCase, load_gold_cases

log = logging.getLogger("eval_retrieval_gold")


@dataclass
class StageScore:
    keys: list[str]
    hits: list[str]
    misses: list[str]
    recall: float

    @staticmethod
    def from_keys(expected: list[str], keys: list[str]) -> "StageScore":
        hits = [key for key in expected if key in keys]
        misses = [key for key in expected if key not in keys]
        recall = (len(hits) / len(expected)) if expected else 0.0
        return StageScore(keys=keys, hits=hits, misses=misses, recall=recall)


@dataclass
class CaseResult:
    case_id: str
    title: str
    language: str
    query: str
    expected: list[str]
    fuse: StageScore
    llm_context: StageScore
    miss_at_fuse: list[str]
    dropped_by_topk: list[str]
    leak_class: str
    context_size: int
    statute_refs: list[str]
    ms: int
    ok: bool
    error: str = ""


def constitution_article_keys(chunks: list[dict]) -> list[str]:
    """Article keys from constitution passages only (statutes ignored for this gold)."""
    keys: list[str] = []
    for chunk in chunks:
        collection = str(chunk.get("collection") or "")
        if not collection.startswith("constitution"):
            continue
        key = chunk.get("article_key")
        if key is None or key == "":
            continue
        text = str(key)
        if text not in keys:
            keys.append(text)
    return keys


def statute_refs(chunks: list[dict], limit: int = 6) -> list[str]:
    refs: list[str] = []
    for chunk in chunks:
        if str(chunk.get("collection") or "") != "other-acts":
            continue
        label = (
            chunk.get("section_number")
            or chunk.get("display_number")
            or chunk.get("act_title")
            or chunk.get("chunk_id")
            or "?"
        )
        text = str(label)[:48]
        if text not in refs:
            refs.append(text)
        if len(refs) >= limit:
            break
    return refs


def classify_leak(
    expected: list[str],
    fuse: StageScore,
    llm: StageScore,
) -> tuple[str, list[str], list[str]]:
    miss_at_fuse = list(fuse.misses)
    dropped_by_topk = [
        key for key in expected if key in fuse.keys and key not in llm.keys
    ]
    if not miss_at_fuse and not dropped_by_topk:
        leak = "ok"
    elif miss_at_fuse and not dropped_by_topk:
        leak = "ranker_miss"
    elif dropped_by_topk and not miss_at_fuse:
        leak = "topk_truncation"
    else:
        leak = "mixed_ranker_and_topk"
    return leak, miss_at_fuse, dropped_by_topk


def trace_case(case: GoldCase) -> CaseResult:
    """Same path as _answer_chunks: fuse, then fused top-k."""
    from answer_quality import context_limit, retrieval_language, retrieval_text
    from legal_status import attach_legal_status_flags
    import rag_utils

    t0 = time.time()
    expected = list(case.expected_articles)
    search_text = retrieval_text(case.query, None)
    search_language = retrieval_language(case.query, case.language)
    limit = context_limit()
    if search_language not in ("en", "bn"):
        empty = StageScore.from_keys(expected, [])
        return CaseResult(
            case_id=case.case_id,
            title=case.title,
            language=case.language,
            query=case.query,
            expected=expected,
            fuse=empty,
            llm_context=empty,
            miss_at_fuse=list(expected),
            dropped_by_topk=[],
            leak_class="no_language",
            context_size=0,
            statute_refs=[],
            ms=int((time.time() - t0) * 1000),
            ok=False,
            error="search_language not en/bn",
        )

    ranked, statutes, _stats = rag_utils._parallel_hybrid_retrieve(
        search_text, search_language
    )
    fuse = StageScore.from_keys(expected, constitution_article_keys(ranked))

    constitution: list[dict] = []
    seen: set[str] = set()
    for chunk in ranked[:limit]:
        identity = str(chunk.get("chunk_id") or id(chunk))
        if identity in seen:
            continue
        seen.add(identity)
        constitution.append(attach_legal_status_flags(chunk))

    llm_chunks = constitution + statutes
    llm_context = StageScore.from_keys(
        expected, constitution_article_keys(llm_chunks)
    )
    leak, miss_at_fuse, dropped_by_topk = classify_leak(expected, fuse, llm_context)

    return CaseResult(
        case_id=case.case_id,
        title=case.title,
        language=case.language,
        query=case.query,
        expected=expected,
        fuse=fuse,
        llm_context=llm_context,
        miss_at_fuse=miss_at_fuse,
        dropped_by_topk=dropped_by_topk,
        leak_class=leak,
        context_size=len(llm_chunks),
        statute_refs=statute_refs(statutes),
        ms=int((time.time() - t0) * 1000),
        ok=not llm_context.misses,
    )


def _print_case(result: CaseResult) -> None:
    mark = "PASS" if result.ok else "FAIL"
    print(
        f"[{mark}] {result.case_id}  leak={result.leak_class}  "
        f"llm_recall={result.llm_context.recall:.2f}  {result.ms}ms"
    )
    print(f"  expected={result.expected}")
    print(
        f"  fuse         recall={result.fuse.recall:.2f}  "
        f"keys={result.fuse.keys or '-'}  "
        f"miss={result.fuse.misses or '-'}"
    )
    print(
        f"  llm_context  recall={result.llm_context.recall:.2f}  "
        f"keys={result.llm_context.keys or '-'}  "
        f"miss={result.llm_context.misses or '-'}  "
        f"dropped_by_topk={result.dropped_by_topk or '-'}  "
        f"ctx={result.context_size}  statutes={result.statute_refs or '-'}"
    )


def _stage_micro(results: list[CaseResult], attr: str) -> tuple[float, int, int]:
    hits = 0
    total = 0
    for row in results:
        stage: StageScore = getattr(row, attr)
        hits += len(stage.hits)
        total += len(row.expected)
    return ((hits / total) if total else 0.0, hits, total)


def _print_breakdown_summary(results: list[CaseResult]) -> None:
    total = len(results)
    leak_counts = Counter(row.leak_class for row in results)
    fuse_micro, fuse_h, fuse_t = _stage_micro(results, "fuse")
    llm_micro, llm_h, llm_t = _stage_micro(results, "llm_context")

    print("\n=== Fuse vs top-k breakdown ===")
    print(f"micro_recall by stage (article mentions recovered / {fuse_t}):")
    print(f"  fuse          {fuse_micro:.3f}  ({fuse_h}/{fuse_t})")
    print(f"  llm_context   {llm_micro:.3f}  ({llm_h}/{llm_t})")

    print("\nleak_class counts (primary failure mode per case):")
    for name in (
        "ok",
        "ranker_miss",
        "topk_truncation",
        "mixed_ranker_and_topk",
        "no_language",
        "error",
    ):
        count = leak_counts.get(name, 0)
        if count:
            print(f"  {name:28} {count}/{total}")

    fuse_misses = sum(len(row.miss_at_fuse) for row in results)
    topk_drops = sum(len(row.dropped_by_topk) for row in results)
    print("\nexpected-article loss events:")
    print(f"  miss_at_fuse (never in fused list)     {fuse_misses}")
    print(f"  dropped_by_topk (fused → top-k cut)    {topk_drops}")

    print("\nHow to read this:")
    print("  ranker_miss      → improve hybrid / diversification")
    print("  topk_truncation  → raise ANSWER_CONTEXT_LIMIT or diversify into top-k")
    print("  ok               → all gold articles in LLM context")


def main() -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(
        description="Fair retrieval-only gold eval (fuse then top-k)."
    )
    parser.add_argument("--gold", type=Path, default=DEFAULT_GOLD_PATH)
    parser.add_argument(
        "--language", choices=("en", "bn", "both"), default="both"
    )
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--json-out", type=Path, default=None)
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )

    cases = load_gold_cases(args.gold)
    if args.language != "both":
        cases = [case for case in cases if case.language == args.language]
    if args.limit and args.limit > 0:
        cases = cases[: args.limit]
    if not cases:
        print("No gold cases loaded.", file=sys.stderr)
        return 2

    print(f"Gold file: {args.gold}")
    print(f"Cases: {len(cases)} (fuse → top-k, no select/issue filters)")
    print(
        "Fairness: expected articles are scoring labels only; "
        "not passed into retrieval.\n"
    )

    import rag_utils

    rag_utils._lazy_init_models()

    results: list[CaseResult] = []
    for case in cases:
        try:
            result = trace_case(case)
        except Exception as exc:
            log.exception("Case failed case_id=%s", case.case_id)
            empty = StageScore.from_keys(list(case.expected_articles), [])
            result = CaseResult(
                case_id=case.case_id,
                title=case.title,
                language=case.language,
                query=case.query,
                expected=list(case.expected_articles),
                fuse=empty,
                llm_context=empty,
                miss_at_fuse=list(case.expected_articles),
                dropped_by_topk=[],
                leak_class="error",
                context_size=0,
                statute_refs=[],
                ms=0,
                ok=False,
                error=f"{type(exc).__name__}: {exc}",
            )
            print(f"[ERROR] {case.case_id}: {result.error}")
        results.append(result)
        _print_case(result)
        print()

    total = len(results)
    passed = sum(1 for row in results if row.ok)
    mean_recall = (
        sum(row.llm_context.recall for row in results) / total if total else 0.0
    )
    llm_micro, llm_h, llm_t = _stage_micro(results, "llm_context")

    print("=== Summary (LLM context = fused top-k) ===")
    print(f"cases_passed={passed}/{total} ({passed / total:.1%})")
    print(f"macro_recall={mean_recall:.3f}")
    print(f"micro_recall={llm_micro:.3f}  ({llm_h}/{llm_t} article mentions)")
    by_lang: dict[str, list[CaseResult]] = {"en": [], "bn": []}
    for row in results:
        by_lang.setdefault(row.language, []).append(row)
    for language, rows in by_lang.items():
        if not rows:
            continue
        lang_pass = sum(1 for row in rows if row.ok)
        lang_recall = sum(row.llm_context.recall for row in rows) / len(rows)
        print(
            f"  {language}: passed={lang_pass}/{len(rows)}  "
            f"macro_recall={lang_recall:.3f}"
        )

    _print_breakdown_summary(results)

    if args.json_out:
        payload = {
            "gold": str(args.gold),
            "cases": total,
            "passed": passed,
            "macro_recall": mean_recall,
            "micro_recall": llm_micro,
            "stage_micro_recall": {
                "fuse": _stage_micro(results, "fuse")[0],
                "llm_context": llm_micro,
            },
            "leak_class_counts": dict(Counter(r.leak_class for r in results)),
            "results": [asdict(row) for row in results],
        }
        args.json_out.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"\nWrote {args.json_out}")

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
