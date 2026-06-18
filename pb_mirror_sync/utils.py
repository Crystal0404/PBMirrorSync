from pathlib import Path

from pb_mirror_sync.constant import SI


def broadcast(key: str, *args, **kwargs):
    SI.broadcast(SI.rtr(key, *args, **kwargs))


def get_server_path() -> Path:
    config = SI.get_mcdr_config()
    return Path(config['working_directory'])
