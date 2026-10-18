from pathlib import Path

from mcdreforged import PluginServerInterface


__all__ = [
    'PB_ID',
    'si',
    'broadcast',
    'get_server_path'
]
PB_ID = 'prime_backup'

def si():
    return PluginServerInterface.get_instance()

def broadcast(key: str, *args, **kwargs):
    si().broadcast(si().rtr(key, *args, **kwargs))


def get_server_path() -> Path:
    config = si().get_mcdr_config()
    return Path(config['working_directory'])
