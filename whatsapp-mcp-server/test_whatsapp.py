import importlib
import os

import whatsapp


def _config_after_reload_with_env(**env):
    """Reload whatsapp.py with the given env vars set (None = unset) and
    snapshot the resulting config, then restore the previous environment.

    The snapshot is necessary because reload() mutates the module in place;
    returning the module itself would let the env restore below overwrite
    the values before the caller gets to assert on them.
    """
    old = {key: os.environ.get(key) for key in env}
    try:
        for key, value in env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        importlib.reload(whatsapp)
        return whatsapp.WHATSAPP_API_BASE_URL, whatsapp.MESSAGES_DB_PATH
    finally:
        for key, value in old.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        importlib.reload(whatsapp)


def test_config_uses_env_var_overrides_when_set():
    api_base_url, db_path = _config_after_reload_with_env(
        WHATSAPP_API_BASE_URL="http://whatsapp-bridge:8090/api",
        MESSAGES_DB_PATH="/app/store/messages.db",
    )
    assert api_base_url == "http://whatsapp-bridge:8090/api"
    assert db_path == "/app/store/messages.db"


def test_config_falls_back_to_defaults_without_env_vars():
    api_base_url, db_path = _config_after_reload_with_env(
        WHATSAPP_API_BASE_URL=None, MESSAGES_DB_PATH=None
    )
    assert api_base_url == "http://localhost:8090/api"
    assert db_path.endswith(os.path.join("whatsapp-bridge", "store", "messages.db"))
