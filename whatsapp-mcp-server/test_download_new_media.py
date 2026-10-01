import sqlite3

import pipeline_state
import whatsapp
from download_new_media import download_new_media


def _make_messages_db(path, rows):
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE messages (id TEXT, chat_jid TEXT, timestamp TEXT, media_type TEXT)")
    conn.executemany(
        "INSERT INTO messages (id, chat_jid, timestamp, media_type) VALUES (?, ?, ?, ?)",
        rows,
    )
    conn.commit()
    conn.close()


def test_download_new_media_only_downloads_unprocessed_and_skips_failures(tmp_path, monkeypatch):
    state_db = str(tmp_path / "pipeline_state.db")
    monkeypatch.setattr(pipeline_state, "PIPELINE_STATE_DB_PATH", state_db)

    messages_db = str(tmp_path / "messages.db")
    _make_messages_db(
        messages_db,
        [
            ("msg1", "123@s.whatsapp.net", "2026-01-01T00:00:00Z", "image"),
            ("msg2", "456@g.us", "2026-01-02T00:00:00Z", "document"),
        ],
    )
    monkeypatch.setattr(whatsapp, "MESSAGES_DB_PATH", messages_db)

    calls = []

    def fake_download_media(message_id, chat_jid, skip_retry=False):
        calls.append((message_id, chat_jid, skip_retry))
        if message_id == "msg1":
            return f"/app/store/{chat_jid}/{message_id}.jpg"
        return None

    monkeypatch.setattr(whatsapp, "download_media", fake_download_media)

    manifest = download_new_media()

    assert calls == [
        ("msg1", "123@s.whatsapp.net", True),
        ("msg2", "456@g.us", True),
    ]
    assert manifest == [
        {
            "message_id": "msg1",
            "chat_jid": "123@s.whatsapp.net",
            "media_type": "image",
            "path": "/app/store/123@s.whatsapp.net/msg1.jpg",
        }
    ]
