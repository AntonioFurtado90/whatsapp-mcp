"""Tracks which media messages the Google Drive export pipeline has already
finished (downloaded, renamed and uploaded), so the hourly run only picks up
new ones.

This is a separate state store from messages.db on purpose: once a
downloaded file is renamed, its on-disk name no longer matches what
messages.db recorded, so "does the file already exist" can't be used as the
completion check for this pipeline.
"""

import os
import sqlite3
import sys

PIPELINE_STATE_DB_PATH = os.environ.get(
    "PIPELINE_STATE_DB_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "whatsapp-bridge", "store", "pipeline_state.db"),
)

EXCLUDED_CHAT_JID = "status@broadcast"


def _connect():
    conn = sqlite3.connect(PIPELINE_STATE_DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS processed_media (
            message_id TEXT NOT NULL,
            chat_jid TEXT NOT NULL,
            processed_at TEXT NOT NULL DEFAULT (datetime('now')),
            PRIMARY KEY (message_id, chat_jid)
        )
        """
    )
    return conn


def list_unprocessed(messages_db_path, media_types=("image", "document")):
    """Return (message_id, chat_jid, media_type) for every media message not
    yet marked processed, excluding the WhatsApp status/broadcast chat."""
    state_conn = _connect()
    try:
        done = {(row[0], row[1]) for row in state_conn.execute("SELECT message_id, chat_jid FROM processed_media")}
    finally:
        state_conn.close()

    placeholders = ",".join("?" for _ in media_types)
    msg_conn = sqlite3.connect(messages_db_path)
    try:
        cursor = msg_conn.execute(
            f"SELECT id, chat_jid, media_type FROM messages "
            f"WHERE media_type IN ({placeholders}) AND chat_jid != ? "
            f"ORDER BY chat_jid, timestamp",
            (*media_types, EXCLUDED_CHAT_JID),
        )
        rows = cursor.fetchall()
    finally:
        msg_conn.close()

    return [row for row in rows if (row[0], row[1]) not in done]


def mark_processed(message_id, chat_jid):
    conn = _connect()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO processed_media (message_id, chat_jid) VALUES (?, ?)",
            (message_id, chat_jid),
        )
        conn.commit()
    finally:
        conn.close()


def is_processed(message_id, chat_jid):
    conn = _connect()
    try:
        cursor = conn.execute(
            "SELECT 1 FROM processed_media WHERE message_id = ? AND chat_jid = ?",
            (message_id, chat_jid),
        )
        return cursor.fetchone() is not None
    finally:
        conn.close()


if __name__ == "__main__":
    import whatsapp

    if len(sys.argv) < 2:
        print("Usage: pipeline_state.py list | mark <message_id> <chat_jid>", file=sys.stderr)
        sys.exit(1)

    command = sys.argv[1]
    if command == "list":
        for message_id, chat_jid, media_type in list_unprocessed(whatsapp.MESSAGES_DB_PATH):
            print(f"{message_id}\t{chat_jid}\t{media_type}")
    elif command == "mark":
        if len(sys.argv) != 4:
            print("Usage: pipeline_state.py mark <message_id> <chat_jid>", file=sys.stderr)
            sys.exit(1)
        mark_processed(sys.argv[2], sys.argv[3])
    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        sys.exit(1)
