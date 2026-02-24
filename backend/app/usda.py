"""USDA FoodData Central lookup for ingredient density data.

This module resolves ingredient aliases (deterministic + curated + optional LLM),
searches USDA, scores candidate foods deterministically, and only accepts
confident matches with usable measures. If USDA has no confident match, an
optional LLM density fallback can provide grams_per_cup with confidence gating.
"""

from __future__ import annotations

import csv
import json
import logging
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

FDC_SEARCH_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"

OPENAI_API_KEY_ENV = "OPENAI_API_KEY"
OPENAI_API_BASE_ENV = "RETREAT_OPS_OPENAI_API_BASE"
USDA_ALIAS_MODEL_ENV = "RETREAT_OPS_USDA_ALIAS_MODEL"
USDA_LLM_DENSITY_FALLBACK_ENV = "RETREAT_OPS_USDA_LLM_DENSITY_FALLBACK"
DEFAULT_OPENAI_API_BASE = "https://api.openai.com/v1"
DEFAULT_USDA_ALIAS_MODEL = "gpt-5-mini"

CURATED_ALIAS_PATH = Path(__file__).resolve().parents[1] / "seeds" / "ingredient_aliases.csv"

# Measures we care about — maps USDA abbreviations/names to our canonical units.
MEASURE_MAP: dict[str, str] = {
    "cup": "cup",
    "cups": "cup",
    "tbsp": "tbsp",
    "tablespoon": "tbsp",
    "tsp": "tsp",
    "teaspoon": "tsp",
    "oz": "oz",
    "ounce": "oz",
}

# Volume measures that can be used to derive grams_per_cup.
VOLUME_TO_CUP: dict[str, float] = {
    "cup": 1.0,
    "tbsp": 1 / 16,
    "tsp": 1 / 48,
}

SOURCE_WEIGHTS: dict[str, float] = {
    "input": 1.0,
    "stored": 1.06,
    "curated": 1.04,
    "deterministic": 0.98,
    "llm": 0.94,
}

MIN_MATCH_SCORE = 0.63
MIN_TOKEN_RECALL = 0.34
MIN_LLM_DENSITY_CONFIDENCE = 0.75
MAX_ALIAS_CANDIDATES = 28
MAX_LLM_ALIASES = 8

TOKEN_SPLIT_RE = re.compile(r"[^a-z0-9]+")
PARENS_RE = re.compile(r"\([^)]*\)")

DETERMINISTIC_REPLACEMENTS: dict[str, str] = {
    "mung": "moong",
    "moong": "mung",
    "urad": "black gram",
    "methi": "fenugreek",
    "hing": "asafoetida",
    "poha": "flattened rice",
    "jeera": "cumin",
    "kalonji": "nigella",
}

MATCH_STOPWORDS = {
    "and",
    "or",
    "fresh",
    "dry",
    "dried",
    "powder",
    "whole",
    "split",
    "raw",
}

_CURATED_ALIAS_CACHE: dict[str, list[str]] | None = None


@dataclass
class FoodMeasure:
    """A single USDA food measure entry."""

    unit: str
    gram_weight: float
    label: str


@dataclass
class FoodMatch:
    """A scored USDA food candidate."""

    query: str
    source: str
    description: str
    score: float
    token_recall: float
    measures: list[FoodMeasure]


def _api_key() -> str:
    return os.environ.get("USDA_API_KEY", "DEMO_KEY")


def read_project_env_value(key: str) -> str:
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.exists():
        return ""
    prefix = f"{key}="
    try:
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or not line.startswith(prefix):
                continue
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    except Exception:
        return ""
    return ""


def resolve_openai_api_base() -> str:
    configured = str(os.getenv(OPENAI_API_BASE_ENV, DEFAULT_OPENAI_API_BASE) or "").strip()
    if not configured:
        return DEFAULT_OPENAI_API_BASE
    return configured.rstrip("/")


def resolve_openai_api_key() -> str:
    api_key = str(os.getenv(OPENAI_API_KEY_ENV, "") or "").strip()
    if api_key:
        return api_key
    return read_project_env_value(OPENAI_API_KEY_ENV)


