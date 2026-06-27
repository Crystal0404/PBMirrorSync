import shutil
import subprocess
from functools import wraps
from threading import Event, RLock

from mcdreforged import *

from pb_mirror_sync.config import Config
from pb_mirror_sync.constant import SI
from pb_mirror_sync.utils import broadcast, get_server_path

CONFIG: Config
sync_status = False
abort_event = Event()
lock = RLock()


def on_load(server: PluginServerInterface, _):
    global CONFIG
    CONFIG = server.load_config_simple(target_class=Config)
    root = (
        Literal(CONFIG.prefix)
        .requires(
            Requirements.has_permission(CONFIG.permission),
            lambda: server.rtr('mcdreforged.mcdr_command.permission_denied')
        )
        .runs(root_command)
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


def root_command(source: CommandSource):
    source.reply(
        SI.rtr(
            'pb_mirror_sync.common.root_title',
            command=RText(f'{CONFIG.prefix} sync', color=RColor.gray)
            .set_click_event(RClickRunCommand(f'{CONFIG.prefix} sync'))
            .set_hover_event(RHoverText(RText(SI.rtr('pb_mirror_sync.common.sync_hover'))))
        )
    )


def sync():
    global sync_status
    if lock.locked():
        broadcast('pb_mirror_sync.common.running')
    else:
        sync_status = True
        broadcast('pb_mirror_sync.common.sync_prepare')
        broadcast(
            'pb_mirror_sync.common.sync_confirm_hint',
            confirm=RText(f'{CONFIG.prefix} confirm', color=RColor.gray)
            .set_click_event(RClickRunCommand(f'{CONFIG.prefix} confirm'))
            .set_hover_event(RHoverText(SI.rtr('pb_mirror_sync.confirm.hover'))),
            abort=RText(f'{CONFIG.prefix} abort', color=RColor.gray)
            .set_click_event(RClickRunCommand(f'{CONFIG.prefix} abort'))
            .set_hover_event(RHoverText(SI.rtr('pb_mirror_sync.abort.hover')))
        )


@new_thread('MirrorSync')
@warp_lock
def _sync():
    global sync_status
    abort_event.clear()
    for i in range(10, 0, -1):
        broadcast(
            'pb_mirror_sync.common.sync_countdown',
            sec=RText(i, color=RColor.yellow)
        )
        abort_event.wait(timeout=1)
        if abort_event.is_set():
            broadcast('pb_mirror_sync.abort.cancel')
            return

    SI.stop()
    SI.wait_until_stop()

    if CONFIG.backup.enabled:
        SI.logger.info('Backup world')
        arg = [
            CONFIG.backup.python,
            CONFIG.backup.pb_path,
            '-d',
            CONFIG.backup.db_file,
            'make',
            '-s',
            CONFIG.backup.source_root,
            SI.tr('pb_mirror_sync.common.pb_make_commet')
        ]
        if CONFIG.backup.config_file is not None:
            arg[4:4] = ['-c', CONFIG.backup.config_file]
        output = subprocess.run(arg, capture_output=True, text=True)
        SI.logger.info(output.stdout.strip())

    SI.logger.info('Delete the world')
    for e in CONFIG.sync.target:
        path = get_server_path().joinpath(e)
        if not path.exists() or not path.is_dir():
            continue
        shutil.rmtree(path)

    SI.logger.info('Exporting world from PB')
    for e in CONFIG.sync.target:
        path = get_server_path().joinpath(e)
        arg = [
            CONFIG.sync.python,
            CONFIG.sync.pb_path,
            '-d',
            CONFIG.sync.db_file,
            'extract',
            'latest',
            str(e),
            '-r',
            '-o',
            str(path.parent)
        ]
        if CONFIG.sync.config_file is not None:
            arg[4:4] = ['-c', CONFIG.sync.config_file]
        output = subprocess.run(arg, capture_output=True, text=True)
        SI.logger.info(output.stdout.strip())

    SI.start()


def confirm():
    global sync_status
    if lock.locked() and sync_status:
        sync_status = False
        broadcast('pb_mirror_sync.common.running')
        return
    if sync_status:
        sync_status = False
        _sync()
    else:
        broadcast('pb_mirror_sync.confirm.no_confirm')


def abort():
    global sync_status
    abort_event.set()
    sync_status = False
    broadcast('pb_mirror_sync.common.cancel')
