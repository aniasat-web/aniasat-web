from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated
from typing import Any
from typing import Literal
from urllib import error as urllib_error
from urllib import request as urllib_request

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .auth import (
    BOOTSTRAP_ADMIN_PASSWORD_ENV,
    BOOTSTRAP_ADMIN_USERNAME_ENV,
    ROLE_ADMIN,
    ROLE_PLANNER,
    SESSION_COOKIE_NAME,
    AuthUser,
    authenticate_credentials,
    authenticate_session_token,
    cookie_secure_enabled,
    create_session,
    create_user,
    default_route_for_role,
    delete_session,
    ensure_bootstrap_admin,
    hash_session_token,
    has_any_users,
    list_users,
    normalize_role,
    update_user,
)
from .db import get_connection, init_db, table_columns, table_exists
from .usda import populate_ingredient_conversions

app = FastAPI(title="Blossom Foundation Volunteering API", version="0.2.0")

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
    "sprig",
    "sprigs",
    "leaf",
    "leaves",
    "pinch",
    "pinches",
    "bag",
    "bags",
}

DAL_RICE_TOKEN_RE = re.compile(r"\b(rice|dal|moong|mung|toor|urad|masoor)\b")

RECIPE_CATEGORIES = [
    "M's Recipes",
    "Breakfast",
    "Salads",
    "Vegetable Dishes",
    "Dals & Stews",
    "Khichdi & Kadhi",
    "Rice Dishes",
    "Desserts",
    "Chai & Coffee",
    "Pickles",
    "Ready to Serve",
]

OPENAI_API_KEY_ENV = "OPENAI_API_KEY"
OPENAI_API_BASE_ENV = "RETREAT_OPS_OPENAI_API_BASE"
OPENAI_INGREDIENT_DUP_MODEL_ENV = "RETREAT_OPS_INGREDIENT_DUP_MODEL"
DEFAULT_OPENAI_API_BASE = "https://api.openai.com/v1"
DEFAULT_INGREDIENT_DUP_MODEL = "gpt-5-mini"

PUBLIC_API_PATHS = {
    "/api/health",
    "/api/auth/login",
    "/api/auth/bootstrap-status",
}

PUBLIC_API_GET_PREFIXES = (
    "/api/service-snapshots/by-plan/",
)

PUBLIC_API_GET_PATHS = {
    "/api/service-snapshots/latest",
}

HEADCOUNT_PROFILES = {"retreat", "test"}
DEFAULT_TEST_HEADCOUNT = 4.0
DEFAULT_SHOPPING_PROFILE = "retreat"
SHOPPING_PHASES = ["bulk", "fresh", "daily", "custom"]
MANUAL_INVENTORY_SOURCE = "Shopping Manual Override"


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
    category: str | None = None
    base_servings: int = Field(gt=0)
    notes: str | None = None
    ingredients: list[RecipeIngredientCreate] = Field(min_length=1)
    steps: list[str] = Field(default_factory=list)


class RetreatPlanMeal(BaseModel):
    day: int = Field(ge=1)
    meal: str = Field(min_length=1)
    people: float = Field(ge=0)
    dishes: list[str] = Field(default_factory=list)


class RetreatPlanPayload(BaseModel):
    id: int | None = Field(default=None, ge=1)
    name: str = Field(min_length=1)
    startDate: str | None = None
    dayCount: int = Field(ge=1, le=10)
    defaultPeople: float = Field(gt=0)
    meals: list[RetreatPlanMeal] = Field(min_length=1)
    retreatDefaultPeople: float | None = Field(default=None, gt=0)
    testDefaultPeople: float = Field(default=4, gt=0)
    activeProfile: Literal["retreat", "test"] = "retreat"
    shoppingProfile: Literal["retreat", "test"] = "retreat"
    retreatMeals: list[RetreatPlanMeal] | None = None
    testMeals: list[RetreatPlanMeal] | None = None


class RetreatPlanDuplicatePayload(BaseModel):
    name: str | None = None


class AuthLoginPayload(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


class AuthUserCreatePayload(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)
    role: str = Field(min_length=1)
    is_active: bool = True


class AuthUserUpdatePayload(BaseModel):
    password: str | None = None
    role: str | None = None
    is_active: bool | None = None


class AuthChangePasswordPayload(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=1)


class IngredientUpdatePayload(BaseModel):
    name: str = Field(min_length=1)
    canonical_unit: str | None = None
    grams_per_cup: float | None = None
    notes: str | None = None
    category: str | None = None
    purchase_tier: str | None = None


class IngredientDuplicateScanPayload(BaseModel):
    max_groups: int = Field(default=20, ge=1, le=60)
    model: str | None = None


class StandaloneInventoryCreate(BaseModel):
    item_name: str = Field(min_length=1)
    quantity: float = Field(ge=0, default=0)
    unit: str | None = None
    category: str | None = None
    location: str | None = None
    notes: str | None = None


class StandaloneInventoryUpdate(BaseModel):
    item_name: str = Field(min_length=1)
    quantity: float = Field(ge=0, default=0)
    unit: str | None = None
    category: str | None = None
    location: str | None = None
    notes: str | None = None


class RetreatInventoryCategoryCreate(BaseModel):
    name: str = Field(min_length=1)
    trackingMode: Literal["ITEM", "CATEGORY"] = "ITEM"
    imageUrl: str | None = None


class RetreatInventoryCategoryUpdate(BaseModel):
    name: str | None = None
    trackingMode: Literal["ITEM", "CATEGORY"] | None = None
    imageUrl: str | None = None
    active: bool | None = None


class RetreatInventoryLocationCreate(BaseModel):
    name: str = Field(min_length=1)
    description: str | None = None
    active: bool = True


class RetreatInventoryLocationUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    active: bool | None = None


class RetreatInventoryItemLocationInput(BaseModel):
    locationId: int = Field(gt=0)
    quantity: int = Field(default=0, ge=0)


class RetreatInventoryItemCreate(BaseModel):
    name: str = Field(min_length=1)
    barcode: str = Field(min_length=1)
    categoryId: int = Field(gt=0)
    # Deprecated legacy input, kept for backward compatibility.
    shelfLocation: str | None = None
    unit: str = Field(default="each", min_length=1)
    purchaseUrl: str | None = None
    brand: str | None = None
    description: str | None = None
    imageUrl: str | None = None
    active: bool = True
    locations: list[RetreatInventoryItemLocationInput] = Field(default_factory=list)


class RetreatInventoryItemUpdate(BaseModel):
    name: str | None = None
    barcode: str | None = None
    categoryId: int | None = Field(default=None, gt=0)
    # Deprecated legacy input, kept for backward compatibility.
    shelfLocation: str | None = None
    unit: str | None = None
    purchaseUrl: str | None = None
    brand: str | None = None
    description: str | None = None
    imageUrl: str | None = None
    active: bool | None = None
    locations: list[RetreatInventoryItemLocationInput] | None = None


class RetreatInventoryScanPayload(BaseModel):
    barcode: str = Field(min_length=1)
    transactionType: Literal["IN", "OUT", "ADJUSTMENT"] = "IN"
    quantity: int = 1
    reason: str | None = None
    locationId: int | None = Field(default=None, gt=0)


class ShoppingListGeneratePayload(BaseModel):
    retreatPlanId: int | None = Field(default=None, gt=0)
    retreatPlanIds: list[int] | None = None
    allRetreats: bool = False
    name: str | None = None
    phase: Literal["bulk", "fresh", "daily", "custom"] = "bulk"
    purchaseTiers: list[Literal["bulk", "fresh", "daily"]] | None = None
    profile: Literal["retreat", "test"] = "retreat"
    subtractInventory: bool = True
    includeZeroToBuy: bool = False


class ShoppingListItemUpdatePayload(BaseModel):
    vendorId: int | None = Field(default=None, ge=1)
    inStockQty: float | None = Field(default=None, ge=0)
    ordered: bool | None = None
    received: bool | None = None
    notes: str | None = None


class ShoppingListUpdatePayload(BaseModel):
    name: str = Field(min_length=1)


class ShoppingListCarryForwardPayload(BaseModel):
    name: str | None = None
    phase: Literal["bulk", "fresh", "daily", "custom"] | None = None


class ShoppingListSplitSelectedPayload(BaseModel):
    itemIds: list[int] = Field(min_length=1)
    name: str | None = None


class ShoppingListItemSplitPayload(BaseModel):
    buyNowPercent: float = Field(gt=0, lt=100)


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
    profile: Literal["retreat", "test"] | None = None


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    with get_connection() as conn:
        created = ensure_bootstrap_admin(conn)
        conn.commit()
    if created:
        print("Bootstrap admin user created from environment variables.")


def get_request_user(request: Request) -> AuthUser | None:
    candidate = getattr(request.state, "auth_user", None)
    if isinstance(candidate, AuthUser):
        return candidate
    return None


def require_authenticated_user(request: Request) -> AuthUser:
    user = get_request_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


def require_roles(*allowed_roles: str):
    normalized_allowed = {normalize_role(role) for role in allowed_roles}

    def dependency(user: Annotated[AuthUser, Depends(require_authenticated_user)]) -> AuthUser:
        if user.role not in normalized_allowed:
            raise HTTPException(
                status_code=403,
                detail=f"Requires one of roles: {', '.join(sorted(normalized_allowed))}",
            )
        return user

    return dependency


@app.middleware("http")
async def api_auth_middleware(request: Request, call_next):
    path = request.url.path
    if not path.startswith("/api"):
        return await call_next(request)

    if request.method == "OPTIONS" or path in PUBLIC_API_PATHS:
        return await call_next(request)

    if request.method in {"GET", "HEAD"}:
        if path in PUBLIC_API_GET_PATHS or any(path.startswith(prefix) for prefix in PUBLIC_API_GET_PREFIXES):
            return await call_next(request)

    raw_token = request.cookies.get(SESSION_COOKIE_NAME)
    if not raw_token:
        return JSONResponse(status_code=401, content={"detail": "Authentication required"})

    with get_connection() as conn:
        user = authenticate_session_token(conn, raw_token)
        conn.commit()

    if not user:
        return JSONResponse(status_code=401, content={"detail": "Session expired. Please log in again."})

    request.state.auth_user = user
    return await call_next(request)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/auth/bootstrap-status")
def auth_bootstrap_status() -> dict[str, Any]:
    with get_connection() as conn:
        configured = has_any_users(conn)
    return {
        "has_users": configured,
        "bootstrap_env_required": [BOOTSTRAP_ADMIN_USERNAME_ENV, BOOTSTRAP_ADMIN_PASSWORD_ENV],
    }


@app.post("/api/auth/login")
def login(payload: AuthLoginPayload, response: Response) -> dict[str, Any]:
    with get_connection() as conn:
        if not has_any_users(conn):
            raise HTTPException(
                status_code=503,
                detail=(
                    "No users configured. Set "
                    f"{BOOTSTRAP_ADMIN_USERNAME_ENV} and {BOOTSTRAP_ADMIN_PASSWORD_ENV}, "
                    "then restart the service."
                ),
            )
        user = authenticate_credentials(conn, payload.username, payload.password)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid username or password")
        token = create_session(conn, user.id)
        conn.commit()

    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=cookie_secure_enabled(),
        samesite="lax",
        path="/",
    )

    return {
        "id": user.id,
        "username": user.username,
        "role": user.role,
        "default_path": default_route_for_role(user.role),
    }


@app.post("/api/auth/logout")
def logout(request: Request, response: Response) -> dict[str, str]:
    raw_token = request.cookies.get(SESSION_COOKIE_NAME)
    with get_connection() as conn:
        delete_session(conn, raw_token)
        conn.commit()

    response.delete_cookie(SESSION_COOKIE_NAME, path="/")
    return {"status": "ok"}


@app.get("/api/auth/me")
def auth_me(request: Request) -> dict[str, Any]:
    user = require_authenticated_user(request)
    return {
        "id": user.id,
        "username": user.username,
        "role": user.role,
        "is_active": user.is_active,
        "default_path": default_route_for_role(user.role),
    }


@app.post("/api/auth/change-password")
def auth_change_password(
    payload: AuthChangePasswordPayload,
    request: Request,
    user: Annotated[AuthUser, Depends(require_authenticated_user)],
) -> dict[str, str]:
    if payload.current_password == payload.new_password:
        raise HTTPException(status_code=400, detail="New password must be different from current password.")

    with get_connection() as conn:
        verified = authenticate_credentials(conn, user.username, payload.current_password)
        if not verified or verified.id != user.id:
            raise HTTPException(status_code=400, detail="Current password is incorrect.")

        try:
            update_user(conn, user.id, password=payload.new_password)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        # Keep the current browser session and revoke other sessions for this user.
        raw_token = request.cookies.get(SESSION_COOKIE_NAME)
        if raw_token:
            token_hash = hash_session_token(raw_token)
            conn.execute(
                "DELETE FROM auth_sessions WHERE user_id = ? AND token_hash != ?",
                (user.id, token_hash),
            )
        else:
            conn.execute("DELETE FROM auth_sessions WHERE user_id = ?", (user.id,))

        conn.commit()

    return {"status": "ok"}


@app.get("/api/auth/users")
def auth_list_users(
    _user: Annotated[AuthUser, Depends(require_roles(ROLE_ADMIN))],
) -> list[dict[str, Any]]:
    with get_connection() as conn:
        return list_users(conn)


@app.post("/api/auth/users")
def auth_create_user(
    payload: AuthUserCreatePayload,
    _user: Annotated[AuthUser, Depends(require_roles(ROLE_ADMIN))],
) -> dict[str, Any]:
    with get_connection() as conn:
        try:
            created = create_user(
                conn,
                payload.username,
                payload.password,
                payload.role,
                is_active=payload.is_active,
            )
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Could not create user: {exc}") from exc
        conn.commit()
    return {
        "id": created.id,
        "username": created.username,
        "role": created.role,
        "is_active": created.is_active,
    }


@app.put("/api/auth/users/{user_id}")
def auth_update_user(
    user_id: int,
    payload: AuthUserUpdatePayload,
    request: Request,
    _user: Annotated[AuthUser, Depends(require_roles(ROLE_ADMIN))],
) -> Any:
    with get_connection() as conn:
        try:
            updated = update_user(
                conn,
                user_id,
                password=payload.password,
                role=payload.role,
                is_active=payload.is_active,
            )
            admins = conn.execute(
                "SELECT COUNT(*) AS admin_count FROM users WHERE role = 'admin' AND is_active = 1"
            ).fetchone()
            if admins and int(admins["admin_count"]) <= 0:
                conn.rollback()
                raise HTTPException(
                    status_code=400,
                    detail="Refusing to remove the last active admin user.",
                )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        conn.commit()

    current = get_request_user(request)
    if current and current.id == updated.id and not updated.is_active:
        response = JSONResponse(
            {
                "id": updated.id,
                "username": updated.username,
                "role": updated.role,
                "is_active": updated.is_active,
            }
        )
        response.delete_cookie(SESSION_COOKIE_NAME, path="/")
        return response

    return {
        "id": updated.id,
        "username": updated.username,
        "role": updated.role,
        "is_active": updated.is_active,
    }


