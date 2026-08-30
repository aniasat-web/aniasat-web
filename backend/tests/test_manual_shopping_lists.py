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


class ManualShoppingListTests(unittest.TestCase):
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

    def insert_ingredient(self, name: str, canonical_unit: str = "g") -> int:
        with self.get_connection() as conn:
            created = conn.execute(
                """
                INSERT INTO ingredients(name, canonical_unit, category, purchase_tier)
                VALUES (?, ?, 'Produce', 'bulk')
                RETURNING id
                """,
                (name, canonical_unit),
            ).fetchone()
            conn.commit()
        return int(created["id"])

    def test_manual_list_lifecycle(self) -> None:
        ghee_id = self.insert_ingredient("Ghee")

        created = self.client.post(
            "/api/shopping-lists",
            json={"name": "Sir's Kitchen - Sep", "listDate": "2026-09-01"},
        )
        self.assertEqual(created.status_code, 200, created.text)
        detail = created.json()
        list_id = int(detail["id"])
        self.assertEqual(detail["phase"], "custom")
        self.assertEqual(detail["items"], [])

        # Add an existing catalog ingredient
        added = self.client.post(
            f"/api/shopping-lists/{list_id}/items",
            json={"ingredientName": "ghee", "qty": 2, "unit": "kg"},
        )
        self.assertEqual(added.status_code, 200, added.text)
        items = added.json()["items"]
        self.assertEqual(len(items), 1)
        self.assertEqual(int(items[0]["ingredient_id"]), ghee_id)
        self.assertEqual(items[0]["required_qty"], 2.0)
        self.assertEqual(items[0]["to_buy_qty"], 2.0)

        # Same ingredient + unit again sums
        again = self.client.post(
            f"/api/shopping-lists/{list_id}/items",
            json={"ingredientName": "Ghee", "qty": 1.5, "unit": "kg"},
        )
        items = again.json()["items"]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["required_qty"], 3.5)

        # Unknown name creates a catalog ingredient
        new_item = self.client.post(
            f"/api/shopping-lists/{list_id}/items",
            json={"ingredientName": "Sir's Special Biscuits", "qty": 3, "unit": "packet"},
        )
        self.assertEqual(new_item.status_code, 200, new_item.text)
        items = new_item.json()["items"]
        self.assertEqual(len(items), 2)
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT canonical_unit FROM ingredients WHERE name = ?",
                ("Sir's Special Biscuits",),
            ).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["canonical_unit"], "packet")

        # Manual lists cannot be refreshed from a plan
        refused = self.client.post(f"/api/shopping-lists/{list_id}/refresh")
        self.assertEqual(refused.status_code, 400, refused.text)

        # Delete one item
        biscuit_item = next(i for i in items if i["ingredient_name"] == "Sir's Special Biscuits")
        deleted = self.client.delete(f"/api/shopping-lists/{list_id}/items/{biscuit_item['id']}")
        self.assertEqual(deleted.status_code, 200, deleted.text)
        self.assertEqual(len(deleted.json()["items"]), 1)


if __name__ == "__main__":
    unittest.main()
