import unittest

from fastapi.testclient import TestClient

from app.main import app


def _base_ctx():
    return {
        "sessionInfo": {"session_id": "s1", "interaction_id": "i1"},
        "userInfo": {"user_id": "u1"},
        "DeviceInfo": {"device_id": "d1"},
        "AppBaseInfo": {"package_name": "pkg.test"},
        "SystemSetting": {"gps": ""},
    }


class FeedbackApiTest(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def _assert_feedback_issue_types(self, data: dict):
        fb = data.get("feedback") or {}
        types_ = fb.get("dislike_issue_types") or []
        ids = {t["id"] for t in types_}
        self.assertIn("incorrect_fact", ids)
        self.assertIn("other", ids)
        for t in types_:
            self.assertIn("id", t)
            self.assertIn("label", t)

    def test_assets_all_includes_feedback_types(self):
        r = self.client.get("/api/v1_app/assets/all")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body.get("code"), 0)
        self._assert_feedback_issue_types(body["data"])

    def test_assets_config_includes_feedback_types(self):
        r = self.client.get("/api/v1_app/assets/config")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body.get("code"), 0)
        self._assert_feedback_issue_types(body["data"])

    def test_submit_like_ok(self):
        body = {**_base_ctx(), "rating": "like", "target_type": "chat_response"}
        r = self.client.post("/api/v1_app/feedback/submit", json=body)
        self.assertEqual(r.status_code, 200, r.text)
        data = r.json()
        self.assertEqual(data["code"], 0)
        self.assertTrue(data["data"]["received"])
        self.assertEqual(data["data"]["rating"], "like")

    def test_submit_like_allows_issue_types_no_strict_check(self):
        body = {
            **_base_ctx(),
            "rating": "like",
            "issue_types": ["custom_client_tag"],
        }
        r = self.client.post("/api/v1_app/feedback/submit", json=body)
        self.assertEqual(r.status_code, 200, r.text)

    def test_submit_none_revokes_feedback(self):
        body = {
            **_base_ctx(),
            "rating": "none",
            "target_type": "chat_response",
            "target_ref": "msg_42",
        }
        r = self.client.post("/api/v1_app/feedback/submit", json=body)
        self.assertEqual(r.status_code, 200, r.text)
        data = r.json()
        self.assertEqual(data["data"]["rating"], "none")

    def test_submit_dislike_ok(self):
        body = {
            **_base_ctx(),
            "rating": "dislike",
            "target_type": "task_result",
            "target_ref": "task_123",
            "issue_types": ["incomplete", "other"],
            "detail": "第三步没有执行完",
        }
        r = self.client.post("/api/v1_app/feedback/submit", json=body)
        self.assertEqual(r.status_code, 200, r.text)
        data = r.json()
        self.assertEqual(data["code"], 0)
        self.assertEqual(data["data"]["rating"], "dislike")
        self.assertEqual(data["data"]["target_type"], "task_result")

    def test_submit_dislike_without_issue_types_ok(self):
        body = {**_base_ctx(), "rating": "dislike"}
        r = self.client.post("/api/v1_app/feedback/submit", json=body)
        self.assertEqual(r.status_code, 200, r.text)

    def test_submit_dislike_arbitrary_issue_types_ok(self):
        body = {
            **_base_ctx(),
            "rating": "dislike",
            "issue_types": ["not_in_assets_list", "another_custom"],
        }
        r = self.client.post("/api/v1_app/feedback/submit", json=body)
        self.assertEqual(r.status_code, 200, r.text)
