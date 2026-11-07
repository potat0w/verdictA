"""Shared answer shaping for text and voice.

The legal answer is built once. Text chat and the voice tool both receive it.
This module does not call a model and does not retrieve.
"""

from __future__ import annotations

import os
import re

from article_parser import normalize_bn_article_token
from hybrid_search import tokenize

_STOP = {
    "a", "an", "the", "of", "to", "and", "or", "for", "in", "on", "at", "by",
    "with", "from", "that", "this", "was", "were", "is", "are", "be", "been",
    "their", "them", "they", "someone", "without", "not", "did", "do", "does",
    "can", "how", "what", "when", "where", "who", "why", "into", "his", "her",
    "person", "because", "its", "about", "your", "you", "have", "has", "had",
    "any", "all", "if", "then", "than", "also", "only", "just", "been",
    "reason", "right", "rights", "state", "public", "government", "order",
    "time", "shall", "such", "under", "before", "after", "other", "more",
    "সরকারি", "সরকার",
    "এবং", "বা", "না", "কে", "কি", "কী", "এই", "সে", "তার", "জন্য", "করা",
    "হয়েছে", "হয়েছে", "কাউকে", "কিন্তু", "থেকে", "কোন",
    "enter", "entered", "entering", "tell", "told",
    "woman", "women", "mother", "father", "man", "men",
    "work", "working", "higher", "authority", "authorities", "principal",
}

_GENERIC = {
    "law", "laws", "legal", "lawful", "unlawful", "constitution",
    "constitutional", "article", "section", "bangladesh", "people",
    "citizen", "citizens",
}

_CITE_SPAN = re.compile(
    r"(?P<label>articles?|arts?\.?|sections?|secs?\.?|অনুচ্ছেদ|ধারা)"
    r"(?P<body>(?:\s*[0-9০-৯]+[A-Za-zক-হ]?"
    r"(?:\s*(?:,|and|or|ও|এবং)\s*[0-9০-৯]+[A-Za-zক-হ]?)*)+)",
    re.IGNORECASE,
)
_NUMBER = re.compile(r"[0-9০-৯]+[A-Za-zক-হ]?")
_STATUTE_START = re.compile(r"^\s*([0-9০-৯]+)")
_AUDIO_TAG = re.compile(r"\[[^\[\]\n]{1,40}\](?!\()")

_EN_HEADINGS = (
    "# Direct answer",
    "## What the law says",
    "## How this applies",
    "## What you can do",
    "## Limits",
)
_BN_HEADINGS = (
    "# সরাসরি উত্তর",
    "## আইন কী বলে",
    "## এটি কীভাবে প্রযোজ্য",
    "## কী করা যায়",
    "## সীমা",
)


def normalize_history(history) -> list[dict]:
    """Keep the latest user and assistant turns. Drop anything else."""
    if not history:
        return []
    cleaned: list[dict] = []
    for turn in list(history)[-8:]:
        if isinstance(turn, dict):
            role = turn.get("role")
            content = turn.get("content")
        else:
            role = getattr(turn, "role", None)
            content = getattr(turn, "content", None)
        if role not in ("user", "assistant"):
            continue
        text = str(content or "").strip()[:1000]
        if text:
            cleaned.append({"role": role, "content": text})
    return cleaned


def question_script(query: str) -> str | None:
    """bn or en when the text is a recognizable question. Gibberish is None."""
    from chunking import detect_language

    text = query or ""
    if detect_language(text) == "bn":
        return "bn"
    for token in re.findall(r"[A-Za-z]{3,}", text):
        vowels = sum(char in "aeiouy" for char in token.lower())
        if vowels >= 2 or vowels / len(token) >= 0.3:
            return "en"
    return None


def retrieval_language(query: str, selected: str | None) -> str | None:
    """Search the constitution written in the question's script."""
    script = question_script(query)
    if script in ("en", "bn"):
        return script
    if selected in ("en", "bn"):
        return selected
    return None


def response_language(query: str, selected: str | None) -> str | None:
    """Bangla questions are answered in Bangla, English questions in English."""
    script = question_script(query)
    if script in ("en", "bn"):
        return script
    if selected in ("en", "bn"):
        return selected
    return "en"