def resolve_alias_model() -> str:
    configured = str(os.getenv(USDA_ALIAS_MODEL_ENV, "") or "").strip()
    if configured:
        return configured
    configured = read_project_env_value(USDA_ALIAS_MODEL_ENV)
    if configured:
        return configured
    return DEFAULT_USDA_ALIAS_MODEL


def llm_density_fallback_enabled() -> bool:
    raw = str(os.getenv(USDA_LLM_DENSITY_FALLBACK_ENV, "") or "").strip().lower()
    if not raw:
        raw = str(read_project_env_value(USDA_LLM_DENSITY_FALLBACK_ENV) or "").strip().lower()
    if not raw:
        return True
    return raw not in {"0", "false", "off", "no"}


def parse_confidence(value: object, default: float = 0.0) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = default
    if parsed < 0:
        return 0.0
    if parsed > 1:
        return 1.0
    return parsed


def normalize_phrase(value: str) -> str:
    normalized = " ".join(str(value or "").strip().split()).lower()
    return normalized


def tokenize_for_match(value: str) -> set[str]:
    tokens = [tok for tok in TOKEN_SPLIT_RE.split(normalize_phrase(value)) if tok]
    return {tok for tok in tokens if tok not in MATCH_STOPWORDS}


def dedupe_keep_order(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = normalize_phrase(value)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(" ".join(value.strip().split()))
    return result


def load_curated_alias_map() -> dict[str, list[str]]:
    global _CURATED_ALIAS_CACHE
    if _CURATED_ALIAS_CACHE is not None:
        return _CURATED_ALIAS_CACHE

    alias_map: dict[str, list[str]] = {}
    if not CURATED_ALIAS_PATH.exists():
        _CURATED_ALIAS_CACHE = alias_map
        return alias_map

    try:
        with CURATED_ALIAS_PATH.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                ingredient = normalize_phrase(str(row.get("ingredient_name") or ""))
                alias = " ".join(str(row.get("alias_name") or "").strip().split())
                if not ingredient or not alias:
                    continue
                alias_map.setdefault(ingredient, []).append(alias)
    except Exception as exc:
        logger.warning("Could not load curated alias map from %s: %s", CURATED_ALIAS_PATH, exc)
        alias_map = {}

    _CURATED_ALIAS_CACHE = {
        ingredient: dedupe_keep_order(aliases)
        for ingredient, aliases in alias_map.items()
    }
    return _CURATED_ALIAS_CACHE


def curated_aliases_for(ingredient_name: str) -> list[str]:
    key = normalize_phrase(ingredient_name)
    return list(load_curated_alias_map().get(key, []))


def stored_aliases_for(conn: Any, ingredient_name: str) -> list[str]:
    if conn is None:
        return []
    try:
        rows = conn.execute(
            """
            SELECT alias_name
            FROM ingredient_aliases
            WHERE lower(ingredient_name) = lower(?)
            ORDER BY CASE WHEN confidence IS NULL THEN 1 ELSE 0 END, confidence DESC, id DESC
            """,
            (ingredient_name,),
        ).fetchall()
    except Exception:
        return []
    return dedupe_keep_order([str(row["alias_name"] or "") for row in rows])


def persist_alias(
    conn: Any,
    *,
    ingredient_name: str,
    alias_name: str,
    source: str,
    confidence: float | None,
    notes: str | None,
) -> None:
    if conn is None:
        return
    ingredient = " ".join(str(ingredient_name or "").strip().split())
    alias = " ".join(str(alias_name or "").strip().split())
    if not ingredient or not alias:
        return
    if normalize_phrase(ingredient) == normalize_phrase(alias):
        return
    try:
        conn.execute(
            """
            INSERT OR IGNORE INTO ingredient_aliases(ingredient_name, alias_name, source, confidence, notes)
            VALUES (?, ?, ?, ?, ?)
            """,
            (ingredient, alias, source, confidence, notes),
        )
    except Exception as exc:
        logger.warning("Could not persist ingredient alias %r -> %r: %s", ingredient, alias, exc)


def deterministic_alias_candidates(ingredient_name: str) -> list[str]:
    base = " ".join(ingredient_name.strip().split())
    if not base:
        return []

    aliases: list[str] = [base]

    without_parens = " ".join(PARENS_RE.sub(" ", base).split())
    if without_parens and normalize_phrase(without_parens) != normalize_phrase(base):
        aliases.append(without_parens)

    slash_expanded = " ".join(base.replace("/", " ").replace(",", " ").split())
    if slash_expanded and normalize_phrase(slash_expanded) != normalize_phrase(base):
        aliases.append(slash_expanded)

    for seed in list(aliases):
        lowered = normalize_phrase(seed)
        for source_token, replacement in DETERMINISTIC_REPLACEMENTS.items():
            pattern = rf"\b{re.escape(source_token)}\b"
            if re.search(pattern, lowered):
                aliases.append(re.sub(pattern, replacement, seed, flags=re.IGNORECASE))

    return dedupe_keep_order(aliases)


def llm_alias_candidates(ingredient_name: str) -> list[str]:
    api_key = resolve_openai_api_key()
    if not api_key:
        return []

    endpoint = f"{resolve_openai_api_base()}/chat/completions"
    payload = {
        "model": resolve_alias_model(),
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": (
                    "Return concise ingredient aliases for USDA food lookup. "
                    "Output JSON only: {\"aliases\":[\"...\"]}. "
                    "Aliases must be safe literal food-name variants, not recipes."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "ingredient": ingredient_name,
                        "constraints": {
                            "max_aliases": MAX_LLM_ALIASES,
                            "language": "english",
                            "include_transliteration_variants": True,
                        },
                    },
                    ensure_ascii=True,
                ),
            },
        ],
    }
    req = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as response:
            raw = response.read().decode("utf-8")
        parsed = json.loads(raw)
        content = parsed["choices"][0]["message"]["content"]
        body = json.loads(content if isinstance(content, str) else "{}")
        aliases_raw = body.get("aliases")
        if not isinstance(aliases_raw, list):
            return []
        aliases = [
            " ".join(str(alias or "").strip().split())
            for alias in aliases_raw
            if str(alias or "").strip()
        ]
        aliases = dedupe_keep_order(aliases)
        return aliases[:MAX_LLM_ALIASES]
    except Exception as exc:
        logger.warning("LLM alias expansion failed for %r: %s", ingredient_name, exc)
        return []


