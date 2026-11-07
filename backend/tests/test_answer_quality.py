"""The text and voice answers are built by the same prompt and citation check."""

from fastapi.testclient import TestClient

from answer_quality import (
    append_citation_note,
    build_answer_prompt,
    citation_problems,
    clean_answer,
    legal_system_prompt,
    normalize_history,
    retrieval_text,
    select_relevant_chunks,
)
from app import app
from hybrid_search import partition_ids

SECRET = "test-webhook-secret"


def _chunk(article_key, content, collection="constitution-en"):
    return {
        "collection": collection,
        "article_key": article_key,
        "act_title": "The Constitution of the People's Republic of Bangladesh",
        "content": content,
        "chunk_id": f"bd-constitution:en:{article_key}:0",
    }


def test_language_partition_stays_on_the_constitution_collection():
    chunks = [
        {"collection": "constitution-en", "chunk_type": "article"},
        {"collection": "other-acts", "language": "en", "chunk_type": "section"},
        {"collection": "constitution-bn", "chunk_type": "article"},
        {"collection": "constitution-en", "chunk_type": "footnote"},
    ]
    assert partition_ids(chunks, "en") == [0]


def test_relevant_chunks_keep_matching_articles_and_drop_the_rest():
    ranked = [
        _chunk("33", "No person who is arrested shall be detained without the grounds."),
        _chunk("51", "The President is not answerable in any court."),
        _chunk("35", "No person shall be subjected to torture. A person arrested has safeguards."),
        _chunk("152", "In this Constitution, unless the context requires otherwise."),
    ]
    query = "The police arrested someone and did not tell them the reason."
    chosen = select_relevant_chunks(query, ranked)
    keys = [chunk["article_key"] for chunk in chosen]
    assert keys[0] == "33"
    assert "35" in keys
    assert "51" not in keys
    assert "152" not in keys


def test_a_role_word_does_not_select_an_unrelated_act():
    ranked = [
        {
            "collection": "other-acts",
            "act_title": "The Married Women's Property Act, 1874",
            "section_number": "8",
            "content": "If a married woman possesses separate property.",
        },
        {
            "collection": "other-acts",
            "act_title": "The Penal Code, 1860",
            "section_number": "503",
            "content": "Whoever threatens another with any injury to his reputation commits criminal intimidation.",
        },
    ]
    query = "The principal is threatening my mother if she does not do the principal's work."
    chosen = select_relevant_chunks(query, ranked)
    assert [chunk["section_number"] for chunk in chosen] == ["503"]
    from answer_quality import statutes_about_the_issue

    assert statutes_about_the_issue(query, chosen) == []


def test_bangla_function_words_do_not_select_an_article():
    from answer_quality import question_script, unrecognized_question

    ranked = [
        _chunk("81", "একটি আইন এই ক্ষেত্রে প্রযোজ্য।"),
        _chunk("135", "কোনো ব্যক্তিকে বরখাস্ত করা যাইবে না।"),
    ]
    query = "হাসানকে বিনা নোটিশে বরখাস্ত করা হয়েছে। সরকারি চাকরির নিয়ম কেন খাটে না?"
    assert [chunk["article_key"] for chunk in select_relevant_chunks(query, ranked)] == ["135"]
    assert question_script(query) == "bn"
    assert question_script("gfrgseg") is None
    assert "legal question" in unrecognized_question("en")
    assert "আইনি প্রশ্ন" in unrecognized_question("bn")
    assert unrecognized_question("en") != __import__("answer_quality").insufficient_answer("en")