def retrieval_text(query: str, history=None) -> str:
    """Current question first, then earlier user questions, for retrieval only."""
    prior = [
        turn["content"]
        for turn in normalize_history(history)
        if turn["role"] == "user"
    ]
    parts = [str(query or "").strip(), *prior[-3:]]
    return "\n".join(part for part in parts if part)[:2000]


def _aspect_rewrite_enabled() -> bool:
    raw = os.getenv("RETRIEVAL_ASPECT_QUERIES", "1").strip().lower()
    return raw not in ("0", "false", "no", "off")


def retrieval_aspect_queries(query: str, language: str | None = None) -> list[str]:
    """Cheap LLM split of one legal story into role-shaped search queries.

    Always includes the original question first. Each extra query should target
    one operative legal role tied to the facts (right / duty / prohibition /
    safeguard), so retrieval prefers provision text over glossary or vague
    rights umbrellas. Never asks for article numbers. On failure, returns
    [query] only. Disable with RETRIEVAL_ASPECT_QUERIES=0.
    """
    import json

    text = (query or "").strip()
    if not text:
        return []
    if not _aspect_rewrite_enabled():
        return [text]

    lang = language if language in ("en", "bn") else question_script(text)
    if lang == "bn":
        lang_rule = "Write every search query in Bangla."
    else:
        lang_rule = "Write every search query in English."

    system = (
        "You prepare search queries for a Bangladesh law retrieval index "
        "(constitution and statutes). "
        "Return JSON only: {\"queries\": [\"...\", \"...\"]}. "
        "Give 2 or 3 short queries. Each query covers ONE distinct legal role "
        "in the user's facts — a right, a duty, a prohibition, or a procedural "
        "safeguard that an operative provision would state — and stays tied to "
        "who did what to whom. "
        "Phrase each query like operative provision language, for example: "
        "equality before law without birth-based discrimination; "
        "no deprivation of personal liberty except in accordance with law; "
        "public servant duty to serve the people; "
        "arrest must state grounds and allow consult with a lawyer; "
        "prohibition of forced unpaid labour. "
        "Do not write vague umbrella queries such as constitutional rights, "
        "fundamental rights, relevant provisions, legal definitions, "
        "interpretation of terms, or high court writ / enforcement of rights. "
        f"{lang_rule} "
        "Do not name article numbers, section numbers, act titles, or case citations. "
        "Do not answer the legal question. Do not invent facts."
    )
    prompt = (
        "User question:\n"
        f"{text[:1500]}\n\n"
        "JSON with 2 or 3 role-shaped search queries:"
    )
    try:
        from groq_client import generate_text

        raw = generate_text(
            prompt,
            system=system,
            temperature=0,
            max_tokens=280,
            json_mode=True,
        )
        payload = json.loads(raw or "")
        rows = payload.get("queries") if isinstance(payload, dict) else None
    except Exception:
        return [text]

    # Drop rewriter lines that cite provision numbers (retrieval must not be
    # steered by invented article labels).
    cite_noise = re.compile(
        r"(?i)\b(?:article|art\.?|section|sec\.?|অনুচ্ছেদ|ধারা)\s*[0-9০-৯]+"
    )
    aspects: list[str] = [text]
    seen = {text.casefold()}
    if isinstance(rows, list):
        for item in rows:
            if not isinstance(item, str):
                continue
            cleaned = " ".join(item.split()).strip()
            if len(cleaned) < 8 or len(cleaned) > 300:
                continue
            if cite_noise.search(cleaned):
                continue
            key = cleaned.casefold()
            if key in seen:
                continue
            seen.add(key)
            aspects.append(cleaned)
            # Original question + up to 3 role aspects.
            if len(aspects) >= 4:
                break
    return aspects


def _specific_tokens(text: str) -> set[str]:
    tokens = set()
    for token in tokenize(text):
        if token in _STOP or token in _GENERIC:
            continue
        bangla = any("\u0980" <= char <= "\u09ff" for char in token)
        if bangla or len(token) >= 4:
            tokens.add(token)
    return tokens


