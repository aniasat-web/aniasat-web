# Retreat Ops Web

Standalone local web app for retreat recipe planning, scaling, inventory, and shopping. Replaces spreadsheet-heavy workflows with structured data and predictable calculations.

## Why this app

- Define recipes at base servings (e.g., 4 or 6 people).
- Plan multi-day retreat menus with per-meal headcounts.
- Scale recipes automatically to actual attendee counts.
- Convert kitchen units (cup/tbsp/tsp) to purchase units (g/kg/lb/oz/ml/l).
- Publish scaled menus to a kitchen display for live service.

## Quick start

```bash
cd backend
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Then open `frontend/retreat-planner-sample.html` in a browser. The frontend resolves the API base from `window.location.origin` or the `?api=` query parameter.

## Project layout

```
retreat-ops-web/
├── backend/
│   ├── app/
│   │   ├── main.py             FastAPI app, all endpoints and scaling logic
│   │   ├── db.py               SQLite connection and schema initialization
│   │   ├── schema.sql          Database schema (tables + migrations)
│   │   └── usda.py             USDA FoodData Central density lookups
│   ├── data/
│   │   └── retreat_ops.db      SQLite database (auto-created on startup)
│   ├── seeds/
│   │   └── master_data.json    Exportable recipe/ingredient master data
│   ├── scripts/                Import/export CLI utilities
│   └── requirements.txt
├── frontend/
│   ├── retreat-planner-sample.html   Retreat menu planner
│   ├── kitchen-service-view.html     Kitchen display (read-only)
│   ├── recipe-admin.html             Recipe CRUD editor
│   ├── recipe-scaling.html           Ad-hoc scaling preview
│   ├── app.js                        Shared JS for scaling page
│   └── assets/                       Logo images
└── README.md
```

---

## Frontend pages

### Retreat Planner (`retreat-planner-sample.html`)

Main planning interface. Users create a retreat by entering a name, start date, number of days (1-10), and a default headcount. Clicking "Build Schedule" generates day cards, each with four meal slots: Breakfast, Lunch, Dinner, and Evening Chai. Dishes are selected from the recipe catalog via searchable dropdowns (Tom Select). Headcount can be adjusted per meal.

Changes auto-save to the backend (1.2s debounce). Saved plans appear in a datalist on the retreat name input so returning users can select and reload them. Plans can be duplicated.

When a plan is saved, a kitchen snapshot is auto-published so the kitchen page always reflects the latest menu. A shareable URL with `?plan={id}` links directly to that plan's kitchen view.

### Kitchen Service View (`kitchen-service-view.html`)

Read-only display for kitchen staff during live service. Shows the latest published menu or a specific plan via `?plan={id}`. Organized by day tabs and meal tabs. Each recipe card expands to show:

- **Ingredients tab** -- scaled quantities ready to cook (with shopping-friendly units like kg/l).
- **Instructions tab** -- numbered cooking steps.

Supports print layout (hides nav, shows only the active meal).

### Recipe Admin (`recipe-admin.html`)

Full CRUD interface for the recipe catalog. Left panel lists all recipes with search and category filtering. Right panel is a form to create or edit a dish:

- Name, category (from a fixed list), base servings, notes.
- Ingredients table: name, quantity, unit, prep notes. Rows can be added/removed.
- Cooking steps: ordered textareas with numbered circles.

Saves via POST (create) or PUT (update). Ctrl+S shortcut supported.

### Recipe Scaling Preview (`recipe-scaling.html`)

Standalone ad-hoc scaling tool. Enter base servings, target servings, and a list of ingredients. Calls `POST /api/scale-preview` and displays the scaled output with canonical and shopping-friendly units.

---

## Workflow

### 1. Create recipes (Recipe Admin)

```
Recipe Admin page
  → Enter dish name, category, base servings
  → Add ingredients (name, qty, unit, prep notes)
  → Add cooking steps
  → Save  →  POST /api/recipes  →  recipes, recipe_ingredients, recipe_steps tables
              (new ingredients auto-created; USDA density lookup runs)
