"""USDA FoodData Central lookup for ingredient density data.

Uses the free FoodData Central API to find gram weights per household
measure (cup, tbsp, tsp, etc.) for a given ingredient.  Results are
stored in the ``ingredients`` and ``unit_conversions`` tables so that
the conversion pipeline works automatically for newly-added items.

Set the ``USDA_API_KEY`` environment variable for production use.
Falls back to ``DEMO_KEY`` (rate-limited) when unset.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

FDC_SEARCH_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"

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


@dataclass
class FoodMeasure:
    """A single USDA food measure entry."""
    unit: str          # our canonical unit (cup/tbsp/tsp/oz)
    gram_weight: float # grams for *one* of this unit
    label: str         # original USDA text, e.g. "1 cup, chopped"


def _api_key() -> str:
    return os.environ.get("USDA_API_KEY", "DEMO_KEY")


def search_food(query: str, *, timeout: float = 8) -> list[dict[str, Any]] | None:
    """Search FDC for a food item.  Returns the ``foods`` list or None on error."""
    params = urllib.parse.urlencode({
        "api_key": _api_key(),
        "query": query,
        "dataType": "Foundation,SR Legacy",
        "pageSize": "3",
    })
    url = f"{FDC_SEARCH_URL}?{params}"

    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
        return data.get("foods")
    except (urllib.error.URLError, OSError, json.JSONDecodeError, KeyError) as exc:
        logger.warning("USDA search failed for %r: %s", query, exc)
        return None


def extract_measures(food: dict[str, Any]) -> list[FoodMeasure]:
    """Pull usable measures from a single USDA food result."""
    measures: list[FoodMeasure] = []

    for fm in food.get("foodMeasures", []):
        gram_weight = fm.get("gramWeight")
        if not gram_weight or gram_weight <= 0:
            continue

        label = (fm.get("disseminationText") or "").strip().lower()
        abbrev = (fm.get("measureUnitAbbreviation") or "").strip().lower()

        # Try to match either the abbreviation or words in the label.
        matched_unit: str | None = None

        if abbrev in MEASURE_MAP:
            matched_unit = MEASURE_MAP[abbrev]
        else:
            for key, canonical in MEASURE_MAP.items():
                if key in label.split(",")[0]:  # only check before first comma
                    matched_unit = canonical
                    break

        if matched_unit is None:
            continue

        # The USDA disseminationText is usually "1 cup" — gram_weight is for that qty.
        measures.append(FoodMeasure(
            unit=matched_unit,
            gram_weight=gram_weight,
            label=fm.get("disseminationText") or f"1 {matched_unit}",
        ))

    return measures


def derive_grams_per_cup(measures: list[FoodMeasure]) -> float | None:
    """Derive grams_per_cup from the best available measure."""
    # Prefer a direct cup measure.
    for m in measures:
        if m.unit == "cup":
            return m.gram_weight

    # Fall back to converting tbsp or tsp.
    for m in measures:
        ratio = VOLUME_TO_CUP.get(m.unit)
        if ratio and ratio > 0:
            return m.gram_weight / ratio

    return None


def lookup_ingredient(ingredient_name: str) -> tuple[float | None, list[FoodMeasure]]:
    """Look up an ingredient in USDA and return (grams_per_cup, measures).

    Returns (None, []) if the lookup fails or nothing useful is found.
    """
    foods = search_food(ingredient_name)
    if not foods:
        return None, []

    # Try each result until we find one with usable measures.
    for food in foods:
        measures = extract_measures(food)
        if measures:
            gpc = derive_grams_per_cup(measures)
            logger.info(
                "USDA match for %r: %s (grams_per_cup=%s, %d measures)",
                ingredient_name,
                food.get("description", "?"),
                gpc,
                len(measures),
            )
            return gpc, measures

    logger.info("USDA: no usable measures found for %r", ingredient_name)
    return None, []


def populate_ingredient_conversions(
    conn: Any,
    ingredient_id: int,
    ingredient_name: str,
) -> bool:
    """Fetch USDA data for an ingredient and store it.

    Updates ``ingredients.grams_per_cup`` and inserts rows into
    ``unit_conversions``.  Returns True if any data was stored.

    This is safe to call even if the USDA API is unreachable — it
    just returns False with no side effects.
    """
    grams_per_cup, measures = lookup_ingredient(ingredient_name)

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

    # Insert unit_conversions rows (1 unit → X grams).
    for m in measures:
        # Avoid duplicates.
        dup = conn.execute(
            """
            SELECT id FROM unit_conversions
            WHERE lower(item_name) = lower(?)
              AND unit_from = ?
              AND context = 'usda_fdc'
            LIMIT 1
            """,
            (ingredient_name, m.unit),
        ).fetchone()

        if dup:
            continue

        conn.execute(
            """
            INSERT INTO unit_conversions(
                item_name, quantity_from, unit_from, quantity_to, unit_to,
                context, source_sheet, notes
            )
            VALUES (?, 1, ?, ?, 'g', 'usda_fdc', NULL, ?)
            """,
            (ingredient_name, m.unit, m.gram_weight, f"USDA: {m.label}"),
        )
        changed = True

    return changed