def is_definition_dump(chunk: dict, query: str) -> bool:
    """Skip dictionary provisions unless the user asked about that provision.

    Article 152 and a statute's definition section list defined words, so an
    ordinary question can match the list without the list stating the rule.
    """
    from hybrid_search import cited_keys

    cited = set(cited_keys(query))
    if str(chunk.get("article_key") or "") == "152" and "152" not in cited:
        return True
    if statute_section_key(chunk) == "2" and not _has_any(
        query, ("define", "definition", "meaning", "অর্থ কী", "অর্থ কি")
    ):
        return True
    return False


def _pending_proceeding(chunk: dict, query: str) -> bool:
    """A rule about an already-pending case does not answer a question that is not about one."""
    content = (chunk.get("content") or "").lower()
    asked = (query or "").lower()
    markers = ("চলাকালে", "pendency", "pending")
    return any(marker in content for marker in markers) and not any(
        marker in asked for marker in markers
    )


def _has_any(text: str, words: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(word in lowered for word in words)


# How many passages an answer keeps after hybrid search. ANSWER_CONTEXT_LIMIT
# overrides this and is clamped to the range below.
DEFAULT_CONTEXT_LIMIT = 8
CONTEXT_LIMIT_MIN = 1
CONTEXT_LIMIT_MAX = 12
# Two chunks of one article can both be kept only when each passes on its own.
ARTICLE_CHUNK_CAP = 2
# Semantic admission looks at the nearest Qdrant neighbors. The list is treated
# as peaked only when the top score clears the fifth score by SEMANTIC_LIST_SPREAD.
# A neighbor is then kept only when it clears that same fifth score by
# SEMANTIC_HIT_MARGIN. Checked on the six evaluation queries: English arrest and
# property gaps are 0.192 and 0.149; English movement is 0.041; the three Bengali
# gaps are 0.012, 0.023, and 0.033. The irrelevant neighbor behind a real top hit
# sits 0.053 to 0.067 above the fifth score, so the hit margin is wider than that.
SEMANTIC_TOP_HITS = 3
SEMANTIC_REFERENCE_RANK = 5
SEMANTIC_LIST_SPREAD = 0.08
SEMANTIC_HIT_MARGIN = 0.09


def context_limit() -> int:
    """Passage cap for one answer. Invalid values use the default."""
    raw = os.getenv("ANSWER_CONTEXT_LIMIT", "").strip()
    if not raw:
        return DEFAULT_CONTEXT_LIMIT
    try:
        value = int(raw)
    except ValueError:
        return DEFAULT_CONTEXT_LIMIT
    return min(CONTEXT_LIMIT_MAX, max(CONTEXT_LIMIT_MIN, value))


def semantic_admit_ids(scored: list[tuple[int, float]]) -> set[int]:
    """Point ids a peaked semantic list may keep without a shared keyword.

    scored is best-first. A flat list admits nothing. Keyword matches are decided
    separately and do not depend on this set.
    """
    if len(scored) < SEMANTIC_REFERENCE_RANK:
        return set()
    reference = scored[SEMANTIC_REFERENCE_RANK - 1][1]
    if scored[0][1] - reference < SEMANTIC_LIST_SPREAD:
        return set()
    return {
        row_id
        for row_id, score in scored[:SEMANTIC_TOP_HITS]
        if score - reference >= SEMANTIC_HIT_MARGIN
    }


def select_relevant_chunks(
    query: str,
    ranked: list[dict],
    limit: int | None = None,
) -> list[dict]:
    """Keep named, keyword-matching, or peaked semantic passages.

    Keyword and citation matches are unchanged. semantic_admit supplements them
    for a passage the score gate already accepted. Chunks are not added because
    another chunk of the same article was accepted.
    """
    from hybrid_search import cited_keys

    if limit is None:
        limit = context_limit()
    wanted = _specific_tokens(query)
    cited = set(cited_keys(query))
    chosen: list[dict] = []
    seen_chunks: set[str] = set()
    per_article: dict[str, int] = {}
    for index, chunk in enumerate(ranked):
        if is_definition_dump(chunk, query) or _pending_proceeding(chunk, query):
            continue
        chunk_id = str(chunk.get("chunk_id") or "")
        if chunk_id and chunk_id in seen_chunks:
            continue
        article_key = (
            normalize_bn_article_token(str(chunk.get("article_key")))
            if chunk.get("article_key")
            else ""
        )
        section_key = statute_section_key(chunk) or ""
        named = (article_key and article_key in cited) or (section_key and section_key in cited)
        overlap = wanted & _specific_tokens(chunk.get("content") or "")
        if not named and not overlap and not chunk.get("semantic_admit"):
            continue
        if article_key and per_article.get(article_key, 0) >= ARTICLE_CHUNK_CAP:
            continue
        chosen.append(chunk)
        if chunk_id:
            seen_chunks.add(chunk_id)
        if article_key:
            per_article[article_key] = per_article.get(article_key, 0) + 1
        if len(chosen) >= limit:
            break
    return chosen


def statute_section_key(chunk: dict) -> str | None:
    if str(chunk.get("collection") or "").startswith("constitution"):
        return None
    number = chunk.get("section_number")
    if number:
        return normalize_bn_article_token(str(number))
    match = _STATUTE_START.match(chunk.get("content") or "")
    if not match:
        return None
    return normalize_bn_article_token(match.group(1))


_TITLE_GENERIC = {
    "the", "of", "and", "act", "ordinance", "rules", "code", "bangladesh",
    "বাংলাদেশ", "আইন", "অধ্যাদেশ", "বিধি", "শ্রম", "labour", "labor",
}


def _title_tokens(title: str) -> set[str]:
    tokens = set()
    for token in re.findall(r"[A-Za-z\u0980-\u09FF]{2,}", title.lower()):
        if token in _TITLE_GENERIC:
            continue
        if all(char.isdigit() or "\u09e6" <= char <= "\u09ef" for char in token):
            continue
        tokens.add(token)
    return tokens


def on_the_same_issue(query: str, statutes: list[dict], constitution: list[dict]) -> list[dict]:
    """Keep a constitutional passage only when it shares the statute's issue word.

    An impeachment article can match the words "allegation" and "misconduct"
    while the statute is about dismissal. The shared issue word decides.
    """
    if not statutes:
        return constitution
    statute_tokens: set[str] = set()
    for chunk in statutes:
        statute_tokens |= _specific_tokens(chunk.get("content") or "")
    # An accusation word can link a dismissal to an unrelated proceeding, such as impeachment.
    reason_words = {"অভিযোগ", "অসদাচরণ", "অসদাচরণের", "misconduct", "allegation", "allegations"}
    issue = (_specific_tokens(query) & statute_tokens) - reason_words
    if not issue:
        return constitution
    kept = [
        chunk
        for chunk in constitution
        if issue & _specific_tokens(chunk.get("content") or "")
    ]
    return kept or constitution


def statutes_about_the_issue(query: str, chunks: list[dict]) -> list[dict]:
    """A statute needs two of the question's words. One shared verb is not the issue."""
    wanted = _specific_tokens(query)
    return [
        chunk
        for chunk in chunks
        if len(wanted & _specific_tokens(chunk.get("content") or "")) >= 2
    ]


def prefer_general_statutes(query: str, chunks: list[dict]) -> list[dict]:
    """Drop a special-class Act when a more general Act in the same set also matches.

    An export-zone statute stays when it is the only match, or when the
    question itself names that zone.
    """
    titles = {str(chunk.get("act_title") or "") for chunk in chunks}
    distinctive = {title: _title_tokens(title) for title in titles}
    query_text = query.lower()
    kept: list[dict] = []
    for chunk in chunks:
        title = str(chunk.get("act_title") or "")
        extra = {token for token in distinctive[title] if token not in query_text}
        narrower = extra and any(
            other < distinctive[title] for other in distinctive.values()
        )
        if narrower:
            continue
        kept.append(chunk)
    return kept


def provision_label(chunk: dict) -> str:
    collection = str(chunk.get("collection") or "")
    title = str(chunk.get("act_title") or "").strip()
    if collection.startswith("constitution"):
        key = chunk.get("article_key")
        if key:
            return f"Article {key} of the Constitution"
        return "Constitution passage"
    section = statute_section_key(chunk)
    act = title or "a Bangladesh statute"
    if section:
        return f"Section {section} of {act}"
    return f"Passage from {act}"


def _conversation_block(history) -> str:
    turns = normalize_history(history)
    if not turns:
        return ""
    lines = ["Conversation so far:"]
    for turn in turns:
        speaker = "User" if turn["role"] == "user" else "VerdictAI"
        lines.append(f"{speaker}: {turn['content']}")
    return "\n".join(lines) + "\n\n"


def legal_system_prompt(language: str | None = None) -> str:
    """Instructions sent to Groq as the system message for text and voice."""
    if language == "bn":
        language_rule = (
            "The user selected Bangla. Write every sentence in Bangla. "
            "Understand informal Bangla and Banglish. Do not switch to English."
        )
        headings = "\n".join(_BN_HEADINGS)
    elif language == "en":
        language_rule = (
            "The user selected English. Write every sentence in English. "
            "Understand informal Bangla and Banglish. Do not switch to Bangla."
        )
        headings = "\n".join(_EN_HEADINGS)
    else:
        language_rule = (
            "Write in the language of the current question. "
            "Understand informal Bangla and Banglish. Do not switch languages."
        )
        headings = "\n".join(_EN_HEADINGS)

    return f"""You are VerdictAI. Text chat and voice chat use this same legal reasoning. Bangladesh law only. Do not use or mention the law of any other country.

Before answering, identify the legal issue and its domain: a constitutional provision, a statute, a regulation, or a judicial decision. Do not assume the Constitution answers every question.
Where a source allows an action only if a condition is met, and the question says that condition is absent, say the action was not permitted. Then say the person can dispute that action because the written condition was not met.
The passages in the user message are retrieval candidates. A high rank is not proof of legal relevance. Use a passage only when its own words address the issue. A shared word is not enough when the passage uses that word for a different issue. Explain how each cited provision relates to the question.
Never build an answer around an unrelated provision. Never invent an article number, a section number, an act, a court, a penalty, a time limit, or a legal conclusion.
A line titled Article is part of the Constitution. A line titled Section is a statute, not a constitutional article. Copy an act title as it appears. If a constitutional provision is limited to the State or to service of the Republic, do not apply it to a private person. If a statute's title limits it to a zone, an industry, or a class of employer, do not apply it unless the question is about that class. If a text gives different periods to different groups, keep each period.
Read an exception in the direction it is written. If a text forbids an action unless a condition is met, that action is not permitted when the condition is absent. A person can dispute an action the text does not permit. A payment or punishment that the text gives only after a finding of guilt does not apply when the question says there was no such finding.
Do not say a person is guilty or liable. An offence is made out only when every element written in the provision is present in the question. If one element is missing, say that the definition is not met and which element is missing.
Separate what the text states from what is only an interpretation. If an essential fact is missing, ask for it. If the candidates do not contain the rule, say that the available sources are insufficient and do not fill the gap.
{language_rule}
Write in plain sentences. No emotion or delivery tags. No repeated disclaimer. Use **bold** for a provision number and __semibold__ for the main right or duty.
For a detailed question, use these headings when they add information. Put each heading on its own line, starting with the # marks shown:
{headings}
For a narrow question, give the direct answer and the provision. Omit a heading that would be empty.
Under the law, quote or closely restate only words that support the claim. Do not name a provision in order to say that it does not apply. Under practical options, name only a step the source text itself mentions, such as a notice or a payment that text required. Do not add a grievance process, a board, a lawyer, or record-keeping unless the text states it. Name a forum only when the text names it for this issue. Under limits, include exceptions written in the text and the points the sources do not decide.
Use the conversation only for facts. An earlier answer is not a source of law."""


def build_answer_prompt(
    query: str,
    chunks: list[dict],
    language: str | None = None,
    history=None,
) -> str:
    """User message: conversation, candidate sources, and the current question."""
    del language
    blocks = []
    labels = []
    for chunk in chunks:
        label = provision_label(chunk)
        labels.append(label)
        content = (chunk.get("content") or "").strip()
        if len(content) > 1400:
            content = content[:1400] + "..."
        flags = chunk.get("legal_status_flags") or []
        note = f"\nStatus notes: {', '.join(flags)}" if flags else ""
        blocks.append(f"[{label}]\n{content}{note}")
    sources = "\n\n".join(blocks) if blocks else "(no candidate source was retrieved)"
    allowed = "; ".join(dict.fromkeys(labels)) if labels else "(none)"

    return f"""{_conversation_block(history)}Candidate sources. Ignore any source that does not address the legal issue.
You may name only these provisions, and only if the source text supports the claim: {allowed}

{sources}

Current question: {query}
Before writing, apply each permission in the direction it is written. If a source allows an action only when a condition is met, and that condition did not happen, say the action was not permitted.
Answer:"""


def voice_summary_instructions(language: str | None) -> str:
    """How to compress one finished legal answer for speech. No topic is named."""
    if language == "bn":
        language_rule = "Write every sentence in Bangla."
    elif language == "en":
        language_rule = "Write every sentence in English."
    else:
        language_rule = "Write in the language of the answer."
    return f"""You compress one finished legal answer into speech.
Keep the direct conclusion, every provision number the answer itself uses, how that provision applies, the most important practical step, and every limit or warning.
Leave out repeated explanation, examples, and background. Say each point once.
Do not add a provision, a number, a forum, a step, or a fact that the answer does not already state.
Plain sentences only. No headings, bullets, or markdown.
{language_rule}"""


def build_voice_summary_prompt(answer: str) -> str:
    """User message for the spoken summary. The finished answer is the only source."""
    return (
        "Finished legal answer:\n"
        f"{answer}\n\n"
        "Speak the essential parts of this answer only.\n"
        "Summary:"
    )


def spoken_form(text: str) -> str:
    """Plain speech, without heading marks or emphasis markers."""
    cleaned = clean_answer(text)
    cleaned = re.sub(r"^#{1,6}\s*", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"^>\s*", "", cleaned, flags=re.MULTILINE)
    cleaned = cleaned.replace("**", "").replace("__", "")
    cleaned = re.sub(r"(?<!\w)\*(?!\s)", "", cleaned)
    cleaned = re.sub(r"\s*\n+\s*", " ", cleaned)
    return re.sub(r"[ \t]{2,}", " ", cleaned).strip()


def reference_keys(text: str) -> set[str]:
    """Provision numbers named in a text, regardless of article or section."""
    return {key for _kind, key in _citations(text)}


def without_new_references(source: str, spoken: str) -> str:
    """Drop any spoken sentence that names a provision the finished answer does not."""
    allowed = reference_keys(source)
    kept: list[str] = []
    for sentence in re.split(r"(?<=[.!?।])\s+", spoken or ""):
        if reference_keys(sentence) - allowed:
            continue
        if sentence.strip():
            kept.append(sentence.strip())
    return " ".join(kept).strip()


def trim_spoken(text: str, character_limit: int) -> str:
    """Keep whole sentences inside the spoken character budget."""
    if character_limit <= 0 or len(text) <= character_limit:
        return text
    pieces = re.split(r"(?<=[.!?।])\s+", text)
    kept: list[str] = []
    total = 0
    for piece in pieces:
        addition = len(piece) + (1 if kept else 0)
        if kept and total + addition > character_limit:
            break
        if not kept and len(piece) > character_limit:
            return piece[:character_limit].rsplit(" ", 1)[0].strip()
        kept.append(piece)
        total += addition
    return " ".join(kept).strip() or text[:character_limit].rsplit(" ", 1)[0].strip()


def clean_answer(text: str) -> str:
    cleaned = (text or "").strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z]*\n?", "", cleaned)
        cleaned = re.sub(r"\n?```$", "", cleaned).strip()
    cleaned = _AUDIO_TAG.sub(" ", cleaned)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    if cleaned.lower().startswith("answer:"):
        cleaned = cleaned[7:].strip()
    return cleaned.strip()


