from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .db import get_connection, init_db

app = FastAPI(title="Retreat Ops API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"

MASS_TO_G = {
    "g": 1.0,
    "kg": 1000.0,
    "lb": 453.59237,
    "lbs": 453.59237,
    "oz": 28.349523125,
}

VOLUME_TO_ML = {
    "ml": 1.0,
    "l": 1000.0,
    "cup": 240.0,
    "cups": 240.0,
    "tbsp": 14.7868,
    "tsp": 4.92892,
}

COUNT_UNITS = {
    "piece",
    "pieces",
    "packet",
    "packets",
    "can",
    "cans",
    "bunch",
    "bunches",
    "loaf",
    "loaves",
}


class IngredientInput(BaseModel):
    name: str = Field(min_length=1)
    quantity: float = Field(gt=0)
    unit: str = Field(min_length=1)


class ScalePreviewRequest(BaseModel):
    base_servings: float = Field(gt=0)
    target_servings: float = Field(gt=0)
    ingredients: list[IngredientInput] = Field(min_length=1)


class ScaledIngredient(BaseModel):
    name: str
    input_quantity: float
    input_unit: str
    scaled_quantity: float
    scaled_unit: str
    canonical_quantity: float | None
    canonical_unit: str | None
    shopping_quantity: float | None
    shopping_unit: str | None
    note: str | None = None


class ScalePreviewResponse(BaseModel):
    scale_factor: float
    ingredients: list[ScaledIngredient]


class RecipeIngredientCreate(BaseModel):
    ingredient_name: str = Field(min_length=1)
    quantity: float = Field(gt=0)
    unit: str = Field(min_length=1)
    prep_notes: str | None = None


class RecipeCreate(BaseModel):
    name: str = Field(min_length=1)
    base_servings: float = Field(gt=0)
    notes: str | None = None
    ingredients: list[RecipeIngredientCreate] = Field(min_length=1)


class RetreatPlanMeal(BaseModel):
    day: int = Field(ge=1)
    meal: str = Field(min_length=1)
    people: float = Field(ge=0)
    dishes: list[str] = Field(default_factory=list)


class RetreatPlanPayload(BaseModel):
    name: str = Field(min_length=1)
    startDate: str | None = None
    dayCount: int = Field(ge=1, le=10)
    defaultPeople: float = Field(gt=0)
    meals: list[RetreatPlanMeal] = Field(min_length=1)


class ServiceSnapshotIngredient(BaseModel):
    name: str = Field(min_length=1)
    scaledQty: str = Field(min_length=1)
    scaledUnit: str = Field(min_length=1)
    shopQty: str | None = None
    shopUnit: str | None = None


class ServiceSnapshotDish(BaseModel):
    name: str = Field(min_length=1)
    serves: float = Field(gt=0)
    baseServings: float = Field(gt=0)
    factor: float = Field(gt=0)
    ingredients: list[ServiceSnapshotIngredient] = Field(min_length=1)
    steps: list[str] = Field(min_length=1)


class ServiceSnapshotMeal(BaseModel):
    day: int = Field(ge=1)
    meal: str = Field(min_length=1)
    people: float = Field(gt=0)
    dishes: list[ServiceSnapshotDish] = Field(min_length=1)


class ServiceSnapshotPayload(BaseModel):
    version: int = Field(default=1, ge=1)
    retreatName: str = Field(min_length=1)
    generatedAt: str | None = None
    meals: list[ServiceSnapshotMeal] = Field(min_length=1)
    retreatPlanId: int | None = None


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/ingredients")
def list_ingredients() -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, name, canonical_unit, grams_per_cup, notes FROM ingredients ORDER BY name"
        ).fetchall()
    return [dict(r) for r in rows]