```

### 2. Plan a retreat (Planner)

```
Planner page
  → Enter retreat name, start date, days, headcount
  → Build Schedule  →  generates day cards with 4 meal slots each
  → Select dishes per meal from recipe catalog dropdown
  → Adjust headcount per meal if needed
  → Auto-save (1.2s debounce)  →  POST /api/retreat-plans  →  retreat_plans table
  → Auto-publish kitchen snapshot  →  POST /api/service-snapshots
```

### 3. Kitchen service (Kitchen View)

```
Kitchen page loads  →  GET /api/service-snapshots/latest (or /by-plan/{id})
  → Renders day/meal tabs with scaled recipe cards
  → Kitchen staff expands cards to see ingredients + steps
  → Reload button fetches latest snapshot
```

### 4. Scaling pipeline (how quantities are computed)

When the planner publishes to kitchen, each recipe is scaled:

```
scale_factor = meal_headcount / recipe.base_servings

For each ingredient:
  scaled_qty = ingredient.quantity * scale_factor
      ↓
  normalize unit (cups→cup, tbs→tbsp, gms→g)
      ↓
  to_canonical: convert to grams or ml
    - mass units (g, kg, lb, oz) → multiply by MASS_TO_G factor → grams
    - volume units (cup, tbsp, tsp, ml, l) → if grams_per_cup known for ingredient,
        convert to grams; otherwise convert to ml
    - count units (piece, bunch, packet) → keep as-is
      ↓
  to_shopping_unit: optimize for purchase
    - ≥1000g → kg
    - ≥1000ml → l
    - otherwise keep g or ml
```

The planner frontend performs this scaling client-side using conversion data loaded from the API at startup (`/api/unit-conversions` and `/api/ingredients`). The backend `POST /api/scale-preview` endpoint performs the same logic server-side for the scaling preview page.

---

## Database schema

All tables live in `backend/data/retreat_ops.db` (SQLite). Schema is in `backend/app/schema.sql`.

### ingredients

Master ingredient list with optional density data for unit conversion.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PK | Auto-increment |
| name | TEXT UNIQUE | Ingredient name, e.g., "Toor Dal" |
| canonical_unit | TEXT | Standard unit (g, ml, piece) |
| grams_per_cup | REAL | Density for volume-to-mass conversion |
| notes | TEXT | Optional notes |
| created_at | TIMESTAMP | Row creation time |

### recipes

Recipe definitions with base serving size.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PK | Auto-increment |
| name | TEXT UNIQUE | Recipe name |
| category | TEXT | One of the fixed category list |
| base_servings | REAL | Reference serving count (e.g., 6) |
| notes | TEXT | Optional description |
| created_at | TIMESTAMP | Row creation time |

### recipe_ingredients

Join table linking recipes to ingredients with quantities.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PK | Auto-increment |
| recipe_id | FK → recipes | Parent recipe |
| ingredient_id | FK → ingredients | Ingredient reference |
| quantity | REAL | Amount at base servings |
| unit | TEXT | Unit (g, cup, tbsp, piece, etc.) |
| prep_notes | TEXT | "diced", "chopped", etc. |

### recipe_steps

Ordered cooking instructions for a recipe.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PK | Auto-increment |
| recipe_id | FK → recipes | Parent recipe |
| step_order | INTEGER | Step sequence number |
| instruction | TEXT | Step text |

### unit_conversions

Lookup table for unit conversions, populated from Excel imports and USDA.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PK | Auto-increment |
| item_name | TEXT | Ingredient name or "generic" |
| quantity_from | REAL | Source quantity |
| unit_from | TEXT | Source unit |
| quantity_to | REAL | Target quantity |
| unit_to | TEXT | Target unit |
| context | TEXT | `ingredient_specific`, `generic_solid`, `generic_liquid`, or `usda_fdc` |
| source_sheet | TEXT | Excel sheet name (if imported) |
| source_row | INTEGER | Excel row number (if imported) |
| notes | TEXT | Optional |
| created_at | TIMESTAMP | Row creation time |

### retreat_plans

Saved retreat planning data with full meal assignments.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PK | Auto-increment |
| name | TEXT UNIQUE | Retreat name (upsert key) |
| start_date | TEXT | ISO date string |
| day_count | INTEGER | Number of days (1-10) |
| default_people | REAL | Default headcount per meal |
| plan_json | TEXT | Full meal plan as JSON |
| created_at | TIMESTAMP | Row creation time |
| updated_at | TIMESTAMP | Last update time |

The `plan_json` column stores a JSON object with a `meals` array. Each meal entry has `day`, `meal`, `people`, and `dishes` (list of recipe names).

### service_snapshots

Published kitchen menus with fully scaled recipes, ready for display.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PK | Auto-increment |
| retreat_name | TEXT | Retreat name |
| payload_json | TEXT | Full scaled menu as JSON |
| retreat_plan_id | FK → retreat_plans | Optional link to source plan |
| created_at | TIMESTAMP | Row creation time |

---

## API endpoints

Base URL: `http://localhost:8000`