def _citations(answer: str) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for match in _CITE_SPAN.finditer(answer or ""):
        label = match.group("label").lower()
        kind = "section" if label.startswith(("section", "sec", "ধারা")) else "article"
        for number in _NUMBER.findall(match.group("body")):
            key = normalize_bn_article_token(number)
            if key:
                found.append((kind, key))
    return found


def _allowed_keys(chunks: list[dict]) -> tuple[set[str], set[str]]:
    articles: set[str] = set()
    sections: set[str] = set()
    for chunk in chunks:
        if str(chunk.get("collection") or "").startswith("constitution"):
            key = chunk.get("article_key")
            if key:
                articles.add(normalize_bn_article_token(str(key)))
            continue
        section = statute_section_key(chunk)
        if section:
            sections.add(section)
    return articles, sections


def answer_problems(answer: str, chunks: list[dict]) -> list[str]:
    """Unsupported citations, plus a forum the retrieved texts never name."""
    problems = citation_problems(answer, chunks)
    source = " ".join((chunk.get("content") or "") for chunk in chunks).lower()
    lowered = (answer or "").lower()
    for needle, label in _FORUMS:
        if needle in lowered and needle not in source and label not in problems:
            problems.append(label)
    return problems


def _outside_sources(answer: str, chunks: list[dict]) -> str:
    """Drop spans copied from a source so a cross-reference inside a quote is not a new citation."""
    source = "\n".join((chunk.get("content") or "") for chunk in chunks)
    text = answer or ""
    if len(source) < 40 or len(text) < 40:
        return text
    kept: list[str] = []
    index = 0
    while index < len(text):
        window = text[index:index + 40]
        if len(window) == 40 and window in source:
            end = index + 40
            while end <= len(text) and text[index:end] in source:
                end += 1
            index = end - 1
            continue
        kept.append(text[index])
        index += 1
    return "".join(kept)