@app.post("/api/recipes")
def create_recipe(payload: RecipeCreate) -> dict[str, Any]:
    with get_connection() as conn:
        try:
            recipe_row = conn.execute(
                "INSERT INTO recipes(name, base_servings, notes) VALUES (?, ?, ?) RETURNING id, name, base_servings, notes",
                (payload.name.strip(), payload.base_servings, payload.notes),
            ).fetchone()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Could not create recipe: {exc}") from exc

        recipe_id = recipe_row["id"]

        for item in payload.ingredients:
            ing_name = item.ingredient_name.strip()
            ing_row = conn.execute(
                "SELECT id FROM ingredients WHERE lower(name) = lower(?)", (ing_name,)
            ).fetchone()
            if not ing_row:
                ing_row = conn.execute(
                    "INSERT INTO ingredients(name) VALUES (?) RETURNING id", (ing_name,)
                ).fetchone()

            conn.execute(
                """
                INSERT INTO recipe_ingredients(recipe_id, ingredient_id, quantity, unit, prep_notes)
                VALUES (?, ?, ?, ?, ?)
                """,
                (recipe_id, ing_row["id"], item.quantity, normalize_unit(item.unit), item.prep_notes),
            )

        conn.commit()

    return {
        "id": recipe_row["id"],
        "name": recipe_row["name"],
        "base_servings": recipe_row["base_servings"],
        "notes": recipe_row["notes"],
    }


@app.get("/api/recipes")
def list_recipes() -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, name, base_servings, notes, created_at FROM recipes ORDER BY created_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


@app.get("/api/recipes/full")
def list_recipes_full() -> list[dict[str, Any]]:
    with get_connection() as conn:
        recipes = conn.execute(
            "SELECT id, name, base_servings, notes, created_at FROM recipes ORDER BY name"
        ).fetchall()

        ingredient_rows = conn.execute(
            """
            SELECT
                ri.recipe_id,
                i.name AS ingredient_name,
                ri.quantity,
                ri.unit,
                ri.prep_notes
            FROM recipe_ingredients ri
            JOIN ingredients i ON i.id = ri.ingredient_id
            ORDER BY ri.recipe_id, ri.id
            """
        ).fetchall()

        step_rows = conn.execute(
            """
            SELECT recipe_id, step_order, instruction
            FROM recipe_steps
            ORDER BY recipe_id, step_order, id
            """
        ).fetchall()

    ingredients_by_recipe: dict[int, list[dict[str, Any]]] = {}
    for row in ingredient_rows:
        recipe_id = int(row["recipe_id"])
        ingredients_by_recipe.setdefault(recipe_id, []).append(
            {
                "name": row["ingredient_name"],
                "quantity": float(row["quantity"]),
                "unit": row["unit"],
                "prep_notes": row["prep_notes"],
            }
        )

    steps_by_recipe: dict[int, list[str]] = {}
    for row in step_rows:
        recipe_id = int(row["recipe_id"])
        steps_by_recipe.setdefault(recipe_id, []).append(row["instruction"])

    output: list[dict[str, Any]] = []
    for recipe in recipes:
        recipe_id = int(recipe["id"])
        output.append(
            {
                "id": recipe_id,
                "name": recipe["name"],
                "base_servings": float(recipe["base_servings"]),
                "notes": recipe["notes"],
                "created_at": recipe["created_at"],
                "ingredients": ingredients_by_recipe.get(recipe_id, []),
                "steps": steps_by_recipe.get(recipe_id, []),
            }
        )

    return output


@app.post("/api/scale-preview", response_model=ScalePreviewResponse)
def scale_preview(payload: ScalePreviewRequest) -> ScalePreviewResponse:
    factor = payload.target_servings / payload.base_servings
    scaled_items: list[ScaledIngredient] = []

    for item in payload.ingredients:
        unit = normalize_unit(item.unit)
        scaled_qty = item.quantity * factor
        canonical_qty, canonical_unit, note = to_canonical(item.name, scaled_qty, unit)
        shopping_qty, shopping_unit = to_shopping_unit(canonical_qty, canonical_unit)

        scaled_items.append(
            ScaledIngredient(
                name=item.name,
                input_quantity=round(item.quantity, 4),
                input_unit=unit,
                scaled_quantity=round(scaled_qty, 4),
                scaled_unit=unit,
                canonical_quantity=round(canonical_qty, 4) if canonical_qty is not None else None,
                canonical_unit=canonical_unit,
                shopping_quantity=round(shopping_qty, 4) if shopping_qty is not None else None,
                shopping_unit=shopping_unit,
                note=note,
            )
        )

    return ScalePreviewResponse(scale_factor=round(factor, 4), ingredients=scaled_items)