def llm_density_estimate(ingredient_name: str) -> tuple[float | None, float, str | None]:
    """Ask LLM for grams_per_cup estimate. Returns (grams_per_cup, confidence, note)."""
    if not llm_density_fallback_enabled():
        return None, 0.0, None

    api_key = resolve_openai_api_key()
    if not api_key:
        return None, 0.0, None

    endpoint = f"{resolve_openai_api_base()}/chat/completions"
    payload = {
        "model": resolve_alias_model(),
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": (
                    "You estimate dry-ingredient density. "
                    "Return JSON only with keys: grams_per_cup (number), confidence (0..1), note (string). "
                    "If uncertain, lower confidence. Do not include markdown."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "ingredient": ingredient_name,
                        "request": "Estimate grams in 1 US cup of this ingredient.",
                    },
                    ensure_ascii=True,
                ),
            },
        ],
    }
    req = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as response:
            raw = response.read().decode("utf-8")
        parsed = json.loads(raw)
        content = parsed["choices"][0]["message"]["content"]
        body = json.loads(content if isinstance(content, str) else "{}")
        grams_per_cup = float(body.get("grams_per_cup"))
        confidence = parse_confidence(body.get("confidence"), default=0.0)
        note_raw = body.get("note")
        note = str(note_raw).strip() if note_raw is not None else ""
        note = note if note else None
        # Keep broad but realistic bounds to reject malformed outputs.
        if grams_per_cup <= 0 or grams_per_cup > 5000:
            return None, confidence, note
        return grams_per_cup, confidence, note
    except Exception as exc:
        logger.warning("LLM density fallback failed for %r: %s", ingredient_name, exc)
        return None, 0.0, None


