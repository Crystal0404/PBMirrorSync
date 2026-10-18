import shutil
import subprocess
from threading import Event, Lock, Thread

from mcdreforged import *

from pb_mirror_sync.config import Config
from pb_mirror_sync.utils import broadcast, get_server_path, si

CONFIG: Config
sync_status = False
abort_event = Event()
lock = Lock()


def on_load(server: PluginServerInterface, _):
    global CONFIG
    CONFIG = server.load_config_simple(target_class=Config)
    root = (Literal(CONFIG.prefix).requires(Requirements.has_permission(CONFIG.permission),
        lambda: server.rtr('mcdreforged.mcdr_command.permission_denied')).runs(root_command).then(
        Literal('sync').runs(sync)).then(Literal('confirm').runs(confirm)).then(Literal('abort').runs(abort)))
    server.register_command(root)


def root_command(source: CommandSource):
    source.reply(si().rtr('pb_mirror_sync.common.root_title',
        command=RText(f'{CONFIG.prefix} sync', color=RColor.gray).set_click_event(
            RClickRunCommand(f'{CONFIG.prefix} sync')).set_hover_event(
            RHoverText(RText(si().rtr('pb_mirror_sync.common.sync_hover'))))))


def sync():
    global sync_status
    if lock.locked():
        broadcast('pb_mirror_sync.common.running')
    else:
        sync_status = True
        broadcast('pb_mirror_sync.common.sync_prepare')
        broadcast('pb_mirror_sync.common.sync_confirm_hint',
            confirm=RText(f'{CONFIG.prefix} confirm', color=RColor.gray).set_click_event(
                RClickRunCommand(f'{CONFIG.prefix} confirm')).set_hover_event(
                RHoverText(si().rtr('pb_mirror_sync.confirm.hover'))),
            abort=RText(f'{CONFIG.prefix} abort', color=RColor.gray).set_click_event(
                RClickRunCommand(f'{CONFIG.prefix} abort')).set_hover_event(
                RHoverText(si().rtr('pb_mirror_sync.abort.hover'))))


def sync_entry():
    try:
        _sync()
    finally:
        lock.release()


def _sync():
    abort_event.clear()
    for i in range(10, 0, -1):
        broadcast('pb_mirror_sync.common.sync_countdown', sec=RText(i, color=RColor.yellow))
        abort_event.wait(timeout=1)
        if abort_event.is_set():
            broadcast('pb_mirror_sync.abort.cancel')
            return

    si().stop()
    si().wait_until_stop()

    if CONFIG.backup.enabled:
        si().logger.info('Backup world')
        arg = [CONFIG.backup.python, CONFIG.backup.pb_path, '-d', CONFIG.backup.db_file, 'make', '-s',
            str(get_server_path()), si().tr('pb_mirror_sync.common.pb_make_commet')]
        if CONFIG.backup.config_file is not None:
            arg[4:4] = ['-c', CONFIG.backup.config_file]
        output = subprocess.run(arg, capture_output=True, text=True)
        si().logger.info(output.stdout.strip())

    si().logger.info('Delete the world')
    for e in CONFIG.sync.target:
        path = get_server_path().joinpath(e)
        if path.is_dir():
            shutil.rmtree(path)

    si().logger.info('Exporting world from PB')
    for e in CONFIG.sync.target:
        path = get_server_path().joinpath(e)
        arg = [CONFIG.sync.python, CONFIG.sync.pb_path, '-d', CONFIG.sync.db_file, 'extract', 'latest', str(e), '-r',
            '-o', str(path.parent)]
        if CONFIG.sync.config_file is not None:
            arg[4:4] = ['-c', CONFIG.sync.config_file]
        output = subprocess.run(arg, capture_output=True, text=True)
        si().logger.info(output.stdout.strip())

    si().start()


def confirm():
    global sync_status
    if sync_status and lock.acquire(blocking=False):
        sync_status = False
        Thread(target=sync_entry, name='MirrorSync').start()
    elif sync_status:
        sync_status = False
        broadcast('pb_mirror_sync.common.running')
    else:
        broadcast('pb_mirror_sync.confirm.no_confirm')


def abort():
    global sync_status
    abort_event.set()
    sync_status = False
    broadcast('pb_mirror_sync.common.cancel')
