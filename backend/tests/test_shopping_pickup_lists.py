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


class ShoppingPickupListTests(unittest.TestCase):
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

    def insert_vendor(self, name: str = "Costco") -> int:
        with self.get_connection() as conn:
            existing = conn.execute(
                "SELECT id FROM vendors WHERE lower(name) = lower(?)",
                (name,),
            ).fetchone()
            if existing:
                return int(existing["id"])
            created = conn.execute(
                "INSERT INTO vendors(name) VALUES (?) RETURNING id",
                (name,),
            ).fetchone()
            conn.commit()
        return int(created["id"])

    def insert_ingredient(self, name: str, category: str = "Produce") -> int:
        with self.get_connection() as conn:
            created = conn.execute(
                """
                INSERT INTO ingredients(name, canonical_unit, category, purchase_tier)
                VALUES (?, ?, ?, ?)
                RETURNING id
                """,
                (name, "g", category, "bulk"),
            ).fetchone()
            conn.commit()
        return int(created["id"])

    def create_shopping_list_with_items(self) -> tuple[int, list[int], int]:
        vendor_id = self.insert_vendor()
        rice_id = self.insert_ingredient("Basmati Rice", "Grains & Flours")
        dal_id = self.insert_ingredient("Moong Dal", "Pulses & Legumes")

        with self.get_connection() as conn:
            created_list = conn.execute(
                """
                INSERT INTO shopping_lists(name, phase, status)
                VALUES (?, 'bulk', 'draft')
                RETURNING id
                """,
                ("Pickup Test Master",),
            ).fetchone()
            shopping_list_id = int(created_list["id"])

            item_ids: list[int] = []
            for ingredient_id, qty, unit in ((rice_id, 5, "kg"), (dal_id, 2, "kg")):
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
                        ordered,
                        received,
                        status
                    )
                    VALUES (?, ?, ?, ?, 0, ?, ?, ?, ?, 0, 0, 'open')
                    RETURNING id
                    """,
                    (
                        shopping_list_id,
                        ingredient_id,
                        qty,
                        unit,
                        unit,
                        qty,
                        unit,
                        vendor_id,
                    ),
                ).fetchone()
                item_ids.append(int(created_item["id"]))
            conn.commit()
        return shopping_list_id, item_ids, rice_id

    def test_create_list_load_and_delete_pickup_list(self) -> None:
        shopping_list_id, item_ids, _rice_id = self.create_shopping_list_with_items()

        created = self.client.post(
            f"/api/shopping-lists/{shopping_list_id}/pickup-lists",
            json={
                "itemIds": item_ids,
                "name": "Costco Run - Friday AM",
                "assignee": "Asha",
                "pickupDate": "2026-03-28",
                "notes": "Only bulk pantry items",
            },
        )
        self.assertEqual(created.status_code, 200, created.text)
        payload = created.json()
        self.assertEqual(payload["name"], "Costco Run - Friday AM")
        self.assertEqual(payload["item_count"], 2)
        self.assertEqual(payload["ordered_count"], 0)
        self.assertEqual(payload["received_count"], 0)
        self.assertEqual(payload["missing_item_count"], 0)
        pickup_list_id = int(payload["id"])

        listed = self.client.get(f"/api/shopping-lists/{shopping_list_id}/pickup-lists")
        self.assertEqual(listed.status_code, 200, listed.text)
        listed_payload = listed.json()
        self.assertEqual(len(listed_payload), 1)
        self.assertEqual(int(listed_payload[0]["id"]), pickup_list_id)
        self.assertEqual(listed_payload[0]["assignee"], "Asha")

        detail = self.client.get(f"/api/shopping-pickup-lists/{pickup_list_id}")
        self.assertEqual(detail.status_code, 200, detail.text)
        detail_payload = detail.json()
        self.assertEqual(sorted(detail_payload["item_ids"]), sorted(item_ids))
        self.assertEqual(detail_payload["pickup_date"], "2026-03-28")

        deleted = self.client.delete(f"/api/shopping-pickup-lists/{pickup_list_id}")
        self.assertEqual(deleted.status_code, 200, deleted.text)

        after_delete = self.client.get(f"/api/shopping-lists/{shopping_list_id}/pickup-lists")
        self.assertEqual(after_delete.status_code, 200, after_delete.text)
        self.assertEqual(after_delete.json(), [])

    def test_pickup_list_items_relink_after_master_items_are_regenerated(self) -> None:
        shopping_list_id, item_ids, rice_id = self.create_shopping_list_with_items()

        created = self.client.post(
            f"/api/shopping-lists/{shopping_list_id}/pickup-lists",
            json={
                "itemIds": [item_ids[0]],
                "name": "Rice Run",
            },
        )
        self.assertEqual(created.status_code, 200, created.text)
        pickup_list_id = int(created.json()["id"])

        with self.get_connection() as conn:
            conn.execute("DELETE FROM shopping_list_items WHERE shopping_list_id = ?", (shopping_list_id,))
            recreated_item = conn.execute(
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
                    ordered,
                    received,
                    status
                )
                VALUES (?, ?, ?, ?, 0, ?, ?, ?, 0, 0, 'open')
                RETURNING id
                """,
                (
                    shopping_list_id,
                    rice_id,
                    5,
                    "kg",
                    "kg",
                    5,
                    "kg",
                ),
            ).fetchone()
            new_item_id = int(recreated_item["id"])
            self.main.relink_shopping_pickup_list_items(conn, shopping_list_id)
            conn.commit()

        detail = self.client.get(f"/api/shopping-pickup-lists/{pickup_list_id}")
        self.assertEqual(detail.status_code, 200, detail.text)
        payload = detail.json()
        self.assertEqual(payload["missing_item_count"], 0)
        self.assertEqual(payload["item_ids"], [new_item_id])


if __name__ == "__main__":
    unittest.main()
