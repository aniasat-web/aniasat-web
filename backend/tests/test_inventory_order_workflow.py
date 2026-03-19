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


class InventoryOrderWorkflowStageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.env_backup = {key: os.environ.get(key) for key in ENV_KEYS}
        self.db_path = Path(self.tempdir.name) / "test-retreat-ops.db"

        os.environ.pop("DATABASE_URL", None)
        os.environ["RETREAT_OPS_SQLITE_DB_PATH"] = str(self.db_path)
        os.environ["RETREAT_OPS_AUTO_SEED_MASTER_DATA"] = "0"
        os.environ["RETREAT_OPS_BOOTSTRAP_ADMIN_USERNAME"] = "admin"
        os.environ["RETREAT_OPS_BOOTSTRAP_ADMIN_PASSWORD"] = "password"

        from app.main import app

        self.client_ctx = TestClient(app)
        self.client = self.client_ctx.__enter__()
        self.addCleanup(self.client_ctx.__exit__, None, None, None)
        self.addCleanup(self._restore_env)
        self.addCleanup(self.tempdir.cleanup)

        login = self.client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "password"},
        )
        self.assertEqual(login.status_code, 200, login.text)

        created_item = self.client.post(
            "/api/inventory/order-draft-item",
            json={
                "itemName": "Workflow Test Cleaner",
                "category": "Cleaning",
                "unit": "each",
                "location": "A1",
            },
        )
        self.assertEqual(created_item.status_code, 201, created_item.text)
        self.inventory_item_id = int(created_item.json()["id"])

    def _restore_env(self) -> None:
        for key, value in self.env_backup.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def build_non_food_item(self, *, required_quantity: float, draft_ordered_purchase_quantity: float = 0) -> dict:
        payload = {
            "itemType": "STANDALONE_INVENTORY",
            "itemId": self.inventory_item_id,
            "requiredQuantity": required_quantity,
            "orderedQuantity": 0,
            "receivedQuantity": 0,
            "appliedQuantity": 0,
            "unit": "each",
            "purchaseUnit": "unit",
            "unitsPerPurchase": 1,
            "notes": None,
        }
        if draft_ordered_purchase_quantity > 0:
            payload["draftPurchaseUnit"] = "case"
            payload["draftUnitsPerPurchase"] = 6
            payload["draftOrderedPurchaseQuantity"] = draft_ordered_purchase_quantity
        return payload

    def create_order(self, *, required_quantity: float = 6) -> dict:
        response = self.client.post(
            "/api/orders",
            json={
                "domain": "NON_FOOD",
                "sourceType": "NON_FOOD_PLAN",
                "name": "Workflow Test Order",
                "items": [self.build_non_food_item(required_quantity=required_quantity)],
            },
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def test_stale_planning_update_is_rejected_after_move_to_purchasing(self) -> None:
        created = self.create_order(required_quantity=6)
        order_id = int(created["id"])

        moved = self.client.patch(
            f"/api/orders/{order_id}",
            json={
                "name": "Workflow Test Order",
                "expectedWorkflowStage": "PLANNING",
                "workflowStage": "PURCHASING",
                "items": [self.build_non_food_item(required_quantity=6)],
            },
        )
        self.assertEqual(moved.status_code, 200, moved.text)
        self.assertEqual(moved.json()["workflow_stage"], "PURCHASING")

        stale_save = self.client.patch(
            f"/api/orders/{order_id}",
            json={
                "name": "Workflow Test Order",
                "expectedWorkflowStage": "PLANNING",
                "workflowStage": "PLANNING",
                "items": [self.build_non_food_item(required_quantity=12)],
            },
        )
        self.assertEqual(stale_save.status_code, 409, stale_save.text)
        self.assertIn("currently in PURCHASING", stale_save.text)

        detail = self.client.get(f"/api/orders/{order_id}")
        self.assertEqual(detail.status_code, 200, detail.text)
        payload = detail.json()
        self.assertEqual(payload["workflow_stage"], "PURCHASING")
        self.assertEqual(float(payload["items"][0]["required_quantity"]), 6.0)

    def test_purchasing_update_succeeds_with_matching_expected_stage(self) -> None:
        created = self.create_order(required_quantity=4)
        order_id = int(created["id"])

        moved = self.client.patch(
            f"/api/orders/{order_id}",
            json={
                "name": "Workflow Test Order",
                "expectedWorkflowStage": "PLANNING",
                "workflowStage": "PURCHASING",
                "items": [self.build_non_food_item(required_quantity=4)],
            },
        )
        self.assertEqual(moved.status_code, 200, moved.text)

        purchasing_save = self.client.patch(
            f"/api/orders/{order_id}",
            json={
                "name": "Workflow Test Order",
                "expectedWorkflowStage": "PURCHASING",
                "workflowStage": "PURCHASING",
                "items": [
                    self.build_non_food_item(
                        required_quantity=4,
                        draft_ordered_purchase_quantity=2,
                    )
                ],
            },
        )
        self.assertEqual(purchasing_save.status_code, 200, purchasing_save.text)
        saved_payload = purchasing_save.json()
        self.assertEqual(saved_payload["workflow_stage"], "PURCHASING")
        self.assertEqual(float(saved_payload["items"][0]["draft_ordered_purchase_quantity"]), 2.0)


if __name__ == "__main__":
    unittest.main()