@app.delete("/api/auth/users/{user_id}")
def auth_delete_user(
    user_id: int,
    request: Request,
    _user: Annotated[AuthUser, Depends(require_roles(ROLE_ADMIN))],
) -> Any:
    with get_connection() as conn:
        existing = conn.execute(
            "SELECT id, username, role, is_active FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="User not found")

        if existing["role"] == ROLE_ADMIN and bool(existing["is_active"]):
            admins = conn.execute(
                "SELECT COUNT(*) AS admin_count FROM users WHERE role = 'admin' AND is_active = 1"
            ).fetchone()
            if admins and int(admins["admin_count"]) <= 1:
                raise HTTPException(
                    status_code=400,
                    detail="Refusing to remove the last active admin user.",
                )

        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()

    deleted_payload = {
        "id": int(existing["id"]),
        "username": existing["username"],
        "role": existing["role"],
        "is_active": bool(existing["is_active"]),
    }

    current = get_request_user(request)
    if current and current.id == int(existing["id"]):
        response = JSONResponse({**deleted_payload, "self_deleted": True})
        response.delete_cookie(SESSION_COOKIE_NAME, path="/")
        return response

    return {**deleted_payload, "self_deleted": False}


def resolve_openai_api_base() -> str:
    configured = str(os.getenv(OPENAI_API_BASE_ENV, DEFAULT_OPENAI_API_BASE) or "").strip()
    if not configured:
        return DEFAULT_OPENAI_API_BASE
    return configured.rstrip("/")


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


def resolve_ingredient_duplicate_model(requested: str | None) -> str:
    candidate = str(requested or "").strip()
    if candidate:
        return candidate
    configured = str(os.getenv(OPENAI_INGREDIENT_DUP_MODEL_ENV, "") or "").strip()
    if not configured:
        configured = read_project_env_value(OPENAI_INGREDIENT_DUP_MODEL_ENV)
    if configured:
        return configured
    return DEFAULT_INGREDIENT_DUP_MODEL


def parse_float_confidence(value: object, default: float = 0.5) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = default
    if parsed < 0:
        return 0.0
    if parsed > 1:
        return 1.0
    return parsed


def normalize_duplicate_group_type(raw_type: object, confidence: float) -> str:
    value = str(raw_type or "").strip().lower().replace("-", "_").replace(" ", "_")
    strict_values = {"strict", "strict_duplicate", "exact_duplicate", "duplicate"}
    possible_values = {"possible", "possible_consolidation", "review", "candidate"}
    if value in strict_values:
        return "strict_duplicate"
    if value in possible_values:
        return "possible_consolidation"
    return "strict_duplicate" if confidence >= 0.82 else "possible_consolidation"


def normalize_llm_duplicate_groups(
    raw_groups: object,
    ingredient_by_id: dict[int, dict[str, Any]],
    max_groups: int,
) -> dict[str, list[dict[str, Any]]]:
    if not isinstance(raw_groups, list):
        return {
            "strict_duplicates": [],
            "possible_consolidations": [],
        }

    provisional: list[dict[str, Any]] = []
    seen_signatures: set[tuple[int, ...]] = set()

    for entry in raw_groups:
        if not isinstance(entry, dict):
            continue
        raw_member_ids = entry.get("member_ingredient_ids")
        if not isinstance(raw_member_ids, list):
            continue

        member_ids: list[int] = []
        for candidate in raw_member_ids:
            try:
                member_id = int(candidate)
            except (TypeError, ValueError):
                continue
            if member_id not in ingredient_by_id:
                continue
            if member_id not in member_ids:
                member_ids.append(member_id)
        if len(member_ids) < 2:
            continue

        canonical_raw = entry.get("canonical_ingredient_id")
        try:
            canonical_id = int(canonical_raw)
        except (TypeError, ValueError):
            canonical_id = member_ids[0]
        if canonical_id not in ingredient_by_id:
            canonical_id = member_ids[0]
        if canonical_id not in member_ids:
            member_ids = [canonical_id, *member_ids]
            member_ids = list(dict.fromkeys(member_ids))

        signature = tuple(sorted(member_ids))
        if signature in seen_signatures:
            continue
        seen_signatures.add(signature)

        reason_raw = entry.get("reason")
        reason = str(reason_raw).strip() if reason_raw is not None else ""
        confidence = parse_float_confidence(entry.get("confidence"), default=0.5)
        group_type = normalize_duplicate_group_type(entry.get("group_type"), confidence)
        provisional.append(
            {
                "canonical_id": canonical_id,
                "member_ids": member_ids,
                "confidence": confidence,
                "reason": reason,
                "group_type": group_type,
            }
        )

    strict_provisional = [
        group for group in provisional if group["group_type"] == "strict_duplicate"
    ]
    possible_provisional = [
        group for group in provisional if group["group_type"] == "possible_consolidation"
    ]
    strict_provisional.sort(key=lambda group: (-group["confidence"], -len(group["member_ids"]), group["canonical_id"]))
    possible_provisional.sort(key=lambda group: (-group["confidence"], -len(group["member_ids"]), group["canonical_id"]))

    used_member_ids: set[int] = set()
    strict_duplicates: list[dict[str, Any]] = []
    possible_consolidations: list[dict[str, Any]] = []

    def materialize(group: dict[str, Any], *, bucket: str) -> None:
        canonical = ingredient_by_id[group["canonical_id"]]
        members = [ingredient_by_id[member_id] for member_id in group["member_ids"]]
        payload = {
            "canonical": {
                "id": int(canonical["id"]),
                "name": canonical["name"],
            },
            "confidence": round(float(group["confidence"]), 3),
            "reason": group["reason"],
            "members": members,
            "group_type": bucket,
        }
        if bucket == "strict_duplicate":
            strict_duplicates.append(payload)
        else:
            possible_consolidations.append(payload)
        used_member_ids.update(group["member_ids"])

    for group in strict_provisional:
        if any(member_id in used_member_ids for member_id in group["member_ids"]):
            continue
        if len(strict_duplicates) + len(possible_consolidations) >= max_groups:
            break
        materialize(group, bucket="strict_duplicate")

    for group in possible_provisional:
        if any(member_id in used_member_ids for member_id in group["member_ids"]):
            continue
        if len(strict_duplicates) + len(possible_consolidations) >= max_groups:
            break
        materialize(group, bucket="possible_consolidation")

    return {
        "strict_duplicates": strict_duplicates,
        "possible_consolidations": possible_consolidations,
    }


def call_openai_for_ingredient_duplicates(
    *,
    model: str,
    ingredients: list[dict[str, Any]],
) -> dict[str, Any]:
    api_key = str(os.getenv(OPENAI_API_KEY_ENV, "") or "").strip()
    if not api_key:
        api_key = read_project_env_value(OPENAI_API_KEY_ENV)
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail=f"{OPENAI_API_KEY_ENV} is not configured on the backend.",
        )

    api_base = resolve_openai_api_base()
    endpoint = f"{api_base}/chat/completions"
    system_prompt = (
        "You are a strict ingredient-normalization assistant for a recipe database. "
        "Find likely duplicate ingredients using semantic understanding, including Hindi/English synonyms "
        "and transliteration variants (example: rajma vs kidney beans). "
        "Return two types of groups: strict duplicates and possible consolidations for manual review. "
        "A strict duplicate means the same ingredient with naming variants. "
        "A possible consolidation means likely same ingredient family/variant that may be merged with human review "
        "(example: spring onion vs green onion). "
        "Return JSON only with this exact shape: "
        "{"
        "\"groups\":["
        "{"
        "\"canonical_ingredient_id\":number,"
        "\"member_ingredient_ids\":[number,number],"
        "\"group_type\":\"strict_duplicate|possible_consolidation\","
        "\"confidence\":number,"
        "\"reason\":string"
        "}"
        "]"
        "}"
    )
    user_prompt = {
        "task": "Find duplicate ingredient groups.",
        "constraints": [
            "Each group must represent the same real-world ingredient.",
            "Each group must contain at least 2 IDs from the input list.",
            "Use the existing ingredient IDs only.",
            "Pick canonical_ingredient_id from member_ingredient_ids.",
            "Use group_type=strict_duplicate for clear exact synonyms/aliases only.",
            "Use group_type=possible_consolidation for likely merge candidates that need review.",
        ],
        "ingredients": ingredients,
    }
    payload = {
        "model": model,
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(user_prompt, ensure_ascii=True)},
        ],
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib_request.Request(
        endpoint,
        data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib_request.urlopen(req, timeout=90) as response:
            raw = response.read().decode("utf-8")
    except urllib_error.HTTPError as exc:
        body = ""
        try:
            body = exc.read().decode("utf-8")
        except Exception:
            body = ""
        detail = f"LLM request failed ({exc.code})."
        if body:
            detail = f"{detail} {body[:500]}"
        raise HTTPException(status_code=502, detail=detail) from exc
    except urllib_error.URLError as exc:
        raise HTTPException(status_code=502, detail=f"Could not reach LLM service: {exc.reason}") from exc

    try:
        parsed = json.loads(raw)
        content = parsed["choices"][0]["message"]["content"]
        if not isinstance(content, str) or not content.strip():
            raise ValueError("Missing model content")
        return json.loads(content)
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Invalid LLM duplicate response format.") from exc


@app.get("/api/ingredients")
def list_ingredients() -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, name, category, purchase_tier, canonical_unit, grams_per_cup, notes FROM ingredients ORDER BY name"
        ).fetchall()
    return [dict(r) for r in rows]


@app.post("/api/ingredients/find-duplicates")
def find_ingredient_duplicates(
    payload: IngredientDuplicateScanPayload,
    _user: Annotated[AuthUser, Depends(require_roles(ROLE_ADMIN))],
) -> dict[str, Any]:
    model = resolve_ingredient_duplicate_model(payload.model)
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                i.id,
                i.name,
                i.category,
                i.purchase_tier,
                i.canonical_unit,
                COUNT(ri.id) AS recipe_usage_count
            FROM ingredients i
            LEFT JOIN recipe_ingredients ri ON ri.ingredient_id = i.id
            GROUP BY i.id
            ORDER BY lower(i.name), i.id
            """
        ).fetchall()

    ingredients = [
        {
            "id": int(row["id"]),
            "name": row["name"],
            "category": row["category"],
            "purchase_tier": row["purchase_tier"],
            "canonical_unit": row["canonical_unit"],
            "recipe_usage_count": int(row["recipe_usage_count"] or 0),
        }
        for row in rows
    ]
    if len(ingredients) < 2:
        return {
            "model": model,
            "ingredient_count": len(ingredients),
            "groups": [],
        }

    llm_response = call_openai_for_ingredient_duplicates(
        model=model,
        ingredients=ingredients,
    )
    ingredient_by_id = {int(item["id"]): item for item in ingredients}
    grouped = normalize_llm_duplicate_groups(
        llm_response.get("groups"),
        ingredient_by_id=ingredient_by_id,
        max_groups=payload.max_groups,
    )
    strict_duplicates = grouped["strict_duplicates"]
    possible_consolidations = grouped["possible_consolidations"]
    return {
        "model": model,
        "ingredient_count": len(ingredients),
        "strict_duplicate_count": len(strict_duplicates),
        "possible_consolidation_count": len(possible_consolidations),
        "group_count": len(strict_duplicates) + len(possible_consolidations),
        "strict_duplicates": strict_duplicates,
        "possible_consolidations": possible_consolidations,
        # Backward compatibility for older frontend handlers.
        "groups": [*strict_duplicates, *possible_consolidations],
    }


PURCHASE_TIERS = ["bulk", "fresh", "daily"]


@app.get("/api/purchase-tiers")
def list_purchase_tiers() -> list[str]:
    return PURCHASE_TIERS


@app.get("/api/shopping-phases")
def list_shopping_phases() -> list[str]:
    return SHOPPING_PHASES


@app.get("/api/vendors")
def list_vendors() -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, name, notes FROM vendors ORDER BY name"
        ).fetchall()
    return [dict(row) for row in rows]


@app.get("/api/shopping-lists")
def list_shopping_lists(
    retreatPlanId: int | None = Query(default=None, ge=1),
    phase: str | None = Query(default=None),
) -> list[dict[str, Any]]:
    filters: list[str] = []
    params: list[Any] = []
    if retreatPlanId is not None:
        filters.append("sl.retreat_plan_id = ?")
        params.append(retreatPlanId)
    if phase and phase.strip():
        filters.append("lower(sl.phase) = lower(?)")
        params.append(phase.strip())

    where_sql = f"WHERE {' AND '.join(filters)}" if filters else ""

    with get_connection() as conn:
        rows = conn.execute(
            f"""
            SELECT
                sl.id,
                sl.name,
                sl.phase,
                sl.status,
                sl.created_at,
                sl.retreat_plan_id,
                rp.name AS retreat_plan_name,
                COUNT(sli.id) AS item_count,
                COALESCE(SUM(CASE WHEN COALESCE(sli.ordered, 0) = 1 THEN 1 ELSE 0 END), 0) AS ordered_count,
                COALESCE(SUM(CASE WHEN COALESCE(sli.received, 0) = 1 THEN 1 ELSE 0 END), 0) AS received_count
            FROM shopping_lists sl
            LEFT JOIN retreat_plans rp ON rp.id = sl.retreat_plan_id
            LEFT JOIN shopping_list_items sli ON sli.shopping_list_id = sl.id
            {where_sql}
            GROUP BY sl.id
            ORDER BY sl.id DESC
            """,
            tuple(params),
        ).fetchall()

    return [
        {
            "id": int(row["id"]),
            "name": row["name"],
            "phase": row["phase"] or "bulk",
            "status": row["status"] or "draft",
            "created_at": row["created_at"],
            "retreat_plan_id": int(row["retreat_plan_id"]) if row["retreat_plan_id"] is not None else None,
            "retreat_plan_name": row["retreat_plan_name"],
            "item_count": int(row["item_count"] or 0),
            "ordered_count": int(row["ordered_count"] or 0),
            "received_count": int(row["received_count"] or 0),
        }
        for row in rows
    ]


@app.get("/api/shopping-lists/{shopping_list_id}")
def get_shopping_list(shopping_list_id: int) -> dict[str, Any]:
    with get_connection() as conn:
        detail = load_shopping_list_detail(conn, shopping_list_id)
    return detail


@app.patch("/api/shopping-lists/{shopping_list_id}")
def rename_shopping_list(
    shopping_list_id: int,
    payload: ShoppingListUpdatePayload,
    _user: Annotated[AuthUser, Depends(require_roles(ROLE_PLANNER, ROLE_ADMIN))],
) -> dict[str, Any]:
    requested_name = " ".join(payload.name.strip().split())
    if not requested_name:
        raise HTTPException(status_code=400, detail="Shopping list name cannot be blank")

    with get_connection() as conn:
        existing = conn.execute(
            """
            SELECT id, name
            FROM shopping_lists
            WHERE id = ?
            """,
            (shopping_list_id,),
        ).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Shopping list not found")

        final_name = unique_shopping_list_name(
            conn,
            requested_name,
            exclude_shopping_list_id=shopping_list_id,
        )
        conn.execute(
            "UPDATE shopping_lists SET name = ? WHERE id = ?",
            (final_name, shopping_list_id),
        )
        detail = load_shopping_list_detail(conn, shopping_list_id)
        conn.commit()

    detail["renamed_from"] = existing["name"]
    return detail


@app.delete("/api/shopping-lists/{shopping_list_id}")
def delete_shopping_list(
    shopping_list_id: int,
    _user: Annotated[AuthUser, Depends(require_roles(ROLE_PLANNER, ROLE_ADMIN))],
) -> dict[str, Any]:
    with get_connection() as conn:
        existing = conn.execute(
            "SELECT id, name FROM shopping_lists WHERE id = ?",
            (shopping_list_id,),
        ).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Shopping list not found")

        conn.execute("DELETE FROM shopping_lists WHERE id = ?", (shopping_list_id,))
        conn.commit()

    return {
        "id": int(existing["id"]),
        "name": existing["name"],
        "status": "deleted",
    }


@app.post("/api/shopping-lists/generate")
def generate_shopping_list(
    payload: ShoppingListGeneratePayload,
    _user: Annotated[AuthUser, Depends(require_roles(ROLE_PLANNER, ROLE_ADMIN))],
) -> dict[str, Any]:
    purchase_tiers = resolve_purchase_tiers_for_shopping(payload.phase, payload.purchaseTiers)
    with get_connection() as conn:
        aggregate: dict[tuple[int, str], dict[str, Any]] = {}
        missing_recipes: set[str] = set()
        included_plan_ids: list[int] = []
        plan_dish_breakdown_by_plan_id: dict[int, dict[tuple[int, str], dict[str, float]]] = {}
        plan_name_by_id: dict[int, str] = {}
        retreat_plan_id_for_list: int | None = None

        if payload.allRetreats:
            plan_rows = conn.execute(
                """
                SELECT id, name, plan_json
                FROM retreat_plans
                ORDER BY id
                """
            ).fetchall()
            if not plan_rows:
                raise HTTPException(status_code=404, detail="No retreat plans found")

            for plan_row in plan_rows:
                try:
                    plan_payload = json.loads(plan_row["plan_json"]) if plan_row["plan_json"] else {}
                except json.JSONDecodeError as exc:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Retreat plan #{int(plan_row['id'])} payload is not valid JSON",
                    ) from exc
                if not isinstance(plan_payload, dict):
                    raise HTTPException(
                        status_code=400,
                        detail=f"Retreat plan #{int(plan_row['id'])} payload is malformed",
                    )

                plan_aggregate, plan_missing, plan_dish_breakdown = build_required_ingredients_from_plan(
                    conn,
                    plan_payload=plan_payload,
                    profile=payload.profile,
                    purchase_tiers=purchase_tiers,
                )
                if plan_aggregate:
                    plan_id = int(plan_row["id"])
                    merge_required_ingredient_aggregate(aggregate, plan_aggregate)
                    included_plan_ids.append(plan_id)
                    plan_dish_breakdown_by_plan_id[plan_id] = plan_dish_breakdown
                    plan_name_by_id[plan_id] = str(plan_row["name"] or f"Retreat #{plan_id}").strip() or f"Retreat #{plan_id}"
                missing_recipes.update(plan_missing)
        else:
            requested_plan_ids: list[int] = []
            if payload.retreatPlanIds:
                for raw_id in payload.retreatPlanIds:
                    plan_id = int(raw_id)
                    if plan_id <= 0:
                        raise HTTPException(status_code=400, detail="retreatPlanIds must contain positive integers")
                    requested_plan_ids.append(plan_id)

            if payload.retreatPlanId is not None:
                requested_plan_ids.append(int(payload.retreatPlanId))

            requested_plan_ids = sorted(set(requested_plan_ids))
            if not requested_plan_ids:
                raise HTTPException(
                    status_code=400,
                    detail="Select at least one retreat plan unless allRetreats=true",
                )

            placeholders = ",".join("?" for _ in requested_plan_ids)
            plan_rows = conn.execute(
                f"""
                SELECT id, name, plan_json
                FROM retreat_plans
                WHERE id IN ({placeholders})
                ORDER BY id
                """,
                tuple(requested_plan_ids),
            ).fetchall()
            found_ids = sorted(int(row["id"]) for row in plan_rows)
            if found_ids != requested_plan_ids:
                missing_ids = sorted(set(requested_plan_ids) - set(found_ids))
                raise HTTPException(
                    status_code=404,
                    detail=f"Retreat plan(s) not found: {', '.join(str(x) for x in missing_ids)}",
                )

            for plan_row in plan_rows:
                try:
                    plan_payload = json.loads(plan_row["plan_json"]) if plan_row["plan_json"] else {}
                except json.JSONDecodeError as exc:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Retreat plan #{int(plan_row['id'])} payload is not valid JSON",
                    ) from exc
                if not isinstance(plan_payload, dict):
                    raise HTTPException(
                        status_code=400,
                        detail=f"Retreat plan #{int(plan_row['id'])} payload is malformed",
                    )

                plan_aggregate, plan_missing, plan_dish_breakdown = build_required_ingredients_from_plan(
                    conn,
                    plan_payload=plan_payload,
                    profile=payload.profile,
                    purchase_tiers=purchase_tiers,
                )
                if plan_aggregate:
                    plan_id = int(plan_row["id"])
                    merge_required_ingredient_aggregate(aggregate, plan_aggregate)
                    included_plan_ids.append(plan_id)
                    plan_dish_breakdown_by_plan_id[plan_id] = plan_dish_breakdown
                    plan_name_by_id[plan_id] = str(plan_row["name"] or f"Retreat #{plan_id}").strip() or f"Retreat #{plan_id}"
                missing_recipes.update(plan_missing)

            if len(requested_plan_ids) == 1:
                retreat_plan_id_for_list = requested_plan_ids[0]

        if not aggregate:
            raise HTTPException(
                status_code=400,
                detail="No ingredients found for this profile and tier filter.",
            )

        inventory_by_key = (
            load_inventory_canonical_by_key(conn)
            if payload.subtractInventory
            else {}
        )

        label = payload.name.strip() if payload.name and payload.name.strip() else None
        if not label:
            if payload.allRetreats:
                label = f"All Retreats - {payload.phase.title()} Order"
            else:
                if len(included_plan_ids) == 1:
                    plan_id_for_label = included_plan_ids[0]
                    plan_name_row = conn.execute(
                        "SELECT name FROM retreat_plans WHERE id = ?",
                        (plan_id_for_label,),
                    ).fetchone()
                    plan_name = plan_name_row["name"] if plan_name_row else "Retreat"
                    label = f"{plan_name} - {payload.phase.title()} Order"
                else:
                    label = f"Selected Retreats - {payload.phase.title()} Order"
        label = unique_shopping_list_name(conn, label)

        created = conn.execute(
            """
            INSERT INTO shopping_lists(retreat_plan_id, name, phase, status)
            VALUES (?, ?, ?, 'draft')
            RETURNING id
            """,
            (retreat_plan_id_for_list, label, payload.phase),
        ).fetchone()
        shopping_list_id = int(created["id"])

        inserted_items = 0
        ingredient_category_by_id: dict[int, str | None] = {}
        ingredient_ids = sorted({int(entry["ingredient_id"]) for entry in aggregate.values()})
        if ingredient_ids:
            placeholders = ",".join("?" for _ in ingredient_ids)
            category_rows = conn.execute(
                f"SELECT id, category FROM ingredients WHERE id IN ({placeholders})",
                tuple(ingredient_ids),
            ).fetchall()
            ingredient_category_by_id = {
                int(row["id"]): (str(row["category"] or "").strip() or None)
                for row in category_rows
            }

        for key, entry in sorted(
            aggregate.items(),
            key=lambda item: item[1]["ingredient_name"].lower(),
        ):
            ingredient_id, canonical_unit = key
            required_canonical = float(entry["required_qty"])
            in_stock_canonical = float(inventory_by_key.get(key, 0.0))
            to_buy_canonical = max(required_canonical - in_stock_canonical, 0.0)
            if not payload.includeZeroToBuy and to_buy_canonical <= 0:
                continue

            ingredient_category = ingredient_category_by_id.get(int(ingredient_id))
            if canonical_unit == "g" and is_spice_or_seasoning_category(ingredient_category):
                row_unit = "g"
            elif canonical_unit == "g" and is_produce_category(ingredient_category):
                # Keep produce in kilograms in shopping lists for consistency.
                row_unit = "kg"
            else:
                row_unit = preferred_metric_unit(required_canonical, canonical_unit)
            required_qty = canonical_qty_to_unit(required_canonical, canonical_unit, row_unit)
            in_stock_qty = canonical_qty_to_unit(in_stock_canonical, canonical_unit, row_unit)
            to_buy_qty = canonical_qty_to_unit(to_buy_canonical, canonical_unit, row_unit)
            required_unit = row_unit
            in_stock_unit = row_unit
            to_buy_unit = row_unit

            created_item = conn.execute(
                """
                INSERT INTO shopping_list_items(
                    shopping_list_id,
                    ingredient_id,
                    required_qty,
                    required_unit,
                    in_stock_qty,
                    in_stock_unit,
                    to_buy_qty,
                    to_buy_unit,
                    status,
                    ordered,
                    received
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'open', 0, 0)
                RETURNING id
                """,
                (
                    shopping_list_id,
                    ingredient_id,
                    round(required_qty, 4),
                    required_unit,
                    round(in_stock_qty, 4),
                    in_stock_unit,
                    round(to_buy_qty, 4),
                    to_buy_unit,
                ),
            ).fetchone()
            shopping_list_item_id = int(created_item["id"])

            for plan_id, plan_dish_breakdown in plan_dish_breakdown_by_plan_id.items():
                dish_required_by_name = plan_dish_breakdown.get(key) or {}
                if not dish_required_by_name:
                    continue

                for dish_name, dish_required_canonical in sorted(
                    dish_required_by_name.items(),
                    key=lambda item: item[0].lower(),
                ):
                    if dish_required_canonical <= 0:
                        continue
                    dish_required_qty = canonical_qty_to_unit(
                        float(dish_required_canonical),
                        canonical_unit,
                        row_unit,
                    )
                    conn.execute(
                        """
                        INSERT INTO shopping_list_item_sources(
                            shopping_list_item_id,
                            retreat_plan_id,
                            retreat_plan_name,
                            dish_name,
                            required_qty,
                            required_unit
                        )
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            shopping_list_item_id,
                            plan_id,
                            plan_name_by_id.get(plan_id) or f"Retreat #{plan_id}",
                            dish_name,
                            round(dish_required_qty, 4),
                            row_unit,
                        ),
                    )
            inserted_items += 1

        if inserted_items <= 0:
            conn.execute("DELETE FROM shopping_lists WHERE id = ?", (shopping_list_id,))
            raise HTTPException(
                status_code=400,
                detail="All filtered ingredients are already fully covered by inventory.",
            )

        refresh_shopping_list_status(conn, shopping_list_id)
        detail = load_shopping_list_detail(conn, shopping_list_id)
        conn.commit()

    detail["missing_recipes"] = sorted(missing_recipes)
    detail["source_retreat_plan_ids"] = sorted(included_plan_ids)
    detail["source_retreat_plan_count"] = len(included_plan_ids)
    return detail


