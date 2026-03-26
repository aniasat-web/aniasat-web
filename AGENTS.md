# Project Background

Use this as shared context for work in this repository.

## Inventory Background

- Build an inventory management system under the top navigation `Inventory`.
- This is distinct from the `Kitchen` navigation and workflow.
- Physical storage is organized as shelf/section grid locations:
  - Shelves are lettered (`A`, `B`, `C`, `D`, ...).
  - Sections are numbered (`1`, `2`, `3`, `4`, ...).
  - Combined locations form grid slots (for example `A1`, `B3`, `D12`).
- Storage covers about 300-400 non-food retreat operations items (for example multipurpose solutions, dishwashing detergent, mops, cleaning towels, and related supplies).
- Required inventory capabilities:
  - View current inventory.
  - Use barcode scanning to add received items from new orders to inventory.
  - Use barcode scanning to remove items taken from storage.
  - Support ordering/reordering flows.
- Current baseline data source is an uploaded Excel file that is currently maintained manually.
- On scan of an existing barcode, enrich item records with product information and an item image from available industry sources whenever possible.

## Session Learnings (2026-02-25)

- Weekend baseline counting should use `frontend/inventory.html` with `/api/inventory` (`standalone_inventory`), not `/api/retreat-inventory` flows.
- Data snapshot on 2026-02-25:
  - `standalone_inventory`: 403 rows.
  - Missing barcode: 403.
  - Missing image: 403.
  - Missing location: 127.
  - `retreat_inventory_*` tables were empty.
- Existing-item scan flow in `inventory.html` was changed to confirm/update mode (non-additive quantity update).
- Baseline UI was added in `inventory.html`:
  - Header progress counters (`Verified`, `Pending`, `Missing Image`).
  - Cleanup filters (`Pending Verify`, `Verified`, `Missing Image`, `Missing Barcode`, `Missing Location`).
  - Row status chips and quick verify action.
  - Modal checkbox `Mark as baseline verified`.
  - Verification persists in notes as `[baseline-verified:YYYY-MM-DD]`.
- Dedicated volunteer page added: `frontend/inventory-baseline.html` (scan/search only, compare current vs industry data, bind barcode, confirm fields, save).
- Barcode lookup providers were expanded in `backend/app/main.py`:
  - Open Products Facts
  - Open Beauty Facts
  - Open Food Facts
  - UPCItemDB (optional `UPCITEMDB_API_KEY`)
- Workbook finding for `Non-Food Inventory` (2026-02-25):
  - 403 item rows.
  - 0 embedded sheet images.
  - Product links are mostly hyperlinks (120 in column G, 5 in column H).
- Importer enhancement in `backend/scripts/import_nonfood_inventory.py`:
  - Added `--resolve-image-from-links` and `--image-link-timeout`.
  - Attempts to derive images from linked pages via `og:image` / `twitter:image`.
- Inventory data cleanup enhancement:
  - Added `standalone_inventory.order_url` column.
  - Startup migration now extracts URLs from `standalone_inventory.notes` into `order_url` and removes URL text from notes.
  - Existing local data result (2026-02-25): 125 URLs moved into `order_url`, notes URL count reduced to 0.
- Notes/source cleanup enhancement:
  - Added `standalone_inventory.import_source` column for import provenance.
  - Startup migration removes `[import:...]` source markers from notes and migrates source value into `import_source`.
  - Existing local data result (2026-02-25): import-tag notes reduced from 403 to 0; `import_source` populated for 403 rows.
- Full inventory list enhancement in `frontend/inventory.html`:
  - Item name is inline-editable in the table and saves only on `Enter`.
  - Category is inline-editable in the table and saves only on `Enter`.
  - Notes are inline-editable in the table and save only on `Enter`.
  - Added `Order URL` column with external-link button for replenishment links.
- Category normalization and recategorization follow-up (2026-02-25, late session):
  - `Cleaning` is now preserved as `Cleaning` (no longer auto-coerced to `Infra` by generic cleaning text).
  - `Infra` normalization now applies only to explicit infra aliases (for example `infra`, `infrastructure`, `facility maintenance`).
  - Existing local data was batch-recategorized from `Infra` to `Cleaning` using description/notes keyword hints:
    - 59 rows moved.
    - Category counts changed from `Infra: 156 -> 97` and `Cleaning: 1 -> 60`.
  - This was intentionally conservative and should still be reviewed in-line in the inventory table.
- Inline edit save reliability follow-up:
  - Field-specific PATCH routes were added for `item_name`, `category`, and `notes` so inline saves do not fail due to unrelated full-record validation.
  - `inventory.html` inline save errors now surface a visible status and alert so volunteers/admins can detect failed saves immediately.
- Baseline equivalent-merge enhancement:
  - Added `GET /api/inventory/equivalent-search` to return both current-inventory matches and industry matches for one query.
  - `GET /api/inventory/barcode-lookup/{barcode}` now also returns `similar_matches` from current inventory when exact barcode match is missing.
  - `frontend/inventory-baseline.html` now supports mixed-source candidate selection:
    - Search results include both `Current` and `Industry` rows.
    - Volunteers can load a current candidate, then apply industry details (`name/category/unit/image`) before save.
    - Dedicated merge buttons allow applying full industry details or image-only updates.
- Runtime note:
  - Backend was restarted after these changes on `0.0.0.0:8089` (`uvicorn app.main:app`).
- Recommended import command when resuming:
  - `cd backend && .venv/bin/python scripts/import_nonfood_inventory.py --xlsx "/mnt/nas_home/Spring 2026 Inventory File.xlsx" --apply --replace-existing-import --resolve-image-from-links`
