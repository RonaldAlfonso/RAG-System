import re
from typing import Optional

# alias (minúsculas) → valor canónico guardado en metadata.pais
_ALIASES: dict[str, str] = {
    # Argentina
    "argentina":                    "Argentina",
    "argentino":                    "Argentina",
    "argentina":                    "Argentina",
    # Bolivia
    "bolivia":                      "Bolivia",
    "boliviano":                    "Bolivia",
    # Brasil
    "brasil":                       "Brasil",
    "brazil":                       "Brasil",
    "brasileño":                    "Brasil",
    "brasileira":                   "Brasil",
    # Chile
    "chile":                        "Chile",
    "chileno":                      "Chile",
    # Colombia
    "colombia":                     "Colombia",
    "colombiano":                   "Colombia",
    # Costa Rica
    "costa rica":                   "Costa Rica",
    "costarricense":                "Costa Rica",
    # Cuba
    "cuba":                         "Cuba",
    "cubano":                       "Cuba",
    # Ecuador
    "ecuador":                      "Ecuador",
    "ecuatoriano":                  "Ecuador",
    # El Salvador
    "el salvador":                  "El Salvador",
    "salvadoreño":                  "El Salvador",
    # Guatemala
    "guatemala":                    "Guatemala",
    "guatemalteco":                 "Guatemala",
    # Honduras
    "honduras":                     "Honduras",
    "hondureño":                    "Honduras",
    # Mexico
    "mexico":                       "Mexico",
    "méxico":                       "Mexico",
    "mexicano":                     "Mexico",
    # Nicaragua
    "nicaragua":                    "Nicaragua",
    "nicaragüense":                 "Nicaragua",
    "nicaraguense":                 "Nicaragua",
    # Panama
    "panama":                       "Panama",
    "panamá":                       "Panama",
    "panameño":                     "Panama",
    # Paraguay
    "paraguay":                     "Paraguay",
    "paraguayo":                    "Paraguay",
    # Peru
    "peru":                         "Peru",
    "perú":                         "Peru",
    "peruano":                      "Peru",
    # Republica Dominicana
    "república dominicana":         "Republica Dominicana",
    "republica dominicana":         "Republica Dominicana",
    "santo domingo":                "Republica Dominicana",
    "dominicano":                   "Republica Dominicana",
    # Uruguay
    "uruguay":                      "Uruguay",
    "uruguayo":                     "Uruguay",
    # Venezuela
    "venezuela":                    "Venezuela",
    "venezolano":                   "Venezuela",
    # Jamaica
    "jamaica":                      "Jamaica",
    "jamaicano":                    "Jamaica",
    "jamaiquino":                   "Jamaica",
    # Trinidad y Tobago
    "trinidad y tobago":            "Trinidad y Tobago",
    "trinidad":                     "Trinidad y Tobago",
    "tobago":                       "Trinidad y Tobago",
    # Haiti
    "haiti":                        "Haiti",
    "haití":                        "Haiti",
    "haitiano":                     "Haiti",
    # Puerto Rico
    "puerto rico":                  "Puerto Rico",
    "puertorriqueño":               "Puerto Rico",
    "boriken":                      "Puerto Rico",
    # Belize
    "belize":                       "Belize",
    "belice":                       "Belize",
    "beliceño":                     "Belize",
    # Guyana
    "guyana":                       "Guyana",
    "guyanés":                      "Guyana",
    "guayana":                      "Guyana",
    # Guyana Francesa
    "guyana francesa":              "Guyana Francesa",
    "guayana francesa":             "Guyana Francesa",
    "cayena":                       "Guyana Francesa",
    # Surinam
    "surinam":                      "Surinam",
    "suriname":                     "Surinam",
    "surinamés":                    "Surinam",
    # Barbados
    "barbados":                     "Barbados",
    "barbadense":                   "Barbados",
    # Bahamas
    "bahamas":                      "Bahamas",
    "las bahamas":                  "Bahamas",
    "bahameño":                     "Bahamas",
    # Aruba
    "aruba":                        "Aruba",
    "arubeño":                      "Aruba",
    # Curazao
    "curazao":                      "Curazao",
    "curaçao":                      "Curazao",
    "curacao":                      "Curazao",
    # Antigua y Barbuda
    "antigua y barbuda":            "Antigua y Barbuda",
    "antigua":                      "Antigua y Barbuda",
    # Santa Lucia
    "santa lucía":                  "Santa Lucia",
    "santa lucia":                  "Santa Lucia",
    # San Vicente y las Granadinas
    "san vicente y las granadinas": "San Vicente y las Granadinas",
    "san vicente":                  "San Vicente y las Granadinas",
    "granadinas":                   "San Vicente y las Granadinas",
    # Granada
    "granada":                      "Granada",
    "granadino":                    "Granada",
    # Dominica
    "dominica":                     "Dominica",
    "dominiqués":                   "Dominica",
    # San Cristobal y Nieves
    "san cristóbal y nieves":       "San Cristobal y Nieves",
    "san cristobal y nieves":       "San Cristobal y Nieves",
    "saint kitts":                  "San Cristobal y Nieves",
    # Islas Caimán
    "islas caimán":                 "Islas Caiman",
    "islas caiman":                 "Islas Caiman",
    "gran caimán":                  "Islas Caiman",
    "cayman":                       "Islas Caiman",
    # Islas Vírgenes
    "islas vírgenes":               "Islas Virgenes",
    "islas virgenes":               "Islas Virgenes",
    # Martinica
    "martinica":                    "Martinica",
    "martinique":                   "Martinica",
    # Guadalupe
    "guadalupe":                    "Guadalupe",
    "guadeloupe":                   "Guadalupe",
    # Turcos y Caicos
    "turcos y caicos":              "Turcos y Caicos",
    "turks and caicos":             "Turcos y Caicos",
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
