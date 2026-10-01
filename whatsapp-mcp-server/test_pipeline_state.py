import sqlite3

import pipeline_state


def _make_messages_db(path, rows):
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE messages (id TEXT, chat_jid TEXT, timestamp TEXT, media_type TEXT)")
    conn.executemany(
        "INSERT INTO messages (id, chat_jid, timestamp, media_type) VALUES (?, ?, ?, ?)",
        rows,
    )
    conn.commit()
    conn.close()


def test_list_unprocessed_excludes_other_media_types_and_status_broadcast(tmp_path, monkeypatch):
    state_db = str(tmp_path / "pipeline_state.db")
    monkeypatch.setattr(pipeline_state, "PIPELINE_STATE_DB_PATH", state_db)

    messages_db = str(tmp_path / "messages.db")
    _make_messages_db(
        messages_db,
        [
            ("msg1", "123@s.whatsapp.net", "2026-01-01T00:00:00Z", "image"),
            ("msg2", "123@s.whatsapp.net", "2026-01-02T00:00:00Z", "audio"),
            ("msg3", "status@broadcast", "2026-01-03T00:00:00Z", "image"),
            ("msg4", "456@g.us", "2026-01-04T00:00:00Z", "document"),
        ],
    )

    result = pipeline_state.list_unprocessed(messages_db)

    assert result == [("msg1", "123@s.whatsapp.net", "image"), ("msg4", "456@g.us", "document")]


def test_list_unprocessed_skips_already_marked_messages(tmp_path, monkeypatch):
    state_db = str(tmp_path / "pipeline_state.db")
    monkeypatch.setattr(pipeline_state, "PIPELINE_STATE_DB_PATH", state_db)

    messages_db = str(tmp_path / "messages.db")
    _make_messages_db(
        messages_db,
        [
            ("msg1", "123@s.whatsapp.net", "2026-01-01T00:00:00Z", "image"),
            ("msg2", "123@s.whatsapp.net", "2026-01-02T00:00:00Z", "document"),
        ],
    )

    pipeline_state.mark_processed("msg1", "123@s.whatsapp.net")

    result = pipeline_state.list_unprocessed(messages_db)

    assert result == [("msg2", "123@s.whatsapp.net", "document")]


def test_mark_processed_is_idempotent(tmp_path, monkeypatch):
    state_db = str(tmp_path / "pipeline_state.db")
    monkeypatch.setattr(pipeline_state, "PIPELINE_STATE_DB_PATH", state_db)

    pipeline_state.mark_processed("msg1", "123@s.whatsapp.net")
    pipeline_state.mark_processed("msg1", "123@s.whatsapp.net")

    assert pipeline_state.is_processed("msg1", "123@s.whatsapp.net")


def test_is_processed_false_for_unknown_message(tmp_path, monkeypatch):
    state_db = str(tmp_path / "pipeline_state.db")
    monkeypatch.setattr(pipeline_state, "PIPELINE_STATE_DB_PATH", state_db)

    assert not pipeline_state.is_processed("missing", "123@s.whatsapp.net")
