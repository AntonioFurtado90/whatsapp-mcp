"""One-off admin script: download every attachment referenced in the
messages database into the bridge's per-chat store folders.

Safe to re-run: the bridge's /api/download endpoint is idempotent and
returns the existing file instead of re-downloading it, so an interrupted
or failed run can simply be started again.
"""

import sqlite3

import whatsapp


def get_media_messages():
    """Return (message_id, chat_jid) for every message with an attachment."""
    conn = sqlite3.connect(whatsapp.MESSAGES_DB_PATH)
    try:
        cursor = conn.execute(
            "SELECT id, chat_jid FROM messages WHERE media_type != '' ORDER BY chat_jid, timestamp"
        )
        return cursor.fetchall()
    finally:
        conn.close()


def download_all_media():
    """Download every attachment in the database, logging progress.

    Returns (downloaded_count, failed) where failed is a list of the
    (message_id, chat_jid) pairs that could not be downloaded.
    """
    messages = get_media_messages()
    total = len(messages)
    downloaded = 0
    failed = []

    for index, (message_id, chat_jid) in enumerate(messages, start=1):
        path = whatsapp.download_media(message_id, chat_jid, skip_retry=True)
        if path:
            downloaded += 1
        else:
            failed.append((message_id, chat_jid))
        print(f"[{index}/{total}] chat={chat_jid} message={message_id} -> {'ok' if path else 'FAILED'}")

    print(f"\nDone: {downloaded}/{total} downloaded, {len(failed)} failed.")
    if failed:
        print("Failed messages:")
        for message_id, chat_jid in failed:
            print(f"  {chat_jid} / {message_id}")

    return downloaded, failed


if __name__ == "__main__":
    download_all_media()
