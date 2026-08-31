import os
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

ENV_KEYS = [
    "DATABASE_URL",
    "RETREAT_OPS_SQLITE_DB_PATH",
    "RETREAT_OPS_AUTO_SEED_MASTER_DATA",
    "RETREAT_OPS_BOOTSTRAP_ADMIN_USERNAME",
    "RETREAT_OPS_BOOTSTRAP_ADMIN_PASSWORD",
]


class KitchenInventoryCountTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.env_backup = {key: os.environ.get(key) for key in ENV_KEYS}
        self.db_path = Path(self.tempdir.name) / "test-retreat-ops.db"

        os.environ.pop("DATABASE_URL", None)
        os.environ["RETREAT_OPS_SQLITE_DB_PATH"] = str(self.db_path)
        os.environ["RETREAT_OPS_AUTO_SEED_MASTER_DATA"] = "0"
        os.environ["RETREAT_OPS_BOOTSTRAP_ADMIN_USERNAME"] = "admin"
        os.environ["RETREAT_OPS_BOOTSTRAP_ADMIN_PASSWORD"] = "password"

        from app import main as main_module
        from app.db import get_connection

        self.main = main_module
        self.get_connection = get_connection

        self.client_ctx = TestClient(main_module.app)
        self.client = self.client_ctx.__enter__()
        self.addCleanup(self.client_ctx.__exit__, None, None, None)
        self.addCleanup(self._restore_env)
        self.addCleanup(self.tempdir.cleanup)

        login = self.client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "password"},
        )
        self.assertEqual(login.status_code, 200, login.text)

    def _restore_env(self) -> None:
        for key, value in self.env_backup.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def insert_ingredient(
        self,
        name: str,
        canonical_unit: str = "g",
        grams_per_cup: float | None = None,
    ) -> int:
        with self.get_connection() as conn:
            created = conn.execute(
                """
                INSERT INTO ingredients(name, canonical_unit, grams_per_cup, category, purchase_tier)
                VALUES (?, ?, ?, 'Produce', 'bulk')
                RETURNING id
                """,
                (name, canonical_unit, grams_per_cup),
            ).fetchone()
            conn.commit()
        return int(created["id"])

    def upload_count(self, csv_text: str, inventory_date: str = "2026-08-30", name: str = "") -> dict:
        response = self.client.post(
            "/api/kitchen-inventory/upload",
            files={"file": ("count.csv", csv_text.encode("utf-8"), "text/csv")},
            data={"name": name, "inventoryDate": inventory_date},
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def test_upload_converts_to_canonical_units(self) -> None:
        self.insert_ingredient("Basmati Rice", "g", grams_per_cup=185.0)
        self.insert_ingredient("Olive Oil", "ml")

        detail = self.upload_count(
            "Ingredient,Qty,Unit\n"
            "Basmati Rice,2,kg\n"
            "basmati rice,4,cup\n"
            "Olive Oil,1.5,l\n"
            "Dragon Fruit,3,piece\n"
            "Basmati Rice,oops,kg\n"
        )

        self.assertEqual(detail["inventory_date"], "2026-08-30")
        self.assertEqual(detail["item_count"], 4)
        self.assertEqual(detail["matched_count"], 3)
        self.assertEqual(detail["unmatched_count"], 1)
        self.assertEqual(len(detail["skipped_rows"]), 1)

        by_input = {
            (item["input_name"].lower(), item["input_unit"]): item
            for item in detail["items"]
        }
        rice_kg = by_input[("basmati rice", "kg")]
        self.assertEqual(rice_kg["canonical_qty"], 2000.0)
        self.assertEqual(rice_kg["canonical_unit"], "g")

        rice_cup = by_input[("basmati rice", "cup")]
        self.assertEqual(rice_cup["canonical_qty"], 740.0)
        self.assertEqual(rice_cup["canonical_unit"], "g")

        oil = by_input[("olive oil", "l")]
        self.assertEqual(oil["canonical_qty"], 1500.0)
        self.assertEqual(oil["canonical_unit"], "ml")

        unmatched = by_input[("dragon fruit", "piece")]
        self.assertIsNone(unmatched["ingredient_id"])
        self.assertIsNone(unmatched["canonical_qty"])

        listing = self.client.get("/api/kitchen-inventory")
        self.assertEqual(listing.status_code, 200, listing.text)
        rows = listing.json()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["item_count"], 4)
        self.assertEqual(rows[0]["matched_count"], 3)

    def test_manual_entry_create(self) -> None:
        rice_id = self.insert_ingredient("Basmati Rice", "g")
        oil_id = self.insert_ingredient("Olive Oil", "ml")

        response = self.client.post(
            "/api/kitchen-inventory",
            json={
                "name": "Manual Count",
                "inventoryDate": "2026-08-30",
                "items": [
                    {"ingredientId": rice_id, "qty": 2, "unit": "kg"},
                    {"ingredientId": oil_id, "qty": 1.5, "unit": "l"},
                ],
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        detail = response.json()
        self.assertEqual(detail["item_count"], 2)
        self.assertEqual(detail["matched_count"], 2)
        by_name = {item["input_name"]: item for item in detail["items"]}
        self.assertEqual(by_name["Basmati Rice"]["canonical_qty"], 2000.0)
        self.assertEqual(by_name["Basmati Rice"]["canonical_unit"], "g")
        self.assertEqual(by_name["Olive Oil"]["canonical_qty"], 1500.0)
        self.assertEqual(by_name["Olive Oil"]["canonical_unit"], "ml")

        unknown = self.client.post(
            "/api/kitchen-inventory",
            json={"items": [{"ingredientId": 99999, "qty": 1, "unit": "kg"}]},
        )
        self.assertEqual(unknown.status_code, 400, unknown.text)

    def test_upload_mass_converts_to_volume_with_density(self) -> None:
        self.insert_ingredient("Ghee", "ml", grams_per_cup=218.4)
        detail = self.upload_count("Ingredient,Qty,Unit\nGhee,38,lbs\n")
        item = detail["items"][0]
        self.assertEqual(item["canonical_unit"], "ml")
        self.assertAlmostEqual(item["canonical_qty"], 18941.22, places=2)

    def test_upload_without_header_and_default_unit(self) -> None:
        self.insert_ingredient("Jaggery", "g")
        detail = self.upload_count("Jaggery,500\n")
        item = detail["items"][0]
        self.assertEqual(item["canonical_qty"], 500.0)
        self.assertEqual(item["canonical_unit"], "g")

    def create_shopping_list(self, rice_id: int, dal_id: int) -> tuple[int, int, int]:
        with self.get_connection() as conn:
            created_list = conn.execute(
                """
                INSERT INTO shopping_lists(name, phase, status)
                VALUES ('Count Apply Test', 'bulk', 'draft')
                RETURNING id
                """
            ).fetchone()
            shopping_list_id = int(created_list["id"])
            item_ids = []
            for ingredient_id, qty, unit in ((rice_id, 5, "kg"), (dal_id, 2, "kg")):
                created_item = conn.execute(
                    """
                    INSERT INTO shopping_list_items(
                        shopping_list_id, ingredient_id, required_qty, required_unit,
                        in_stock_qty, in_stock_unit, to_buy_qty, to_buy_unit,
                        ordered, received, status
                    )
                    VALUES (?, ?, ?, ?, 0, ?, ?, ?, 0, 0, 'open')
                    RETURNING id
                    """,
                    (shopping_list_id, ingredient_id, qty, unit, unit, qty, unit),
                ).fetchone()
                item_ids.append(int(created_item["id"]))
            conn.commit()
        return shopping_list_id, item_ids[0], item_ids[1]

    def test_apply_inventory_list_to_shopping_list(self) -> None:
        rice_id = self.insert_ingredient("Basmati Rice", "g")
        dal_id = self.insert_ingredient("Moong Dal", "g")
        shopping_list_id, rice_item_id, dal_item_id = self.create_shopping_list(rice_id, dal_id)

        count = self.upload_count("Ingredient,Qty,Unit\nBasmati Rice,2,kg\n")

        applied = self.client.post(
            f"/api/shopping-lists/{shopping_list_id}/apply-inventory-list",
            json={"inventoryListId": count["id"]},
        )
        self.assertEqual(applied.status_code, 200, applied.text)
        summary = applied.json()
        self.assertEqual(summary["matched_count"], 1)
        self.assertEqual(summary["zeroed_count"], 1)

        detail = self.client.get(f"/api/shopping-lists/{shopping_list_id}").json()
        items_by_id = {int(item["id"]): item for item in detail["items"]}
        rice_item = items_by_id[rice_item_id]
        self.assertEqual(rice_item["in_stock_qty"], 2.0)
        self.assertEqual(rice_item["in_stock_unit"], "kg")
        self.assertEqual(rice_item["to_buy_qty"], 3.0)
        dal_item = items_by_id[dal_item_id]
        self.assertEqual(dal_item["in_stock_qty"], 0.0)
        self.assertEqual(dal_item["to_buy_qty"], 2.0)

    def test_in_stock_editable_on_bulk_list(self) -> None:
        rice_id = self.insert_ingredient("Basmati Rice", "g")
        dal_id = self.insert_ingredient("Moong Dal", "g")
        shopping_list_id, rice_item_id, _dal_item_id = self.create_shopping_list(rice_id, dal_id)

        response = self.client.patch(
            f"/api/shopping-lists/{shopping_list_id}/items/{rice_item_id}",
            json={"inStockQty": 1.5},
        )
        self.assertEqual(response.status_code, 200, response.text)
        detail = response.json()
        item = next(item for item in detail["items"] if int(item["id"]) == rice_item_id)
        self.assertEqual(item["in_stock_qty"], 1.5)
        self.assertEqual(item["to_buy_qty"], 3.5)

    def test_delete_inventory_list(self) -> None:
        self.insert_ingredient("Basmati Rice", "g")
        count = self.upload_count("Ingredient,Qty,Unit\nBasmati Rice,2,kg\n")
        deleted = self.client.delete(f"/api/kitchen-inventory/{count['id']}")
        self.assertEqual(deleted.status_code, 200, deleted.text)
        listing = self.client.get("/api/kitchen-inventory").json()
        self.assertEqual(listing, [])


if __name__ == "__main__":
    unittest.main()
