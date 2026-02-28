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
export RETREAT_OPS_BOOTSTRAP_ADMIN_USERNAME=admin
export RETREAT_OPS_BOOTSTRAP_ADMIN_PASSWORD='change-this-password'
# Optional: use Postgres (recommended for concurrent scanner usage)
# export DATABASE_URL='postgresql://user:pass@host:5432/retreat_ops'
uvicorn app.main:app --reload --port 8000
```

Then open `frontend/retreat-planner-sample.html` in a browser. The frontend resolves the API base from `window.location.origin` or the `?api=` query parameter.

## Authentication and roles

The app uses cookie-based authentication.

- Login page: `/login.html`
- Session cookie: `retreat_ops_session` (`HttpOnly`, `SameSite=Lax`)
- Default session lifetime: 14 days (`RETREAT_OPS_SESSION_HOURS` to override)

Bootstrap admin:

- On startup, if no user exists and both env vars are set, the app creates an admin user:
  - `RETREAT_OPS_BOOTSTRAP_ADMIN_USERNAME`
  - `RETREAT_OPS_BOOTSTRAP_ADMIN_PASSWORD`
  - If `RETREAT_OPS_BOOTSTRAP_ADMIN_USERNAME` is unset, it defaults to `admin`.

Roles:

- `viewer`: kitchen + scaling read access
- `planner`: viewer access + retreat plan create/update/publish
- `admin`: planner access + recipe CRUD + user management APIs

## Project layout

```
retreat-ops-web/
├── backend/
│   ├── app/
│   │   ├── main.py             FastAPI app, all endpoints and scaling logic
│   │   ├── db.py               DB connection layer (SQLite or Postgres via DATABASE_URL)
│   │   ├── schema.sql          SQLite schema (tables + migrations)
│   │   ├── schema_postgres.sql Postgres schema (tables + migrations)
│   │   └── usda.py             USDA FoodData Central density lookups
│   ├── data/
│   │   └── retreat_ops.db      SQLite database (auto-created on startup)
│   ├── seeds/
│   │   └── master_data.json    Exportable recipe/ingredient master data
│   ├── scripts/                Import/export CLI utilities
│   └── requirements.txt
├── frontend/
│   ├── retreat-planner-sample.html   Retreat menu planner
│   ├── shopping-list.html            Shopping list generation + tracking
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

### Shopping Lists (`shopping-list.html`)

Planner/admin workflow for procurement:

- Generate list from a saved retreat plan and profile (`retreat` or `test`).
- Default phase filter (`bulk`, `fresh`, `daily`) or custom tier selection.
- Subtract imported inventory stock to compute `to_buy`.
- Assign source vendor per item.
- Track item state with explicit `ordered` and `received` toggles.

### Inventory Baseline (`inventory-baseline.html`)

Volunteer-first baseline counting workflow:

- No full-list editing on entry; scanner/search-first screen for one item at a time.
- Scan barcode or search an item, then compare:
  - current inventory data (qty/location/category/notes)
  - industry lookup data (name/category/unit/image/source)
- `Search Equivalent Item` returns mixed candidates from both:
  - current inventory (`exact` + `similar` matches)
  - industry lookup providers
- Mixed-source candidate table supports:
  - `Use Current` to load/update an existing inventory row
  - `Apply Industry` to overwrite descriptive fields (name/category/unit/image)
  - `Lookup` to pivot by candidate barcode
- Merge shortcuts above the form support:
  - `Use Current Candidate`
  - `Apply Industry Details`
  - `Apply Industry Image`
- If scan has no exact inventory barcode match, flow stays in create mode by default;
  users can still bind to an existing row or save a new item.
- Applying industry image/details immediately updates the current-inventory panel preview before save.
- Confirm quantity, unit, location, image, and save.
- Optionally bind a newly scanned barcode to an existing imported item.
- Mark baseline verification on save.

### Inventory Orders Planning (`inventory-orders.html`)

- Purpose: planning + placing only (no receiving/putaway actions on this page).
- Enter required quantity per line and auto-calculate `to_order` from current stock snapshot.
- Track ordered quantities with purchase-unit support (`unit`, `case`, `pack`) and units-per-purchase conversion.
- Override purchase URL per order line.
- Create ad-hoc new items directly from Orders when they do not yet exist in inventory.

### Inventory Receiving (`inventory-receiving.html`)

