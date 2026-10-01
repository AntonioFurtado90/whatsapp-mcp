"""Downloads media messages not yet seen by the export pipeline
(pipeline_state.py) and prints a JSON-lines manifest of what landed on disk,
for the renaming/upload step to pick up.

Does not mark anything as processed -- that only happens once a file has
been renamed AND uploaded, which is the caller's responsibility.
"""

import json
import os

import whatsapp
from pipeline_state import list_unprocessed

# Caps how much a single run takes on, so a burst of backlog (e.g. the bridge
# being offline for a day) can't hand the renaming/upload step more than it
# can realistically get through in one pass. Anything left over just rolls
# over to the next run.
MAX_PER_RUN = int(os.environ.get("PIPELINE_MAX_PER_RUN", "25"))


def download_new_media():
    pending = list_unprocessed(whatsapp.MESSAGES_DB_PATH)[:MAX_PER_RUN]
    manifest = []
    for message_id, chat_jid, media_type in pending:
        path = whatsapp.download_media(message_id, chat_jid, skip_retry=True)
        if path:
            manifest.append(
                {"message_id": message_id, "chat_jid": chat_jid, "media_type": media_type, "path": path}
            )
    return manifest


if __name__ == "__main__":
    for entry in download_new_media():
        print(json.dumps(entry, ensure_ascii=False))
