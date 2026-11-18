"""Scanner configuration shared by uploads and readiness."""
import os
import shlex


def operational():
    return os.getenv('FRAMATEX_MODE', '').upper() == 'OPERATIONAL'


def scanner_command(backend):
    configured = os.getenv('FRAMATEX_SCANNER_COMMAND', '').strip()
    if configured:
        return shlex.split(configured)
    if backend == 'clamav':
        directory = os.getenv('FRAMATEX_CLAMAV_DATABASE_DIR', '/var/lib/clamav')
        return ['clamscan', '--no-summary', '--alert-encrypted=yes', '--database=' + directory]
    return []