def citation_problems(answer: str, chunks: list[dict]) -> list[str]:
    """Citations whose number is not in the retrieved texts, or that use the wrong kind."""
    articles, sections = _allowed_keys(chunks)
    mentioned = {
        normalize_bn_article_token(number)
        for chunk in chunks
        for number in _NUMBER.findall(chunk.get("content") or "")
    }
    problems: list[str] = []
    for kind, key in _citations(_outside_sources(answer, chunks)):
        if kind == "article":
            if key not in articles:
                label = f"Article {key}"
            else:
                continue
        elif key in sections or key in mentioned:
            continue
        else:
            label = f"Section {key}"
        if label not in problems:
            problems.append(label)
    return problems


_FORUMS = (
    ("high court", "the High Court Division"),
    ("labour court", "a labour court"),
    ("labor court", "a labour court"),
    ("labour tribunal", "a labour tribunal"),
    ("labor tribunal", "a labour tribunal"),
    ("labour office", "a labour office"),
    ("labor office", "a labour office"),
    ("labour board", "a labour board"),
    ("civil suit", "a civil suit"),
    ("civil court", "a civil court"),
    ("শ্রম আদালত", "শ্রম আদালত"),
    ("শ্রম আপিল ট্রাইব্যুনাল", "শ্রম আপিল ট্রাইব্যুনাল"),
    ("হাইকোর্ট", "হাইকোর্ট"),
    ("দেওয়ানি আদালত", "দেওয়ানি আদালত"),
    ("শ্রম মন্ত্রণালয়", "শ্রম মন্ত্রণালয়"),
    ("আদালত", "আদালত"),
)


