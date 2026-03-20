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


class KitchenGuestAccessTests(unittest.TestCase):
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

        self.admin_client_ctx = TestClient(app)
        self.admin_client = self.admin_client_ctx.__enter__()
        self.addCleanup(self.admin_client_ctx.__exit__, None, None, None)

        self.guest_client_ctx = TestClient(app)
        self.guest_client = self.guest_client_ctx.__enter__()
        self.addCleanup(self.guest_client_ctx.__exit__, None, None, None)

        self.addCleanup(self._restore_env)
        self.addCleanup(self.tempdir.cleanup)

        login = self.admin_client.post(
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

    def set_shared_code(self, scope: str, access_code: str) -> None:
        response = self.admin_client.post(
            f"/api/admin/kitchen-access/{scope}",
            json={"accessCode": access_code},
        )
        self.assertEqual(response.status_code, 200, response.text)

    def test_testing_guest_code_requires_code_and_remains_scoped(self) -> None:
        self.set_shared_code("testing", "TEST-1234")

        status = self.guest_client.get("/api/kitchen-access/testing")
        self.assertEqual(status.status_code, 200, status.text)
        self.assertFalse(status.json()["authorized"])
        self.assertTrue(status.json()["guestAccessEnabled"])

        unauth_plan_list = self.guest_client.get("/api/retreat-plans")
        self.assertEqual(unauth_plan_list.status_code, 401, unauth_plan_list.text)

        bad_login = self.guest_client.post(
            "/api/kitchen-access/testing/login",
            json={"accessCode": "WRONG-CODE"},
        )
        self.assertEqual(bad_login.status_code, 403, bad_login.text)

        good_login = self.guest_client.post(
            "/api/kitchen-access/testing/login",
            json={"accessCode": "TEST-1234"},
        )
        self.assertEqual(good_login.status_code, 200, good_login.text)
        self.assertEqual(good_login.json()["sessionMode"], "guest")

        plan_list = self.guest_client.get("/api/retreat-plans")
        self.assertEqual(plan_list.status_code, 200, plan_list.text)

        recipes = self.guest_client.get("/api/recipes/full")
        self.assertEqual(recipes.status_code, 200, recipes.text)

        retreat_view_endpoint = self.guest_client.get("/api/service-snapshots/latest")
        self.assertEqual(retreat_view_endpoint.status_code, 401, retreat_view_endpoint.text)

    def test_retreat_view_code_is_separate_and_rotation_revokes_guest_sessions(self) -> None:
        self.set_shared_code("retreat-view", "RETREAT-1111")

        good_login = self.guest_client.post(
            "/api/kitchen-access/retreat-view/login",
            json={"accessCode": "RETREAT-1111"},
        )
        self.assertEqual(good_login.status_code, 200, good_login.text)
        self.assertEqual(good_login.json()["sessionMode"], "guest")

        retreat_snapshot = self.guest_client.get("/api/service-snapshots/latest")
        self.assertIn(retreat_snapshot.status_code, {200, 404}, retreat_snapshot.text)

        testing_scope_endpoint = self.guest_client.get("/api/retreat-plans")
        self.assertEqual(testing_scope_endpoint.status_code, 401, testing_scope_endpoint.text)

        self.set_shared_code("retreat-view", "RETREAT-2222")

        revoked_snapshot = self.guest_client.get("/api/service-snapshots/latest")
        self.assertEqual(revoked_snapshot.status_code, 401, revoked_snapshot.text)

        old_code_login = self.guest_client.post(
            "/api/kitchen-access/retreat-view/login",
            json={"accessCode": "RETREAT-1111"},
        )
        self.assertEqual(old_code_login.status_code, 403, old_code_login.text)

        new_code_login = self.guest_client.post(
            "/api/kitchen-access/retreat-view/login",
            json={"accessCode": "RETREAT-2222"},
        )
        self.assertEqual(new_code_login.status_code, 200, new_code_login.text)

        restored_snapshot = self.guest_client.get("/api/service-snapshots/latest")
        self.assertIn(restored_snapshot.status_code, {200, 404}, restored_snapshot.text)


if __name__ == "__main__":
    unittest.main()