@app.post("/api/shopping-lists/{shopping_list_id}/carry-forward")
def carry_forward_shopping_list(
    shopping_list_id: int,
    _user: Annotated[AuthUser, Depends(require_roles(ROLE_PLANNER, ROLE_ADMIN))],
    payload: ShoppingListCarryForwardPayload | None = None,
) -> dict[str, Any]:
    name_override = payload.name if payload else None
    phase_override = payload.phase if payload else None
    with get_connection() as conn:
        detail = create_carry_forward_shopping_list(
            conn,
            source_list_id=shopping_list_id,
            name_override=name_override,
            phase_override=phase_override,
        )
        conn.commit()
    return detail


@app.post("/api/shopping-lists/{shopping_list_id}/split-selected")
def split_selected_shopping_list(
    shopping_list_id: int,
    payload: ShoppingListSplitSelectedPayload,
    _user: Annotated[AuthUser, Depends(require_roles(ROLE_PLANNER, ROLE_ADMIN))],
) -> dict[str, Any]:
    selected_item_ids = sorted({int(raw_id) for raw_id in payload.itemIds if int(raw_id) > 0})
    if not selected_item_ids:
        raise HTTPException(status_code=400, detail="itemIds must contain positive integers")

    with get_connection() as conn:
        result = split_selected_shopping_list_items(
            conn,
            source_list_id=shopping_list_id,
            selected_item_ids=selected_item_ids,
            name_override=payload.name,
        )
        conn.commit()

    return result


@app.post("/api/shopping-lists/{shopping_list_id}/apply-inventory")
def apply_shopping_list_inventory(
    shopping_list_id: int,
    _user: Annotated[AuthUser, Depends(require_roles(ROLE_PLANNER, ROLE_ADMIN))],
) -> dict[str, Any]:
    with get_connection() as conn:
        list_row = conn.execute(
            """
            SELECT id, name, phase
            FROM shopping_lists
            WHERE id = ?
            """,
            (shopping_list_id,),
        ).fetchone()
        if not list_row:
            raise HTTPException(status_code=404, detail="Shopping list not found")

        phase = str(list_row["phase"] or "").strip().lower()
        if phase not in {"fresh", "daily"}:
            raise HTTPException(
                status_code=400,
                detail="Apply to inventory is enabled only for fresh and daily shopping lists.",
            )

        rows = conn.execute(
            """
            SELECT ingredient_id, in_stock_qty, in_stock_unit, required_unit
            FROM shopping_list_items
            WHERE shopping_list_id = ?
            """,
            (shopping_list_id,),
        ).fetchall()

        ingredient_ids = sorted({int(row["ingredient_id"]) for row in rows})
        if ingredient_ids:
            placeholders = ",".join("?" for _ in ingredient_ids)
            conn.execute(
                f"DELETE FROM inventory_items WHERE source = ? AND ingredient_id IN ({placeholders})",
                (MANUAL_INVENTORY_SOURCE, *ingredient_ids),
            )

        applied_count = 0
        for row in rows:
            qty = float(row["in_stock_qty"] or 0.0)
            unit = normalize_unit(str(row["in_stock_unit"] or row["required_unit"] or "").strip())
            if qty <= 0 or not unit:
                continue
            conn.execute(
                """
                INSERT INTO inventory_items(ingredient_id, quantity, unit, source, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (
                    int(row["ingredient_id"]),
                    round(qty, 4),
                    unit,
                    MANUAL_INVENTORY_SOURCE,
                ),
            )
            applied_count += 1

        conn.commit()

    return {
        "status": "ok",
        "shopping_list_id": shopping_list_id,
        "shopping_list_name": list_row["name"],
        "phase": phase,
        "inventory_source": MANUAL_INVENTORY_SOURCE,
        "applied_count": applied_count,
    }


@app.patch("/api/shopping-lists/{shopping_list_id}/items/{item_id}")
def update_shopping_list_item(
    shopping_list_id: int,
    item_id: int,
    payload: ShoppingListItemUpdatePayload,
    _user: Annotated[AuthUser, Depends(require_roles(ROLE_PLANNER, ROLE_ADMIN))],
) -> dict[str, Any]:
    fields = payload.model_fields_set
    if not fields:
        raise HTTPException(status_code=400, detail="No fields supplied")

    with get_connection() as conn:
        item_row = conn.execute(
            """
            SELECT
                sli.id,
                sli.shopping_list_id,
                sli.required_qty,
                sli.required_unit,
                sli.in_stock_qty,
                sli.in_stock_unit,
                sli.to_buy_unit,
                sli.vendor_id,
                sli.ordered,
                sli.ordered_at,
                sli.received,
                sli.received_at,
                sli.notes,
                sl.phase
            FROM shopping_list_items sli
            JOIN shopping_lists sl ON sl.id = sli.shopping_list_id
            WHERE sli.id = ? AND sli.shopping_list_id = ?
            """,
            (item_id, shopping_list_id),
        ).fetchone()
        if not item_row:
            raise HTTPException(status_code=404, detail="Shopping list item not found")

        required_qty = float(item_row["required_qty"] or 0.0)
        required_unit = normalize_unit(str(item_row["required_unit"] or "").strip())
        in_stock_unit = normalize_unit(str(item_row["in_stock_unit"] or required_unit).strip() or required_unit)
        to_buy_unit = normalize_unit(str(item_row["to_buy_unit"] or required_unit).strip() or required_unit)
        in_stock_qty = float(item_row["in_stock_qty"] or 0.0)
        if "inStockQty" in fields:
            list_phase = str(item_row["phase"] or "").strip().lower()
            if list_phase not in {"fresh", "daily"}:
                raise HTTPException(
                    status_code=400,
                    detail="Current inventory can be edited only for fresh and daily shopping lists.",
                )
            in_stock_qty = float(payload.inStockQty or 0.0)
        required_canonical_qty, required_canonical_unit = quantity_to_canonical(required_qty, required_unit)
        in_stock_canonical_qty, in_stock_canonical_unit = quantity_to_canonical(in_stock_qty, in_stock_unit)
        if required_canonical_qty is not None and required_canonical_unit == in_stock_canonical_unit:
            to_buy_canonical_qty = max(required_canonical_qty - (in_stock_canonical_qty or 0.0), 0.0)
            converted = canonical_qty_to_unit_or_none(to_buy_canonical_qty, required_canonical_unit, required_unit)
            to_buy_qty = converted if converted is not None else max(required_qty - in_stock_qty, 0.0)
        else:
            to_buy_qty = max(required_qty - in_stock_qty, 0.0)
        in_stock_unit = required_unit
        to_buy_unit = required_unit

        vendor_id = item_row["vendor_id"]
        if "vendorId" in fields:
            vendor_id = payload.vendorId
            if vendor_id is not None:
                vendor_exists = conn.execute(
                    "SELECT id FROM vendors WHERE id = ?",
                    (vendor_id,),
                ).fetchone()
                if not vendor_exists:
                    raise HTTPException(status_code=400, detail="Vendor not found")

        ordered = bool(item_row["ordered"])
        received = bool(item_row["received"])

        if "ordered" in fields:
            ordered = bool(payload.ordered)
            if not ordered:
                received = False

        if "received" in fields:
            received = bool(payload.received)
            if received:
                ordered = True

        now_iso = datetime.now(timezone.utc).isoformat()
        ordered_at = item_row["ordered_at"]
        received_at = item_row["received_at"]

        if ordered and not bool(item_row["ordered"]):
            ordered_at = now_iso
        if not ordered:
            ordered_at = None

        if received and not bool(item_row["received"]):
            received_at = now_iso
        if not received:
            received_at = None

        notes = item_row["notes"]
        if "notes" in fields:
            notes = payload.notes.strip() if payload.notes and payload.notes.strip() else None

        status = derive_shopping_item_status(ordered=ordered, received=received)
        conn.execute(
            """
            UPDATE shopping_list_items
            SET vendor_id = ?,
                in_stock_qty = ?,
                in_stock_unit = ?,
                to_buy_qty = ?,
                to_buy_unit = ?,
                ordered = ?,
                ordered_at = ?,
                received = ?,
                received_at = ?,
                status = ?,
                notes = ?
            WHERE id = ? AND shopping_list_id = ?
            """,
            (
                vendor_id,
                round(in_stock_qty, 4),
                in_stock_unit,
                round(to_buy_qty, 4),
                to_buy_unit,
                1 if ordered else 0,
                ordered_at,
                1 if received else 0,
                received_at,
                status,
                notes,
                item_id,
                shopping_list_id,
            ),
        )

        refresh_shopping_list_status(conn, shopping_list_id)
        detail = load_shopping_list_detail(conn, shopping_list_id)
        conn.commit()
    return detail


@app.post("/api/shopping-lists/{shopping_list_id}/items/{item_id}/split")
def split_shopping_list_item_partial_buy(
    shopping_list_id: int,
    item_id: int,
    payload: ShoppingListItemSplitPayload,
    _user: Annotated[AuthUser, Depends(require_roles(ROLE_PLANNER, ROLE_ADMIN))],
) -> dict[str, Any]:
    buy_now_percent = float(payload.buyNowPercent)
    if buy_now_percent <= 0 or buy_now_percent >= 100:
        raise HTTPException(status_code=400, detail="buyNowPercent must be between 0 and 100.")

    buy_later_percent = 100.0 - buy_now_percent
    now_ratio = buy_now_percent / 100.0

    def split_amount(total: float) -> tuple[float, float]:
        total_value = float(total or 0.0)
        now_value = round(total_value * now_ratio, 4)
        later_value = round(total_value - now_value, 4)
        return now_value, later_value

    with get_connection() as conn:
        item_row = conn.execute(
            """
            SELECT
                sli.id,
                sli.shopping_list_id,
                sli.ingredient_id,
                sli.required_qty,
                sli.required_unit,
                sli.in_stock_qty,
                sli.in_stock_unit,
                sli.to_buy_qty,
                sli.to_buy_unit,
                sli.vendor_id,
                sli.owner,
                sli.pickup_date,
                sli.ordered,
                sli.received,
                sli.notes
            FROM shopping_list_items sli
            WHERE sli.id = ? AND sli.shopping_list_id = ?
            """,
            (item_id, shopping_list_id),
        ).fetchone()
        if not item_row:
            raise HTTPException(status_code=404, detail="Shopping list item not found")

        if bool(item_row["ordered"]) or bool(item_row["received"]):
            raise HTTPException(
                status_code=400,
                detail="Cannot split items that are already marked ordered or received.",
            )

        required_qty = float(item_row["required_qty"] or 0.0)
        in_stock_qty = float(item_row["in_stock_qty"] or 0.0)
        to_buy_qty = float(item_row["to_buy_qty"] or 0.0)
        if to_buy_qty <= 0:
            raise HTTPException(status_code=400, detail="Only items with quantity to buy can be split.")

        required_now, required_later = split_amount(required_qty)
        in_stock_now, in_stock_later = split_amount(in_stock_qty)
        to_buy_now, to_buy_later = split_amount(to_buy_qty)
        if to_buy_now <= 0 or to_buy_later <= 0:
            raise HTTPException(
                status_code=400,
                detail="Split percentage is too extreme for this quantity. Try a value closer to 50.",
            )

        required_unit = str(item_row["required_unit"] or "").strip()
        in_stock_unit = str(item_row["in_stock_unit"] or required_unit).strip() or required_unit
        to_buy_unit = str(item_row["to_buy_unit"] or required_unit).strip() or required_unit
        vendor_id = int(item_row["vendor_id"]) if item_row["vendor_id"] is not None else None
        owner = str(item_row["owner"] or "").strip() or None
        pickup_date = str(item_row["pickup_date"] or "").strip() or None
        existing_notes = str(item_row["notes"] or "").strip() or None

        now_note = partial_buy_note("Now", buy_now_percent, existing_notes)
        later_note = partial_buy_note("Later", buy_later_percent, existing_notes)

        created_later = conn.execute(
            """
            INSERT INTO shopping_list_items(
                shopping_list_id,
                ingredient_id,
                required_qty,
                required_unit,
                in_stock_qty,
                in_stock_unit,
                to_buy_qty,
                to_buy_unit,
                vendor_id,
                owner,
                pickup_date,
                ordered,
                ordered_at,
                received,
                received_at,
                status,
                notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, NULL, 0, NULL, 'open', ?)
            RETURNING id
            """,
            (
                shopping_list_id,
                int(item_row["ingredient_id"]),
                required_later,
                required_unit,
                in_stock_later,
                in_stock_unit,
                to_buy_later,
                to_buy_unit,
                vendor_id,
                owner,
                pickup_date,
                later_note,
            ),
        ).fetchone()
        later_item_id = int(created_later["id"])

        conn.execute(
            """
            UPDATE shopping_list_items
            SET required_qty = ?,
                required_unit = ?,
                in_stock_qty = ?,
                in_stock_unit = ?,
                to_buy_qty = ?,
                to_buy_unit = ?,
                ordered = 0,
                ordered_at = NULL,
                received = 0,
                received_at = NULL,
                status = 'open',
                notes = ?
            WHERE id = ? AND shopping_list_id = ?
            """,
            (
                required_now,
                required_unit,
                in_stock_now,
                in_stock_unit,
                to_buy_now,
                to_buy_unit,
                now_note,
                item_id,
                shopping_list_id,
            ),
        )

        source_rows = conn.execute(
            """
            SELECT
                id,
                retreat_plan_id,
                retreat_plan_name,
                dish_name,
                required_qty,
                required_unit
            FROM shopping_list_item_sources
            WHERE shopping_list_item_id = ?
            ORDER BY id
            """,
            (item_id,),
        ).fetchall()
        for source_row in source_rows:
            source_required_now, source_required_later = split_amount(float(source_row["required_qty"] or 0.0))
            if source_required_now > 0:
                conn.execute(
                    """
                    UPDATE shopping_list_item_sources
                    SET required_qty = ?
                    WHERE id = ?
                    """,
                    (source_required_now, int(source_row["id"])),
                )
            else:
                conn.execute(
                    "DELETE FROM shopping_list_item_sources WHERE id = ?",
                    (int(source_row["id"]),),
                )

            if source_required_later > 0:
                conn.execute(
                    """
                    INSERT INTO shopping_list_item_sources(
                        shopping_list_item_id,
                        retreat_plan_id,
                        retreat_plan_name,
                        dish_name,
                        required_qty,
                        required_unit
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        later_item_id,
                        int(source_row["retreat_plan_id"]) if source_row["retreat_plan_id"] is not None else None,
                        str(source_row["retreat_plan_name"] or "").strip() or "Unknown retreat",
                        str(source_row["dish_name"] or "").strip() or None,
                        source_required_later,
                        str(source_row["required_unit"] or "").strip(),
                    ),
                )

        refresh_shopping_list_status(conn, shopping_list_id)
        detail = load_shopping_list_detail(conn, shopping_list_id)
        detail["split_result"] = {
            "source_item_id": int(item_id),
            "later_item_id": later_item_id,
            "buy_now_percent": round(buy_now_percent, 2),
            "buy_later_percent": round(buy_later_percent, 2),
        }
        conn.commit()
    return detail


@app.put("/api/ingredients/{ingredient_id}")
def update_ingredient(
    ingredient_id: int,
    payload: IngredientUpdatePayload,
    _user: Annotated[AuthUser, Depends(require_roles(ROLE_ADMIN))],
) -> dict[str, Any]:
    ingredient_name = payload.name.strip()
    if not ingredient_name:
        raise HTTPException(status_code=400, detail="Ingredient name cannot be blank")

    canonical_unit = payload.canonical_unit.strip() if payload.canonical_unit and payload.canonical_unit.strip() else None
    notes = payload.notes.strip() if payload.notes and payload.notes.strip() else None
    category = payload.category.strip() if payload.category and payload.category.strip() else None
    purchase_tier = payload.purchase_tier.strip() if payload.purchase_tier and payload.purchase_tier.strip() else None

    with get_connection() as conn:
        existing = conn.execute("SELECT id FROM ingredients WHERE id = ?", (ingredient_id,)).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Ingredient not found")

        duplicate = conn.execute(
            "SELECT id FROM ingredients WHERE lower(name) = lower(?) AND id != ?",
            (ingredient_name, ingredient_id),
        ).fetchone()
        if duplicate:
            raise HTTPException(status_code=400, detail=f"An ingredient named '{ingredient_name}' already exists")

        conn.execute(
            """
            UPDATE ingredients
            SET name = ?, canonical_unit = ?, grams_per_cup = ?, notes = ?, category = ?, purchase_tier = ?
            WHERE id = ?
            """,
            (ingredient_name, canonical_unit, payload.grams_per_cup, notes, category, purchase_tier, ingredient_id),
        )
        updated = conn.execute(
            "SELECT id, name, category, purchase_tier, canonical_unit, grams_per_cup, notes FROM ingredients WHERE id = ?",
            (ingredient_id,),
        ).fetchone()
        conn.commit()

    return dict(updated)