_NOT_PERMITTED = (
    "not permitted", "not allowed", "unlawful", "illegal", "অবৈধ",
    "করা যাইবে না", "করা যাবে না",
)
_NO_REMEDY = (
    "no remedy", "no legal remedy", "no legal action", "cannot claim",
    "প্রতিকার নেই", "প্রতিকার পেতে পারবেন না", "পদক্ষেপ নিতে পারবেন না",
    "দাবি করতে পারবেন না", "দাবি বা প্রতিকার", "আইনি ভিত্তি নেই",
)
_UNSUPPORTED_REMEDY = ("পুনর্বহাল", "ক্ষতিপূরণ", "reinstatement", "compensation")
_INVENTED_STEPS = (
    "grievance", "lawyer", "education board", "written record", "witness",
)


def repair_answer(answer: str, chunks: list[dict]) -> str:
    """Drop lines that deny a remedy or name a forum or remedy the sources do not contain."""
    source = " ".join((chunk.get("content") or "") for chunk in chunks).lower()
    forums = [needle for needle, _label in _FORUMS if needle not in source]
    remedies = [word for word in _UNSUPPORTED_REMEDY if word not in source]
    invented = [word for word in _INVENTED_STEPS if word not in source]
    kept: list[str] = []
    for line in (answer or "").splitlines():
        lowered = line.lower()
        if any(phrase in lowered for phrase in _NO_REMEDY):
            continue
        if any(needle in lowered for needle in forums):
            continue
        if any(word in lowered for word in remedies):
            continue
        if any(word in lowered for word in invented):
            continue
        if _invented_period(line, source):
            continue
        kept.append(line)
    text = re.sub(r"\n{3,}", "\n\n", "\n".join(kept)).strip()
    return _drop_empty_headings(_fill_empty_direct(text))


