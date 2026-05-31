from __future__ import annotations

import sys
import types

# Compatibility: in containers /app/services is used; locally we often insert 'services'
# in sys.path before importing this module.
if "/app/services" not in sys.path:
    sys.path.insert(0, "/app/services")


def _mk_context(n: int) -> str:
    return "x" * n


def test_policy_is_insufficient() -> None:
    from retrival.fallback_policy import (
        WEB_FALLBACK_CONTEXT_MIN_CHARS,
        WEB_FALLBACK_SCORE_THRESHOLD,
        is_insufficient,
    )

    # 1) results vacíos → True
    assert is_insufficient([], _mk_context(WEB_FALLBACK_CONTEXT_MIN_CHARS + 10)) is True

    # 2) score bajo → True
    low = WEB_FALLBACK_SCORE_THRESHOLD - 0.01
    assert (
        is_insufficient([
            {"score": low, "text": "a", "metadata": {}},
        ], _mk_context(WEB_FALLBACK_CONTEXT_MIN_CHARS + 10))
        is True
    )

    # 3) contexto corto → True
    high = WEB_FALLBACK_SCORE_THRESHOLD + 0.5
    assert (
        is_insufficient([
            {"score": high, "text": "a", "metadata": {}},
        ], _mk_context(WEB_FALLBACK_CONTEXT_MIN_CHARS - 1))
        is True
    )

    # 4) resultados buenos + contexto largo → False
    assert (
        is_insufficient([
            {"score": high, "text": "a", "metadata": {}},
        ], _mk_context(WEB_FALLBACK_CONTEXT_MIN_CHARS + 10))
        is False
    )


def test_wikivoyage_parser_offline() -> None:
    from retrival.web_fallback_wikivoyage import _build_search_url, _extract_result_urls

    url = _build_search_url("Cusco Perú")
    assert url.startswith("https://es.wikivoyage.org/w/index.php?search=")
    assert "title=Special:Search" in url
    assert "fulltext=1" in url
    assert "Cusco" in url

    html = """
    <html><body>
      <a href="/wiki/Cusco">Cusco</a>
      <a href="/wiki/Special:Search">Special:Search</a>
      <a href="/wiki/Lima#History">Lima</a>
      <a href="/wiki/Lima">Lima</a>
      <a href="/w/index.php?search=Cusco">not-a-wiki-link</a>
    </body></html>
    """
    urls = _extract_result_urls(html, max_pages=10)
    assert "https://es.wikivoyage.org/wiki/Cusco" in urls
    assert "https://es.wikivoyage.org/wiki/Lima" in urls
    assert all("Special:Search" not in u for u in urls)


def test_web_ingest_offline() -> None:
    from retrival import web_ingest

    calls: list[int] = []

    def fake_index_chunks_batch(chunks):
        calls.append(len(chunks))
        return len(chunks)

    fake_indexer = types.ModuleType("processor.indexer")
    fake_indexer.BATCH_SIZE = 2
    fake_indexer.index_chunks_batch = fake_index_chunks_batch
    sys.modules["processor.indexer"] = fake_indexer

    docs = [
        {
            "text": "p1\n" + ("a" * 50) + "\n" + ("b" * 60) + "\n",
            "metadata": {"title": "T", "url": "U", "source": "wikivoyage"},
        }
    ]

    out = web_ingest.ingest_web_documents(docs)
    assert out["docs_received"] == 1
    assert out["chunks_indexed"] > 0
    assert sum(calls) == out["chunks_indexed"]


def test_retrieve_with_fallback_offline() -> None:
    calls = {"hybrid": 0, "fetch": 0, "ingest": 0}

    def fake_hybrid_search(query, top_k=5, filters=None):
        calls["hybrid"] += 1
        if calls["hybrid"] == 1:
            return []
        return [{"score": 1.0, "text": "ok", "metadata": {}}]

    def fake_format_context(results):
        return "ctx" if results else ""

    def fake_is_insufficient(results, context):
        return True

    def fake_fetch(query, max_pages, timeout_seconds):
        calls["fetch"] += 1
        return [
            {
                "text": "texto web",
                "metadata": {"title": "T", "url": "U", "source": "wikivoyage"},
            }
        ]

    def fake_ingest(docs):
        calls["ingest"] += 1
        return {"docs_received": len(docs), "chunks_indexed": 2}

    # Inject fake modules BEFORE importing retrieve_with_fallback
    fake_retriever = types.ModuleType("retrival.retriever")
    fake_retriever.hybrid_search = fake_hybrid_search
    fake_retriever.format_context = fake_format_context
    sys.modules["retrival.retriever"] = fake_retriever

    fake_fallback_policy = types.ModuleType("retrival.fallback_policy")
    fake_fallback_policy.WEB_FALLBACK_ENABLED = True
    fake_fallback_policy.WEB_FALLBACK_MAX_PAGES = 3
    fake_fallback_policy.WEB_FALLBACK_TIMEOUT_SECONDS = 20
    fake_fallback_policy.is_insufficient = fake_is_insufficient
    sys.modules["retrival.fallback_policy"] = fake_fallback_policy

    fake_fetcher = types.ModuleType("retrival.web_fallback_wikivoyage")
    fake_fetcher.fetch_wikivoyage_pages = fake_fetch
    sys.modules["retrival.web_fallback_wikivoyage"] = fake_fetcher

    fake_ingest_mod = types.ModuleType("retrival.web_ingest")
    fake_ingest_mod.ingest_web_documents = fake_ingest
    sys.modules["retrival.web_ingest"] = fake_ingest_mod

    from retrival import retrieve_with_fallback

    out = retrieve_with_fallback.retrieve_context_with_fallback("q", top_k=5, filters=None)

    assert out["web_fallback_attempted"] is True
    assert out["web_fallback_used"] is True
    assert out["web_docs_received"] == 1
    assert out["web_chunks_indexed"] == 2
    assert isinstance(out["web_pages"], list) and out["web_pages"][0]["source"] == "wikivoyage"

    assert calls["hybrid"] == 2
    assert calls["fetch"] == 1
    assert calls["ingest"] == 1


def run_all() -> None:
    tests = [
        ("fallback_policy", test_policy_is_insufficient),
        ("wikivoyage_parser", test_wikivoyage_parser_offline),
        ("web_ingest", test_web_ingest_offline),
        ("retrieve_with_fallback", test_retrieve_with_fallback_offline),
    ]

    for name, fn in tests:
        fn()
        print(f"OK - {name}")


if __name__ == "__main__":
    run_all()