def test_a_special_zone_act_drops_when_a_general_act_also_matches():
    from answer_quality import citation_problems, prefer_general_statutes

    general = {
        "collection": "other-acts",
        "act_title": "বাংলাদেশ শ্রম আইন, ২০০৬",
        "section_number": "23",
        "content": "ধারা ২৪ এর অধীন অসদাচরণের অপরাধে দোষী সাব্যস্ত হইলে বিনা নোটিশে বরখাস্ত করা যাইবে।",
    }
    zone = {
        "collection": "other-acts",
        "act_title": "বাংলাদেশ ইপিজেড শ্রম আইন, ২০১৯",
        "section_number": "21",
        "content": "বিনা নোটিশে বরখাস্ত করা যাইবে।",
    }
    query = "বেসরকারি কোম্পানি হাসানকে বরখাস্ত করেছে।"
    kept = prefer_general_statutes(query, [zone, general])
    assert [chunk["section_number"] for chunk in kept] == ["23"]
    alone = prefer_general_statutes(query, [zone])
    assert alone == [zone]
    quoted = (
        "Section 23 says ধারা ২৪ এর অধীন অসদাচরণের অপরাধে দোষী সাব্যস্ত হইলে বিনা নোটিশে বরখাস্ত করা যাইবে। "
        "Section 99 also applies."
    )
    assert citation_problems(quoted, [general]) == ["Section 99"]
    assert citation_problems("ধারা ২৪ এর অধীন দোষী সাব্যস্ত হতে হয়।", [general]) == []


def test_a_forbidden_action_cannot_also_have_no_remedy():
    from answer_quality import remedy_contradiction

    assert remedy_contradiction(
        "বিনা নোটিশে বরখাস্ত অবৈধ। তিনি কোনো প্রতিকার পেতে পারবেন না।"
    )
    assert not remedy_contradiction("বিনা নোটিশে বরখাস্ত অবৈধ। তিনি সেই বরখাস্ত নিয়ে আপত্তি করতে পারেন।")
    from answer_quality import repair_answer

    broken = (
        "# সরাসরি উত্তর\n"
        "তিনি কোনো অধিকার দাবি করতে পারবেন না।\n\n"
        "## কী করা যায়\n"
        "বরখাস্ত অবৈধ।\n"
        "তিনি পুনর্বহাল চাইতে শ্রম আদালতে যেতে পারেন।"
    )
    repaired = repair_answer(broken, [])
    assert "দাবি করতে পারবেন না" not in repaired
    assert "শ্রম আদালত" not in repaired
    assert "পুনর্বহাল" not in repaired
    assert "অবৈধ" in repaired
    from answer_quality import on_the_same_issue

    statute = {"content": "কোনো শ্রমিককে বিনা নোটিশে বরখাস্ত করা যাইবে না।"}
    dismissal = _chunk("135", "প্রজাতন্ত্রের কর্মে নিযুক্ত ব্যক্তিকে বরখাস্ত করা যাইবে না।")
    impeachment = _chunk("52", "গুরুতর অসদাচরণের অভিযোগে রাষ্ট্রপতিকে অভিশংসিত করা যাইতে পারিবে।")
    aligned = on_the_same_issue(
        "হাসানকে বরখাস্ত করা হয়েছে।",
        [statute],
        [impeachment, dismissal],
    )
    assert [chunk["article_key"] for chunk in aligned] == ["135"]
    pending = _chunk("228", "সালিসী কার্যধারা চলাকালে কোনো শ্রমিককে বরখাস্ত করা যাইবে না।")
    dismissal = _chunk("23", "কোনো শ্রমিককে বিনা নোটিশে বরখাস্ত করা যাইবে, যদি তিনি অসদাচরণে দোষী সাব্যস্ত হন।")
    kept = select_relevant_chunks("হাসানকে বিনা নোটিশে বরখাস্ত করা হয়েছে।", [pending, dismissal])
    assert [chunk["article_key"] for chunk in kept] == ["23"]


def test_an_unrelated_top_hit_is_not_used():
    ranked = [
        _chunk("4", "The national anthem is the first ten lines of the song. The national flag is green."),
        _chunk("42", "Every citizen shall have the right to acquire, hold, transfer or otherwise dispose of property."),
    ]
    query = "Someone illegally occupied my property."
    assert [chunk["article_key"] for chunk in select_relevant_chunks(query, ranked)] == ["42"]
    assert select_relevant_chunks(query, ranked[:1]) == []
    named = select_relevant_chunks("What does Article 4 say?", ranked)
    assert named[0]["article_key"] == "4"
    assert named[0]["chunk_id"] == "bd-constitution:en:4:0"
    assert named[0]["act_title"] == "The Constitution of the People's Republic of Bangladesh"