- Purpose: record what arrived for each order line (including partial receipts).
- Dedicated receipt inputs for ordered vs received quantities in purchase units.
- Keeps receiving state separate from physical stocking.
- Includes direct handoff link to Putaway page.

### Inventory Putaway / Add (`inventory-add.html`)

- Purpose: move already-received quantities into live on-hand inventory.
- Pulls a queue of lines where `received_quantity > applied_received_quantity`.
- Lets users set putaway quantity and shelf grid location (`A1`, `B3`, etc.) before applying.
- Writes inventory transactions and increments `standalone_inventory.quantity`.

### Full Inventory (`inventory.html?full=1`)

Volunteer-focused storage inventory for campus supplies:

- Full inventory list supports inline item-name editing; changes are saved only when Enter is pressed.
- Full inventory list supports inline category editing; changes are saved only when Enter is pressed.
- Full inventory list supports inline notes editing; changes are saved only when Enter is pressed.
- `order_url` is tracked separately from notes for replenishment links.
- Import/source markers are removed from visible notes and stored in `import_source`.
- Uses shelf-grid locations in the format `A1` through `Z99` (`A1`-`A20` preferred for new shelf mapping).
- Lookup providers: local `inventory_product_catalog` (for example Webstaurant UPC imports), Open Products Facts, Open Beauty Facts, Open Food Facts, plus UPCItemDB (optional auth via `UPCITEMDB_API_KEY`).
- `inventory.html` now routes to Inventory Home by default; use `inventory.html?full=1` for the full table view.

### Inventory Background (Shared Project Context)

Canonical project background is maintained in `AGENTS.md` at the repo root.
Keep that file updated so new sessions start with the same Inventory context.

### Inventory Change Log

#### 2026-02-28

- Added local UPC catalog table `inventory_product_catalog` for store-specific lookup.
- Barcode/equivalent-search now query local catalog first, ahead of external providers.
- Added importer script:
  - `backend/scripts/import_inventory_product_catalog.py`
  - Supports Webstaurant CSV imports (source label: `webstaurantstore`).
- Inventory-only Render sync now includes `inventory_product_catalog`.
- Added Inventory workflow split pages:
  - `inventory-orders.html` now focuses on planning and ordering only.
  - `inventory-receiving.html` (new) handles receipt entry only.
  - `inventory-add.html` now handles putaway/add-to-stock from received lines.
- Added backend endpoints for new flow:
  - `POST /api/inventory/order-draft-item` to create new orderable items not yet in cataloged inventory.
  - `GET /api/inventory/orders/putaway-queue` for pending putaway lines.
  - `POST /api/inventory/orders/{order_id}/putaway` to apply putaway quantity + location to inventory.
- Inventory navigation and Inventory Home cards were updated to show:
  - Orders Planning
  - Receiving
  - Putaway / Add

#### 2026-02-27

- Baseline scan form (`inventory-baseline.html`) now uses a **Category dropdown** instead of free text.
  - Options are loaded from `GET /api/inventory/categories` with defaults (`Cleaning`, `Infra`).
  - Industry-apply and current-item merge flows still populate category automatically.
- Inventory navigation behavior was improved:
  - Inventory dropdown remains active on shared routes that are linked from Inventory (for example `shopping-list.html`).
  - Inventory dropdown auto-opens when user is on an Inventory submenu page.
  - Fixed-top navbar z-index was set explicitly so nav stays above page-level sticky content.
- Full inventory naming was clarified:
  - `inventory.html` browser/page title now reads **Full Inventory**.
- Added inventory-only Render sync mode:
  - `backend/scripts/sync_db_to_render.sh --scope inventory`
  - Syncs local inventory tables to Render without overwriting kitchen/planning tables.
  - Synced on 2026-02-27 with counts:
    - `standalone_inventory`: 396
    - `inventory_items`: 50
    - `retreat_inventory_items`: 0
    - `retreat_inventory_transactions`: 0

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
    - volume units (cup, tbsp, tsp, ml, l):
        - ingredient-specific mapping (`unit_conversions` to `g` OR `grams_per_cup`) → grams
        - canonical volume ingredient (`ml`/`l`) → ml
        - otherwise conversion fails with a 400 mapping error (no generic fallback)
    - count units (piece, bunch, packet):
        - same canonical count unit → keep as-is
        - ingredient-specific count mapping required when canonical count unit differs
        - count↔mass/volume without explicit mapping fails with a 400 mapping error
      ↓
  to_shopping_unit: optimize for purchase
    - ≥1000g → kg
    - ≥1000ml → l
    - otherwise keep g or ml
