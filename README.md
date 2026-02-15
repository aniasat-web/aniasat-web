# Retreat Ops Web

Standalone local web app for retreat recipe planning, scaling, inventory, and shopping.

## Why this app
This replaces spreadsheet-heavy workflows with structured data and predictable calculations:
- Define recipes at base servings (e.g., 4 or 6 people).
- Scale recipes to actual attendee counts.
- Convert kitchen units (cup/tbsp/tsp) to planning/purchase units (g/kg/lb/oz/ml/l).
- Compare required quantities vs inventory.
- Generate a shopping list grouped by vendor and status.

## Project layout
- `backend/`: FastAPI API + SQLite data model
- `frontend/`: simple browser UI consuming backend APIs

## Quick start
1. Create a virtual environment in `backend/` and install dependencies.
2. Start backend API on port `8000`.
3. Open `frontend/index.html` in a browser.

Example:
```bash
cd backend
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Then open `frontend/index.html` and use the scaling form.

## Import from existing Excel
### Import all recipes (recommended)
This imports recipe definitions from all currently supported tabs:
- `Common Recipes`
- `KY1 + Upa`
- `KY2 + KY3`
- `Pranams`

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
To version recipe and conversion master data (while excluding retreat plans/service snapshots), use:

### Export current DB master data
```bash
cd backend
. .venv/bin/activate
python scripts/export_master_data.py --out seeds/master_data.json
```

### Import/upsert master data into DB
```bash
cd backend
. .venv/bin/activate
python scripts/import_master_data.py --seed seeds/master_data.json
```

### Validate import without writing
```bash
python scripts/import_master_data.py --seed seeds/master_data.json --dry-run
```

What is included:
- `ingredients`
- `unit_conversions`
- `recipes` + `recipe_ingredients` + `recipe_steps`

What is excluded:
- retreat plans
- kitchen/service snapshots
- shopping/inventory operational records

## Current status
This is an MVP scaffold with:
- Core schema for recipes, ingredients, inventory, retreats, and shopping.
- Scaling endpoint with unit normalization logic.
- Excel import scripts for bootstrapping from your existing workbook.

Next steps:
1. Add authentication/roles.
2. Build full recipe CRUD UI.
3. Add retreat menu planning UI.
4. Add inventory + shopping workflows.
5. Add import validation/reporting UI.