def test_score_gate_uses_the_measured_query_gaps():
    from answer_quality import semantic_admit_ids

    arrest = semantic_admit_ids(
        [(1, 0.5828), (2, 0.4902), (3, 0.4573), (4, 0.4008), (5, 0.3907)]
    )
    assert arrest == {1, 2}
    property_rights = semantic_admit_ids(
        [(10, 0.5258), (11, 0.4301), (12, 0.4063), (13, 0.3923), (14, 0.3768)]
    )
    assert property_rights == {10}
    movement = semantic_admit_ids(
        [(20, 0.5190), (21, 0.5054), (22, 0.5018), (23, 0.4844), (24, 0.4776)]
    )
    assert movement == set()
    bangla_arrest = semantic_admit_ids(
        [(30, 0.8772), (31, 0.8771), (32, 0.8706), (33, 0.8681), (34, 0.8653)]
    )
    assert bangla_arrest == set()
    bangla_property = semantic_admit_ids(
        [(40, 0.8860), (41, 0.8805), (42, 0.8789), (43, 0.8684), (44, 0.8629)]
    )
    assert bangla_property == set()
    bangla_movement = semantic_admit_ids(
        [(50, 0.7754), (51, 0.7526), (52, 0.7473), (53, 0.7466), (54, 0.7425)]
    )
    assert bangla_movement == set()


def test_semantic_admit_supplements_keyword_matching():
    ranked = [
        _chunk("43", "Every citizen shall have the right to be secure in his home."),
        _chunk("33", "No person who is arrested shall be detained without the grounds."),
    ]
    ranked[0]["semantic_admit"] = True
    query = "What rights does a person have after being arrested?"
    chosen = select_relevant_chunks(query, ranked, limit=8)
    assert [chunk["article_key"] for chunk in chosen] == ["43", "33"]
    assert chosen[0]["act_title"]
    flat = dict(ranked[0])
    flat["semantic_admit"] = False
    assert [chunk["article_key"] for chunk in select_relevant_chunks(query, [flat], limit=8)] == []


def test_bangla_flat_neighbors_stay_out_and_the_keyword_article_stays():
    from answer_quality import semantic_admit_ids

    scored = [(1, 0.8772), (2, 0.8771), (3, 0.8706), (4, 0.8681), (5, 0.8653)]
    assert semantic_admit_ids(scored) == set()
    court = _chunk(
        "112",
        "প্রজাতন্ত্রের সকল কর্তৃপক্ষ সুপ্রীম কোর্টের সহায়তা করিবেন।",
        collection="constitution-bn",
    )
    arrest = _chunk(
        "33",
        "গ্রেপ্তারকৃত কোন ব্যক্তিকে গ্রেপ্তারের কারণ জ্ঞাপন না করিয়া আটক রাখা যাইবে না।",
        collection="constitution-bn",
    )
    query = "গ্রেপ্তারের পর একজন ব্যক্তির কী অধিকার থাকে?"
    chosen = select_relevant_chunks(query, [court, arrest], limit=8)
    assert [chunk["article_key"] for chunk in chosen] == ["33"]
    assert chosen[0]["collection"] == "constitution-bn"
    assert chosen[0]["act_title"]


def test_two_chunks_of_one_article_each_have_to_qualify():
    first = _chunk("33", "No person who is arrested shall be detained without the grounds.")
    second = _chunk("33", "Preventive detention requires an advisory board.")
    third = _chunk("33", "The detainee may make a representation against the detention order.")
    second["chunk_id"] = "bd-constitution:en:33:1"
    third["chunk_id"] = "bd-constitution:en:33:2"
    second["semantic_admit"] = True
    query = "What rights does a person have after being arrested?"
    chosen = select_relevant_chunks(query, [first, second, third], limit=8)
    assert [chunk["chunk_id"] for chunk in chosen] == [
        "bd-constitution:en:33:0",
        "bd-constitution:en:33:1",
    ]
    assert all(chunk["article_key"] == "33" for chunk in chosen)


