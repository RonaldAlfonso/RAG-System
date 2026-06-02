#!/usr/bin/env python3
"""
Descarga el dump XML de Wikivoyage en español, extrae artículos de LATAM
y el Caribe, y los indexa en la KB principal (índice 'documents').

Ejecutar dentro del contenedor processor:
    docker exec -it processor_rag python scripts/wikivoyage_dump_ingest.py
"""

import sys
import bz2
import logging
import re
import urllib.request
from pathlib import Path
from xml.etree import ElementTree as ET
from typing import Iterator, Optional

sys.path.insert(0, "/app/services")

from processor.chunker import chunk_documents
from processor.indexer import index_chunks_batch
from processor.vector_store import create_index

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ── Configuración ──────────────────────────────────────────────────────────────

DUMP_URL  = "https://dumps.wikimedia.org/eswikivoyage/latest/eswikivoyage-latest-pages-articles.xml.bz2"
DUMP_PATH = Path("/tmp/eswikivoyage-latest.xml.bz2")
BASE_URL  = "https://es.wikivoyage.org/wiki/"

BATCH_SIZE = 40

# ── Países LATAM + Caribe ─────────────────────────────────────────────────────

LATAM_COUNTRIES: dict[str, str] = {
    "México":                       "Mexico",
    "Mexico":                       "Mexico",
    "Guatemala":                    "Guatemala",
    "Belice":                       "Belice",
    "Honduras":                     "Honduras",
    "El Salvador":                  "El Salvador",
    "Nicaragua":                    "Nicaragua",
    "Costa Rica":                   "Costa Rica",
    "Panamá":                       "Panama",
    "Panama":                       "Panama",
    "Cuba":                         "Cuba",
    "República Dominicana":         "Republica Dominicana",
    "Haití":                        "Haiti",
    "Haiti":                        "Haiti",
    "Puerto Rico":                  "Puerto Rico",
    "Jamaica":                      "Jamaica",
    "Trinidad y Tobago":            "Trinidad y Tobago",
    "Barbados":                     "Barbados",
    "Bahamas":                      "Bahamas",
    "Antigua y Barbuda":            "Antigua y Barbuda",
    "San Cristóbal y Nieves":       "San Cristobal y Nieves",
    "Santa Lucía":                  "Santa Lucia",
    "San Vicente y las Granadinas": "San Vicente y las Granadinas",
    "Granada":                      "Granada",
    "Dominica":                     "Dominica",
    "Martinica":                    "Martinica",
    "Guadalupe":                    "Guadalupe",
    "Aruba":                        "Aruba",
    "Curazao":                      "Curacao",
    "Curaçao":                      "Curacao",
    "Colombia":                     "Colombia",
    "Venezuela":                    "Venezuela",
    "Ecuador":                      "Ecuador",
    "Perú":                         "Peru",
    "Peru":                         "Peru",
    "Bolivia":                      "Bolivia",
    "Chile":                        "Chile",
    "Argentina":                    "Argentina",
    "Uruguay":                      "Uruguay",
    "Paraguay":                     "Paraguay",
    "Brasil":                       "Brasil",
    "Brazil":                       "Brasil",
    "Guyana":                       "Guyana",
    "Surinam":                      "Surinam",
    "Suriname":                     "Surinam",
    "Guayana Francesa":             "Guayana Francesa",
}

# Palabras clave de regiones LATAM (para categorías y títulos)
_REGION_KEYWORDS = {
    kw.lower() for kw in [
        "Caribe", "América Central", "Centroamérica",
        "América del Sur", "Sudamérica", "América Latina", "Latinoamérica",
        "Antillas", "Indias Occidentales", "Centroamérica y el Caribe",
    ]
}

# Países en minúsculas para búsqueda rápida
_COUNTRY_LOWER: dict[str, str] = {k.lower(): v for k, v in LATAM_COUNTRIES.items()}

