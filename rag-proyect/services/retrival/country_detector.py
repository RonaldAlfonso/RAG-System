import re
from typing import Optional

# alias (minúsculas) → valor canónico guardado en metadata.pais
_ALIASES: dict[str, str] = {
    # Argentina
    "argentina":            "Argentina",
    "argentino":            "Argentina",
    "argentina":            "Argentina",
    # Bolivia
    "bolivia":              "Bolivia",
    "boliviano":            "Bolivia",
    # brasil
    "brasil":               "Brasil",
    "brazil":               "Brasil",
    "brasileño":            "Brasil",
    # chile
    "chile":                "Chile",
    "chileno":              "Chile",
    # colombia
    "colombia":             "Colombia",
    "colombiano":           "Colombia",
    # costa rica
    "costa rica":           "Costa Rica",
    "costarricense":        "Costa Rica",
    # cuba
    "cuba":                 "Cuba",
    "cubano":               "Cuba",
    # ecuador
    "ecuador":              "Ecuador",
    "ecuatoriano":          "Ecuador",
    # el salvador
    "el salvador":          "El Salvador",
    "salvadoreño":          "El Salvador",
    # guatemala
    "guatemala":            "Guatemala",
    "guatemalteco":         "Guatemala",
    # honduras
    "honduras":             "Honduras",
    "hondureño":            "Honduras",
    # mexico
    "mexico":               "Mexico",
    "méxico":               "Mexico",
    "mexicano":             "Mexico",
    # nicaragua
    "nicaragua":            "Nicaragua",
    "nicaragüense":         "Nicaragua",
    # panama
    "panama":               "Panama",
    "panamá":               "Panama",
    "panameño":             "Panama",
    # paraguay
    "paraguay":             "Paraguay",
    "paraguayo":            "Paraguay",
    # peru
    "peru":                 "Peru",
    "perú":                 "Peru",
    "peruano":              "Peru",
    # republica dominicana
    "república dominicana": "Republica Dominicana",
    "republica dominicana": "Republica Dominicana",
    "dominicano":           "Republica Dominicana",
    # uruguay
    "uruguay":              "Uruguay",
    "uruguayo":             "Uruguay",
    # venezuela
    "venezuela":            "Venezuela",
    "venezolano":           "Venezuela",
}

# ordena por longitud descendente para que "costa rica" se pruebe antes que "rica"
_SORTED_ALIASES = sorted(_ALIASES.keys(), key=len, reverse=True)


def detect_country(query: str) -> Optional[str]:
    """Retorna el nombre canónico del país si aparece en la query, o None."""
    normalized = query.lower()
    # elimina acentos comunes para comparación robusta
    normalized = (normalized
                  .replace("á", "a").replace("é", "e")
                  .replace("í", "i").replace("ó", "o")
                  .replace("ú", "u").replace("ü", "u")
                  .replace("ñ", "n"))

    for alias in _SORTED_ALIASES:
        alias_norm = (alias
                      .replace("á", "a").replace("é", "e")
                      .replace("í", "i").replace("ó", "o")
                      .replace("ú", "u").replace("ü", "u")
                      .replace("ñ", "n"))
        # busca la palabra completa (no substrings)
        if re.search(rf"\b{re.escape(alias_norm)}\b", normalized):
            return _ALIASES[alias]

    return None