### Health

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Returns `{"status": "ok"}` |

### Ingredients & conversions

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/ingredients` | List all ingredients with density data |
| GET | `/api/unit-conversions` | List all unit conversion rules |
| GET | `/api/recipe-categories` | List valid recipe categories |

### Recipes

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/recipes` | List recipes (id, name, category, base_servings) |
| GET | `/api/recipes/full` | List recipes with ingredients and steps |
| POST | `/api/recipes` | Create a new recipe |
| PUT | `/api/recipes/{recipe_id}` | Update an existing recipe |
| GET | `/api/recipes/{recipe_id}/scale?target_servings=N` | Scale a recipe from the database |

### Scaling

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/scale-preview` | Scale ad-hoc ingredients (not saved to DB) |

**Request body:**
```json
{
  "base_servings": 6,
  "target_servings": 120,
  "ingredients": [
    {"name": "Rice", "quantity": 2, "unit": "cup"}
  ]
}
```

**Response:**
```json
{
  "scale_factor": 20.0,
  "ingredients": [
    {
      "name": "Rice",
      "input_qty": 2, "input_unit": "cup",
      "scaled_qty": 40, "scaled_unit": "cup",
      "canonical_qty": 7680, "canonical_unit": "g",
      "shopping_qty": 7.68, "shopping_unit": "kg",
      "note": "..."
    }
  ]
}
```

### Retreat plans

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/retreat-plans` | List all saved retreat plans |
| GET | `/api/retreat-plans/{plan_id}` | Get a single retreat plan with meals |
| POST | `/api/retreat-plans` | Create or upsert a retreat plan (by name) |
| POST | `/api/retreat-plans/{plan_id}/duplicate` | Clone a retreat plan with a new name |