def test_context_limit_reads_the_environment(monkeypatch):
    from answer_quality import context_limit

    monkeypatch.delenv("ANSWER_CONTEXT_LIMIT", raising=False)
    assert context_limit() == 8
    monkeypatch.setenv("ANSWER_CONTEXT_LIMIT", "4")
    assert context_limit() == 4
    monkeypatch.setenv("ANSWER_CONTEXT_LIMIT", "40")
    assert context_limit() == 12
    monkeypatch.setenv("ANSWER_CONTEXT_LIMIT", "0")
    assert context_limit() == 1
    monkeypatch.setenv("ANSWER_CONTEXT_LIMIT", "many")
    assert context_limit() == 8


def test_retrieval_aspect_queries_keeps_original_and_rejects_empty(monkeypatch):
    from answer_quality import retrieval_aspect_queries

    monkeypatch.setenv("RETRIEVAL_ASPECT_QUERIES", "1")
    monkeypatch.setattr(
        "groq_client.generate_text",
        lambda *args, **kwargs: (
            '{"queries":["arrest must state grounds to the detained person",'
            '"right to consult a lawyer after arrest",'
            '"no detention except in accordance with law",'
            '"Article 33"]}'
        ),
    )
    query = "Police arrest Karim and refuse to say why."
    aspects = retrieval_aspect_queries(query, "en")
    assert aspects[0] == query
    assert "arrest must state grounds to the detained person" in aspects
    assert "right to consult a lawyer after arrest" in aspects
    assert "no detention except in accordance with law" in aspects
    assert len(aspects) == 4
    # Article numbers from the rewriter must not be kept as search aspects.
    assert all("article 33" not in item.casefold() for item in aspects[1:])

    monkeypatch.setenv("RETRIEVAL_ASPECT_QUERIES", "0")
    assert retrieval_aspect_queries(query, "en") == [query]


def test_definition_lists_are_not_used_as_the_rule():
    from answer_quality import is_definition_dump

    ranked = [
        _chunk("152", "In this Constitution, police means the police force."),
        _chunk("43", "Every citizen has the right to be secure in his home."),
    ]
    chosen = select_relevant_chunks("Police entered someone's home.", ranked)
    assert [chunk["article_key"] for chunk in chosen] == ["43"]
    cited = select_relevant_chunks("What does Article 152 define?", ranked)
    assert cited[0]["article_key"] == "152"
    wage_definition = {
        "collection": "other-acts",
        "section_number": "2",
        "content": "মজুরী অর্থ টাকায় প্রকাশিত পারিশ্রমিক।",
    }
    assert is_definition_dump(wage_definition, "A worker was not paid for overtime.")
    assert not is_definition_dump(wage_definition, "What is the definition of wage?")


def test_prompt_is_shared_and_locks_the_selected_language():
    chunks = [
        _chunk("33", "No person who is arrested shall be detained without the grounds."),
        {
            "collection": "other-acts",
            "act_title": "বাংলাদেশ শ্রম আইন, ২০০৬",
            "section_number": "108",
            "content": "অধিকাল কাজের জন্য দ্বিগুণ হারে ভাতা পাইবেন।",
        },
    ]
    system = legal_system_prompt("en")
    prompt = build_answer_prompt(
        "A worker was not paid for overtime.",
        chunks,
        "en",
        history=[{"role": "user", "content": "He works in a factory."}, {"role": "note", "content": "skip"}],
    )
    assert "Text chat and voice chat use this same legal reasoning." in system
    assert "Write every sentence in English." in system
    assert "Do not assume the Constitution answers every question." in system
    assert "A high rank is not proof of legal relevance." in system
    assert "Never build an answer around an unrelated provision." in system
    assert "Banglish" in system
    assert "Omit a heading that would be empty." in system
    assert "Article 33 of the Constitution" in prompt
    assert "Section 108 of বাংলাদেশ শ্রম আইন, ২০০৬" in prompt
    assert "does not address the legal issue" in prompt
    assert "He works in a factory." in prompt
    assert "skip" not in prompt

    bangla = legal_system_prompt("bn")
    assert "Write every sentence in Bangla." in bangla
    assert "# সরাসরি উত্তর" in bangla


