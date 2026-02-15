PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS ingredients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    canonical_unit TEXT,
    grams_per_cup REAL,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS unit_conversions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_name TEXT,
    quantity_from REAL NOT NULL,
    unit_from TEXT NOT NULL,
    quantity_to REAL NOT NULL,
    unit_to TEXT NOT NULL,
    context TEXT NOT NULL,
    source_sheet TEXT,
    source_row INTEGER,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS recipes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    base_servings REAL NOT NULL,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS recipe_ingredients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recipe_id INTEGER NOT NULL,
    ingredient_id INTEGER NOT NULL,
    quantity REAL NOT NULL,
    unit TEXT NOT NULL,
    prep_notes TEXT,
    FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE,
    FOREIGN KEY (ingredient_id) REFERENCES ingredients(id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS recipe_steps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recipe_id INTEGER NOT NULL,
    step_order INTEGER NOT NULL,
    instruction TEXT NOT NULL,
    FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS retreats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    start_date TEXT,
    end_date TEXT,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS menu_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    retreat_id INTEGER NOT NULL,
    day_label TEXT NOT NULL,
    meal_label TEXT NOT NULL,
    recipe_id INTEGER NOT NULL,
    target_servings REAL NOT NULL,
    FOREIGN KEY (retreat_id) REFERENCES retreats(id) ON DELETE CASCADE,
    FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS inventory_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ingredient_id INTEGER NOT NULL,
    quantity REAL NOT NULL,
    unit TEXT NOT NULL,
    source TEXT,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ingredient_id) REFERENCES ingredients(id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS vendors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS shopping_lists (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    retreat_id INTEGER,
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (retreat_id) REFERENCES retreats(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS shopping_list_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    shopping_list_id INTEGER NOT NULL,
    ingredient_id INTEGER NOT NULL,
    required_qty REAL NOT NULL,
    required_unit TEXT NOT NULL,
    in_stock_qty REAL,
    in_stock_unit TEXT,
    to_buy_qty REAL,
    to_buy_unit TEXT,
    vendor_id INTEGER,
    owner TEXT,
    pickup_date TEXT,
    status TEXT NOT NULL DEFAULT 'open',
    notes TEXT,
    FOREIGN KEY (shopping_list_id) REFERENCES shopping_lists(id) ON DELETE CASCADE,
    FOREIGN KEY (ingredient_id) REFERENCES ingredients(id) ON DELETE RESTRICT,
    FOREIGN KEY (vendor_id) REFERENCES vendors(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_recipe_ingredients_recipe_id ON recipe_ingredients(recipe_id);
CREATE INDEX IF NOT EXISTS idx_menu_items_retreat_id ON menu_items(retreat_id);
CREATE INDEX IF NOT EXISTS idx_inventory_items_ingredient_id ON inventory_items(ingredient_id);
CREATE INDEX IF NOT EXISTS idx_shopping_items_list_id ON shopping_list_items(shopping_list_id);
CREATE INDEX IF NOT EXISTS idx_unit_conversions_item_name ON unit_conversions(item_name);
CREATE INDEX IF NOT EXISTS idx_unit_conversions_context ON unit_conversions(context);

CREATE TABLE IF NOT EXISTS retreat_plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    start_date TEXT,
    day_count INTEGER NOT NULL,
    default_people REAL NOT NULL,
    plan_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_retreat_plans_updated_at ON retreat_plans(updated_at);

CREATE TABLE IF NOT EXISTS service_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    retreat_name TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    retreat_plan_id INTEGER REFERENCES retreat_plans(id) ON DELETE SET NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_service_snapshots_created_at ON service_snapshots(created_at);
CREATE INDEX IF NOT EXISTS idx_service_snapshots_retreat_plan_id ON service_snapshots(retreat_plan_id);