def build_alias_candidates(
    ingredient_name: str,
    *,
    conn: Any,
    include_llm: bool,
) -> list[tuple[str, str]]:
    candidates: list[tuple[str, str]] = [("input", ingredient_name)]
    candidates.extend(("stored", alias) for alias in stored_aliases_for(conn, ingredient_name))
    candidates.extend(("curated", alias) for alias in curated_aliases_for(ingredient_name))
    candidates.extend(("deterministic", alias) for alias in deterministic_alias_candidates(ingredient_name))
    if include_llm:
        candidates.extend(("llm", alias) for alias in llm_alias_candidates(ingredient_name))

    unique: list[tuple[str, str]] = []
    seen: set[str] = set()
    for source, candidate in candidates:
        normalized = normalize_phrase(candidate)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        unique.append((source, " ".join(candidate.strip().split())))
        if len(unique) >= MAX_ALIAS_CANDIDATES:
            break
    return unique


def search_food(query: str, *, timeout: float = 10, page_size: int = 5) -> list[dict[str, Any]] | None:
    """Search FDC for a food item. Returns the ``foods`` list or None on error."""
    params = urllib.parse.urlencode(
        {
            "api_key": _api_key(),
            "query": query,
            "dataType": "Foundation,SR Legacy",
            "pageSize": str(page_size),
        }
    )
    url = f"{FDC_SEARCH_URL}?{params}"

    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
        return data.get("foods")
    except (urllib.error.URLError, OSError, json.JSONDecodeError, KeyError) as exc:
        logger.warning("USDA search failed for %r: %s", query, exc)
        return None


def parse_quantity_token(token: str) -> float | None:
    cleaned = token.strip().lower()
    if not cleaned:
        return None
    if "/" in cleaned and cleaned.count("/") == 1 and cleaned.replace("/", "").replace(".", "").isdigit():
        numerator, denominator = cleaned.split("/", 1)
        try:
            n = float(numerator)
            d = float(denominator)
            if d > 0:
                return n / d
        except Exception:
            return None
        return None
    try:
        value = float(cleaned)
    except ValueError:
        return None
    return value if value > 0 else None


def parse_label_quantity(label: str) -> float:
    """Estimate leading quantity in USDA measure labels like '1 1/2 tbsp'."""
    head = str(label or "").strip().lower().split(",")[0]
    if not head:
        return 1.0
    tokens = head.split()
    total = 0.0
    consumed = 0
    for token in tokens[:2]:
        value = parse_quantity_token(token)
        if value is None:
            break
        total += value
        consumed += 1
    if consumed == 0 or total <= 0:
        return 1.0
    return total


def extract_measures(food: dict[str, Any]) -> list[FoodMeasure]:
    """Pull usable measures from a single USDA food result."""
    measures: list[FoodMeasure] = []

    for fm in food.get("foodMeasures", []):
        gram_weight = fm.get("gramWeight")
        if not gram_weight or gram_weight <= 0:
            continue

        label = (fm.get("disseminationText") or "").strip().lower()
        abbrev = (fm.get("measureUnitAbbreviation") or "").strip().lower()

        matched_unit: str | None = None
        if abbrev in MEASURE_MAP:
            matched_unit = MEASURE_MAP[abbrev]
        else:
            first_segment = label.split(",")[0]
            for key, canonical in MEASURE_MAP.items():
                if key in first_segment:
                    matched_unit = canonical
                    break

        if matched_unit is None:
            continue

        quantity = parse_label_quantity(label)
        per_unit_weight = float(gram_weight) / quantity if quantity > 0 else float(gram_weight)
        if per_unit_weight <= 0:
            continue

        measures.append(
            FoodMeasure(
                unit=matched_unit,
                gram_weight=per_unit_weight,
                label=fm.get("disseminationText") or f"1 {matched_unit}",
            )
        )

    # Keep the first measure per unit for stable behavior.
    seen_units: set[str] = set()
    deduped: list[FoodMeasure] = []
    for measure in measures:
        if measure.unit in seen_units:
            continue
        seen_units.add(measure.unit)
        deduped.append(measure)
    return deduped


def derive_grams_per_cup(measures: list[FoodMeasure]) -> float | None:
    """Derive grams_per_cup from the best available measure."""
    for measure in measures:
        if measure.unit == "cup":
            return measure.gram_weight

    for measure in measures:
        ratio = VOLUME_TO_CUP.get(measure.unit)
        if ratio and ratio > 0:
            return measure.gram_weight / ratio

    return None