def _drop_empty_headings(text: str) -> str:
    lines = text.splitlines()
    kept: list[str] = []
    for index, line in enumerate(lines):
        if line.startswith("#"):
            body = []
            for later in lines[index + 1:]:
                if later.startswith("#"):
                    break
                body.append(later)
            if not any(part.strip() for part in body):
                continue
        kept.append(line)
    return "\n".join(kept).strip()


_PERIOD = re.compile(
    r"([0-9০-৯]+)\s*(?:দিন|মাস|বৎসর|বছর|কার্যদিবস|days?|months?|years?)",
    re.IGNORECASE,
)


def _invented_period(line: str, source: str) -> bool:
    for match in _PERIOD.finditer(line):
        number = normalize_bn_article_token(match.group(1))
        if number and number not in source and match.group(1) not in source:
            return True
    return False


def _fill_empty_direct(text: str) -> str:
    lines = text.splitlines()
    headings = [index for index, line in enumerate(lines) if line.startswith("#")]
    if not headings:
        return text
    end = headings[1] if len(headings) > 1 else len(lines)
    if any(line.strip() for line in lines[headings[0] + 1:end]):
        return text
    for line in lines[end:]:
        if line.startswith("#") or not line.strip():
            continue
        if any(phrase in line.lower() for phrase in _NOT_PERMITTED):
            lines.insert(headings[0] + 1, line.strip().lstrip("-").strip())
            break
    return "\n".join(lines)


