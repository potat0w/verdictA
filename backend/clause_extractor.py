"""Split contract text into clauses. Pure function: no model calls."""

from __future__ import annotations

import re
from dataclasses import dataclass

MAX_CLAUSE_CHARS = 1500
MAX_CLAUSES = 60
FRAGMENT_CHARS = 40
SHORT_CHILD_CHARS = 280
GROUP_COMBINED_CHARS = 900

_DECIMAL_DOTTED = re.compile(r"^(\d+(?:\.\d+)*)\.\s*(.*)$")
_DECIMAL_BARE = re.compile(r"^(\d+\.\d+(?:\.\d+)*)\s+(.*)$")
_PAREN = re.compile(r"^\(([A-Za-z0-9]+)\)\s+(.*)$")
_LABELED = re.compile(
    r"^(Clause|Article|Section)\s+(\d+[A-Za-z]?)\b\s*[:.\-]?\s*(.*)$",
    re.IGNORECASE,
)
_MARKER_START = re.compile(
    r"^(?:\d+(?:\.\d+)+\s+|\d+\.\s*|\([A-Za-z0-9]+\)\s+|(?:Clause|Article|Section)\s+\d+)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Clause:
    clause_id: str
    heading: str | None
    text: str


@dataclass(frozen=True)
class ClauseExtraction:
    """clauses plus whether the 60-clause cap dropped trailing text."""

    clauses: list[Clause]
    truncated: bool


@dataclass
class _Segment:
    depth: int
    heading: str | None
    text: str


def extract_clauses(text: str) -> ClauseExtraction:
    """Return clauses in document order.

    The result is a ClauseExtraction rather than a bare list so the caller
    can report truncation. `.clauses` is the clause list.
    """
    normalized = (text or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        return ClauseExtraction(clauses=[], truncated=False)

    if _has_structure(normalized):
        segments = _segment_structured(normalized)
    else:
        segments = _segment_paragraphs(normalized)

    segments = _group_short_children(segments)
    segments = _attach_short_parent_headings(segments)
    segments = _merge_fragments(segments)
    pieces = _split_long_segments(segments)
    kept = pieces[:MAX_CLAUSES]
    truncated = len(pieces) > MAX_CLAUSES
    clauses = [
        Clause(clause_id=f"c{index + 1}", heading=piece.heading, text=piece.text)
        for index, piece in enumerate(kept)
        if piece.text.strip()
    ]
    return ClauseExtraction(clauses=clauses, truncated=truncated)


def _has_structure(text: str) -> bool:
    for line in text.split("\n"):
        if _match_marker(line.strip()) is not None or _is_caps_heading(line.strip()):
            return True
    return False


def _match_marker(line: str) -> tuple[int, str, str] | None:
    """Return (depth, heading, remainder) for a clause-start line."""
    if not line:
        return None

    bare = _DECIMAL_BARE.match(line)
    if bare:
        key = bare.group(1)
        return key.count(".") + 1, key, bare.group(2).strip()

    dotted = _DECIMAL_DOTTED.match(line)
    if dotted:
        key = dotted.group(1)
        heading = key if "." in key else f"{key}."
        return key.count(".") + 1, heading, dotted.group(2).strip()

    paren = _PAREN.match(line)
    if paren:
        return -1, f"({paren.group(1)})", paren.group(2).strip()

    labeled = _LABELED.match(line)
    if labeled:
        heading = f"{labeled.group(1).title()} {labeled.group(2)}"
        return 1, heading, labeled.group(3).strip()

    return None


def _is_caps_heading(line: str) -> bool:
    if not line or len(line) < 4 or len(line) > 80 or line.endswith("."):
        return False
    letters = [char for char in line if char.isalpha()]
    if len(letters) < 4 or any(char.islower() for char in letters):
        return False
    return all(char.isalpha() or char in " &/'-,()" for char in line)


def _segment_paragraphs(text: str) -> list[_Segment]:
    parts = re.split(r"\n\s*\n", text)
    return [_Segment(0, None, part.strip()) for part in parts if part.strip()]


def _segment_structured(text: str) -> list[_Segment]:
    lines = text.split("\n")
    segments: list[_Segment] = []
    buf: list[str] = []
    heading: str | None = None
    depth = 0
    last_numbered_depth = 0

    def flush() -> None:
        nonlocal buf, heading, depth
        raw = "\n".join(buf).strip()
        buf = []
        if not raw:
            heading = None
            return
        segments.append(_Segment(depth=depth, heading=heading, text=raw))
        heading = None

    index = 0
    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if not stripped and not buf:
            index += 1
            continue

        marker = _match_marker(stripped) if stripped else None
        caps = bool(stripped) and marker is None and _is_caps_heading(stripped)

        if caps:
            following = _next_nonempty(lines, index + 1)
            # A capitals line sitting above a numbered clause is a document title.
            if following and _match_marker(following) is not None:
                index += 1
                continue
            if buf:
                flush()
            heading = stripped
            depth = 1
            buf = [stripped]
            index += 1
            continue

        if marker is not None:
            if buf:
                flush()
            marker_depth, marker_heading, _remainder = marker
            if marker_depth == -1:
                marker_depth = last_numbered_depth + 1 if last_numbered_depth else 2
            else:
                last_numbered_depth = marker_depth
            depth = marker_depth
            heading = marker_heading
            buf = [stripped]
            index += 1
            continue

        buf.append(line)
        index += 1

    flush()
    return segments


def _next_nonempty(lines: list[str], start: int) -> str | None:
    for line in lines[start:]:
        stripped = line.strip()
        if stripped:
            return stripped
    return None


def _group_short_children(segments: list[_Segment]) -> list[_Segment]:
    grouped: list[_Segment] = []
    for segment in segments:
        if (
            grouped
            and segment.depth > grouped[-1].depth
            and len(segment.text) <= SHORT_CHILD_CHARS
        ):
            parent = grouped[-1]
            combined = f"{parent.text}\n{segment.text}".strip()
            if len(combined) <= GROUP_COMBINED_CHARS:
                grouped[-1] = _Segment(parent.depth, parent.heading, combined)
                continue
        grouped.append(segment)
    return grouped


def _attach_short_parent_headings(segments: list[_Segment]) -> list[_Segment]:
    attached: list[_Segment] = []
    index = 0
    while index < len(segments):
        current = segments[index]
        nxt = segments[index + 1] if index + 1 < len(segments) else None
        if (
            nxt is not None
            and len(current.text) < FRAGMENT_CHARS
            and nxt.depth > current.depth
        ):
            heading = current.heading or current.text.strip()
            attached.append(
                _Segment(
                    depth=nxt.depth,
                    heading=heading,
                    text=f"{current.text}\n{nxt.text}".strip(),
                )
            )
            index += 2
            continue
        attached.append(current)
        index += 1
    return attached


def _merge_fragments(segments: list[_Segment]) -> list[_Segment]:
    merged: list[_Segment] = []
    for segment in segments:
        structural = _MARKER_START.match(segment.text.lstrip()) is not None
        if merged and len(segment.text) < FRAGMENT_CHARS and not structural:
            previous = merged[-1]
            merged[-1] = _Segment(
                previous.depth,
                previous.heading,
                f"{previous.text}\n{segment.text}".strip(),
            )
            continue
        merged.append(segment)
    return merged


def _split_long_segments(segments: list[_Segment]) -> list[_Segment]:
    pieces: list[_Segment] = []
    for segment in segments:
        for part in _split_text(segment.text, MAX_CLAUSE_CHARS):
            pieces.append(_Segment(segment.depth, segment.heading, part))
    return pieces


def _split_text(text: str, limit: int) -> list[str]:
    remaining = text.strip()
    if len(remaining) <= limit:
        return [remaining] if remaining else []

    parts: list[str] = []
    while len(remaining) > limit:
        window = remaining[:limit]
        cut = max(window.rfind("\n"), window.rfind(". "))
        if cut < limit // 2:
            cut = limit
        elif window.rfind(". ") == cut:
            cut += 1
        piece = remaining[:cut].strip()
        if piece:
            parts.append(piece)
        remaining = remaining[cut:].strip()
    if remaining:
        parts.append(remaining)
    return parts