def measure_quality_score(measures: list[FoodMeasure]) -> float:
    units = {m.unit for m in measures}
    if "cup" in units:
        return 1.0
    if "tbsp" in units or "tsp" in units:
        return 0.8
    if "oz" in units:
        return 0.55
    return 0.35


def score_food_match(
    *,
    ingredient_name: str,
    query: str,
    source: str,
    description: str,
    measures: list[FoodMeasure],
) -> FoodMatch | None:
    if not measures:
        return None

    ingredient_tokens = tokenize_for_match(ingredient_name)
    query_tokens = tokenize_for_match(query)
    description_tokens = tokenize_for_match(description)
    if not ingredient_tokens or not description_tokens:
        return None

    ingredient_overlap = len(ingredient_tokens & description_tokens) / len(ingredient_tokens)
    query_overlap = (
        len(query_tokens & description_tokens) / len(query_tokens)
        if query_tokens
        else ingredient_overlap
    )
    quality = measure_quality_score(measures)

    ingredient_norm = normalize_phrase(ingredient_name)
    description_norm = normalize_phrase(description)
    contains_bonus = 0.08 if ingredient_norm and ingredient_norm in description_norm else 0.0
    starts_bonus = 0.08 if ingredient_norm and description_norm.startswith(ingredient_norm) else 0.0

    raw_score = (
        (0.56 * ingredient_overlap)
        + (0.22 * query_overlap)
        + (0.22 * quality)
        + contains_bonus
        + starts_bonus
    )
    weighted_score = raw_score * SOURCE_WEIGHTS.get(source, 1.0)

    return FoodMatch(
        query=query,
        source=source,
        description=description,
        score=weighted_score,
        token_recall=ingredient_overlap,
        measures=measures,
    )


def is_confident_match(match: FoodMatch | None) -> bool:
    if match is None:
        return False
    return match.score >= MIN_MATCH_SCORE and match.token_recall >= MIN_TOKEN_RECALL


def find_best_food_match(
    ingredient_name: str,
    candidates: list[tuple[str, str]],
) -> FoodMatch | None:
    best: FoodMatch | None = None

    for source, query in candidates:
        foods = search_food(query)
        if not foods:
            continue
        for food in foods:
            description = str(food.get("description") or "").strip()
            if not description:
                continue
            measures = extract_measures(food)
            match = score_food_match(
                ingredient_name=ingredient_name,
                query=query,
                source=source,
                description=description,
                measures=measures,
            )
            if match is None:
                continue
            if best is None or match.score > best.score:
                best = match

    return best


def lookup_ingredient_detailed(
    ingredient_name: str,
    *,
    conn: Any = None,
) -> dict[str, Any]:
    """Look up an ingredient in USDA and return detailed matching metadata."""
    primary_candidates = build_alias_candidates(
        ingredient_name,
        conn=conn,
        include_llm=False,
    )
    best = find_best_food_match(ingredient_name, primary_candidates)

    if not is_confident_match(best):
        llm_candidates = build_alias_candidates(
            ingredient_name,
            conn=conn,
            include_llm=True,
        )
        # Only evaluate genuinely new candidates in this second pass.
        primary_set = {normalize_phrase(candidate) for _, candidate in primary_candidates}
        llm_only = [
            (source, candidate)
            for source, candidate in llm_candidates
            if normalize_phrase(candidate) not in primary_set
        ]
        best_llm = find_best_food_match(ingredient_name, llm_only)
        if best_llm and (best is None or best_llm.score > best.score):
            best = best_llm

    if not is_confident_match(best):
        llm_gpc, llm_confidence, llm_note = llm_density_estimate(ingredient_name)
        if llm_gpc is not None and llm_confidence >= MIN_LLM_DENSITY_CONFIDENCE:
            llm_measures = [
                FoodMeasure(
                    unit="cup",
                    gram_weight=llm_gpc,
                    label=f"1 cup (LLM estimate; confidence={llm_confidence:.2f})",
                )
            ]
            logger.info(
                "LLM density fallback for %r (grams_per_cup=%s, confidence=%.3f)",
                ingredient_name,
                llm_gpc,
                llm_confidence,
            )
            return {
                "matched": True,
                "grams_per_cup": llm_gpc,
                "measures": llm_measures,
                "query": ingredient_name,
                "source": "llm_density",
                "description": llm_note,
                "score": llm_confidence,
            }

        logger.info(
            "USDA: no confident match for %r and no acceptable LLM density fallback.",
            ingredient_name,
        )
        return {
            "matched": False,
            "grams_per_cup": None,
            "measures": [],
            "query": None,
            "source": None,
            "description": None,
            "score": None,
        }

    grams_per_cup = derive_grams_per_cup(best.measures)
    logger.info(
        "USDA match for %r via %r (%s): %s (score=%.3f, grams_per_cup=%s, measures=%d)",
        ingredient_name,
        best.query,
        best.source,
        best.description,
        best.score,
        grams_per_cup,
        len(best.measures),
    )

    if conn is not None and normalize_phrase(best.query) != normalize_phrase(ingredient_name):
        persist_alias(
            conn,
            ingredient_name=ingredient_name,
            alias_name=best.query,
            source=f"auto_{best.source}",
            confidence=round(best.score, 4),
            notes=f"USDA matched food: {best.description[:240]}",
        )

    return {
        "matched": True,
        "grams_per_cup": grams_per_cup,
        "measures": best.measures,
        "query": best.query,
        "source": best.source,
        "description": best.description,
        "score": best.score,
    }