def remedy_contradiction(answer: str) -> bool:
    """True when an answer says an action was not permitted and also says there is no remedy."""
    text = (answer or "").lower()
    return any(phrase in text for phrase in _NOT_PERMITTED) and any(
        phrase in text for phrase in _NO_REMEDY
    )


def unrecognized_question(language: str | None) -> str:
    if language == "bn":
        return (
            "# সরাসরি উত্তর\n"
            "এটি কোনো আইনি প্রশ্ন হিসেবে বোঝা যায়নি।\n\n"
            "## সীমা\n"
            "পুরো বাক্যে জিজ্ঞাসা করুন।"
        )
    return (
        "# Direct answer\n"
        "This does not look like a legal question.\n\n"
        "## Limits\n"
        "Please ask it in a full sentence."
    )


def insufficient_answer(language: str | None) -> str:
    if language == "bn":
        return (
            "# সরাসরি উত্তর\n"
            "প্রাপ্ত আইনি অংশে এই প্রশ্নের উত্তর দেওয়ার মতো তথ্য নেই।\n\n"
            "## সীমা\n"
            "যে নিয়ম ওই অংশে লেখা নেই, সেটি বলা যাবে না।"
        )
    return (
        "# Direct answer\n"
        "The retrieved legal texts do not contain enough to answer this.\n\n"
        "## Limits\n"
        "A rule that is not written in those texts cannot be stated."
    )


def append_citation_note(answer: str, problems: list[str], language: str | None) -> str:
    if not problems:
        return answer
    listed = ", ".join(problems)
    if language == "bn":
        note = f"প্রাপ্ত অংশে {listed} নেই। এই উত্তর সেই সংখ্যার ওপর নির্ভর করে না।"
    else:
        note = (
            f"The retrieved texts do not include {listed}. "
            "This answer does not rely on those citations."
        )
    return answer.rstrip() + "\n\n" + note