@app.get("/api/unit-conversions")
def list_unit_conversions() -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                id,
                item_name,
                quantity_from,
                unit_from,
                quantity_to,
                unit_to,
                context,
                source_sheet,
                source_row,
                notes
            FROM unit_conversions
            ORDER BY context, item_name, unit_from, id
            """
        ).fetchall()
    return [
        {
            "id": int(row["id"]),
            "item_name": row["item_name"],
            "quantity_from": float(row["quantity_from"]),
            "unit_from": row["unit_from"],
            "quantity_to": float(row["quantity_to"]),
            "unit_to": row["unit_to"],
            "context": row["context"],
            "source_sheet": row["source_sheet"],
            "source_row": row["source_row"],
            "notes": row["notes"],
        }
        for row in rows
    ]


@app.get("/api/recipe-categories")
def list_recipe_categories() -> list[str]:
    return RECIPE_CATEGORIES


@app.post("/api/recipes")
def create_recipe(
    payload: RecipeCreate,
    _user: Annotated[AuthUser, Depends(require_roles(ROLE_ADMIN))],
) -> dict[str, Any]:
    recipe_name = payload.name.strip()
    if not recipe_name:
        raise HTTPException(status_code=400, detail="Recipe name cannot be blank")
    recipe_category = normalize_recipe_category(payload.category)
    recipe_notes = payload.notes.strip() if payload.notes and payload.notes.strip() else None

    with get_connection() as conn:
        try:
            recipe_row = conn.execute(
                """
                INSERT INTO recipes(name, category, base_servings, notes)
                VALUES (?, ?, ?, ?)
                RETURNING id, name, category, base_servings, notes
                """,
                (recipe_name, recipe_category, payload.base_servings, recipe_notes),
            ).fetchone()
            recipe_id = int(recipe_row["id"])
            replace_recipe_ingredients(conn, recipe_id, payload.ingredients)
            replace_recipe_steps(conn, recipe_id, payload.steps)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Could not create recipe: {exc}") from exc

        conn.commit()

    return {
        "id": recipe_row["id"],
        "name": recipe_row["name"],
        "category": recipe_row["category"],
        "base_servings": recipe_row["base_servings"],
        "notes": recipe_row["notes"],
    }


@app.put("/api/recipes/{recipe_id}")
def update_recipe(
    recipe_id: int,
    payload: RecipeCreate,
    _user: Annotated[AuthUser, Depends(require_roles(ROLE_ADMIN))],
) -> dict[str, Any]:
    recipe_name = payload.name.strip()
    if not recipe_name:
        raise HTTPException(status_code=400, detail="Recipe name cannot be blank")
    recipe_category = normalize_recipe_category(payload.category)
    recipe_notes = payload.notes.strip() if payload.notes and payload.notes.strip() else None

    with get_connection() as conn:
        existing = conn.execute("SELECT id FROM recipes WHERE id = ?", (recipe_id,)).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Recipe not found")

        try:
            conn.execute(
                """
                UPDATE recipes
                SET name = ?, category = ?, base_servings = ?, notes = ?
                WHERE id = ?
                """,
                (recipe_name, recipe_category, payload.base_servings, recipe_notes, recipe_id),
            )
            replace_recipe_ingredients(conn, recipe_id, payload.ingredients)
            replace_recipe_steps(conn, recipe_id, payload.steps)
            updated = conn.execute(
                "SELECT id, name, category, base_servings, notes FROM recipes WHERE id = ?",
                (recipe_id,),
            ).fetchone()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Could not update recipe: {exc}") from exc

        conn.commit()

    return {
        "id": int(updated["id"]),
        "name": updated["name"],
        "category": updated["category"],
        "base_servings": float(updated["base_servings"]),
        "notes": updated["notes"],
    }


@app.get("/api/recipes")
def list_recipes() -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, name, category, base_servings, notes, created_at
            FROM recipes
            ORDER BY created_at DESC
            """
        ).fetchall()
    return [dict(r) for r in rows]