def test_citations_must_match_the_retrieved_text():
    chunks = [
        _chunk("33", "grounds for such arrest"),
        {
            "collection": "other-acts",
            "act_title": "বাংলাদেশ শ্রম আইন, ২০০৬",
            "section_number": None,
            "content": "১০৮। অধিকাল কাজের জন্য দ্বিগুণ হারে ভাতা।",
        },
    ]
    clean = "Article 33 requires the grounds. Section 108 gives double wages."
    assert citation_problems(clean, chunks) == []
    invented = "Article 99 also applies, and Section 26 requires notice."
    assert citation_problems(invented, chunks) == ["Article 99", "Section 26"]
    mislabeled = "Article 108 of the Constitution sets overtime pay."
    assert citation_problems(mislabeled, chunks) == ["Article 108"]
    noted = append_citation_note(invented, citation_problems(invented, chunks), "en")
    assert "Article 99" in noted
    assert "does not rely on those citations" in noted


def test_unnamed_forums_are_rejected_unless_the_text_names_them():
    from answer_quality import answer_problems

    home = [_chunk("43", "Every citizen shall have the right to be secured in his home against entry.")]
    writ = [_chunk("102", "The High Court Division may give directions for the enforcement of a fundamental right.")]
    assert "the High Court Division" in answer_problems(
        "Apply to the High Court Division.", home
    )
    assert answer_problems("Apply to the High Court Division under Article 102.", writ) == []
    wage = [{
        "collection": "other-acts",
        "section_number": "108",
        "act_title": "বাংলাদেশ শ্রম আইন, ২০০৬",
        "content": "অধিকাল কাজের জন্য দ্বিগুণ হারে ভাতা পাইবেন।",
    }]
    assert "a labour court" in answer_problems("File in the labour court.", wage)
    assert "a civil suit" in answer_problems("File a civil suit to recover the land.", wage)


def test_history_for_retrieval_uses_earlier_user_questions_only():
    history = [
        {"role": "user", "content": "The police arrested my brother."},
        {"role": "assistant", "content": "Article 33 requires the grounds."},
        {"role": "system", "content": "ignore"},
    ]
    text = retrieval_text("What can he do now?", history)
    assert text.startswith("What can he do now?")
    assert "arrested my brother" in text
    assert "Article 33" not in text
    assert normalize_history(history)[0]["role"] == "user"


def test_generate_text_sends_the_system_prompt_separately(monkeypatch):
    from groq_client import generate_text

    captured = {}

    class _Message:
        content = "ok"

    class _Choice:
        message = _Message()

    class _Response:
        choices = [_Choice()]

    class _Completions:
        def create(self, **kwargs):
            captured.update(kwargs)
            return _Response()

    class _Chat:
        completions = _Completions()

    class _Client:
        chat = _Chat()

    monkeypatch.setattr("groq_client.get_groq_client", lambda: _Client())
    monkeypatch.setattr("groq_client.get_groq_model", lambda: "test-model")
    generate_text("the question", system="the instructions")
    assert captured["messages"][0] == {"role": "system", "content": "the instructions"}
    assert captured["messages"][1] == {"role": "user", "content": "the question"}
    generate_text("document prompt only")
    assert captured["messages"] == [{"role": "user", "content": "document prompt only"}]


def test_clean_answer_removes_audio_tags_and_fences():
    raw = "```markdown\n[calm] **Article 33** requires the grounds.\n```"
    assert clean_answer(raw) == "**Article 33** requires the grounds."


