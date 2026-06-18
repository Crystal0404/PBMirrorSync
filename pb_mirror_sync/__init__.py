from threading import Event, RLock
from functools import wraps

from mcdreforged import *

from pb_mirror_sync.config import Config
from pb_mirror_sync.constant import SI

CONFIG: Config
sync_status = False
abort_event = Event()
lock = RLock()


def on_load(server: PluginServerInterface, old):
    global CONFIG
    CONFIG = server.load_config_simple(target_class=Config)

    root = (
        Literal(CONFIG.prefix)
        .requires(
            Requirements.has_permission(CONFIG.permission),
            lambda: server.rtr('mcdreforged.mcdr_command.permission_denied')
        )
        .runs(lambda: ...)
        .then(Literal('sync').runs(sync))
        .then(Literal('confirm').runs(confirm))
        .then(Literal('abort').runs(abort))
    )
    server.register_command(root)

def warp_lock(func):
    @wraps(func)
    def warp(*args, **kwargs):
        with lock:
            result = func(*args, **kwargs)
        return result
    return warp


def sync():
    global sync_status
    if lock.locked():
        SI.broadcast(SI.rtr('pb_mirror_sync.running'))
    else:
        sync_status = True


@new_thread('MirrorSync')
@warp_lock
def _sync():
    abort_event.clear()
    for i in range(10, 0, -1):
        SI.logger.info(i)
        abort_event.wait(timeout=1)
        if abort_event.is_set():
            return




def confirm():
    global sync_status
    if lock.locked() and sync_status:
        sync_status = False
        SI.broadcast(SI.rtr('pb_mirror_sync.running'))
        return
    if sync_status:
        sync_status = False
        _sync()
    else:
        SI.broadcast(SI.rtr('pb_mirror_sync.no_confirm'))


def abort():
    global sync_status
    abort_event.set()
    sync_status = False
    SI.broadcast(SI.rtr('pb_mirror_sync.abort'))