# ── Patrones de texto para detectar país en los primeros párrafos ─────────────
# Cada tupla: (regex compilado, código_pais)
# Se busca en los primeros TEXT_SCAN_CHARS del wikitext crudo.
TEXT_SCAN_CHARS = 1200

_TEXT_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r'\bMéxico\b|\bMexico\b'),            "Mexico"),
    (re.compile(r'\bGuatemala\b'),                     "Guatemala"),
    (re.compile(r'\bBelice\b'),                        "Belice"),
    (re.compile(r'\bHonduras\b'),                      "Honduras"),
    (re.compile(r'\bEl Salvador\b'),                   "El Salvador"),
    (re.compile(r'\bNicaragua\b'),                     "Nicaragua"),
    (re.compile(r'\bCosta Rica\b'),                    "Costa Rica"),
    (re.compile(r'\bPanamá\b|\bPanama\b'),             "Panama"),
    (re.compile(r'\bCuba\b'),                          "Cuba"),
    (re.compile(r'\bRepública Dominicana\b'),          "Republica Dominicana"),
    (re.compile(r'\bHaití\b|\bHaiti\b'),               "Haiti"),
    (re.compile(r'\bPuerto Rico\b'),                   "Puerto Rico"),
    (re.compile(r'\bJamaica\b'),                       "Jamaica"),
    (re.compile(r'\bTrinidad y Tobago\b'),             "Trinidad y Tobago"),
    (re.compile(r'\bBarbados\b'),                      "Barbados"),
    (re.compile(r'\bBahamas\b'),                       "Bahamas"),
    (re.compile(r'\bAruba\b'),                         "Aruba"),
    (re.compile(r'\bCurazao\b|\bCuraçao\b'),           "Curacao"),
    (re.compile(r'\bColombia\b'),                      "Colombia"),
    (re.compile(r'\bVenezuela\b'),                     "Venezuela"),
    (re.compile(r'\bEcuador\b'),                       "Ecuador"),
    (re.compile(r'\bPerú\b|\bPeru\b'),                 "Peru"),
    (re.compile(r'\bBolivia\b'),                       "Bolivia"),
    (re.compile(r'\bChile\b'),                         "Chile"),
    (re.compile(r'\bArgentina\b'),                     "Argentina"),
    (re.compile(r'\bUruguay\b'),                       "Uruguay"),
    (re.compile(r'\bParaguay\b'),                      "Paraguay"),
    (re.compile(r'\bBrasil\b|\bBrazil\b'),             "Brasil"),
    (re.compile(r'\bGuyana\b'),                        "Guyana"),
    (re.compile(r'\bSurinam\b|\bSuriname\b'),          "Surinam"),
    (re.compile(r'\bGuayana Francesa\b'),              "Guayana Francesa"),
    (re.compile(r'\bCaribe\b|\bCaribeño\b', re.I),    "Caribe"),
    (re.compile(r'\bAmérica Central\b|Centroamérica\b', re.I), "America Central"),
    (re.compile(r'\bAmérica del Sur\b|Sudamérica\b',  re.I),   "America del Sur"),
]

# Artículos claramente fuera de LATAM — se excluyen aunque mencionen un país LATAM
# (por ejemplo: "Berlín" podría mencionar "Argentina" de pasada)
_BLOCKLIST_CATS = {
    "europa", "españa", "alemania", "francia", "italia", "portugal",
    "reino unido", "asia", "japón", "china", "india", "africa", "áfrica",
    "oceanía", "australia", "oriente medio", "estados unidos", "canadá",
    "dinamarca", "noruega", "suecia", "finlandia", "países bajos",
    "bélgica", "austria", "suiza", "grecia", "turquía", "rusia",
    "polonia", "hungría", "república checa", "eslovaquia", "rumanía",
    "bulgaria", "croacia", "serbia", "eslovenia",
    "marruecos", "egipto", "kenia", "sudáfrica", "etiopía", "tanzania",
    "tailandia", "vietnam", "indonesia", "filipinas", "malasia",
    "singapur", "corea del sur", "corea del norte",
    "new zealand", "nueva zelanda",
    "canarias", "mallorca", "ibiza",  # España
}

