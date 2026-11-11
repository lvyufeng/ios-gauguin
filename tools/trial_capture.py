"""Verify full trial captures before interpreting whether new probe logs pass."""
from pathlib import Path
import hashlib

LOG_PATHS = (
    '/private/var/tmp/gauguin-gles180.log',
    '/private/var/tmp/gauguin-gles180.stderr.log',
    '/private/var/log/backboardd.log',
)


def need(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def captured_file(directory, row):
    name = row['output']
    need(isinstance(name, str) and Path(name).name == name and name not in ('', '.', '..'),
         'unsafe capture filename')
    file = Path(directory) / name
    need(file.is_file() and not file.is_symlink(), 'capture is not a regular file: ' + name)
    need(file.stat().st_size == row['bytes'] and sha(file) == row['sha256'],
         'captured bytes differ: ' + name)
    return file


def validate_capture(expected, directories, before, before_dir, after, after_dir):
    """An empty appended log is valid capture evidence, never probe success.

    Return every verified log suffix only after checking all static files and
    complete old prefixes. Callers must independently qualify runtime activity.
    Neither probe-log growth nor a green capture result proves GPU/UI behavior.
    """
    need(after['phase'] == 'after-boot', 'not an after-boot capture')
    need(after['device_writes'] == after['reboot_commands'] == 0, 'capture performed device mutations')
    need(len(expected) == 27 and set(after['files']) == set(before['files']) == set(expected),
         'wrong captured file set')
    need(len(directories) == 4 and after['directories'] == directories, 'directory owner/mode differs')
    need(set(LOG_PATHS) <= set(expected), 'required log paths missing')
    outputs = [row['output'] for row in after['files'].values()]
    need(len(set(outputs)) == len(outputs), 'duplicate output filename')
    paths, tails = [], {}
    static = 0
    for name, want in expected.items():
        row = after['files'][name]
        need(row['present'] is True, 'captured file missing: ' + name)
        need(all(row[key] == want[key] for key in ['uid', 'gid', 'mode']), 'file owner/mode differs: ' + name)
        file = captured_file(after_dir, row)
        paths.append(file)
        if name not in LOG_PATHS:
            need(all(row[key] == want[key] for key in ['bytes', 'sha256']), 'static file differs: ' + name)
            static += 1
        else:
            old_row = before['files'][name]
            need(old_row['present'] is True and all(old_row[key] == want[key] for key in ['bytes', 'sha256', 'uid', 'gid', 'mode']),
                 'before-log identity differs: ' + name)
            prefix_file = captured_file(before_dir, old_row)
            paths.append(prefix_file)
            prefix, data = prefix_file.read_bytes(), file.read_bytes()
            need(data.startswith(prefix), 'complete old log prefix differs: ' + name)
            tails[name] = data[len(prefix):]
    need(static == 24 and len(tails) == 3, 'incomplete capture validation')
    return dict(state='all-static-files-directories-and-full-log-prefixes-verified',
                static_files_retained=static, directory_owner_modes_retained=4,
                full_old_log_prefixes_retained=3, root_header_sha256=after['root_header_sha256'],
                log_growth_bytes={name: len(data) for name, data in tails.items()},
                tails=tails, verified_input_files=paths)