@app.get("/api/recipes/full")
def list_recipes_full() -> list[dict[str, Any]]:
    with get_connection() as conn:
        recipes = conn.execute(
            """
            SELECT id, name, category, base_servings, notes, created_at
            FROM recipes
            ORDER BY name
            """
        ).fetchall()

        ingredient_rows = conn.execute(
            """
            SELECT
                ri.recipe_id,
                i.name AS ingredient_name,
                ri.quantity,
                ri.unit,
                ri.prep_notes,
                i.category AS ingredient_category,
                i.grams_per_cup,
                i.canonical_unit AS ingredient_canonical_unit
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
        entry: dict[str, Any] = {
            "name": row["ingredient_name"],
            "quantity": float(row["quantity"]),
            "unit": row["unit"],
            "prep_notes": row["prep_notes"],
        }
        if row["ingredient_category"]:
            entry["category"] = row["ingredient_category"]
        if row["grams_per_cup"]:
            entry["grams_per_cup"] = float(row["grams_per_cup"])
        if row["ingredient_canonical_unit"]:
            entry["canonical_unit"] = normalize_unit(str(row["ingredient_canonical_unit"]))
        ingredients_by_recipe.setdefault(recipe_id, []).append(entry)

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
                "category": recipe["category"],
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
        canonical_qty, canonical_unit, note = require_canonical_conversion(
            item.name,
            scaled_qty,
            unit,
            context="Scale preview conversion failed",
        )
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

    retreat_meals = payload.get("retreatMeals")
    if not isinstance(retreat_meals, list):
        retreat_meals = payload.get("meals") if isinstance(payload.get("meals"), list) else []

    test_meals = payload.get("testMeals")
    if not isinstance(test_meals, list):
        test_meals = []

    default_people = float(payload.get("defaultPeople") or row["default_people"])
    retreat_default_people = float(payload.get("retreatDefaultPeople") or default_people)
    test_default_people = float(payload.get("testDefaultPeople") or DEFAULT_TEST_HEADCOUNT)

    active_profile = payload.get("activeProfile")
    if active_profile not in HEADCOUNT_PROFILES:
        active_profile = "retreat"

    shopping_profile = payload.get("shoppingProfile")
    if shopping_profile not in HEADCOUNT_PROFILES:
        shopping_profile = DEFAULT_SHOPPING_PROFILE

    payload["id"] = int(row["id"])
    payload["name"] = payload.get("name") or row["name"]
    payload["startDate"] = payload.get("startDate", row["start_date"])
    payload["dayCount"] = int(payload.get("dayCount") or row["day_count"])
    payload["defaultPeople"] = default_people
    payload["retreatDefaultPeople"] = retreat_default_people
    payload["testDefaultPeople"] = test_default_people
    payload["activeProfile"] = active_profile
    payload["shoppingProfile"] = shopping_profile
    payload["retreatMeals"] = retreat_meals
    payload["testMeals"] = test_meals
    payload["meals"] = retreat_meals
    payload["created_at"] = row["created_at"]
    payload["updated_at"] = row["updated_at"]
    return payload


@app.post("/api/retreat-plans")
def upsert_retreat_plan(
    payload: RetreatPlanPayload,
    _user: Annotated[AuthUser, Depends(require_roles(ROLE_PLANNER, ROLE_ADMIN))],
) -> dict[str, Any]:
    plan_name = payload.name.strip()
    if not plan_name:
        raise HTTPException(status_code=400, detail="Retreat name cannot be blank")
    requested_plan_id = int(payload.id) if payload.id else None

    retreat_meals = payload.retreatMeals if payload.retreatMeals is not None else payload.meals
    test_meals = payload.testMeals if payload.testMeals is not None else []
    meal_lists = [payload.meals, retreat_meals, test_meals]
    if any(meal.day > payload.dayCount for meal_list in meal_lists for meal in meal_list):
        raise HTTPException(status_code=400, detail="Meal day cannot exceed dayCount")

    payload_dict = payload.model_dump()
    payload_dict.pop("id", None)
    payload_dict["name"] = plan_name
    payload_dict["defaultPeople"] = float(payload.defaultPeople)
    payload_dict["retreatDefaultPeople"] = float(payload.retreatDefaultPeople or payload.defaultPeople)
    payload_dict["testDefaultPeople"] = float(payload.testDefaultPeople)
    payload_dict["activeProfile"] = payload.activeProfile
    payload_dict["shoppingProfile"] = DEFAULT_SHOPPING_PROFILE
    payload_dict["retreatMeals"] = [meal.model_dump() for meal in retreat_meals]
    payload_dict["testMeals"] = [meal.model_dump() for meal in test_meals]
    payload_dict["meals"] = [meal.model_dump() for meal in retreat_meals]
    payload_json = json.dumps(payload_dict)

    with get_connection() as conn:
        if requested_plan_id:
            existing = conn.execute(
                "SELECT id FROM retreat_plans WHERE id = ?",
                (requested_plan_id,),
            ).fetchone()
            if not existing:
                raise HTTPException(status_code=404, detail="Retreat plan not found")

            name_conflict = conn.execute(
                "SELECT id FROM retreat_plans WHERE lower(name) = lower(?) AND id <> ?",
                (plan_name, requested_plan_id),
            ).fetchone()
            if name_conflict:
                raise HTTPException(status_code=409, detail="Retreat name already exists")

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
                    payload_dict["defaultPeople"],
                    payload_json,
                    requested_plan_id,
                ),
            )
            plan_id = requested_plan_id
            action = "updated"
        else:
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
                        payload_dict["defaultPeople"],
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
                    (
                        plan_name,
                        payload.startDate,
                        payload.dayCount,
                        payload_dict["defaultPeople"],
                        payload_json,
                    ),
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


@app.post("/api/retreat-plans/{plan_id}/duplicate")
def duplicate_retreat_plan(
    plan_id: int,
    _user: Annotated[AuthUser, Depends(require_roles(ROLE_PLANNER, ROLE_ADMIN))],
    payload: RetreatPlanDuplicatePayload | None = None,
) -> dict[str, Any]:
    with get_connection() as conn:
        source = conn.execute(
            """
            SELECT id, name, start_date, day_count, default_people, plan_json
            FROM retreat_plans
            WHERE id = ?
            """,
            (plan_id,),
        ).fetchone()
        if not source:
            raise HTTPException(status_code=404, detail="Retreat plan not found")

        source_payload = json.loads(source["plan_json"]) if source["plan_json"] else {}
        if not isinstance(source_payload, dict):
            source_payload = {}

        requested_name = payload.name.strip() if payload and payload.name and payload.name.strip() else None
        base_name = requested_name or f"{source['name']} (Copy)"
        copy_name = unique_retreat_plan_name(conn, base_name)

        source_payload["name"] = copy_name
        source_payload["startDate"] = source_payload.get("startDate", source["start_date"])
        source_payload["dayCount"] = int(source_payload.get("dayCount") or source["day_count"])
        source_payload["defaultPeople"] = float(
            source_payload.get("defaultPeople") or source["default_people"]
        )
        source_payload["retreatDefaultPeople"] = float(
            source_payload.get("retreatDefaultPeople") or source_payload["defaultPeople"]
        )
        source_payload["testDefaultPeople"] = float(
            source_payload.get("testDefaultPeople") or DEFAULT_TEST_HEADCOUNT
        )
        active_profile = source_payload.get("activeProfile")
        source_payload["activeProfile"] = active_profile if active_profile in HEADCOUNT_PROFILES else "retreat"
        shopping_profile = source_payload.get("shoppingProfile")
        source_payload["shoppingProfile"] = (
            shopping_profile if shopping_profile in HEADCOUNT_PROFILES else DEFAULT_SHOPPING_PROFILE
        )

        retreat_meals = source_payload.get("retreatMeals")
        if not isinstance(retreat_meals, list):
            retreat_meals = source_payload.get("meals") if isinstance(source_payload.get("meals"), list) else []
        test_meals = source_payload.get("testMeals")
        if not isinstance(test_meals, list):
            test_meals = []
        source_payload["retreatMeals"] = retreat_meals
        source_payload["testMeals"] = test_meals
        source_payload["meals"] = retreat_meals

        created = conn.execute(
            """
            INSERT INTO retreat_plans(name, start_date, day_count, default_people, plan_json)
            VALUES (?, ?, ?, ?, ?)
            RETURNING id, name, created_at, updated_at
            """,
            (
                copy_name,
                source_payload["startDate"],
                source_payload["dayCount"],
                source_payload["defaultPeople"],
                json.dumps(source_payload),
            ),
        ).fetchone()
        conn.commit()

    return {
        "id": int(created["id"]),
        "name": created["name"],
        "status": "duplicated",
        "source_plan_id": int(source["id"]),
        "created_at": created["created_at"],
        "updated_at": created["updated_at"],
    }


@app.delete("/api/retreat-plans/{plan_id}")
def delete_retreat_plan(
    plan_id: int,
    _user: Annotated[AuthUser, Depends(require_roles(ROLE_PLANNER, ROLE_ADMIN))],
) -> dict[str, Any]:
    with get_connection() as conn:
        existing = conn.execute(
            "SELECT id, name FROM retreat_plans WHERE id = ?",
            (plan_id,),
        ).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Retreat plan not found")

        conn.execute("DELETE FROM retreat_plans WHERE id = ?", (plan_id,))
        conn.commit()

    return {
        "id": int(existing["id"]),
        "name": existing["name"],
        "status": "deleted",
    }


@app.post("/api/service-snapshots")
def create_service_snapshot(
    payload: ServiceSnapshotPayload,
    _user: Annotated[AuthUser, Depends(require_roles(ROLE_PLANNER, ROLE_ADMIN))],
) -> dict[str, Any]:
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


def resolve_purchase_tiers_for_shopping(phase: str, purchase_tiers: list[str] | None) -> set[str]:
    if purchase_tiers:
        cleaned = {
            str(tier).strip().lower()
            for tier in purchase_tiers
            if str(tier).strip().lower() in PURCHASE_TIERS
        }
        if not cleaned:
            raise HTTPException(
                status_code=400,
                detail=f"purchaseTiers must contain one of: {', '.join(PURCHASE_TIERS)}",
            )
        return cleaned

    normalized_phase = phase.strip().lower()
    if normalized_phase in PURCHASE_TIERS:
        return {normalized_phase}
    return set()


def meals_for_profile(plan_payload: dict[str, Any], profile: str) -> list[dict[str, Any]]:
    if profile == "test":
        test_meals = plan_payload.get("testMeals")
        return test_meals if isinstance(test_meals, list) else []

    retreat_meals = plan_payload.get("retreatMeals")
    if isinstance(retreat_meals, list):
        return retreat_meals
    meals = plan_payload.get("meals")
    return meals if isinstance(meals, list) else []


def merge_required_ingredient_aggregate(
    target: dict[tuple[int, str], dict[str, Any]],
    source: dict[tuple[int, str], dict[str, Any]],
) -> None:
    for key, source_entry in source.items():
        existing = target.get(key)
        if not existing:
            target[key] = {
                "ingredient_id": int(source_entry["ingredient_id"]),
                "ingredient_name": source_entry["ingredient_name"],
                "canonical_unit": source_entry["canonical_unit"],
                "required_qty": float(source_entry["required_qty"]),
            }
            continue
        existing["required_qty"] += float(source_entry["required_qty"])


def build_required_ingredients_from_plan(
    conn: Any,
    plan_payload: dict[str, Any],
    profile: str,
    purchase_tiers: set[str],
) -> tuple[dict[tuple[int, str], dict[str, Any]], set[str], dict[tuple[int, str], dict[str, float]]]:
    meals = meals_for_profile(plan_payload, profile)
    dish_names: set[str] = set()
    for meal in meals:
        if not isinstance(meal, dict):
            continue
        dishes = meal.get("dishes")
        if not isinstance(dishes, list):
            continue
        for dish in dishes:
            dish_name = str(dish or "").strip()
            if dish_name:
                dish_names.add(dish_name)

    if not dish_names:
        return {}, set(), {}

    placeholders = ",".join("?" for _ in dish_names)
    recipe_rows = conn.execute(
        f"""
        SELECT id, name, base_servings
        FROM recipes
        WHERE lower(name) IN ({placeholders})
        """,
        tuple(dish.lower() for dish in dish_names),
    ).fetchall()

    recipes_by_name: dict[str, dict[str, Any]] = {
        str(row["name"]).strip().lower(): {
            "id": int(row["id"]),
            "name": row["name"],
            "base_servings": float(row["base_servings"]),
        }
        for row in recipe_rows
    }

    recipe_ids = [recipe["id"] for recipe in recipes_by_name.values()]
    ingredients_by_recipe: dict[int, list[dict[str, Any]]] = {}
    if recipe_ids:
        placeholders = ",".join("?" for _ in recipe_ids)
        ingredient_rows = conn.execute(
            f"""
            SELECT
                ri.recipe_id,
                i.id AS ingredient_id,
                i.name AS ingredient_name,
                i.purchase_tier,
                ri.quantity,
                ri.unit
            FROM recipe_ingredients ri
            JOIN ingredients i ON i.id = ri.ingredient_id
            WHERE ri.recipe_id IN ({placeholders})
              AND lower(i.name) NOT IN ('water', 'hot water')
            """,
            tuple(recipe_ids),
        ).fetchall()

        for row in ingredient_rows:
            recipe_id = int(row["recipe_id"])
            ingredients_by_recipe.setdefault(recipe_id, []).append(
                {
                    "ingredient_id": int(row["ingredient_id"]),
                    "ingredient_name": row["ingredient_name"],
                    "purchase_tier": str(row["purchase_tier"] or "").strip().lower() or None,
                    "quantity": float(row["quantity"]),
                    "unit": str(row["unit"] or "").strip(),
                }
            )

    aggregate: dict[tuple[int, str], dict[str, Any]] = {}
    dish_aggregate: dict[tuple[int, str], dict[str, float]] = {}
    missing_recipes: set[str] = set()
    for meal in meals:
        if not isinstance(meal, dict):
            continue
        people = float(meal.get("people") or 0)
        if people <= 0:
            continue
        dishes = meal.get("dishes")
        if not isinstance(dishes, list):
            continue

        for dish in dishes:
            dish_name = str(dish or "").strip()
            if not dish_name:
                continue

            recipe = recipes_by_name.get(dish_name.lower())
            if not recipe:
                missing_recipes.add(dish_name)
                continue

            base_servings = recipe["base_servings"]
            if base_servings <= 0:
                missing_recipes.add(dish_name)
                continue

            factor = people / base_servings
            for ingredient in ingredients_by_recipe.get(recipe["id"], []):
                tier = ingredient["purchase_tier"]
                if purchase_tiers and tier and tier not in purchase_tiers:
                    continue

                normalized_unit = normalize_unit(ingredient["unit"])
                scaled_qty = ingredient["quantity"] * factor
                canonical_qty, canonical_unit, _note = require_canonical_conversion(
                    ingredient["ingredient_name"],
                    scaled_qty,
                    normalized_unit,
                    context=f"Shopping generation conversion failed for recipe '{recipe['name']}'",
                )

                key = (ingredient["ingredient_id"], canonical_unit)
                entry = aggregate.get(key)
                if not entry:
                    entry = {
                        "ingredient_id": ingredient["ingredient_id"],
                        "ingredient_name": ingredient["ingredient_name"],
                        "canonical_unit": canonical_unit,
                        "required_qty": 0.0,
                    }
                    aggregate[key] = entry
                entry["required_qty"] += canonical_qty

                dish_bucket = dish_aggregate.setdefault(key, {})
                dish_bucket[dish_name] = dish_bucket.get(dish_name, 0.0) + canonical_qty

    return aggregate, missing_recipes, dish_aggregate


def load_inventory_canonical_by_key(conn: Any) -> dict[tuple[int, str], float]:
    rows = conn.execute(
        """
        SELECT
            ii.ingredient_id,
            i.name AS ingredient_name,
            ii.quantity,
            ii.unit,
            ii.source
        FROM inventory_items ii
        JOIN ingredients i ON i.id = ii.ingredient_id
        """
    ).fetchall()

    base_aggregate: dict[tuple[int, str], float] = {}
    override_aggregate: dict[tuple[int, str], float] = {}
    for row in rows:
        quantity = float(row["quantity"] or 0)
        if quantity <= 0:
            continue

        unit = normalize_unit(str(row["unit"] or ""))
        canonical_qty, canonical_unit, _note = require_canonical_conversion(
            row["ingredient_name"],
            quantity,
            unit,
            context="Inventory conversion failed",
        )

        key = (int(row["ingredient_id"]), canonical_unit)
        source = str(row["source"] or "").strip()
        if source == MANUAL_INVENTORY_SOURCE:
            override_aggregate[key] = override_aggregate.get(key, 0.0) + canonical_qty
        else:
            base_aggregate[key] = base_aggregate.get(key, 0.0) + canonical_qty

    for key, value in override_aggregate.items():
        base_aggregate[key] = value

    return base_aggregate


def to_metric_display_unit(canonical_qty: float, canonical_unit: str) -> tuple[float, str]:
    if canonical_unit == "g":
        if canonical_qty >= 1000:
            return canonical_qty / 1000.0, "kg"
        return canonical_qty, "g"

    if canonical_unit == "ml":
        if canonical_qty >= 1000:
            return canonical_qty / 1000.0, "l"
        return canonical_qty, "ml"

    return canonical_qty, canonical_unit


def preferred_metric_unit(canonical_qty: float, canonical_unit: str) -> str:
    if canonical_unit == "g":
        return "kg" if canonical_qty >= 1000 else "g"
    if canonical_unit == "ml":
        return "l" if canonical_qty >= 1000 else "ml"
    return canonical_unit


def canonical_qty_to_unit_or_none(canonical_qty: float, canonical_unit: str, target_unit: str) -> float | None:
    target = normalize_unit(target_unit)
    if canonical_unit == "g" and target in MASS_TO_G:
        return canonical_qty / MASS_TO_G[target]
    if canonical_unit == "ml" and target in VOLUME_TO_ML:
        return canonical_qty / VOLUME_TO_ML[target]
    if canonical_unit == target:
        return canonical_qty
    return None


def canonical_qty_to_unit(canonical_qty: float, canonical_unit: str, target_unit: str) -> float:
    converted = canonical_qty_to_unit_or_none(canonical_qty, canonical_unit, target_unit)
    if converted is None:
        return canonical_qty
    return converted


def quantity_to_canonical(quantity: float, unit: str) -> tuple[float | None, str | None]:
    normalized = normalize_unit(unit)
    if normalized in MASS_TO_G:
        return quantity * MASS_TO_G[normalized], "g"
    if normalized in VOLUME_TO_ML:
        return quantity * VOLUME_TO_ML[normalized], "ml"
    if normalized:
        return quantity, normalized
    return None, None


def derive_shopping_item_status(ordered: bool, received: bool) -> str:
    if received:
        return "received"
    if ordered:
        return "ordered"
    return "open"


def partial_buy_note(stage: str, percent: float, existing_notes: str | None = None) -> str:
    base = f"Partial buy: {stage} ({percent:.1f}% of original)."
    extra = str(existing_notes or "").strip()
    if not extra:
        return base
    return f"{base} {extra}"


def refresh_shopping_list_status(conn: Any, shopping_list_id: int) -> None:
    counts = conn.execute(
        """
        SELECT
            COUNT(*) AS total_count,
            COALESCE(SUM(CASE WHEN COALESCE(ordered, 0) = 1 THEN 1 ELSE 0 END), 0) AS ordered_count,
            COALESCE(SUM(CASE WHEN COALESCE(received, 0) = 1 THEN 1 ELSE 0 END), 0) AS received_count
        FROM shopping_list_items
        WHERE shopping_list_id = ?
        """,
        (shopping_list_id,),
    ).fetchone()
    total_count = int(counts["total_count"] or 0)
    ordered_count = int(counts["ordered_count"] or 0)
    received_count = int(counts["received_count"] or 0)

    if total_count <= 0:
        status = "draft"
    elif received_count >= total_count:
        status = "received"
    elif ordered_count > 0:
        status = "in_progress"
    else:
        status = "draft"

    conn.execute(
        "UPDATE shopping_lists SET status = ? WHERE id = ?",
        (status, shopping_list_id),
    )


def load_shopping_list_detail(conn: Any, shopping_list_id: int) -> dict[str, Any]:
    list_row = conn.execute(
        """
        SELECT
            sl.id,
            sl.name,
            sl.phase,
            sl.status,
            sl.created_at,
            sl.retreat_plan_id,
            rp.name AS retreat_plan_name
        FROM shopping_lists sl
        LEFT JOIN retreat_plans rp ON rp.id = sl.retreat_plan_id
        WHERE sl.id = ?
        """,
        (shopping_list_id,),
    ).fetchone()
    if not list_row:
        raise HTTPException(status_code=404, detail="Shopping list not found")

    item_rows = conn.execute(
        """
        SELECT
            sli.id,
            sli.ingredient_id,
            COALESCE(i.name, ('Unknown ingredient #' || sli.ingredient_id)) AS ingredient_name,
            i.category AS ingredient_category,
            sli.required_qty,
            sli.required_unit,
            sli.in_stock_qty,
            sli.in_stock_unit,
            sli.to_buy_qty,
            sli.to_buy_unit,
            sli.vendor_id,
            v.name AS vendor_name,
            sli.ordered,
            sli.ordered_at,
            sli.received,
            sli.received_at,
            sli.status,
            sli.owner,
            sli.pickup_date,
            sli.notes
        FROM shopping_list_items sli
        LEFT JOIN ingredients i ON i.id = sli.ingredient_id
        LEFT JOIN vendors v ON v.id = sli.vendor_id
        WHERE sli.shopping_list_id = ?
        ORDER BY
            CASE WHEN i.name IS NULL THEN 1 ELSE 0 END,
            lower(COALESCE(i.name, '')),
            sli.id
        """,
        (shopping_list_id,),
    ).fetchall()

    source_breakdown_by_item: dict[int, list[dict[str, Any]]] = {}
    top_source_by_item: dict[int, dict[str, Any]] = {}
    if item_rows:
        source_table_exists = table_exists(conn, "shopping_list_item_sources")
        if source_table_exists:
            source_columns = table_columns(conn, "shopping_list_item_sources")
            dish_name_select = "slis.dish_name" if "dish_name" in source_columns else "NULL"
            item_ids = [int(row["id"]) for row in item_rows]
            placeholders = ",".join("?" for _ in item_ids)
            source_rows = conn.execute(
                f"""
                SELECT
                    slis.shopping_list_item_id,
                    slis.retreat_plan_id,
                    COALESCE(rp.name, slis.retreat_plan_name) AS retreat_plan_name,
                    {dish_name_select} AS dish_name,
                    slis.required_qty,
                    slis.required_unit
                FROM shopping_list_item_sources slis
                LEFT JOIN retreat_plans rp ON rp.id = slis.retreat_plan_id
                WHERE slis.shopping_list_item_id IN ({placeholders})
                ORDER BY
                    slis.shopping_list_item_id,
                    lower(COALESCE(rp.name, slis.retreat_plan_name)),
                    slis.id
                """,
                tuple(item_ids),
            ).fetchall()

            retreat_totals_by_item: dict[int, dict[tuple[int | None, str, str], float]] = {}
            for source_row in source_rows:
                item_id = int(source_row["shopping_list_item_id"])
                retreat_id = int(source_row["retreat_plan_id"]) if source_row["retreat_plan_id"] is not None else None
                retreat_name = str(source_row["retreat_plan_name"] or "").strip()
                if not retreat_name:
                    retreat_name = f"Retreat #{retreat_id}" if retreat_id is not None else "Unknown retreat"

                required_qty = float(source_row["required_qty"] or 0.0)
                required_unit = str(source_row["required_unit"] or "").strip()
                if required_qty <= 0 or not required_unit:
                    continue

                retreat_key = (retreat_id, retreat_name, required_unit)
                totals = retreat_totals_by_item.setdefault(item_id, {})
                totals[retreat_key] = totals.get(retreat_key, 0.0) + required_qty

                dish_name = str(source_row["dish_name"] or "").strip()
                if dish_name:
                    current_top = top_source_by_item.get(item_id)
                    if not current_top or required_qty > float(current_top["required_qty"]):
                        top_source_by_item[item_id] = {
                            "retreat_plan_id": retreat_id,
                            "retreat_plan_name": retreat_name,
                            "dish_name": dish_name,
                            "required_qty": required_qty,
                            "required_unit": required_unit,
                        }

            for item_id, totals in retreat_totals_by_item.items():
                breakdown = [
                    {
                        "retreat_plan_id": retreat_id,
                        "retreat_plan_name": retreat_name,
                        "required_qty": round(total_qty, 4),
                        "required_unit": required_unit,
                    }
                    for (retreat_id, retreat_name, required_unit), total_qty in totals.items()
                ]
                breakdown.sort(
                    key=lambda entry: (
                        -float(entry["required_qty"] or 0.0),
                        str(entry["retreat_plan_name"] or "").lower(),
                    )
                )
                source_breakdown_by_item[item_id] = breakdown
                if item_id not in top_source_by_item and breakdown:
                    lead = breakdown[0]
                    top_source_by_item[item_id] = {
                        "retreat_plan_id": lead["retreat_plan_id"],
                        "retreat_plan_name": lead["retreat_plan_name"],
                        "dish_name": None,
                        "required_qty": lead["required_qty"],
                        "required_unit": lead["required_unit"],
                    }

    ingredient_row_counts: dict[int, int] = {}
    for row in item_rows:
        ingredient_id = int(row["ingredient_id"])
        ingredient_row_counts[ingredient_id] = ingredient_row_counts.get(ingredient_id, 0) + 1

    items: list[dict[str, Any]] = []
    ordered_count = 0
    received_count = 0
    for row in item_rows:
        ordered = bool(row["ordered"])
        received = bool(row["received"])
        if ordered:
            ordered_count += 1
        if received:
            received_count += 1

        ingredient_id = int(row["ingredient_id"])
        ingredient_name = row["ingredient_name"]
        if ingredient_row_counts.get(ingredient_id, 0) > 1:
            qualifier = str(row["required_unit"] or row["to_buy_unit"] or "").strip()
            # Keep names clean for count-style units (e.g., "Cardamom" instead of
            # "Cardamom (piece)") while still qualifying other duplicate unit splits.
            if qualifier and qualifier.lower() not in {"piece", "pieces"}:
                ingredient_name = f"{ingredient_name} ({qualifier})"

        item_id = int(row["id"])
        source_breakdown = source_breakdown_by_item.get(item_id, [])
        if not source_breakdown and list_row["retreat_plan_id"] is not None:
            fallback_retreat_id = int(list_row["retreat_plan_id"])
            fallback_retreat_name = (
                str(list_row["retreat_plan_name"] or "").strip() or f"Retreat #{fallback_retreat_id}"
            )
            fallback_required_qty = float(row["required_qty"]) if row["required_qty"] is not None else None
            fallback_required_unit = str(row["required_unit"] or "").strip()
            if fallback_required_qty is not None and fallback_required_unit:
                source_breakdown = [
                    {
                        "retreat_plan_id": fallback_retreat_id,
                        "retreat_plan_name": fallback_retreat_name,
                        "required_qty": round(fallback_required_qty, 4),
                        "required_unit": fallback_required_unit,
                    }
                ]

        top_source = top_source_by_item.get(item_id)
        if not top_source and source_breakdown:
            lead = source_breakdown[0]
            top_source = {
                "retreat_plan_id": lead["retreat_plan_id"],
                "retreat_plan_name": lead["retreat_plan_name"],
                "dish_name": None,
                "required_qty": lead["required_qty"],
                "required_unit": lead["required_unit"],
            }

        items.append(
            {
                "id": item_id,
                "ingredient_id": ingredient_id,
                "ingredient_name": ingredient_name,
                "ingredient_category": row["ingredient_category"],
                "required_qty": float(row["required_qty"]) if row["required_qty"] is not None else None,
                "required_unit": row["required_unit"],
                "in_stock_qty": float(row["in_stock_qty"]) if row["in_stock_qty"] is not None else None,
                "in_stock_unit": row["in_stock_unit"],
                "to_buy_qty": float(row["to_buy_qty"]) if row["to_buy_qty"] is not None else None,
                "to_buy_unit": row["to_buy_unit"],
                "vendor_id": int(row["vendor_id"]) if row["vendor_id"] is not None else None,
                "vendor_name": row["vendor_name"],
                "ordered": ordered,
                "ordered_at": row["ordered_at"],
                "received": received,
                "received_at": row["received_at"],
                "status": row["status"] or derive_shopping_item_status(ordered, received),
                "owner": row["owner"],
                "pickup_date": row["pickup_date"],
                "notes": row["notes"],
                "source_breakdown": source_breakdown,
                "top_source": top_source,
            }
        )

    return {
        "id": int(list_row["id"]),
        "name": list_row["name"],
        "phase": list_row["phase"] or "bulk",
        "status": list_row["status"] or "draft",
        "created_at": list_row["created_at"],
        "retreat_plan_id": int(list_row["retreat_plan_id"]) if list_row["retreat_plan_id"] is not None else None,
        "retreat_plan_name": list_row["retreat_plan_name"],
        "item_count": len(items),
        "ordered_count": ordered_count,
        "received_count": received_count,
        "items": items,
    }


def create_carry_forward_shopping_list(
    conn: Any,
    source_list_id: int,
    name_override: str | None = None,
    phase_override: str | None = None,
) -> dict[str, Any]:
    source_list = conn.execute(
        """
        SELECT id, name, phase, retreat_plan_id
        FROM shopping_lists
        WHERE id = ?
        """,
        (source_list_id,),
    ).fetchone()
    if not source_list:
        raise HTTPException(status_code=404, detail="Source shopping list not found")

    phase = str(source_list["phase"] or "custom").strip().lower() or "custom"
    if phase_override is not None:
        candidate_phase = str(phase_override or "").strip().lower()
        if candidate_phase not in SHOPPING_PHASES:
            raise HTTPException(
                status_code=400,
                detail=f"phase must be one of: {', '.join(SHOPPING_PHASES)}",
            )
        phase = candidate_phase

    source_items = conn.execute(
        """
        SELECT
            ingredient_id,
            required_qty,
            required_unit,
            to_buy_qty,
            to_buy_unit,
            vendor_id,
            notes
        FROM shopping_list_items
        WHERE shopping_list_id = ?
          AND COALESCE(received, 0) = 0
        ORDER BY id
        """,
        (source_list_id,),
    ).fetchall()

    pending_items: list[dict[str, Any]] = []
    for row in source_items:
        pending_qty = float(row["to_buy_qty"]) if row["to_buy_qty"] is not None else float(row["required_qty"] or 0)
        pending_unit = str(row["to_buy_unit"] or row["required_unit"] or "").strip()
        if pending_qty <= 0 or not pending_unit:
            continue
        pending_items.append(
            {
                "ingredient_id": int(row["ingredient_id"]),
                "pending_qty": pending_qty,
                "pending_unit": pending_unit,
                "vendor_id": int(row["vendor_id"]) if row["vendor_id"] is not None else None,
                "notes": row["notes"],
            }
        )

    if not pending_items:
        raise HTTPException(
            status_code=400,
            detail="No unreceived items with remaining quantity to carry forward.",
        )

    name = name_override.strip() if name_override and name_override.strip() else None
    if not name:
        name = f"{source_list['name']} - Step 2"
    name = unique_shopping_list_name(conn, name)

    created = conn.execute(
        """
        INSERT INTO shopping_lists(retreat_plan_id, name, phase, status)
        VALUES (?, ?, ?, 'draft')
        RETURNING id
        """,
        (source_list["retreat_plan_id"], name, phase),
    ).fetchone()
    new_list_id = int(created["id"])

    for item in pending_items:
        notes = (
            f"Carry-forward from list #{source_list_id}: {item['notes']}"
            if item["notes"]
            else f"Carry-forward from list #{source_list_id}"
        )
        conn.execute(
            """
            INSERT INTO shopping_list_items(
                shopping_list_id,
                ingredient_id,
                required_qty,
                required_unit,
                in_stock_qty,
                in_stock_unit,
                to_buy_qty,
                to_buy_unit,
                vendor_id,
                status,
                ordered,
                received,
                notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'open', 0, 0, ?)
            """,
            (
                new_list_id,
                item["ingredient_id"],
                round(item["pending_qty"], 4),
                item["pending_unit"],
                0,
                item["pending_unit"],
                round(item["pending_qty"], 4),
                item["pending_unit"],
                item["vendor_id"],
                notes,
            ),
        )

    refresh_shopping_list_status(conn, new_list_id)
    detail = load_shopping_list_detail(conn, new_list_id)
    detail["carried_from_list_id"] = int(source_list["id"])
    detail["carried_item_count"] = len(pending_items)
    return detail


def split_selected_shopping_list_items(
    conn: Any,
    source_list_id: int,
    selected_item_ids: list[int],
    name_override: str | None = None,
) -> dict[str, Any]:
    source_list = conn.execute(
        """
        SELECT id, name, phase, retreat_plan_id
        FROM shopping_lists
        WHERE id = ?
        """,
        (source_list_id,),
    ).fetchone()
    if not source_list:
        raise HTTPException(status_code=404, detail="Source shopping list not found")

    unique_item_ids = sorted({int(item_id) for item_id in selected_item_ids if int(item_id) > 0})
    if not unique_item_ids:
        raise HTTPException(status_code=400, detail="Select at least one item to split.")

    placeholders = ",".join("?" for _ in unique_item_ids)
    source_items = conn.execute(
        f"""
        SELECT
            id,
            ingredient_id,
            required_qty,
            required_unit,
            in_stock_qty,
            in_stock_unit,
            to_buy_qty,
            to_buy_unit,
            vendor_id,
            owner,
            pickup_date,
            ordered,
            ordered_at,
            received,
            received_at,
            status,
            notes
        FROM shopping_list_items
        WHERE shopping_list_id = ?
          AND id IN ({placeholders})
        ORDER BY id
        """,
        (source_list_id, *unique_item_ids),
    ).fetchall()

    if len(source_items) != len(unique_item_ids):
        found_ids = {int(row["id"]) for row in source_items}
        missing_ids = [item_id for item_id in unique_item_ids if item_id not in found_ids]
        raise HTTPException(
            status_code=404,
            detail=f"Shopping list item(s) not found in source list: {', '.join(str(x) for x in missing_ids)}",
        )

    new_name = name_override.strip() if name_override and name_override.strip() else None
    if not new_name:
        new_name = f"{source_list['name']} - Selected"
    new_name = unique_shopping_list_name(conn, new_name)

    created = conn.execute(
        """
        INSERT INTO shopping_lists(retreat_plan_id, name, phase, status)
        VALUES (?, ?, ?, 'draft')
        RETURNING id
        """,
        (
            source_list["retreat_plan_id"],
            new_name,
            str(source_list["phase"] or "custom").strip().lower() or "custom",
        ),
    ).fetchone()
    new_list_id = int(created["id"])

    old_to_new_item_id: dict[int, int] = {}
    for item in source_items:
        created_item = conn.execute(
            """
            INSERT INTO shopping_list_items(
                shopping_list_id,
                ingredient_id,
                required_qty,
                required_unit,
                in_stock_qty,
                in_stock_unit,
                to_buy_qty,
                to_buy_unit,
                vendor_id,
                owner,
                pickup_date,
                ordered,
                ordered_at,
                received,
                received_at,
                status,
                notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            RETURNING id
            """,
            (
                new_list_id,
                int(item["ingredient_id"]),
                float(item["required_qty"] or 0.0),
                str(item["required_unit"] or ""),
                float(item["in_stock_qty"] or 0.0),
                str(item["in_stock_unit"] or item["required_unit"] or ""),
                float(item["to_buy_qty"] or 0.0),
                str(item["to_buy_unit"] or item["required_unit"] or ""),
                int(item["vendor_id"]) if item["vendor_id"] is not None else None,
                str(item["owner"] or "").strip() or None,
                str(item["pickup_date"] or "").strip() or None,
                1 if bool(item["ordered"]) else 0,
                item["ordered_at"],
                1 if bool(item["received"]) else 0,
                item["received_at"],
                str(item["status"] or "").strip() or derive_shopping_item_status(
                    ordered=bool(item["ordered"]),
                    received=bool(item["received"]),
                ),
                str(item["notes"] or "").strip() or None,
            ),
        ).fetchone()
        old_to_new_item_id[int(item["id"])] = int(created_item["id"])

    source_rows = conn.execute(
        f"""
        SELECT
            shopping_list_item_id,
            retreat_plan_id,
            retreat_plan_name,
            dish_name,
            required_qty,
            required_unit
        FROM shopping_list_item_sources
        WHERE shopping_list_item_id IN ({placeholders})
        ORDER BY id
        """,
        tuple(unique_item_ids),
    ).fetchall()
    for row in source_rows:
        old_item_id = int(row["shopping_list_item_id"])
        new_item_id = old_to_new_item_id.get(old_item_id)
        if not new_item_id:
            continue
        conn.execute(
            """
            INSERT INTO shopping_list_item_sources(
                shopping_list_item_id,
                retreat_plan_id,
                retreat_plan_name,
                dish_name,
                required_qty,
                required_unit
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                new_item_id,
                int(row["retreat_plan_id"]) if row["retreat_plan_id"] is not None else None,
                str(row["retreat_plan_name"] or "").strip() or "Unknown retreat",
                str(row["dish_name"] or "").strip() or None,
                float(row["required_qty"] or 0.0),
                str(row["required_unit"] or "").strip(),
            ),
        )

    conn.execute(
        f"""
        DELETE FROM shopping_list_items
        WHERE shopping_list_id = ?
          AND id IN ({placeholders})
        """,
        (source_list_id, *unique_item_ids),
    )

    refresh_shopping_list_status(conn, source_list_id)
    refresh_shopping_list_status(conn, new_list_id)

    source_detail = load_shopping_list_detail(conn, source_list_id)
    new_detail = load_shopping_list_detail(conn, new_list_id)
    return {
        "status": "ok",
        "split_item_count": len(unique_item_ids),
        "source_list": source_detail,
        "new_list": new_detail,
    }


def unique_shopping_list_name(
    conn: Any,
    base_name: str,
    exclude_shopping_list_id: int | None = None,
) -> str:
    seed = " ".join(str(base_name or "").strip().split()) or "Shopping List"
    candidate = seed
    suffix = 2
    while True:
        if exclude_shopping_list_id is None:
            exists = conn.execute(
                "SELECT 1 FROM shopping_lists WHERE lower(name) = lower(?)",
                (candidate,),
            ).fetchone()
        else:
            exists = conn.execute(
                """
                SELECT 1
                FROM shopping_lists
                WHERE lower(name) = lower(?)
                  AND id != ?
                """,
                (candidate, exclude_shopping_list_id),
            ).fetchone()
        if not exists:
            break
        candidate = f"{seed} ({suffix})"
        suffix += 1
    return candidate


def unique_retreat_plan_name(conn: Any, base_name: str) -> str:
    seed = " ".join(base_name.strip().split()) or "Untitled Retreat (Copy)"
    candidate = seed
    suffix = 2
    while conn.execute(
        "SELECT 1 FROM retreat_plans WHERE lower(name) = lower(?)",
        (candidate,),
    ).fetchone():
        candidate = f"{seed} ({suffix})"
        suffix += 1
    return candidate


def normalize_unit(unit: str) -> str:
    value = unit.strip().lower()
    aliases = {
        "cups": "cup",
        "gms": "g",
        "kilogram": "kg",
        "kilograms": "kg",
        "kilo": "kg",
        "kilos": "kg",
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
        "pieces": "piece",
        "packets": "packet",
        "cans": "can",
        "bunches": "bunch",
        "loaves": "loaf",
        "sprigs": "sprig",
        "springs": "sprig",
        "leaves": "leaf",
        "bags": "bag",
        "pinches": "pinch",
        "pod": "piece",
        "pods": "piece",
        "clove": "piece",
        "cloves": "piece",
    }
    return aliases.get(value, value)


def normalize_ingredient_name(ingredient_name: str) -> str:
    candidate = " ".join(ingredient_name.strip().split())
    aliases = {
        "kidney bean": "Rajma",
        "kidney beans": "Rajma",
        "red kidney bean": "Rajma",
        "red kidney beans": "Rajma",
        "lemon": "Lemon juice concentrate",
        "lime": "Lemon juice concentrate",
        "lemon or lime": "Lemon juice concentrate",
        "english cucumber": "Cucumber",
        "english cucumbers": "Cucumber",
        "purple cabbage": "Red Cabbage",
        "red cabbage": "Red Cabbage",
        "red onion": "Onion",
        "red onions": "Onion",
        "extra firm tofu": "extra-firm tofu",
        "extra firm tofy": "extra-firm tofu",
        "curry leaf": "Curry leaves",
        "cardamom pod": "Cardamom",
        "cardamom pods": "Cardamom",
        "green cardamom": "Cardamom",
        "green cardamom pod": "Cardamom",
        "green cardamom pods": "Cardamom",
        "mung dal": "Yellow Mung Dal",
        "yellow mung dal": "Yellow Mung Dal",
        "yellow moong dal": "Yellow Mung Dal",
    }
    return aliases.get(candidate.lower(), candidate)


def normalize_recipe_category(category: str | None) -> str | None:
    if category is None:
        return None
    candidate = " ".join(str(category).strip().split())
    if not candidate:
        return None

    matches = [known for known in RECIPE_CATEGORIES if known.lower() == candidate.lower()]
    if matches:
        return matches[0]

    raise HTTPException(
        status_code=400,
        detail=(
            f"Unknown recipe category '{candidate}'. "
            f"Allowed categories: {', '.join(RECIPE_CATEGORIES)}"
        ),
    )


def get_or_create_ingredient_id(conn: Any, ingredient_name: str) -> int:
    ing_name = normalize_ingredient_name(ingredient_name)
    if not ing_name:
        raise HTTPException(status_code=400, detail="Ingredient name cannot be blank")

    ing_row = conn.execute(
        "SELECT id FROM ingredients WHERE lower(name) = lower(?)",
        (ing_name,),
    ).fetchone()
    if ing_row:
        return int(ing_row["id"])

    created = conn.execute(
        "INSERT INTO ingredients(name) VALUES (?) RETURNING id",
        (ing_name,),
    ).fetchone()
    ingredient_id = int(created["id"])

    # Automatically fetch USDA density data for the new ingredient.
    try:
        populate_ingredient_conversions(conn, ingredient_id, ing_name)
    except Exception:
        import logging
        logging.getLogger(__name__).warning(
            "USDA lookup failed for %r — ingredient created without density data",
            ing_name,
            exc_info=True,
        )

    return ingredient_id


def replace_recipe_ingredients(
    conn: Any, recipe_id: int, ingredients: list[RecipeIngredientCreate]
) -> None:
    conn.execute("DELETE FROM recipe_ingredients WHERE recipe_id = ?", (recipe_id,))
    for item in ingredients:
        ingredient_id = get_or_create_ingredient_id(conn, item.ingredient_name)
        prep_notes = item.prep_notes.strip() if item.prep_notes and item.prep_notes.strip() else None
        normalized_unit = normalize_unit(item.unit)
        normalized_quantity = float(item.quantity)

        grams_per_cup, canonical_unit, category = ingredient_profile(item.ingredient_name)
        if is_dal_or_rice_ingredient(item.ingredient_name, category):
            if normalized_unit in VOLUME_TO_ML and normalized_unit != "cup":
                normalized_quantity = (
                    normalized_quantity * VOLUME_TO_ML[normalized_unit] / VOLUME_TO_ML["cup"]
                )
                normalized_unit = "cup"
            elif normalized_unit in MASS_TO_G:
                grams_per_cup_value = grams_per_cup
                if not grams_per_cup_value:
                    cup_to_g = ingredient_specific_unit_conversion_factor(
                        item.ingredient_name,
                        "cup",
                        "g",
                    )
                    cup_to_kg = ingredient_specific_unit_conversion_factor(
                        item.ingredient_name,
                        "cup",
                        "kg",
                    )
                    if cup_to_g is not None:
                        grams_per_cup_value = cup_to_g
                    elif cup_to_kg is not None:
                        grams_per_cup_value = cup_to_kg * 1000.0
                if grams_per_cup_value and grams_per_cup_value > 0:
                    grams = normalized_quantity * MASS_TO_G[normalized_unit]
                    normalized_quantity = grams / grams_per_cup_value
                    normalized_unit = "cup"

        if canonical_unit in COUNT_UNITS and normalized_unit in COUNT_UNITS and normalized_unit != canonical_unit:
            factor = ingredient_specific_unit_conversion_factor(item.ingredient_name, normalized_unit, canonical_unit)
            if factor is None:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Missing conversion for ingredient '{item.ingredient_name}': "
                        f"'{normalized_unit}' -> '{canonical_unit}'."
                    ),
                )
            normalized_quantity *= factor
            normalized_unit = canonical_unit
        elif not is_dal_or_rice_ingredient(item.ingredient_name, category) and canonical_unit in MASS_TO_G and normalized_unit != canonical_unit:
            canonical_qty, canonical_base_unit, _note = to_canonical(
                item.ingredient_name,
                normalized_quantity,
                normalized_unit,
            )
            if canonical_qty is None:
                raise HTTPException(
                    status_code=400,
                    detail=_note
                    or (
                        f"Missing conversion for ingredient '{item.ingredient_name}': "
                        f"'{normalized_unit}' -> '{canonical_unit}'."
                    ),
                )
            if canonical_base_unit == "g":
                normalized_quantity = canonical_qty / MASS_TO_G[canonical_unit]
                normalized_unit = canonical_unit
            elif canonical_base_unit in COUNT_UNITS:
                # Preserve count-unit recipes for packaged items when no
                # ingredient-specific weight mapping exists.
                normalized_quantity = canonical_qty
                normalized_unit = canonical_base_unit
            else:
                raise HTTPException(
                    status_code=400,
                    detail=_note
                    or (
                        f"Missing conversion for ingredient '{item.ingredient_name}': "
                        f"'{normalized_unit}' -> '{canonical_unit}'."
                    ),
                )

        conn.execute(
            """
            INSERT INTO recipe_ingredients(recipe_id, ingredient_id, quantity, unit, prep_notes)
            VALUES (?, ?, ?, ?, ?)
            """,
            (recipe_id, ingredient_id, normalized_quantity, normalized_unit, prep_notes),
        )