# ── Limpieza de wikitext ───────────────────────────────────────────────────────

_RE_TEMPLATE    = re.compile(r"\{\{[^{}]*?\}\}", re.DOTALL)
_RE_FILE        = re.compile(r"\[\[(?:Archivo|File|Image|Imagen):[^\]]*?\]\]", re.I)
_RE_WIKILINK    = re.compile(r"\[\[(?:[^|\]]*\|)?([^\]]+)\]\]")
_RE_EXTLINK     = re.compile(r"\[https?://\S+\s+([^\]]+)\]")
_RE_HTML        = re.compile(r"<[^>]+>")
_RE_HEADING     = re.compile(r"^={1,6}\s*(.+?)\s*={1,6}$", re.MULTILINE)
_RE_BULLET      = re.compile(r"^[*#:;]+\s*", re.MULTILINE)
_RE_MULTIBLANKS = re.compile(r"\n{3,}")


def wikitext_to_plain(wikitext: str) -> str:
    text = wikitext
    prev = None
    while prev != text:
        prev = text
        text = _RE_TEMPLATE.sub(" ", text)
    text = _RE_FILE.sub("", text)
    text = _RE_WIKILINK.sub(r"\1", text)
    text = _RE_EXTLINK.sub(r"\1", text)
    text = _RE_HTML.sub(" ", text)
    text = _RE_HEADING.sub(r"\n\1\n", text)
    text = _RE_BULLET.sub("", text)
    text = _RE_MULTIBLANKS.sub("\n\n", text)
    return text.strip()


# ── Parsing del dump XML en streaming ─────────────────────────────────────────

_RE_CATEGORY = re.compile(r"\[\[Categor[íi]a:([^\]|]+)", re.I)


def _get_categories(wikitext: str) -> list[str]:
    return [m.group(1).strip() for m in _RE_CATEGORY.finditer(wikitext)]


def iter_pages(dump_path: Path) -> Iterator[tuple[str, str]]:
    """Itera (título, wikitext) para artículos en namespace 0 sin redirects."""
    with bz2.open(dump_path, "rb") as fh:
        ns_prefix = ""
        context = ET.iterparse(fh, events=("start", "end"))
        for event, elem in context:
            if event == "start" and not ns_prefix and elem.tag.startswith("{"):
                ns_prefix = elem.tag.split("}")[0] + "}"
                continue
            if event != "end":
                continue
            local = elem.tag.replace(ns_prefix, "")
            if local != "page":
                continue
            ns_tag    = elem.find(f"{ns_prefix}ns")
            title_tag = elem.find(f"{ns_prefix}title")
            rev       = elem.find(f"{ns_prefix}revision")
            text_tag  = rev.find(f"{ns_prefix}text") if rev is not None else None
            ns_val = ns_tag.text if ns_tag is not None else "-1"
            title  = title_tag.text if title_tag is not None else ""
            text   = text_tag.text  if text_tag  is not None else ""
            elem.clear()
            if ns_val != "0":
                continue
            if not text or text.strip().upper().startswith("#REDIRECT"):
                continue
            yield title, text


# ── Detección de país LATAM ────────────────────────────────────────────────────