### Kitchen service snapshots

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/service-snapshots` | Publish a scaled menu for kitchen display |
| GET | `/api/service-snapshots/latest` | Get the most recently published menu |
| GET | `/api/service-snapshots/by-plan/{plan_id}` | Get the latest snapshot for a specific plan |

---

## Backend models (Pydantic)

Key request/response models defined in `backend/app/main.py`:

**RecipeCreate** -- used by POST/PUT `/api/recipes`
- `name` (str, min 1 char)
- `category` (str, from RECIPE_CATEGORIES)
- `base_servings` (float, > 0)
- `notes` (str, optional)
- `ingredients` (list of `{ingredient_name, quantity, unit, prep_notes}`)
- `steps` (list of str)

**ScalePreviewRequest** -- used by POST `/api/scale-preview`
- `base_servings` (float, > 0)
- `target_servings` (float, > 0)
- `ingredients` (list of `{name, quantity, unit}`)

**RetreatPlanPayload** -- used by POST `/api/retreat-plans`
- `name` (str)
- `startDate` (str, optional)
- `dayCount` (int, 1-10)
- `defaultPeople` (float, > 0)
- `meals` (list of `{day, meal, people, dishes}`)

**ServiceSnapshotPayload** -- used by POST `/api/service-snapshots`
- `version` (int, always 1)
- `retreatName` (str)
- `generatedAt` (str, ISO datetime)
- `retreatPlanId` (int, optional)
- `meals` (list of `{day, meal, people, dishes}`)

Each dish in a snapshot contains `name`, `serves`, `baseServings`, `factor`, `ingredients` (with `scaledQty`, `scaledUnit`, `shopQty`, `shopUnit`), and `steps`.

---

## Constants

**Recipe categories** (hardcoded in `main.py`):
M's Recipes, Breakfast, Salads, Vegetable Dishes, Dals & Stews, Khichdi & Kadhi, Rice Dishes, Desserts, Chai & Coffee, Pickles

**Meal slots** (hardcoded in planner JS):
Breakfast, Lunch, Dinner, Evening Chai

**Unit aliases** (normalized before conversion):
cups → cup, tablespoons/tbs → tbsp, teaspoons → tsp, gms → g, liters/litres → l

**Mass → grams**: g=1, kg=1000, lb=453.59, oz=28.35

**Volume → ml**: ml=1, l=1000, cup=240, tbsp=14.79, tsp=4.93

**Count units** (kept as-is): piece, pieces, packet, packets, can, cans, bunch, bunches, loaf, loaves

---

## Import from existing Excel

### Import all recipes (recommended)

Imports recipe definitions from all supported tabs: Common Recipes, KY1 + Upa, KY2 + KY3, Pranams.

```bash
cd backend
. .venv/bin/activate

# Preview only
python scripts/import_all_recipes.py \
  --xlsx /tmp/retreat_tracker.xlsx \
  --dry-run

# Write to DB, replacing same-name recipes
python scripts/import_all_recipes.py \
  --xlsx /tmp/retreat_tracker.xlsx \
  --replace-existing
```

### Import only Common Recipes tab

```bash
python scripts/import_common_recipes.py \
  --xlsx /tmp/retreat_tracker.xlsx \
  --replace-existing
```

### Import useful conversions tab

```bash
python scripts/import_useful_conversions.py \
  --xlsx /tmp/retreat_tracker.xlsx \
  --replace-existing
```

Notes:
- Non-numeric ingredient quantities such as `to taste` are skipped.
- The all-recipes importer deduplicates by recipe name and keeps the richest parsed version.
- The conversions importer stores rows in `unit_conversions` and updates ingredient `grams_per_cup` where possible.

## Master data in git (recommended)

To version recipe and conversion master data (while excluding retreat plans/service snapshots):

### Export current DB master data

```bash
cd backend
. .venv/bin/activate
python scripts/export_master_data.py --out seeds/master_data.json
```

### Import/upsert master data into DB

```bash
python scripts/import_master_data.py --seed seeds/master_data.json
```

### Validate import without writing

```bash
python scripts/import_master_data.py --seed seeds/master_data.json --dry-run
```

What is included: `ingredients`, `unit_conversions`, `recipes` + `recipe_ingredients` + `recipe_steps`.

What is excluded: retreat plans, kitchen/service snapshots, shopping/inventory operational records.

### Startup auto-seeding

- On app startup, if master tables are empty and `backend/seeds/master_data.json` exists, the app auto-imports master data.
- This keeps ephemeral SQLite deployments usable after restart.
- Disable with env var: `RETREAT_OPS_AUTO_SEED_MASTER_DATA=0`

## Current status

This is an MVP with:
- Core schema for recipes, ingredients, retreats, and kitchen snapshots.
- Scaling endpoint with unit normalization and USDA density lookups.
- Retreat planner with auto-save and auto-publish to kitchen.
- Kitchen display for live service with day/meal navigation.
- Recipe CRUD editor with category filtering.
- Excel import scripts for bootstrapping from existing workbooks.
- Master data export/import for version control.

Next steps:
1. Add authentication/roles.
2. Add inventory + shopping workflows.
3. Add import validation/reporting UI.
