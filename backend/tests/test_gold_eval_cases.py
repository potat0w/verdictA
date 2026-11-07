"""Unit tests for gold file parsing only — no Qdrant, no model calls."""

from gold_eval_cases import (
    expected_articles_from_text,
    load_gold_cases,
    normalize_article_key,
)


def test_normalize_strips_clause_suffixes():
    assert normalize_article_key("21(2)") == "21"
    assert normalize_article_key("15(a)") == "15"
    assert normalize_article_key("2A") == "2A"
    assert normalize_article_key("২৯") == "29"


def test_expected_articles_dedupe_and_order():
    text = (
        "Article 29(1): Equality.\n"
        "Article 29(2): No discrimination.\n"
        "Article 31: Protection of law."
    )
    assert expected_articles_from_text(text) == ("29", "31")


def test_load_gold_has_en_and_bn_pairs():
    cases = load_gold_cases()
    assert len(cases) == 26  # 13 scenarios × EN + BN
    en = [case for case in cases if case.language == "en"]
    bn = [case for case in cases if case.language == "bn"]
    assert len(en) == len(bn) == 13
    arrest = next(case for case in en if "Police Arrest" in case.title)
    assert arrest.expected_articles == ("33",)
    job = next(case for case in en if "Government Job" in case.title)
    assert job.expected_articles == ("29",)
    assert "place of birth" in job.query.lower()
    education = next(case for case in en if "Right to Education" in case.title)
    assert education.expected_articles == ("17", "15")
    assert "8" not in education.expected_articles
    religion = next(
        case
        for case in cases
        if case.case_id.endswith("-bn") and "41" in case.expected_articles
    )
    assert religion.language == "bn"
    assert "2A" in religion.expected_articles
    rape = next(case for case in en if "Rape and Justice" in case.title)
    assert rape.expected_articles == ("27", "31", "32")
    domestic = next(case for case in bn if "Domestic Violence" in case.title)
    assert domestic.expected_articles == ("27", "28", "31", "32")