def lookup_ingredient(ingredient_name: str) -> tuple[float | None, list[FoodMeasure]]:
    """Backwards-compatible lookup API returning ``(grams_per_cup, measures)``."""
    detail = lookup_ingredient_detailed(ingredient_name)
    if not detail["matched"]:
        return None, []
    return detail["grams_per_cup"], detail["measures"]


def populate_ingredient_conversions(
    conn: Any,
    ingredient_id: int,
    ingredient_name: str,
) -> bool:
    """Fetch USDA data for an ingredient and store it.

    Updates ``ingredients.grams_per_cup`` and inserts rows into
    ``unit_conversions``. Returns True if any data was stored.
    """
    detail = lookup_ingredient_detailed(ingredient_name, conn=conn)
    measures = detail["measures"]
    grams_per_cup = detail["grams_per_cup"]

    if not measures:
        return False

    changed = False

    # Set grams_per_cup if we found one and the ingredient doesn't have one yet.
    if grams_per_cup is not None:
        existing = conn.execute(
            "SELECT grams_per_cup FROM ingredients WHERE id = ?",
            (ingredient_id,),
        ).fetchone()

        if existing and not existing["grams_per_cup"]:
            conn.execute(
                "UPDATE ingredients SET grams_per_cup = ?, canonical_unit = COALESCE(canonical_unit, 'g') WHERE id = ?",
                (grams_per_cup, ingredient_id),
            )
            changed = True

    match_query = detail.get("query")
    match_description = detail.get("description")
    match_source = str(detail.get("source") or "").strip().lower()
    conversion_context = "llm_estimate" if match_source == "llm_density" else "usda_fdc"

    # Insert unit_conversions rows (1 unit -> X grams).
    for measure in measures:
        duplicate = conn.execute(
            """
            SELECT id FROM unit_conversions
            WHERE lower(item_name) = lower(?)
              AND unit_from = ?
              AND context = ?
            LIMIT 1
            """,
            (ingredient_name, measure.unit, conversion_context),
        ).fetchone()

        if duplicate:
            continue

        note_parts = [f"USDA: {measure.label}"]
        if conversion_context == "llm_estimate":
            note_parts = [f"LLM estimate: {measure.label}"]
        if match_query:
            note_parts.append(f"query={match_query}")
        if match_description:
            note_parts.append(f"food={match_description}")
        note = " | ".join(note_parts)

        conn.execute(
            """
            INSERT INTO unit_conversions(
                item_name, quantity_from, unit_from, quantity_to, unit_to,
                context, source_sheet, notes
            )
            VALUES (?, 1, ?, ?, 'g', ?, NULL, ?)
            """,
            (ingredient_name, measure.unit, measure.gram_weight, conversion_context, note),
        )
        changed = True

    return changed
