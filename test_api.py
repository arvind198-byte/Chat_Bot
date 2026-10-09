"""API tests using an isolated SQLite database and mocked Gemini responses."""

import os
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from google.genai.errors import ServerError

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

    def test_status_reports_missing_api_key(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": ""}):
            response = self.client.get("/api/status")

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["api_configured"])

    def test_successful_chat_exchange_and_delete(self):
        chat_response = self.client.post("/api/chats", json={"title": "New Chat"})
        self.assertEqual(chat_response.status_code, 201)
        chat_id = chat_response.json()["id"]

        with (
            patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}),
            patch.object(api.genai, "Client", return_value=object()),
            patch.object(api, "generate_response", return_value="Hello there!"),
        ):
            response = self.client.post(
                f"/api/chats/{chat_id}/messages",
                json={"content": "  Hi, Gemini  "},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["content"], "Hello there!")
        self.assertEqual(
            [message["content"] for message in db.get_messages(chat_id)],
            ["Hi, Gemini", "Hello there!"],
        )
        self.assertEqual(db.get_chat(chat_id)["title"], "Hi, Gemini")
        self.assertEqual(self.client.get("/api/chats").json()[0]["id"], chat_id)

        delete_response = self.client.delete(f"/api/chats/{chat_id}")
        self.assertEqual(delete_response.status_code, 204)
        self.assertEqual(db.get_messages(chat_id), [])
        self.assertEqual(
            self.client.get(f"/api/chats/{chat_id}/messages").status_code,
            404,
        )

    def test_missing_api_key_does_not_persist_user_message(self):
        chat_id = db.create_chat()
        with patch.dict(os.environ, {"GEMINI_API_KEY": ""}):
            response = self.client.post(
                f"/api/chats/{chat_id}/messages",
                json={"content": "Hello"},
            )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(db.get_messages(chat_id), [])

    def test_gemini_failure_does_not_persist_partial_exchange(self):
        chat_id = db.create_chat()
        with (
            patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}),
            patch.object(api.genai, "Client", return_value=object()),
            patch.object(api, "generate_response", side_effect=RuntimeError("offline")),
        ):
            response = self.client.post(
                f"/api/chats/{chat_id}/messages",
                json={"content": "Hello"},
            )

        self.assertEqual(response.status_code, 502)
        self.assertEqual(
            response.json()["detail"],
            "Gemini request failed. Check the backend terminal for details.",
        )
        self.assertEqual(db.get_messages(chat_id), [])
        self.assertEqual(db.get_chat(chat_id)["title"], "New Chat")

    def test_gemini_overload_is_reported_as_temporary_and_not_persisted(self):
        chat_id = db.create_chat()
        overload = ServerError(
            503,
            {
                "error": {
                    "code": 503,
                    "message": "This model is currently experiencing high demand.",
                    "status": "UNAVAILABLE",
                }
            },
        )
        with (
            patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}),
            patch.object(api.genai, "Client", return_value=object()),
            patch.object(api, "generate_response", side_effect=overload),
        ):
            response = self.client.post(
                f"/api/chats/{chat_id}/messages",
                json={"content": "Hello"},
            )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.json()["detail"],
            "Gemini is temporarily overloaded. Wait a moment and try again.",
        )
        self.assertEqual(db.get_messages(chat_id), [])

    def test_legacy_failed_user_turn_is_normalized_before_gemini(self):
        chat_id = db.create_chat()
        db.save_message(chat_id, "user", "An earlier request that failed")
        captured = {}

        def capture_contents(contents, client):
            captured["contents"] = contents
            return "Recovered successfully"

        with (
            patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}),
            patch.object(api.genai, "Client", return_value=object()),
            patch.object(api, "generate_response", side_effect=capture_contents),
        ):
            response = self.client.post(
                f"/api/chats/{chat_id}/messages",
                json={"content": "Try again"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [(content.role, content.parts[0].text) for content in captured["contents"]],
            [("user", "An earlier request that failed\n\nTry again")],
        )

    def test_empty_message_and_unknown_chat_are_rejected(self):
        chat_id = db.create_chat()

        empty_response = self.client.post(
            f"/api/chats/{chat_id}/messages",
            json={"content": "   "},
        )
        missing_chat_response = self.client.get("/api/chats/999999/messages")
        missing_delete_response = self.client.delete("/api/chats/999999")

        self.assertEqual(empty_response.status_code, 400)
        self.assertEqual(missing_chat_response.status_code, 404)
        self.assertEqual(missing_delete_response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