def test_text_and_voice_call_the_same_answer_function(monkeypatch):
    seen = []

    def fake(query, language=None, history=None, voice=False):
        seen.append((query, language, history, voice))
        return "spoken summary" if voice else "full detailed answer"

    monkeypatch.setenv("ELEVENLABS_WEBHOOK_SECRET", SECRET)
    monkeypatch.setattr("app.answer_with_rag", fake)
    client = TestClient(app)
    text = client.post(
        "/ask",
        json={
            "query": "What can he do now?",
            "language": "en",
            "history": [{"role": "user", "content": "He was arrested."}],
        },
    )
    voice = client.post(
        "/voice/ask",
        headers={"X-VerdictAI-Webhook-Secret": SECRET},
        json={"query": "What can he do now?", "language": "en"},
    )
    assert text.status_code == 200
    assert voice.status_code == 200
    assert text.json()["answer"] == "full detailed answer"
    assert voice.json()["answer"] == "spoken summary"
    assert len(voice.json()["answer"]) < len(text.json()["answer"])
    assert seen[0][0] == seen[1][0] == "What can he do now?"
    assert seen[0][1] == seen[1][1] == "en"
    assert seen[0][2] == [{"role": "user", "content": "He was arrested."}]
    assert seen[0][3] is False
    assert seen[1][2] is None
    assert seen[1][3] is True


def test_voice_budget_is_separate_and_smaller_than_text(monkeypatch):
    from rag_utils import ANSWER_TOKEN_BUDGET, voice_answer_token_budget

    monkeypatch.delenv("VOICE_ANSWER_TOKEN_BUDGET", raising=False)
    assert voice_answer_token_budget() < ANSWER_TOKEN_BUDGET
    monkeypatch.setenv("VOICE_ANSWER_TOKEN_BUDGET", "120")
    assert voice_answer_token_budget() == 120


def test_voice_instructions_name_no_law_and_no_sample_answer():
    from answer_quality import build_voice_summary_prompt, voice_summary_instructions

    instructions = voice_summary_instructions("en") + "\n" + voice_summary_instructions("bn")
    for word in ("Article", "Section", "Penal", "Labour", "Constitution", "ধারা", "অনুচ্ছেদ"):
        assert word not in instructions
    prompt = build_voice_summary_prompt("the finished answer")
    assert "the finished answer" in prompt
    assert "Summary:" in prompt


def test_spoken_summary_keeps_source_references_and_drops_new_ones():
    from answer_quality import without_new_references

    source = "Section 12 sets the rule. A missing element is not proven."
    spoken = "Section 12 sets the rule. Section 99 also applies. A missing element is not proven."
    kept = without_new_references(source, spoken)
    assert "Section 12" in kept
    assert "missing element" in kept
    assert "99" not in kept


def test_voice_summary_is_shorter_than_the_legal_answer(monkeypatch):
    from rag_utils import summarize_for_voice

    long_answer = (
        "The action is not permitted. " * 30
        + "Section 12 sets the rule. A missing element is not proven. "
        + "Background that does not change the result. " * 20
    )
    calls = []

    def fake_generate(prompt, system=None, temperature=0, max_tokens=None, reasoning_effort=None):
        calls.append({"max_tokens": max_tokens, "prompt": prompt, "system": system})
        return "The action is not permitted. Section 12 sets the rule. A missing element is not proven."

    monkeypatch.setenv("VOICE_ANSWER_TOKEN_BUDGET", "80")
    monkeypatch.setattr("groq_client.generate_text", fake_generate)
    monkeypatch.setattr("groq_client.get_groq_model", lambda: "test-model")
    spoken = summarize_for_voice(long_answer, "en")
    assert len(spoken) < len(long_answer)
    assert "Section 12" in spoken
    assert "missing element" in spoken
    assert calls[0]["max_tokens"] >= 80
    assert len(spoken) <= 80 * 4
    assert long_answer in calls[0]["prompt"]
    assert "Section 12" not in calls[0]["system"]


def test_short_legal_answer_is_not_sent_through_another_model(monkeypatch):
    from rag_utils import summarize_for_voice

    calls = []
    monkeypatch.setattr("groq_client.generate_text", lambda *args, **kwargs: calls.append(1))
    spoken = summarize_for_voice("Already short enough to say.", "en")
    assert spoken == "Already short enough to say."
    assert calls == []