```

The planner frontend performs this scaling client-side using conversion data loaded from the API at startup (`/api/unit-conversions` and `/api/ingredients`). The backend `POST /api/scale-preview` endpoint performs the same logic server-side for the scaling preview page.
If a required mapping is missing, the backend now returns an explicit `400` error instead of silently applying generic conversion fallbacks.

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
| context | TEXT | Usually `ingredient_specific`, `usda_fdc`, or `llm_estimate` (legacy generic rows may exist) |
| source_sheet | TEXT | Excel sheet name (if imported) |
| source_row | INTEGER | Excel row number (if imported) |
| notes | TEXT | Optional |
| created_at | TIMESTAMP | Row creation time |

### ingredient_aliases

Approved ingredient-name aliases used for USDA lookup candidate expansion.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PK | Auto-increment |
| ingredient_name | TEXT | Canonical ingredient in app DB |
| alias_name | TEXT | Approved alternate search string |
| source | TEXT | Alias source (`manual`, `auto_curated`, `auto_llm`, etc.) |
| confidence | REAL | Optional match confidence score |
| notes | TEXT | Optional provenance/context |
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

### Shopping + inventory operations

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/purchase-tiers` | List supported purchase tiers (`bulk`, `fresh`, `daily`) |
| GET | `/api/shopping-phases` | List supported shopping phases (`bulk`, `fresh`, `daily`, `custom`) |
| GET | `/api/vendors` | List vendor/source options |
| GET | `/api/inventory` | List general inventory records |
| GET | `/api/inventory/categories` | List distinct general inventory categories |
| GET | `/api/inventory/barcode-lookup/{barcode}` | Lookup barcode metadata, exact inventory match, and similar current-inventory candidates |
| GET | `/api/inventory/equivalent-search` | Search both current inventory and industry sources for equivalent candidates |
| POST | `/api/inventory/barcode-bind` | Bind a barcode to an existing inventory item |
| POST | `/api/inventory` | Create general inventory record |
| POST | `/api/inventory/order-draft-item` | Create a draft inventory item (qty `0`) for ordering a brand-new item |
| PUT | `/api/inventory/{item_id}` | Update general inventory record |
| PATCH | `/api/inventory/{item_id}/item-name` | Update only item name for one inventory item |
| PATCH | `/api/inventory/{item_id}/category` | Update only the category for one inventory item |
| PATCH | `/api/inventory/{item_id}/notes` | Update only notes for one inventory item |
| DELETE | `/api/inventory/{item_id}` | Delete general inventory record |
| GET | `/api/inventory/orders` | List inventory orders (planning/receiving flow) |
| POST | `/api/inventory/orders` | Create a new inventory order |
| GET | `/api/inventory/orders/{order_id}` | Get one inventory order with line detail |
| PATCH | `/api/inventory/orders/{order_id}` | Update order metadata and line quantities |
| GET | `/api/inventory/orders/putaway-queue` | List order lines pending putaway (`received > applied`) |
| POST | `/api/inventory/orders/{order_id}/putaway` | Apply putaway qty/location to inventory for selected order lines |
| GET | `/api/shopping-lists` | List shopping lists with ordered/received rollups |
| GET | `/api/shopping-lists/{shopping_list_id}` | Get a shopping list with item detail |
| POST | `/api/shopping-lists/generate` | Generate a shopping list from a retreat plan |
| POST | `/api/shopping-lists/{shopping_list_id}/carry-forward` | Create a Step 2 list from all unreceived items |
| POST | `/api/shopping-lists/{shopping_list_id}/apply-inventory` | Apply current inventory values from a fresh/daily list to inventory overrides |
| PATCH | `/api/shopping-lists/{shopping_list_id}/items/{item_id}` | Update vendor, current inventory (fresh/daily only), notes, ordered, received for one item |

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

**ShoppingListGeneratePayload** -- used by POST `/api/shopping-lists/generate`
- `retreatPlanId` (int, required unless `allRetreats=true`)
- `allRetreats` (bool, default `false`) to combine all saved retreat plans into one list
- `name` (str, optional override)
- `phase` (`bulk` | `fresh` | `daily` | `custom`)
- `purchaseTiers` (optional list of `bulk`/`fresh`/`daily`)
- `profile` (`retreat` | `test`)
- `subtractInventory` (bool)
- `includeZeroToBuy` (bool)