def detect_pais(title: str, categories: list[str], wikitext: str) -> Optional[str]:
    """
    Devuelve el código de país si el artículo pertenece a LATAM/Caribe.
    Usa tres niveles: título → categorías → primeros párrafos del texto.
    """
    # 0. Excluir artículos claramente no-LATAM por sus categorías
    cats_lower = [c.lower() for c in categories]
    for cat_low in cats_lower:
        for blocked in _BLOCKLIST_CATS:
            if blocked in cat_low:
                return None

    # 1. Título es exactamente un país LATAM
    if title in LATAM_COUNTRIES:
        return LATAM_COUNTRIES[title]

    # 2. Categorías contienen el nombre de un país LATAM
    for cat_low in cats_lower:
        for country_low, country_code in _COUNTRY_LOWER.items():
            if country_low in cat_low:
                return country_code

    # 3. Título o categorías contienen una región LATAM genérica
    title_low = title.lower()
    for kw in _REGION_KEYWORDS:
        if kw in title_low:
            return kw.capitalize()
    for cat_low in cats_lower:
        for kw in _REGION_KEYWORDS:
            if kw in cat_low:
                return kw.capitalize()

    # 4. Escanear los primeros párrafos del wikitext en busca del país
    #    (Wikivoyage siempre nombra el país en la intro del artículo)
    excerpt = wikitext[:TEXT_SCAN_CHARS]
    for pattern, country_code in _TEXT_PATTERNS:
        if pattern.search(excerpt):
            return country_code

    return None


# ── Descarga ───────────────────────────────────────────────────────────────────

def download_dump() -> None:
    if DUMP_PATH.exists():
        size_mb = DUMP_PATH.stat().st_size / 1e6
        log.info("Dump ya existe en %s (%.1f MB), omitiendo descarga.", DUMP_PATH, size_mb)
        return
    log.info("Descargando dump de Wikivoyage ES desde %s …", DUMP_URL)

    def _progress(block_num: int, block_size: int, total_size: int) -> None:
        if block_num % 200 == 0:
            downloaded = block_num * block_size
            if total_size > 0:
                pct = min(downloaded / total_size * 100, 100)
                log.info("  %.1f%% (%.1f MB / %.1f MB)", pct, downloaded / 1e6, total_size / 1e6)

    urllib.request.urlretrieve(DUMP_URL, DUMP_PATH, reporthook=_progress)
    log.info("Descarga completa: %s (%.1f MB)", DUMP_PATH, DUMP_PATH.stat().st_size / 1e6)


# ── Pipeline principal ─────────────────────────────────────────────────────────

def process_dump() -> None:
    create_index("documents")

    total_articles = 0
    total_chunks   = 0
    skipped        = 0
    batch_chunks:  list[dict] = []

    def flush() -> None:
        nonlocal total_chunks
        if not batch_chunks:
            return
        ok = index_chunks_batch(batch_chunks, index_name="documents")
        total_chunks += len(batch_chunks)
        status = "OK" if ok else "ERROR"
        log.info("  [%s] %d chunks (acum. artículos=%d, chunks=%d)",
                 status, len(batch_chunks), total_articles, total_chunks)
        batch_chunks.clear()

    log.info("Procesando dump…")
    for title, wikitext in iter_pages(DUMP_PATH):
        categories = _get_categories(wikitext)
        pais = detect_pais(title, categories, wikitext)

        if pais is None:
            skipped += 1
            continue

        plain = wikitext_to_plain(wikitext)
        if len(plain) < 150:
            skipped += 1
            continue

        url = BASE_URL + title.replace(" ", "_")
        doc = {
            "text": plain,
            "metadata": {
                "title":    title,
                "url":      url,
                "pais":     pais,
                "categoria": "turismo",
                "fuente":   "wikivoyage-es",
            },
        }

        doc_chunks = chunk_documents(doc)
        batch_chunks.extend(doc_chunks)
        total_articles += 1

        if total_articles % 50 == 0:
            log.info("Artículos LATAM: %d (descartados: %d)", total_articles, skipped)

        if len(batch_chunks) >= BATCH_SIZE:
            flush()

    flush()

    log.info("=" * 60)
    log.info("RESUMEN FINAL")
    log.info("  Artículos LATAM/Caribe indexados : %d", total_articles)
    log.info("  Chunks indexados                 : %d", total_chunks)
    log.info("  Artículos descartados            : %d", skipped)
    log.info("=" * 60)


if __name__ == "__main__":
    download_dump()
    process_dump()