@app.post("/api/recipes/{recipe_id}/scale", response_model=ScalePreviewResponse)
def scale_recipe(recipe_id: int, target_servings: float = Query(..., gt=0)) -> ScalePreviewResponse:
    with get_connection() as conn:
        recipe = conn.execute(
            "SELECT id, name, base_servings FROM recipes WHERE id = ?", (recipe_id,)
        ).fetchone()
        if not recipe:
            raise HTTPException(status_code=404, detail="Recipe not found")

        items = conn.execute(
            """
            SELECT i.name AS ingredient_name, ri.quantity, ri.unit
            FROM recipe_ingredients ri
            JOIN ingredients i ON i.id = ri.ingredient_id
            WHERE ri.recipe_id = ?
            ORDER BY ri.id
            """,
            (recipe_id,),
        ).fetchall()

    payload = ScalePreviewRequest(
        base_servings=float(recipe["base_servings"]),
        target_servings=target_servings,
        ingredients=[
            IngredientInput(name=row["ingredient_name"], quantity=row["quantity"], unit=row["unit"])
            for row in items
        ],
    )
    return scale_preview(payload)


@app.get("/api/retreat-plans")
def list_retreat_plans() -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, name, start_date, day_count, default_people, created_at, updated_at
            FROM retreat_plans
            ORDER BY updated_at DESC, id DESC
            """
        ).fetchall()
    return [dict(r) for r in rows]


@app.get("/api/retreat-plans/{plan_id}")
def get_retreat_plan(plan_id: int) -> dict[str, Any]:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT id, name, start_date, day_count, default_people, plan_json, created_at, updated_at
            FROM retreat_plans
            WHERE id = ?
            """,
            (plan_id,),
        ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Retreat plan not found")

    payload = json.loads(row["plan_json"]) if row["plan_json"] else {}
    if not isinstance(payload, dict):
        payload = {}

    payload["id"] = int(row["id"])
    payload["name"] = payload.get("name") or row["name"]
    payload["startDate"] = payload.get("startDate", row["start_date"])
    payload["dayCount"] = int(payload.get("dayCount") or row["day_count"])
    payload["defaultPeople"] = float(payload.get("defaultPeople") or row["default_people"])
    payload["meals"] = payload.get("meals") or []
    payload["created_at"] = row["created_at"]
    payload["updated_at"] = row["updated_at"]
    return payload


