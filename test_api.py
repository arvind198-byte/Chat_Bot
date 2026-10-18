"""API tests using an isolated SQLite database and mocked LLM responses."""

import os
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

import backend.main as api
import database as db


class ChatApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db.close()
        self.previous_db_path = db.DB_PATH
        db.DB_PATH = self.temp_db.name
        db.init_db()
        self.client = TestClient(api.app)

    def tearDown(self):
        db.DB_PATH = self.previous_db_path
        os.unlink(self.temp_db.name)

    def test_status_reports_model_info(self):
        response = self.client.get("/api/status")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("assistant_name", data)
        self.assertEqual(data["assistant_name"], "Placement Cell Virtual Assistant")

    def test_successful_chat_exchange_and_feedback(self):
        chat_response = self.client.post("/api/chats", json={"title": "New Chat"})
        self.assertEqual(chat_response.status_code, 201)
        chat_id = chat_response.json()["id"]

        with (
            patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}),
            patch.object(api.genai, "Client", return_value=object()),
            patch.object(api, "generate_response", return_value=("Students must maintain 6.0 CGPA.", 120, 45)),
        ):
            response = self.client.post(
                f"/api/chats/{chat_id}/messages",
                json={"content": "What is the minimum CGPA?"},
            )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["content"], "Students must maintain 6.0 CGPA.")
        self.assertEqual(data["latency_ms"], 120)
        self.assertEqual(data["tokens_used"], 45)
        self.assertIn("id", data)
        self.assertIn("created_at", data)
        self.assertIn("user_message_id", data)
        self.assertIn("user_created_at", data)
        self.assertIsNotNone(data["created_at"])
        self.assertIsNotNone(data["user_created_at"])
        assistant_msg_id = data["id"]

        # Verify feedback submission
        feedback_response = self.client.post(
            "/api/feedback",
            json={"message_id": assistant_msg_id, "rating": 1},
        )
        self.assertEqual(feedback_response.status_code, 201)
        self.assertEqual(feedback_response.json()["status"], "success")

        # Verify database contents
        messages = db.get_messages(chat_id)
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]["role"], "user")
        self.assertEqual(messages[1]["role"], "assistant")
        self.assertEqual(messages[1]["latency_ms"], 120)
        self.assertEqual(messages[1]["tokens_used"], 45)

        # Verify chat deletion
        delete_response = self.client.delete(f"/api/chats/{chat_id}")
        self.assertEqual(delete_response.status_code, 204)
        self.assertEqual(db.get_messages(chat_id), [])

    def test_missing_api_key_returns_503(self):
        chat_id = db.create_chat()
        with patch.dict(os.environ, {"GEMINI_API_KEY": ""}):
            response = self.client.post(
                f"/api/chats/{chat_id}/messages",
                json={"content": "Tell me about Tier 1"},
            )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(db.get_messages(chat_id), [])

    def test_feedback_validation(self):
        invalid_rating = self.client.post(
            "/api/feedback",
            json={"message_id": 1, "rating": 5},
        )
        self.assertEqual(invalid_rating.status_code, 400)


if __name__ == "__main__":
    unittest.main()
