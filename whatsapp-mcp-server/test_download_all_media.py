import sqlite3

import whatsapp
from download_all_media import download_all_media, get_media_messages


def _make_db(path, rows):
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE messages (id TEXT, chat_jid TEXT, timestamp TEXT, media_type TEXT)")
    conn.executemany(
        "INSERT INTO messages (id, chat_jid, timestamp, media_type) VALUES (?, ?, ?, ?)",
        rows,
    )
    conn.commit()
    conn.close()


def test_get_media_messages_only_returns_rows_with_media(tmp_path, monkeypatch):
    db_path = str(tmp_path / "messages.db")
    _make_db(
        db_path,
        [
            ("msg1", "123@s.whatsapp.net", "2026-01-01T00:00:00Z", "image"),
            ("msg2", "123@s.whatsapp.net", "2026-01-02T00:00:00Z", ""),
            ("msg3", "456@g.us", "2026-01-03T00:00:00Z", "document"),
        ],
    )
    monkeypatch.setattr(whatsapp, "MESSAGES_DB_PATH", db_path)

    messages = get_media_messages()

    assert messages == [("msg1", "123@s.whatsapp.net"), ("msg3", "456@g.us")]


def test_download_all_media_downloads_each_message_and_counts_failures(tmp_path, monkeypatch):
    db_path = str(tmp_path / "messages.db")
    _make_db(
        db_path,
        [
            ("msg1", "123@s.whatsapp.net", "2026-01-01T00:00:00Z", "image"),
            ("msg2", "456@g.us", "2026-01-02T00:00:00Z", "document"),
        ],
    )
    monkeypatch.setattr(whatsapp, "MESSAGES_DB_PATH", db_path)

    calls = []

    def fake_download_media(message_id, chat_jid, skip_retry=False):
        calls.append((message_id, chat_jid, skip_retry))
        return f"/app/store/{chat_jid}/{message_id}" if message_id == "msg1" else None

    monkeypatch.setattr(whatsapp, "download_media", fake_download_media)

    downloaded, failed = download_all_media()

    assert calls == [
        ("msg1", "123@s.whatsapp.net", True),
        ("msg2", "456@g.us", True),
    ]
    assert downloaded == 1
    assert failed == [("msg2", "456@g.us")]