def replace_recipe_steps(conn: Any, recipe_id: int, steps: list[str] | None) -> None:
    conn.execute("DELETE FROM recipe_steps WHERE recipe_id = ?", (recipe_id,))
    clean_steps = [step.strip() for step in (steps or []) if step and step.strip()]
    for index, instruction in enumerate(clean_steps, start=1):
        conn.execute(
            """
            INSERT INTO recipe_steps(recipe_id, step_order, instruction)
            VALUES (?, ?, ?)
            """,
            (recipe_id, index, instruction),
        )


def ingredient_profile(ingredient_name: str) -> tuple[float | None, str | None, str | None]:
    normalized_name = normalize_ingredient_name(ingredient_name)
    with get_connection() as conn:
        row = conn.execute(
            "SELECT grams_per_cup, canonical_unit, category FROM ingredients WHERE lower(name) = lower(?)",
            (normalized_name,),
        ).fetchone()
        if not row:
            return None, None, None
        grams_per_cup = float(row["grams_per_cup"]) if row["grams_per_cup"] else None
        canonical_unit = normalize_unit(str(row["canonical_unit"] or "").strip()) if row["canonical_unit"] else None
        category = str(row["category"] or "").strip() if row["category"] else None
        return grams_per_cup, canonical_unit, category


def is_spice_or_seasoning_category(category: str | None) -> bool:
    if not category:
        return False
    normalized = category.strip().lower()
    return "spice" in normalized or "seasoning" in normalized


def is_prepared_packaged_category(category: str | None) -> bool:
    if not category:
        return False
    normalized = category.strip().lower()
    return "prepared" in normalized or "packaged" in normalized


def is_produce_category(category: str | None) -> bool:
    if not category:
        return False
    return category.strip().lower() in {"produce", "fruits"}


def is_pulse_or_legume_category(category: str | None) -> bool:
    if not category:
        return False
    normalized = category.strip().lower()
    return "pulse" in normalized or "legume" in normalized


def is_dal_or_rice_ingredient(ingredient_name: str, category: str | None = None) -> bool:
    normalized_name = normalize_ingredient_name(ingredient_name).lower()
    if not normalized_name:
        return False
    if "vinegar" in normalized_name:
        return False
    if DAL_RICE_TOKEN_RE.search(normalized_name):
        return True

    if is_pulse_or_legume_category(category):
        return True
    return False


