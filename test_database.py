"""
Tests for database.py.

Uses an in-memory SQLite database by temporarily overriding ``database.DB_PATH``
so no on-disk state is touched.
"""

import sys
import os

# Ensure the project root is importable.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import database as db


def _setup():
    """Point the module at an in-memory DB and initialise it."""
    db.DB_PATH = ":memory:"
    # Because each _connect() opens a NEW connection to ":memory:", every call
    # gets a fresh empty database. We need a file-based temp DB instead.
    import tempfile
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    db.DB_PATH = tmp.name
    db.init_db()
    return tmp.name


def _teardown(path):
    try:
        os.unlink(path)
    except OSError:
        pass


def test_init_db_creates_tables():
    path = _setup()
    try:
        import sqlite3
        conn = sqlite3.connect(path)
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()]
        conn.close()
        assert "chats" in tables, f"'chats' table missing; found {tables}"
        assert "messages" in tables, f"'messages' table missing; found {tables}"
        print("PASS test_init_db_creates_tables")
    finally:
        _teardown(path)


def test_create_chat():
    path = _setup()
    try:
        cid = db.create_chat("Test Chat")
        assert isinstance(cid, int) and cid > 0, f"Expected positive int, got {cid}"

        chats = db.get_chats()
        assert len(chats) == 1
        assert chats[0]["title"] == "Test Chat"
        print("PASS test_create_chat")
    finally:
        _teardown(path)


def test_save_and_get_messages():
    path = _setup()
    try:
        cid = db.create_chat()
        db.save_message(cid, "user", "Hello")
        db.save_message(cid, "assistant", "Hi there!")

        msgs = db.get_messages(cid)
        assert len(msgs) == 2, f"Expected 2 messages, got {len(msgs)}"
        assert msgs[0]["role"] == "user"
        assert msgs[0]["content"] == "Hello"
        assert msgs[1]["role"] == "assistant"
        assert msgs[1]["content"] == "Hi there!"
        print("PASS test_save_and_get_messages")
    finally:
        _teardown(path)


def test_messages_ordered_chronologically():
    path = _setup()
    try:
        cid = db.create_chat()
        for i in range(5):
            db.save_message(cid, "user" if i % 2 == 0 else "assistant", f"msg-{i}")

        msgs = db.get_messages(cid)
        ids = [m["id"] for m in msgs]
        assert ids == sorted(ids), "Messages should be in insertion order"
        print("PASS test_messages_ordered_chronologically")
    finally:
        _teardown(path)


def test_get_chats_ordered_by_updated():
    path = _setup()
    try:
        c1 = db.create_chat("Old")
        c2 = db.create_chat("New")
        # Touch old chat so its updated_at becomes newest.
        db.save_message(c1, "user", "bump")

        chats = db.get_chats()
        assert chats[0]["id"] == c1, "Most recently updated chat should come first"
        assert chats[1]["id"] == c2
        print("PASS test_get_chats_ordered_by_updated")
    finally:
        _teardown(path)


def test_update_chat_title():
    path = _setup()
    try:
        cid = db.create_chat("Original")
        db.update_chat_title(cid, "Renamed")

        chats = db.get_chats()
        assert chats[0]["title"] == "Renamed"
        print("PASS test_update_chat_title")
    finally:
        _teardown(path)


def test_delete_chat_removes_messages():
    path = _setup()
    try:
        cid = db.create_chat("To Delete")
        db.save_message(cid, "user", "Hello")
        db.save_message(cid, "assistant", "World")

        db.delete_chat(cid)

        assert db.get_chats() == [], "Chat should be deleted"
        assert db.get_messages(cid) == [], "Messages should be cascade-deleted"
        print("PASS test_delete_chat_removes_messages")
    finally:
        _teardown(path)


def test_empty_database():
    path = _setup()
    try:
        assert db.get_chats() == [], "No chats expected"
        assert db.get_messages(999) == [], "No messages for non-existent chat"
        print("PASS test_empty_database")
    finally:
        _teardown(path)


def test_messages_isolated_between_chats():
    path = _setup()
    try:
        c1 = db.create_chat("Chat 1")
        c2 = db.create_chat("Chat 2")
        db.save_message(c1, "user", "Only in chat 1")
        db.save_message(c2, "user", "Only in chat 2")

        m1 = db.get_messages(c1)
        m2 = db.get_messages(c2)
        assert len(m1) == 1 and m1[0]["content"] == "Only in chat 1"
        assert len(m2) == 1 and m2[0]["content"] == "Only in chat 2"
        print("PASS test_messages_isolated_between_chats")
    finally:
        _teardown(path)


def test_save_message_returns_id():
    path = _setup()
    try:
        cid = db.create_chat()
        mid = db.save_message(cid, "user", "test")
        assert isinstance(mid, int) and mid > 0
        assert getattr(mid, "created_at", None) is not None, "Message created_at should be populated"
        print("PASS test_save_message_returns_id")
    finally:
        _teardown(path)


def test_save_exchange_returns_timestamps():
    path = _setup()
    try:
        cid = db.create_chat("Exchange Test")
        res = db.save_exchange(cid, "Hello prompt", "Hello answer", latency_ms=150, tokens_used=30)
        assert isinstance(res, int) and res > 0
        assert getattr(res, "created_at", None) is not None, "Assistant timestamp should be present"
        assert getattr(res, "user_created_at", None) is not None, "User timestamp should be present"
        assert getattr(res, "user_msg_id", 0) > 0, "User message ID should be present"
        msgs = db.get_messages(cid)
        assert len(msgs) == 2
        assert msgs[0]["created_at"] is not None
        assert msgs[1]["created_at"] is not None
        assert msgs[1]["latency_ms"] == 150
        assert msgs[1]["tokens_used"] == 30
        print("PASS test_save_exchange_returns_timestamps")
    finally:
        _teardown(path)


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    tests = [
        test_init_db_creates_tables,
        test_create_chat,
        test_save_and_get_messages,
        test_messages_ordered_chronologically,
        test_get_chats_ordered_by_updated,
        test_update_chat_title,
        test_delete_chat_removes_messages,
        test_empty_database,
        test_messages_isolated_between_chats,
        test_save_message_returns_id,
        test_save_exchange_returns_timestamps,
    ]

    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except Exception as e:
            print(f"FAIL {t.__name__}: {e}")
            failed += 1

    print(f"\n{'='*40}")
    print(f"Results: {passed} passed, {failed} failed out of {len(tests)}")
    if failed:
        sys.exit(1)
    print("All tests passed.")