---

## Constants

**Recipe categories** (hardcoded in `main.py`):
M's Recipes, Breakfast, Salads, Vegetable Dishes, Dals & Stews, Khichdi & Kadhi, Rice Dishes, Desserts, Chai & Coffee, Pickles

**Meal slots** (hardcoded in planner JS):
Breakfast, Lunch, Evening Chai, Dinner

**Default shopping vendors** (auto-seeded):
OmProduce, Costco, Sams, Other Indian Store, Amazon, Webstaurant, Braums, SunriseNatural, Walmart, American grocery store

**Unit aliases** (normalized before conversion):
cups → cup, tablespoons/tbs → tbsp, teaspoons → tsp, gms/grams → g, liters/litres → l,
pieces → piece, packets → packet, cans → can, bunches → bunch, loaves → loaf, leaves → leaf

**Mass → grams**: g=1, kg=1000, lb=453.59, oz=28.35

**Volume → ml**: ml=1, l=1000, cup=240, tbsp=14.79, tsp=4.93

**Count units** (normalized singular): piece, packet, can, bunch, loaf, sprig, leaf, pinch, bag

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

### Canonicalize ingredient terms/units

Use this helper to normalize ingredient naming in the live DB:
- `Cinnamon stick(s)` -> `Cinnamon`
- `Ginger paste` -> `Ginger`
- Converts all `Ginger` recipe rows to `g`
- Cleans legacy wording in recipe/snapshot text fields

```bash
# Dry-run (no writes)
python scripts/canonicalize_ingredients.py

# Apply changes (creates a timestamped DB backup first)
python scripts/canonicalize_ingredients.py --apply
```

What is included: `ingredients`, `unit_conversions`, `recipes` + `recipe_ingredients` + `recipe_steps`.

What is excluded: retreat plans, kitchen/service snapshots, shopping/inventory operational records.

### Ingredient unit hygiene (recommended before shopping list generation)

Use this helper to normalize unit spellings/plurals and auto-fill missing canonical units where safe:

```bash
# Dry-run audit (no writes)
python scripts/ingredient_hygiene.py

# Apply safe fixes (creates DB backup) + save JSON report
python scripts/ingredient_hygiene.py --apply --report-json data/ingredient_hygiene_report.json
```

What it does:
- Normalizes unit text across `recipe_ingredients`, `ingredients.canonical_unit`, `inventory_items`, `shopping_list_items`, and `unit_conversions`.
- Infers missing `ingredients.canonical_unit` when observed units are unambiguous.
- Reports unresolved ingredients (e.g., mixed `can/cup/ml`) for manual decisions.

### Import storage inventory from workbook

Use this helper to import only the **storage** column from the `Inventory - Food` tab
and ignore kitchen pantry values.

```bash
# Dry-run
python scripts/import_inventory_food.py --xlsx /tmp/spring_2026_inventory_file.xlsx

# Apply (writes inventory_items rows and creates DB backup)
python scripts/import_inventory_food.py --xlsx /tmp/spring_2026_inventory_file.xlsx --apply
```

Default column mapping for `Inventory - Food`:
- ingredient: `B`
- unit: `C`
- storage qty: `D`
- kitchen pantry (`E`) is intentionally not imported

### Import non-food inventory for scanner workflow

Use this helper to seed `standalone_inventory` from the workbook tab
`Non-Food Inventory` (sheet match is case-insensitive).

```bash
# Dry-run
python scripts/import_nonfood_inventory.py --xlsx "/mnt/nas_home/Spring 2026 Inventory File.xlsx"

# Apply and replace only rows previously imported by this script
python scripts/import_nonfood_inventory.py \
  --xlsx "/mnt/nas_home/Spring 2026 Inventory File.xlsx" \
  --apply \
  --replace-existing-import

# Optional: also try to resolve image URLs from product links in the sheet
python scripts/import_nonfood_inventory.py \
  --xlsx "/mnt/nas_home/Spring 2026 Inventory File.xlsx" \
  --apply \
  --replace-existing-import \
  --resolve-image-from-links
```

