from __future__ import annotations

from typing import List, Dict, Any
import re

from sklearn.feature_extraction.text import TfidfVectorizer

from retrival.expansion_config import (
    PRF_ENABLED,
    PRF_TOP_K_DOCS,
    PRF_TOP_N_TERMS,
    PRF_MIN_TERM_LEN,
)

EXTRA_STOPWORDS = [
    "el", "la", "los", "las", "un", "una", "unos", "unas",
    "y", "o", "pero", "sin", "sobre", "entre", "hasta",
    "de", "del", "a", "ante", "bajo", "cabe", "con", "contra",
    "para", "por", "segun", "se", "su", "sus", "tu", "tus",
]

def _extract_texts_from_results(results: List[Dict[str, Any]], top_k: int) -> List[str]:
    texts = []
    for r in results[:top_k]:
        text = r.get("text", "")
        if text and isinstance(text, str):
            texts.append(text)
    return texts

def _preprocess_text(text: str) -> str:
    text = re.sub(r'[^a-zA-ZáéíóúüñÁÉÍÓÚÜÑ\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.lower().strip()

def extract_keywords_tfidf(texts: List[str], top_n: int, min_term_len: int) -> List[str]:
    if not texts:
        return []
    processed = [_preprocess_text(t) for t in texts]
    vectorizer = TfidfVectorizer(
        stop_words=None,
        token_pattern=r"(?u)\b\w+\b",
        min_df=1,
        max_df=1.0,
    )
    try:
        tfidf = vectorizer.fit_transform(processed)
    except ValueError:
        return []
    feature_names = vectorizer.get_feature_names_out()
    term_weights = tfidf.sum(axis=0).A1
    sorted_idx = term_weights.argsort()[::-1]
    keywords = []
    for idx in sorted_idx:
        term = feature_names[idx]
        if len(term) >= min_term_len and term not in EXTRA_STOPWORDS:
            keywords.append(term)
            if len(keywords) >= top_n:
                break
    return keywords

def apply_pseudo_relevance_feedback(query: str, initial_results: List[Dict[str, Any]]) -> str:
    if not PRF_ENABLED:
        return query
    if not initial_results:
        return query

    texts = _extract_texts_from_results(initial_results, PRF_TOP_K_DOCS)
    if not texts:
        return query

    keywords = extract_keywords_tfidf(texts, PRF_TOP_N_TERMS, PRF_MIN_TERM_LEN)
    if not keywords:
        return query

    return (query + " " + " ".join(keywords)).strip()