@app.post("/api/retreat-plans")
def upsert_retreat_plan(payload: RetreatPlanPayload) -> dict[str, Any]:
    plan_name = payload.name.strip()
    if not plan_name:
        raise HTTPException(status_code=400, detail="Retreat name cannot be blank")

    if any(meal.day > payload.dayCount for meal in payload.meals):
        raise HTTPException(status_code=400, detail="Meal day cannot exceed dayCount")

    payload_dict = payload.model_dump()
    payload_dict["name"] = plan_name
    payload_json = json.dumps(payload_dict)

    with get_connection() as conn:
        existing = conn.execute(
            "SELECT id FROM retreat_plans WHERE lower(name) = lower(?)",
            (plan_name,),
        ).fetchone()

        if existing:
            conn.execute(
                """
                UPDATE retreat_plans
                SET name = ?, start_date = ?, day_count = ?, default_people = ?, plan_json = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    plan_name,
                    payload.startDate,
                    payload.dayCount,
                    payload.defaultPeople,
                    payload_json,
                    existing["id"],
                ),
            )
            plan_id = int(existing["id"])
            action = "updated"
        else:
            created = conn.execute(
                """
                INSERT INTO retreat_plans(name, start_date, day_count, default_people, plan_json)
                VALUES (?, ?, ?, ?, ?)
                RETURNING id
                """,
                (plan_name, payload.startDate, payload.dayCount, payload.defaultPeople, payload_json),
            ).fetchone()
            plan_id = int(created["id"])
            action = "created"

        row = conn.execute(
            "SELECT id, name, updated_at FROM retreat_plans WHERE id = ?",
            (plan_id,),
        ).fetchone()
        conn.commit()

    return {
        "id": int(row["id"]),
        "name": row["name"],
        "status": action,
        "updated_at": row["updated_at"],
    }


@app.post("/api/service-snapshots")
def create_service_snapshot(payload: ServiceSnapshotPayload) -> dict[str, Any]:
    with get_connection() as conn:
        if payload.retreatPlanId is not None:
            plan = conn.execute(
                "SELECT id FROM retreat_plans WHERE id = ?", (payload.retreatPlanId,)
            ).fetchone()
            if not plan:
                raise HTTPException(status_code=400, detail="Referenced retreat plan not found")

        row = conn.execute(
            """
            INSERT INTO service_snapshots(retreat_name, payload_json, retreat_plan_id)
            VALUES (?, ?, ?)
            RETURNING id, retreat_name, created_at
            """,
            (payload.retreatName.strip(), payload.model_dump_json(), payload.retreatPlanId),
        ).fetchone()
        conn.commit()

    return {
        "id": int(row["id"]),
        "retreat_name": row["retreat_name"],
        "created_at": row["created_at"],
        "meal_count": len(payload.meals),
    }


@app.get("/api/service-snapshots/latest")
def get_latest_service_snapshot() -> dict[str, Any]:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT id, retreat_name, payload_json, created_at
            FROM service_snapshots
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="No service snapshot found")

    payload = json.loads(row["payload_json"])
    return {
        "snapshot_id": int(row["id"]),
        "retreat_name": row["retreat_name"],
        "created_at": row["created_at"],
        "payload": payload,
    }


@app.get("/api/service-snapshots/by-plan/{plan_id}")
def get_service_snapshot_by_plan(plan_id: int) -> dict[str, Any]:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT id, retreat_name, payload_json, created_at
            FROM service_snapshots
            WHERE retreat_plan_id = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (plan_id,),
        ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="No service snapshot found for this retreat plan")

    payload = json.loads(row["payload_json"])
    return {
        "snapshot_id": int(row["id"]),
        "retreat_name": row["retreat_name"],
        "created_at": row["created_at"],
        "payload": payload,
    }


def normalize_unit(unit: str) -> str:
    value = unit.strip().lower()
    aliases = {
        "gms": "g",
        "kilogram": "kg",
        "kilograms": "kg",
        "gram": "g",
        "grams": "g",
        "liter": "l",
        "liters": "l",
        "litre": "l",
        "litres": "l",
        "milliliter": "ml",
        "milliliters": "ml",
        "millilitre": "ml",
        "millilitres": "ml",
        "tablespoon": "tbsp",
        "tablespoons": "tbsp",
        "tbs": "tbsp",
        "teaspoon": "tsp",
        "teaspoons": "tsp",
        "tsb": "tsp",
        "pound": "lb",
        "pounds": "lb",
    }
    return aliases.get(value, value)


def ingredient_grams_per_cup(ingredient_name: str) -> float | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT grams_per_cup FROM ingredients WHERE lower(name) = lower(?)",
            (ingredient_name.strip(),),
        ).fetchone()
        if row and row["grams_per_cup"]:
            return float(row["grams_per_cup"])
    return None


def to_canonical(ingredient_name: str, qty: float, unit: str) -> tuple[float | None, str | None, str | None]:
    if unit in MASS_TO_G:
        return qty * MASS_TO_G[unit], "g", None

    if unit in VOLUME_TO_ML:
        grams_per_cup = ingredient_grams_per_cup(ingredient_name)
        if grams_per_cup is not None:
            cups = (qty * VOLUME_TO_ML[unit]) / VOLUME_TO_ML["cup"]
            grams = cups * grams_per_cup
            return grams, "g", "Converted using ingredient-specific grams_per_cup."
        return qty * VOLUME_TO_ML[unit], "ml", "No ingredient density found; kept as volume."

    if unit in COUNT_UNITS:
        return qty, unit, None

    return None, None, f"Unknown unit '{unit}'."


def to_shopping_unit(canonical_qty: float | None, canonical_unit: str | None) -> tuple[float | None, str | None]:
    if canonical_qty is None or canonical_unit is None:
        return None, None

    if canonical_unit == "g":
        if canonical_qty >= 1000:
            return canonical_qty / 1000.0, "kg"
        if canonical_qty >= 453.59237:
            return canonical_qty / 453.59237, "lb"
        return canonical_qty, "g"

    if canonical_unit == "ml":
        if canonical_qty >= 1000:
            return canonical_qty / 1000.0, "l"
        return canonical_qty, "ml"

    return canonical_qty, canonical_unit


if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