Notes:
- Imported rows are tracked via `standalone_inventory.import_source` (value: `nonfood-inventory`).
- Product/order links are stored in `order_url` (when present in the workbook link columns).
- Existing non-imported rows are left untouched.
- `barcode` and direct `image_url` are often missing in spreadsheet data and can be filled later during scan-based updates.
- `--resolve-image-from-links` attempts to fetch `og:image`/`twitter:image` from product links when available.

### Import UPC catalog for store-specific barcode lookup (Webstaurant)

Use this helper to import a CSV of UPC rows into `inventory_product_catalog`.
This catalog is checked first during `/api/inventory/barcode-lookup/{barcode}`
and included in equivalent-search industry matches.

```bash
# Dry-run (auto-detects CSV columns like upc/barcode, name, category, unit, url)
python scripts/import_inventory_product_catalog.py \
  --csv /tmp/webstaurant_upcs.csv

# Apply and replace previously imported rows for source=webstaurantstore
python scripts/import_inventory_product_catalog.py \
  --csv /tmp/webstaurant_upcs.csv \
  --source webstaurantstore \
  --apply \
  --replace-source
```

CSV tips:
- Required: one UPC/barcode column (`upc`, `barcode`, `gtin`, etc.).
- Optional fields: `product_name`/`name`, `brand`, `category`, `unit`,
  `image_url`, `product_url`, `source_sku`, `notes`.
- Example UPC row:
  - `barcode=400015839112`, `product_name=Dish Sponges`, `source=webstaurantstore`

### Startup auto-seeding

- On app startup, if master tables are empty and `backend/seeds/master_data.json` exists, the app auto-imports master data.
- This keeps ephemeral SQLite deployments usable after restart.
- Disable with env var: `RETREAT_OPS_AUTO_SEED_MASTER_DATA=0`

### Sync SQLite DB with Render disk (full data, bi-directional)

These scripts copy the entire SQLite file (includes users/sessions and all operational data):

```bash
cd backend
chmod +x scripts/sync_db_from_render.sh scripts/sync_db_to_render.sh
```

Pull Render -> local:

```bash
scripts/sync_db_from_render.sh
```

Pull only kitchen-related tables from Render and overwrite those tables locally
while keeping local inventory tables untouched:

```bash
scripts/sync_db_from_render.sh --scope kitchen
```

Push local -> Render:

```bash
scripts/sync_db_to_render.sh
```

Push only inventory-related tables from local -> Render
while preserving kitchen/planning tables on Render:

```bash
scripts/sync_db_to_render.sh --scope inventory
```

Notes:
- You need SSH access configured in Render (service SSH user + your local SSH key).
- Script defaults are preconfigured for this service user/host and auto-detect `~/.ssh/bitbucket_ed25519` if present.
- Override any default with flags like `--host`, `--user`, `--key`, `--remote-db`, `--local-db`.
- `sync_db_from_render.sh --scope kitchen` overwrites only kitchen/planning tables
  (`ingredients`, `recipes`, `retreats`, `retreat_plans`, shopping + service snapshot tables, etc.)
  and preserves local inventory tables (`standalone_inventory`, `retreat_inventory_*`, `inventory_items`).
- `sync_db_to_render.sh` full sync now creates a local SQLite backup snapshot before upload,
  so pending WAL changes are included in what gets pushed.
- `sync_db_to_render.sh --scope inventory` overwrites only inventory tables on Render
  (`inventory_product_catalog`, `standalone_inventory`, `inventory_items`, and `retreat_inventory_*`).
- Default remote DB path is `/opt/render/project/src/backend/data/retreat_ops.db`.
- `sync_db_to_render.sh` creates a remote pre-sync backup unless `--skip-remote-backup` is set.
- Restart the Render service after push so all workers use the updated file.

## Current status

This is an MVP with:
- Core schema for recipes, ingredients, retreats, and kitchen snapshots.
- Scaling endpoint with unit normalization and USDA density lookups.
- Retreat planner with auto-save and auto-publish to kitchen.
- Kitchen display for live service with day/meal navigation.
- Recipe CRUD editor with category filtering.
- Shopping list generation from retreat plans with vendor assignment.
- Ordered/received tracking on shopping list items.
- Excel import scripts for bootstrapping from existing workbooks.
- Master data export/import for version control.

Next steps:
1. Add inventory receive flow to auto-increment storage stock from received shopping items.
2. Add partial receive quantities per line item.
3. Add import validation/reporting UI.