def ingredient_specific_unit_conversion_factor(
    ingredient_name: str,
    unit_from: str,
    unit_to: str,
) -> float | None:
    normalized_name = normalize_ingredient_name(ingredient_name)
    from_unit = normalize_unit(unit_from)
    to_unit = normalize_unit(unit_to)
    if not normalized_name or not from_unit or not to_unit:
        return None
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT quantity_from, quantity_to
            FROM unit_conversions
            WHERE lower(COALESCE(item_name, '')) = lower(?)
              AND lower(unit_from) = lower(?)
              AND lower(unit_to) = lower(?)
            ORDER BY CASE WHEN context = 'ingredient_specific' THEN 0 ELSE 1 END, id
            LIMIT 1
            """,
            (normalized_name, from_unit, to_unit),
        ).fetchone()
    if not row:
        return None
    quantity_from = float(row["quantity_from"] or 0)
    quantity_to = float(row["quantity_to"] or 0)
    if quantity_from <= 0 or quantity_to <= 0:
        return None
    return quantity_to / quantity_from


def ingredient_specific_g_per_unit(ingredient_name: str, unit: str) -> float | None:
    return ingredient_specific_unit_conversion_factor(ingredient_name, unit, "g")


def to_canonical(ingredient_name: str, qty: float, unit: str) -> tuple[float | None, str | None, str | None]:
    unit = normalize_unit(unit)
    if unit in MASS_TO_G:
        return qty * MASS_TO_G[unit], "g", None

    specific_g_per_unit = ingredient_specific_g_per_unit(ingredient_name, unit)
    if specific_g_per_unit is not None:
        return qty * specific_g_per_unit, "g", "Converted using ingredient-specific unit conversion."

    grams_per_cup, canonical_unit, _ingredient_category = ingredient_profile(ingredient_name)

    if unit in VOLUME_TO_ML:
        if canonical_unit in {"ml", "l"}:
            return qty * VOLUME_TO_ML[unit], "ml", "Canonical volume unit preference applied."

        if grams_per_cup is not None:
            cups = (qty * VOLUME_TO_ML[unit]) / VOLUME_TO_ML["cup"]
            grams = cups * grams_per_cup
            return grams, "g", "Converted using ingredient-specific grams_per_cup."

        if canonical_unit in MASS_TO_G:
            return None, None, (
                f"Missing conversion for ingredient '{ingredient_name}': "
                f"'{unit}' -> '{canonical_unit}' requires ingredient-specific density mapping."
            )
        if canonical_unit in COUNT_UNITS:
            return None, None, (
                f"Missing conversion for ingredient '{ingredient_name}': "
                f"'{unit}' -> '{canonical_unit}' requires ingredient-specific unit mapping."
            )

        return qty * VOLUME_TO_ML[unit], "ml", "No ingredient density found; kept as volume."

    if unit in COUNT_UNITS:
        if canonical_unit in COUNT_UNITS:
            target_unit = normalize_unit(canonical_unit)
            if unit == target_unit:
                return qty, target_unit, "Canonical count unit preference applied."

            factor = ingredient_specific_unit_conversion_factor(ingredient_name, unit, target_unit)
            if factor is not None:
                return qty * factor, target_unit, "Converted using ingredient-specific count-unit conversion."
            return None, None, (
                f"Missing conversion for ingredient '{ingredient_name}': "
                f"'{unit}' -> '{target_unit}'."
            )
        if canonical_unit in MASS_TO_G or canonical_unit in {"ml", "l"}:
            if is_prepared_packaged_category(_ingredient_category):
                return qty, unit, (
                    "Missing mass/volume conversion; kept as count unit for prepared/packaged ingredient."
                )
            return None, None, (
                f"Missing conversion for ingredient '{ingredient_name}': "
                f"'{unit}' -> '{canonical_unit}'."
            )
        return qty, unit, None

    return None, None, f"Unknown unit '{unit}' for ingredient '{ingredient_name}'."


def require_canonical_conversion(
    ingredient_name: str,
    quantity: float,
    unit: str,
    *,
    context: str | None = None,
) -> tuple[float, str, str | None]:
    canonical_qty, canonical_unit, note = to_canonical(ingredient_name, quantity, unit)
    if canonical_qty is None or canonical_unit is None:
        detail = note or f"Could not convert ingredient '{ingredient_name}' with unit '{unit}'."
        if context:
            detail = f"{context}: {detail}"
        raise HTTPException(status_code=400, detail=detail)
    return canonical_qty, canonical_unit, note


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


def normalize_optional_text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text if text else None


def normalize_item_unit(value: Any) -> str:
    text = str(value or "").strip().lower()
    return text if text else "each"


def as_active_flag(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return int(value) != 0
    text = str(value).strip().lower()
    return text not in {"", "0", "false", "no", "off"}


def format_retreat_inventory_location_row(row: Any) -> dict[str, Any]:
    return {
        "id": int(row["id"]),
        "name": row["name"],
        "description": row["description"],
        "active": as_active_flag(row["active"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def ensure_retreat_inventory_location(conn: Any, location_name: str) -> int:
    clean_name = str(location_name or "").strip()
    if not clean_name:
        raise HTTPException(status_code=400, detail="Location name cannot be blank.")

    existing = conn.execute(
        """
        SELECT id
        FROM retreat_inventory_locations
        WHERE deleted_at IS NULL
          AND lower(name) = lower(?)
        """,
        (clean_name,),
    ).fetchone()
    if existing:
        return int(existing["id"])

    row = conn.execute(
        """
        INSERT INTO retreat_inventory_locations(
            name,
            active,
            created_at,
            updated_at
        )
        VALUES (?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        RETURNING id
        """,
        (clean_name,),
    ).fetchone()
    return int(row["id"])


def load_retreat_inventory_item_locations(conn: Any, item_ids: list[int]) -> dict[int, list[dict[str, Any]]]:
    if not item_ids:
        return {}
    placeholders = ", ".join("?" for _ in item_ids)
    rows = conn.execute(
        f"""
        SELECT
            il.item_id,
            il.location_id,
            il.quantity,
            il.updated_at,
            l.name AS location_name,
            l.description AS location_description
        FROM retreat_inventory_item_locations il
        JOIN retreat_inventory_locations l ON l.id = il.location_id
        WHERE il.item_id IN ({placeholders})
          AND l.deleted_at IS NULL
        ORDER BY il.item_id, lower(l.name), il.id
        """,
        tuple(item_ids),
    ).fetchall()

    by_item: dict[int, list[dict[str, Any]]] = {}
    for row in rows:
        item_id = int(row["item_id"])
        by_item.setdefault(item_id, []).append(
            {
                "location_id": int(row["location_id"]),
                "location_name": row["location_name"],
                "location_description": row["location_description"],
                "quantity": int(row["quantity"] or 0),
                "updated_at": row["updated_at"],
            }
        )
    return by_item


def validate_retreat_item_location_inputs(
    conn: Any,
    payload_locations: list[RetreatInventoryItemLocationInput],
) -> list[dict[str, Any]]:
    if not payload_locations:
        return []

    normalized: list[dict[str, Any]] = []
    seen_ids: set[int] = set()
    for entry in payload_locations:
        location_id = int(entry.locationId)
        if location_id in seen_ids:
            raise HTTPException(status_code=400, detail=f"Duplicate location id in payload: {location_id}.")
        seen_ids.add(location_id)
        normalized.append(
            {
                "location_id": location_id,
                "quantity": int(entry.quantity),
            }
        )

    placeholders = ", ".join("?" for _ in normalized)
    location_rows = conn.execute(
        f"""
        SELECT id, name, active
        FROM retreat_inventory_locations
        WHERE deleted_at IS NULL
          AND id IN ({placeholders})
        """,
        tuple(entry["location_id"] for entry in normalized),
    ).fetchall()
    location_by_id = {int(row["id"]): row for row in location_rows}

    for entry in normalized:
        location_row = location_by_id.get(entry["location_id"])
        if not location_row:
            raise HTTPException(status_code=404, detail=f"Location {entry['location_id']} not found.")
        if not as_active_flag(location_row["active"]):
            raise HTTPException(status_code=400, detail=f"Location {location_row['name']} is inactive.")
        entry["location_name"] = location_row["name"]
    return normalized


def replace_retreat_item_locations(conn: Any, item_id: int, locations: list[dict[str, Any]]) -> None:
    conn.execute("DELETE FROM retreat_inventory_item_locations WHERE item_id = ?", (item_id,))
    for entry in locations:
        conn.execute(
            """
            INSERT INTO retreat_inventory_item_locations(
                item_id,
                location_id,
                quantity,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            (
                int(item_id),
                int(entry["location_id"]),
                int(entry["quantity"]),
            ),
        )


def sync_retreat_item_level_from_locations(conn: Any, item_id: int) -> None:
    tracking_row = conn.execute(
        """
        SELECT c.tracking_mode
        FROM retreat_inventory_items i
        JOIN retreat_inventory_categories c ON c.id = i.category_id
        WHERE i.id = ?
          AND i.deleted_at IS NULL
          AND c.deleted_at IS NULL
        """,
        (item_id,),
    ).fetchone()
    if not tracking_row:
        return
    if str(tracking_row["tracking_mode"] or "ITEM").upper() != "ITEM":
        return

    total_row = conn.execute(
        """
        SELECT COALESCE(SUM(il.quantity), 0) AS total_quantity
        FROM retreat_inventory_item_locations il
        JOIN retreat_inventory_locations l ON l.id = il.location_id
        WHERE il.item_id = ?
          AND l.deleted_at IS NULL
        """,
        (item_id,),
    ).fetchone()
    total_quantity = int(total_row["total_quantity"] or 0)

    level_row = conn.execute(
        """
        SELECT id
        FROM retreat_inventory_levels
        WHERE item_id = ?
          AND category_id IS NULL
        """,
        (item_id,),
    ).fetchone()
    if level_row:
        conn.execute(
            """
            UPDATE retreat_inventory_levels
            SET quantity = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (total_quantity, int(level_row["id"])),
        )
        return

    conn.execute(
        """
        INSERT INTO retreat_inventory_levels(
            item_id,
            category_id,
            quantity,
            min_threshold,
            updated_at
        )
        VALUES (?, NULL, ?, 0, CURRENT_TIMESTAMP)
        """,
        (item_id, total_quantity),
    )


def format_retreat_inventory_category_row(row: Any) -> dict[str, Any]:
    return {
        "id": int(row["id"]),
        "name": row["name"],
        "tracking_mode": row["tracking_mode"],
        "image_url": row["image_url"],
        "active": as_active_flag(row["active"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def format_retreat_inventory_item_row(row: Any) -> dict[str, Any]:
    return {
        "id": int(row["id"]),
        "name": row["name"],
        "barcode": row["barcode"],
        "category_id": int(row["category_id"]),
        "category_name": row["category_name"],
        "tracking_mode": row["tracking_mode"],
        "shelf_location": row["shelf_location"],
        "unit": row["unit"],
        "purchase_url": row["purchase_url"],
        "brand": row["brand"],
        "description": row["description"],
        "image_url": row["image_url"],
        "active": as_active_flag(row["active"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def attach_retreat_inventory_item_locations(conn: Any, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    item_ids = [int(item["id"]) for item in items if item.get("id") is not None]
    location_map = load_retreat_inventory_item_locations(conn, item_ids)
    for item in items:
        item_id = int(item["id"])
        locations = location_map.get(item_id, [])
        item["locations"] = locations
        if locations:
            item["location_summary"] = ", ".join(
                f"{loc['location_name']} ({int(loc['quantity'])})" for loc in locations
            )
            # Backward compatibility field.
            item["shelf_location"] = locations[0]["location_name"]
        else:
            item["location_summary"] = None
            item["shelf_location"] = item.get("shelf_location")
    return items


@app.get("/api/retreat-inventory/categories")
def list_retreat_inventory_categories(
    _user: Annotated[AuthUser, Depends(require_roles(ROLE_PLANNER, ROLE_ADMIN))],
    include_inactive: bool = Query(default=False),
) -> list[dict[str, Any]]:
    filters = ["deleted_at IS NULL"]
    if not include_inactive:
        filters.append("active = 1")
    where_sql = f"WHERE {' AND '.join(filters)}"
    with get_connection() as conn:
        rows = conn.execute(
            f"""
            SELECT id, name, tracking_mode, image_url, active, created_at, updated_at
            FROM retreat_inventory_categories
            {where_sql}
            ORDER BY lower(name), id
            """
        ).fetchall()
    return [format_retreat_inventory_category_row(row) for row in rows]


@app.post("/api/retreat-inventory/categories", status_code=201)
def create_retreat_inventory_category(
    payload: RetreatInventoryCategoryCreate,
    _user: Annotated[AuthUser, Depends(require_roles(ROLE_ADMIN))],
) -> dict[str, Any]:
    name = payload.name.strip()
    image_url = normalize_optional_text(payload.imageUrl)
    with get_connection() as conn:
        try:
            row = conn.execute(
                """
                INSERT INTO retreat_inventory_categories(
                    name, tracking_mode, image_url, active, created_at, updated_at
                )
                VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                RETURNING id, name, tracking_mode, image_url, active, created_at, updated_at
                """,
                (name, payload.trackingMode, image_url),
            ).fetchone()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Could not create category: {exc}") from exc
        conn.commit()
    return format_retreat_inventory_category_row(row)


@app.patch("/api/retreat-inventory/categories/{category_id}")
def update_retreat_inventory_category(
    category_id: int,
    payload: RetreatInventoryCategoryUpdate,
    _user: Annotated[AuthUser, Depends(require_roles(ROLE_ADMIN))],
) -> dict[str, Any]:
    updates: list[str] = []
    params: list[Any] = []

    if payload.name is not None:
        clean_name = payload.name.strip()
        if not clean_name:
            raise HTTPException(status_code=400, detail="Category name cannot be blank.")
        updates.append("name = ?")
        params.append(clean_name)
    if payload.trackingMode is not None:
        updates.append("tracking_mode = ?")
        params.append(payload.trackingMode)
    if payload.imageUrl is not None:
        updates.append("image_url = ?")
        params.append(normalize_optional_text(payload.imageUrl))
    if payload.active is not None:
        updates.append("active = ?")
        params.append(1 if payload.active else 0)

    with get_connection() as conn:
        existing = conn.execute(
            "SELECT id FROM retreat_inventory_categories WHERE id = ? AND deleted_at IS NULL",
            (category_id,),
        ).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Category not found")

        if updates:
            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(category_id)
            try:
                conn.execute(
                    f"""
                    UPDATE retreat_inventory_categories
                    SET {', '.join(updates)}
                    WHERE id = ?
                    """,
                    tuple(params),
                )
            except Exception as exc:
                raise HTTPException(status_code=400, detail=f"Could not update category: {exc}") from exc

        row = conn.execute(
            """
            SELECT id, name, tracking_mode, image_url, active, created_at, updated_at
            FROM retreat_inventory_categories
            WHERE id = ?
            """,
            (category_id,),
        ).fetchone()
        conn.commit()

    return format_retreat_inventory_category_row(row)


@app.get("/api/retreat-inventory/locations")
def list_retreat_inventory_locations(
    _user: Annotated[AuthUser, Depends(require_roles(ROLE_PLANNER, ROLE_ADMIN))],
    include_inactive: bool = Query(default=False),
) -> list[dict[str, Any]]:
    filters = ["deleted_at IS NULL"]
    if not include_inactive:
        filters.append("active = 1")
    where_sql = f"WHERE {' AND '.join(filters)}"
    with get_connection() as conn:
        rows = conn.execute(
            f"""
            SELECT id, name, description, active, created_at, updated_at
            FROM retreat_inventory_locations
            {where_sql}
            ORDER BY lower(name), id
            """
        ).fetchall()
    return [format_retreat_inventory_location_row(row) for row in rows]


@app.post("/api/retreat-inventory/locations", status_code=201)
def create_retreat_inventory_location(
    payload: RetreatInventoryLocationCreate,
    _user: Annotated[AuthUser, Depends(require_roles(ROLE_ADMIN))],
) -> dict[str, Any]:
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Location name is required.")

    with get_connection() as conn:
        try:
            row = conn.execute(
                """
                INSERT INTO retreat_inventory_locations(
                    name,
                    description,
                    active,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                RETURNING id, name, description, active, created_at, updated_at
                """,
                (
                    name,
                    normalize_optional_text(payload.description),
                    1 if payload.active else 0,
                ),
            ).fetchone()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Could not create location: {exc}") from exc
        conn.commit()
    return format_retreat_inventory_location_row(row)


@app.patch("/api/retreat-inventory/locations/{location_id}")
def update_retreat_inventory_location(
    location_id: int,
    payload: RetreatInventoryLocationUpdate,
    _user: Annotated[AuthUser, Depends(require_roles(ROLE_ADMIN))],
) -> dict[str, Any]:
    updates: list[str] = []
    params: list[Any] = []

    if payload.name is not None:
        name = payload.name.strip()
        if not name:
            raise HTTPException(status_code=400, detail="Location name cannot be blank.")
        updates.append("name = ?")
        params.append(name)
    if payload.description is not None:
        updates.append("description = ?")
        params.append(normalize_optional_text(payload.description))
    if payload.active is not None:
        updates.append("active = ?")
        params.append(1 if payload.active else 0)

    with get_connection() as conn:
        existing = conn.execute(
            "SELECT id FROM retreat_inventory_locations WHERE id = ? AND deleted_at IS NULL",
            (location_id,),
        ).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Location not found")

        if updates:
            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(location_id)
            try:
                conn.execute(
                    f"""
                    UPDATE retreat_inventory_locations
                    SET {', '.join(updates)}
                    WHERE id = ?
                    """,
                    tuple(params),
                )
            except Exception as exc:
                raise HTTPException(status_code=400, detail=f"Could not update location: {exc}") from exc

        row = conn.execute(
            """
            SELECT id, name, description, active, created_at, updated_at
            FROM retreat_inventory_locations
            WHERE id = ?
            """,
            (location_id,),
        ).fetchone()
        conn.commit()
    return format_retreat_inventory_location_row(row)


@app.get("/api/retreat-inventory/items")
def list_retreat_inventory_items(
    _user: Annotated[AuthUser, Depends(require_roles(ROLE_PLANNER, ROLE_ADMIN))],
    category_id: int | None = Query(default=None, ge=1),
    search: str | None = Query(default=None),
    barcode: str | None = Query(default=None),
    include_inactive: bool = Query(default=False),
) -> list[dict[str, Any]]:
    filters = ["i.deleted_at IS NULL", "c.deleted_at IS NULL"]
    params: list[Any] = []
    if category_id is not None:
        filters.append("i.category_id = ?")
        params.append(category_id)
    if search and search.strip():
        term = f"%{search.strip().lower()}%"
        filters.append(
            """(
                lower(i.name) LIKE ?
                OR lower(COALESCE(i.brand, '')) LIKE ?
                OR lower(COALESCE(i.purchase_url, '')) LIKE ?
                OR lower(COALESCE(i.unit, '')) LIKE ?
                OR EXISTS (
                    SELECT 1
                    FROM retreat_inventory_item_locations il
                    JOIN retreat_inventory_locations l ON l.id = il.location_id
                    WHERE il.item_id = i.id
                      AND l.deleted_at IS NULL
                      AND lower(l.name) LIKE ?
                )
            )"""
        )
        params.extend([term, term, term, term, term])
    if barcode and barcode.strip():
        filters.append("i.barcode = ?")
        params.append(barcode.strip())
    if not include_inactive:
        filters.append("i.active = 1")
        filters.append("c.active = 1")

    where_sql = f"WHERE {' AND '.join(filters)}"
    with get_connection() as conn:
        rows = conn.execute(
            f"""
            SELECT
                i.id,
                i.name,
                i.barcode,
                i.category_id,
                i.shelf_location,
                i.unit,
                i.purchase_url,
                i.brand,
                i.description,
                i.image_url,
                i.active,
                i.created_at,
                i.updated_at,
                c.name AS category_name,
                c.tracking_mode
            FROM retreat_inventory_items i
            JOIN retreat_inventory_categories c ON c.id = i.category_id
            {where_sql}
            ORDER BY lower(i.name), i.id
            """,
            tuple(params),
        ).fetchall()
        items = [format_retreat_inventory_item_row(row) for row in rows]
        return attach_retreat_inventory_item_locations(conn, items)


@app.post("/api/retreat-inventory/items", status_code=201)
def create_retreat_inventory_item(
    payload: RetreatInventoryItemCreate,
    _user: Annotated[AuthUser, Depends(require_roles(ROLE_ADMIN))],
) -> dict[str, Any]:
    name = payload.name.strip()
    barcode = payload.barcode.strip()
    if not barcode:
        raise HTTPException(status_code=400, detail="Barcode is required.")

    with get_connection() as conn:
        category = conn.execute(
            """
            SELECT id
            FROM retreat_inventory_categories
            WHERE id = ? AND deleted_at IS NULL
            """,
            (payload.categoryId,),
        ).fetchone()
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")

        normalized_locations = validate_retreat_item_location_inputs(conn, payload.locations)
        legacy_shelf_location = normalize_optional_text(payload.shelfLocation)
        if not normalized_locations and legacy_shelf_location:
            location_id = ensure_retreat_inventory_location(conn, legacy_shelf_location)
            normalized_locations = [
                {
                    "location_id": location_id,
                    "location_name": legacy_shelf_location,
                    "quantity": 0,
                }
            ]
        shelf_location_value = (
            normalized_locations[0]["location_name"] if normalized_locations else legacy_shelf_location
        )

        try:
            row = conn.execute(
                """
                INSERT INTO retreat_inventory_items(
                    name,
                    barcode,
                    category_id,
                    shelf_location,
                    unit,
                    purchase_url,
                    brand,
                    description,
                    image_url,
                    active,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                RETURNING id
                """,
                (
                    name,
                    barcode,
                    payload.categoryId,
                    shelf_location_value,
                    normalize_item_unit(payload.unit),
                    normalize_optional_text(payload.purchaseUrl),
                    normalize_optional_text(payload.brand),
                    normalize_optional_text(payload.description),
                    normalize_optional_text(payload.imageUrl),
                    1 if payload.active else 0,
                ),
            ).fetchone()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Could not create item: {exc}") from exc

        item_id = int(row["id"])
        replace_retreat_item_locations(conn, item_id, normalized_locations)
        sync_retreat_item_level_from_locations(conn, item_id)
        item = conn.execute(
            """
            SELECT
                i.id,
                i.name,
                i.barcode,
                i.category_id,
                i.shelf_location,
                i.unit,
                i.purchase_url,
                i.brand,
                i.description,
                i.image_url,
                i.active,
                i.created_at,
                i.updated_at,
                c.name AS category_name,
                c.tracking_mode
            FROM retreat_inventory_items i
            JOIN retreat_inventory_categories c ON c.id = i.category_id
            WHERE i.id = ?
            """,
            (item_id,),
        ).fetchone()
        item_payload = format_retreat_inventory_item_row(item)
        attach_retreat_inventory_item_locations(conn, [item_payload])
        conn.commit()

    return item_payload


@app.patch("/api/retreat-inventory/items/{item_id}")
def update_retreat_inventory_item(
    item_id: int,
    payload: RetreatInventoryItemUpdate,
    _user: Annotated[AuthUser, Depends(require_roles(ROLE_ADMIN))],
) -> dict[str, Any]:
    updates: list[str] = []
    params: list[Any] = []
    replace_locations = False
    normalized_locations: list[dict[str, Any]] | None = None

    if payload.name is not None:
        clean_name = payload.name.strip()
        if not clean_name:
            raise HTTPException(status_code=400, detail="Item name cannot be blank.")
        updates.append("name = ?")
        params.append(clean_name)
    if payload.barcode is not None:
        clean_barcode = payload.barcode.strip()
        if not clean_barcode:
            raise HTTPException(status_code=400, detail="Barcode cannot be blank.")
        updates.append("barcode = ?")
        params.append(clean_barcode)
    if payload.categoryId is not None:
        updates.append("category_id = ?")
        params.append(payload.categoryId)
    if payload.unit is not None:
        updates.append("unit = ?")
        params.append(normalize_item_unit(payload.unit))
    if payload.purchaseUrl is not None:
        updates.append("purchase_url = ?")
        params.append(normalize_optional_text(payload.purchaseUrl))
    if payload.brand is not None:
        updates.append("brand = ?")
        params.append(normalize_optional_text(payload.brand))
    if payload.description is not None:
        updates.append("description = ?")
        params.append(normalize_optional_text(payload.description))
    if payload.imageUrl is not None:
        updates.append("image_url = ?")
        params.append(normalize_optional_text(payload.imageUrl))
    if payload.active is not None:
        updates.append("active = ?")
        params.append(1 if payload.active else 0)

    with get_connection() as conn:
        existing = conn.execute(
            "SELECT id FROM retreat_inventory_items WHERE id = ? AND deleted_at IS NULL",
            (item_id,),
        ).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Item not found")

        if payload.categoryId is not None:
            category = conn.execute(
                """
                SELECT id
                FROM retreat_inventory_categories
                WHERE id = ? AND deleted_at IS NULL
                """,
                (payload.categoryId,),
            ).fetchone()
            if not category:
                raise HTTPException(status_code=404, detail="Category not found")

        if payload.locations is not None:
            normalized_locations = validate_retreat_item_location_inputs(conn, payload.locations)
            replace_locations = True
        elif payload.shelfLocation is not None:
            legacy_shelf_location = normalize_optional_text(payload.shelfLocation)
            if legacy_shelf_location:
                location_id = ensure_retreat_inventory_location(conn, legacy_shelf_location)
                normalized_locations = [
                    {
                        "location_id": location_id,
                        "location_name": legacy_shelf_location,
                        "quantity": 0,
                    }
                ]
            else:
                normalized_locations = []
            replace_locations = True

        if replace_locations:
            shelf_location_value = (
                normalized_locations[0]["location_name"] if normalized_locations else None
            )
            updates.append("shelf_location = ?")
            params.append(shelf_location_value)

        if updates:
            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(item_id)
            try:
                conn.execute(
                    f"""
                    UPDATE retreat_inventory_items
                    SET {', '.join(updates)}
                    WHERE id = ?
                    """,
                    tuple(params),
                )
            except Exception as exc:
                raise HTTPException(status_code=400, detail=f"Could not update item: {exc}") from exc

        if replace_locations and normalized_locations is not None:
            replace_retreat_item_locations(conn, item_id, normalized_locations)
            sync_retreat_item_level_from_locations(conn, item_id)

        row = conn.execute(
            """
            SELECT
                i.id,
                i.name,
                i.barcode,
                i.category_id,
                i.shelf_location,
                i.unit,
                i.purchase_url,
                i.brand,
                i.description,
                i.image_url,
                i.active,
                i.created_at,
                i.updated_at,
                c.name AS category_name,
                c.tracking_mode
            FROM retreat_inventory_items i
            JOIN retreat_inventory_categories c ON c.id = i.category_id
            WHERE i.id = ?
            """,
            (item_id,),
        ).fetchone()
        item_payload = format_retreat_inventory_item_row(row)
        attach_retreat_inventory_item_locations(conn, [item_payload])
        conn.commit()

    return item_payload


@app.get("/api/retreat-inventory/levels")
def list_retreat_inventory_levels(
    _user: Annotated[AuthUser, Depends(require_roles(ROLE_PLANNER, ROLE_ADMIN))],
) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                ril.id,
                ril.item_id,
                ril.category_id,
                ril.quantity,
                ril.min_threshold,
                ril.updated_at,
                i.name AS item_name,
                i.barcode AS item_barcode,
                i.unit AS item_unit,
                i.image_url AS item_image_url,
                c.id AS category_row_id,
                c.name AS category_name,
                c.tracking_mode
            FROM retreat_inventory_levels ril
            LEFT JOIN retreat_inventory_items i ON i.id = ril.item_id
            LEFT JOIN retreat_inventory_categories c
              ON c.id = COALESCE(ril.category_id, i.category_id)
            WHERE (i.deleted_at IS NULL OR i.id IS NULL)
              AND (c.deleted_at IS NULL OR c.id IS NULL)
            ORDER BY lower(COALESCE(i.name, c.name, '')), ril.id
            """
        ).fetchall()
        item_ids = [int(row["item_id"]) for row in rows if row["item_id"] is not None]
        location_map = load_retreat_inventory_item_locations(conn, item_ids)

    result: list[dict[str, Any]] = []
    for row in rows:
        item_id_value = row["item_id"]
        category_id_value = row["category_id"] if row["category_id"] is not None else row["category_row_id"]
        entity_type = "ITEM" if item_id_value is not None else "CATEGORY"
        item_locations = location_map.get(int(item_id_value), []) if item_id_value is not None else []
        item_shelf_location = item_locations[0]["location_name"] if item_locations else None
        location_summary = (
            ", ".join(f"{loc['location_name']} ({int(loc['quantity'])})" for loc in item_locations)
            if item_locations
            else None
        )
        result.append(
            {
                "id": int(row["id"]),
                "entity_type": entity_type,
                "item_id": int(item_id_value) if item_id_value is not None else None,
                "category_id": int(category_id_value) if category_id_value is not None else None,
                "item_name": row["item_name"],
                "item_barcode": row["item_barcode"],
                "item_shelf_location": item_shelf_location,
                "item_locations": item_locations,
                "location_summary": location_summary,
                "item_unit": row["item_unit"],
                "item_image_url": row["item_image_url"],
                "category_name": row["category_name"],
                "tracking_mode": row["tracking_mode"],
                "quantity": int(row["quantity"] or 0),
                "min_threshold": int(row["min_threshold"] or 0),
                "is_low_stock": int(row["quantity"] or 0) <= int(row["min_threshold"] or 0),
                "updated_at": row["updated_at"],
            }
        )
    return result


@app.get("/api/retreat-inventory/transactions")
def list_retreat_inventory_transactions(
    _user: Annotated[AuthUser, Depends(require_roles(ROLE_PLANNER, ROLE_ADMIN))],
    limit: int = Query(default=100, ge=1, le=500),
) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                rit.id,
                rit.entity_type,
                rit.entity_id,
                rit.transaction_type,
                rit.quantity,
                rit.reason,
                rit.barcode,
                rit.created_at,
                u.username AS user_name,
                i.name AS item_name,
                c.name AS category_name
            FROM retreat_inventory_transactions rit
            LEFT JOIN users u ON u.id = rit.user_id
            LEFT JOIN retreat_inventory_items i
              ON rit.entity_type = 'ITEM'
             AND i.id = rit.entity_id
            LEFT JOIN retreat_inventory_categories c
              ON rit.entity_type = 'CATEGORY'
             AND c.id = rit.entity_id
            ORDER BY rit.id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [
        {
            "id": int(row["id"]),
            "entity_type": row["entity_type"],
            "entity_id": int(row["entity_id"]),
            "entity_name": row["item_name"] if row["entity_type"] == "ITEM" else row["category_name"],
            "transaction_type": row["transaction_type"],
            "quantity": int(row["quantity"]),
            "reason": row["reason"],
            "barcode": row["barcode"],
            "user_name": row["user_name"],
            "created_at": row["created_at"],
        }
        for row in rows
    ]


@app.post("/api/retreat-inventory/scan")
def scan_retreat_inventory(
    payload: RetreatInventoryScanPayload,
    user: Annotated[AuthUser, Depends(require_roles(ROLE_PLANNER, ROLE_ADMIN))],
) -> dict[str, Any]:
    barcode = payload.barcode.strip()
    if not barcode:
        raise HTTPException(status_code=400, detail="Barcode is required.")

    tx_type = payload.transactionType
    quantity = int(payload.quantity)
    if tx_type in {"IN", "OUT"} and quantity <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be greater than zero for IN/OUT scans.")
    if tx_type == "ADJUSTMENT" and quantity == 0:
        raise HTTPException(status_code=400, detail="Quantity cannot be zero for adjustments.")

    with get_connection() as conn:
        item = conn.execute(
            """
            SELECT
                i.id,
                i.name,
                i.barcode,
                i.image_url,
                i.shelf_location,
                i.unit,
                i.purchase_url,
                i.active AS item_active,
                c.id AS category_id,
                c.name AS category_name,
                c.tracking_mode,
                c.active AS category_active
            FROM retreat_inventory_items i
            JOIN retreat_inventory_categories c ON c.id = i.category_id
            WHERE i.barcode = ?
              AND i.deleted_at IS NULL
              AND c.deleted_at IS NULL
            """,
            (barcode,),
        ).fetchone()
        if not item:
            raise HTTPException(status_code=404, detail=f"Barcode {barcode} not found.")
        if not as_active_flag(item["item_active"]):
            raise HTTPException(status_code=400, detail="Item is inactive.")
        if not as_active_flag(item["category_active"]):
            raise HTTPException(status_code=400, detail="Item category is inactive.")

        tracking_mode = str(item["tracking_mode"] or "ITEM").upper()
        entity_type = "CATEGORY" if tracking_mode == "CATEGORY" else "ITEM"
        entity_id = int(item["category_id"]) if entity_type == "CATEGORY" else int(item["id"])
        item_id = int(item["id"])

        item_locations = load_retreat_inventory_item_locations(conn, [item_id]).get(item_id, [])
        selected_location_id: int | None = None
        selected_location_name: str | None = None
        if entity_type == "ITEM":
            if payload.locationId is None and len(item_locations) > 1:
                raise HTTPException(
                    status_code=400,
                    detail="Select a location when scanning an item stored in multiple locations.",
                )
            if payload.locationId is not None:
                location = conn.execute(
                    """
                    SELECT id, name, active
                    FROM retreat_inventory_locations
                    WHERE id = ?
                      AND deleted_at IS NULL
                    """,
                    (payload.locationId,),
                ).fetchone()
                if not location:
                    raise HTTPException(status_code=404, detail=f"Location {payload.locationId} not found.")
                if not as_active_flag(location["active"]):
                    raise HTTPException(status_code=400, detail=f"Location {location['name']} is inactive.")
                selected_location_id = int(location["id"])
                selected_location_name = location["name"]
            elif len(item_locations) == 1:
                selected_location_id = int(item_locations[0]["location_id"])
                selected_location_name = item_locations[0]["location_name"]
        elif payload.locationId is not None:
            raise HTTPException(
                status_code=400,
                detail="Location cannot be applied when this item uses CATEGORY tracking mode.",
            )

        lock_clause = " FOR UPDATE" if getattr(conn, "backend", "sqlite") == "postgres" else ""
        if entity_type == "ITEM":
            level_where = "item_id = ? AND category_id IS NULL"
            level_params: tuple[Any, ...] = (entity_id,)
            insert_params: tuple[Any, ...] = (entity_id, None)
        else:
            level_where = "category_id = ? AND item_id IS NULL"
            level_params = (entity_id,)
            insert_params = (None, entity_id)

        level = conn.execute(
            f"""
            SELECT id, quantity, min_threshold
            FROM retreat_inventory_levels
            WHERE {level_where}{lock_clause}
            """,
            level_params,
        ).fetchone()
        if not level:
            try:
                conn.execute(
                    """
                    INSERT INTO retreat_inventory_levels(item_id, category_id, quantity, min_threshold, updated_at)
                    VALUES (?, ?, 0, 0, CURRENT_TIMESTAMP)
                    """,
                    insert_params,
                )
            except Exception:
                # Another request can create the row concurrently; read it again below.
                pass
            level = conn.execute(
                f"""
                SELECT id, quantity, min_threshold
                FROM retreat_inventory_levels
                WHERE {level_where}{lock_clause}
                """,
                level_params,
            ).fetchone()
        if not level:
            raise HTTPException(status_code=500, detail="Could not initialize inventory level row.")

        previous_quantity = int(level["quantity"] or 0)
        if tx_type == "IN":
            delta = quantity
        elif tx_type == "OUT":
            delta = -quantity
        else:
            delta = quantity
        next_quantity = previous_quantity + delta
        if next_quantity < 0:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient inventory: current quantity is {previous_quantity}.",
            )

        conn.execute(
            """
            UPDATE retreat_inventory_levels
            SET quantity = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (next_quantity, int(level["id"])),
        )

        location_quantity_after: int | None = None
        if entity_type == "ITEM" and selected_location_id is not None:
            level_location = conn.execute(
                f"""
                SELECT id, quantity
                FROM retreat_inventory_item_locations
                WHERE item_id = ?
                  AND location_id = ?{lock_clause}
                """,
                (item_id, selected_location_id),
            ).fetchone()
            if not level_location:
                conn.execute(
                    """
                    INSERT INTO retreat_inventory_item_locations(
                        item_id,
                        location_id,
                        quantity,
                        created_at,
                        updated_at
                    )
                    VALUES (?, ?, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """,
                    (item_id, selected_location_id),
                )
                level_location = conn.execute(
                    f"""
                    SELECT id, quantity
                    FROM retreat_inventory_item_locations
                    WHERE item_id = ?
                      AND location_id = ?{lock_clause}
                    """,
                    (item_id, selected_location_id),
                ).fetchone()

            previous_location_quantity = int(level_location["quantity"] or 0)
            location_quantity_after = previous_location_quantity + delta
            if location_quantity_after < 0:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Insufficient inventory at location {selected_location_name}: "
                        f"current quantity is {previous_location_quantity}."
                    ),
                )
            conn.execute(
                """
                UPDATE retreat_inventory_item_locations
                SET quantity = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (location_quantity_after, int(level_location["id"])),
            )

        item_locations = load_retreat_inventory_item_locations(conn, [item_id]).get(item_id, [])
        item_shelf_location = item_locations[0]["location_name"] if item_locations else item["shelf_location"]

        tx_row = conn.execute(
            """
            INSERT INTO retreat_inventory_transactions(
                entity_type,
                entity_id,
                transaction_type,
                quantity,
                reason,
                user_id,
                barcode,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            RETURNING id, created_at
            """,
            (
                entity_type,
                entity_id,
                tx_type,
                quantity,
                normalize_optional_text(payload.reason),
                user.id,
                barcode,
            ),
        ).fetchone()
        conn.commit()

    entity_name = item["category_name"] if entity_type == "CATEGORY" else item["name"]
    return {
        "transaction_id": int(tx_row["id"]),
        "created_at": tx_row["created_at"],
        "barcode": barcode,
        "item": {
            "id": int(item["id"]),
            "name": item["name"],
            "image_url": item["image_url"],
            "shelf_location": item_shelf_location,
            "locations": item_locations,
            "unit": item["unit"],
            "purchase_url": item["purchase_url"],
            "category_id": int(item["category_id"]),
            "category_name": item["category_name"],
            "tracking_mode": tracking_mode,
        },
        "location": (
            {
                "id": selected_location_id,
                "name": selected_location_name,
                "quantity_after": location_quantity_after,
            }
            if selected_location_id is not None
            else None
        ),
        "entity": {
            "type": entity_type,
            "id": entity_id,
            "name": entity_name,
        },
        "transaction_type": tx_type,
        "quantity": quantity,
        "delta": delta,
        "quantity_before": previous_quantity,
        "quantity_after": next_quantity,
    }


@app.get("/api/inventory")
def list_inventory(
    _user: Annotated[AuthUser, Depends(require_roles(ROLE_PLANNER, ROLE_ADMIN))],
    category: str | None = Query(default=None),
    search: str | None = Query(default=None),
) -> list[dict[str, Any]]:
    filters: list[str] = []
    params: list[Any] = []
    if category and category.strip():
        filters.append("lower(category) = lower(?)")
        params.append(category.strip())
    if search and search.strip():
        filters.append("lower(item_name) LIKE ?")
        params.append(f"%{search.strip().lower()}%")
    where_sql = f"WHERE {' AND '.join(filters)}" if filters else ""
    with get_connection() as conn:
        rows = conn.execute(
            f"SELECT * FROM standalone_inventory {where_sql} ORDER BY lower(item_name)",
            tuple(params),
        ).fetchall()
    return [dict(r) for r in rows]


@app.get("/api/inventory/categories")
def list_inventory_categories(
    _user: Annotated[AuthUser, Depends(require_roles(ROLE_PLANNER, ROLE_ADMIN))],
) -> list[str]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT DISTINCT category FROM standalone_inventory WHERE category IS NOT NULL AND category != '' ORDER BY lower(category)"
        ).fetchall()
    return [row["category"] for row in rows]


@app.post("/api/inventory", status_code=201)
def create_inventory_item(
    payload: StandaloneInventoryCreate,
    _user: Annotated[AuthUser, Depends(require_roles(ROLE_PLANNER, ROLE_ADMIN))],
) -> dict[str, Any]:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    with get_connection() as conn:
        row = conn.execute(
            """
            INSERT INTO standalone_inventory(item_name, quantity, unit, category, location, notes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            RETURNING *
            """,
            (
                payload.item_name.strip(),
                payload.quantity,
                (payload.unit or "").strip() or None,
                (payload.category or "").strip() or None,
                (payload.location or "").strip() or None,
                (payload.notes or "").strip() or None,
                now,
                now,
            ),
        ).fetchone()
        conn.commit()
    return dict(row)


@app.put("/api/inventory/{item_id}")
def update_inventory_item(
    item_id: int,
    payload: StandaloneInventoryUpdate,
    _user: Annotated[AuthUser, Depends(require_roles(ROLE_PLANNER, ROLE_ADMIN))],
) -> dict[str, Any]:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    with get_connection() as conn:
        existing = conn.execute("SELECT id FROM standalone_inventory WHERE id = ?", (item_id,)).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Inventory item not found")
        conn.execute(
            """
            UPDATE standalone_inventory
            SET item_name = ?, quantity = ?, unit = ?, category = ?, location = ?, notes = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                payload.item_name.strip(),
                payload.quantity,
                (payload.unit or "").strip() or None,
                (payload.category or "").strip() or None,
                (payload.location or "").strip() or None,
                (payload.notes or "").strip() or None,
                now,
                item_id,
            ),
        )
        row = conn.execute("SELECT * FROM standalone_inventory WHERE id = ?", (item_id,)).fetchone()
        conn.commit()
    return dict(row)


@app.delete("/api/inventory/{item_id}")
def delete_inventory_item(
    item_id: int,
    _user: Annotated[AuthUser, Depends(require_roles(ROLE_PLANNER, ROLE_ADMIN))],
) -> dict[str, Any]:
    with get_connection() as conn:
        existing = conn.execute("SELECT id, item_name FROM standalone_inventory WHERE id = ?", (item_id,)).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Inventory item not found")
        conn.execute("DELETE FROM standalone_inventory WHERE id = ?", (item_id,))
        conn.commit()
    return {"id": item_id, "item_name": existing["item_name"], "status": "deleted"}


if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
