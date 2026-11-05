#!/usr/bin/env python3
"""Actual PIO with finite FIFOs, removed-credit failure, and raw protocol frames."""
import os
from pathlib import Path
import resource
import shlex
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent.parent
XNU = Path(os.environ.get('XNU_SOURCE', ROOT / '.deps-cache/xnu-patched-0082-2'))
MODULE = Path(os.environ.get('NVT_MODULE_ROOT', XNU / 'bsd/dev/gauguin_nvt')).resolve()
FIXTURES = ROOT / 'tests/fixtures/gauguin_nvt'


def main():
    required = ['geni_spi_pio.c', 'geni_spi_pio.h', 'nvt_protocol.c', 'nvt_protocol.h']
    missing = [MODULE / name for name in required if not (MODULE / name).is_file()]
    if missing:
        if 'XNU_SOURCE' in os.environ or 'NVT_MODULE_ROOT' in os.environ:
            raise SystemExit(f'NVT transport inputs missing: {missing}')
        print(f'skip NVT transport: module not staged at {MODULE}')
        return
    flags = shlex.split(os.environ.get('CC', 'cc')) + [
        '-std=c11', '-Wall', '-Wextra', '-Werror', '-pedantic', '-O1', '-g',
        '-fsanitize=address,undefined', '-fno-omit-frame-pointer', '-I', str(MODULE)]
    fixture = FIXTURES / 'test_geni_spi_pio.c'
    with tempfile.TemporaryDirectory(prefix='gauguin-nvt-transport-') as temporary:
        directory = Path(temporary)
        output = directory / 'test'
        subprocess.run(flags + [str(MODULE / 'geni_spi_pio.c'), str(fixture),
                               '-o', str(output)], check=True, cwd=directory, timeout=60)
        subprocess.run([str(output)], check=True, cwd=directory, timeout=30)
        # The sole production mutation is this explicit negative control, in
        # temporary storage. Positives above/below compile original XNU files.
        source = (MODULE / 'geni_spi_pio.c').read_text()
        guard = ' &&\n               s->diag.tx_queued - s->diag.rx_received < 60'
        assert source.count(guard) == 1, 'update removed-credit control for actual PIO source'
        bad_source = directory / 'no_credit.c'
        bad_source.write_text(source.replace(guard, '', 1))
        bad_output = directory / 'no_credit'
        subprocess.run(flags + [str(bad_source), str(fixture), '-o', str(bad_output)],
                       check=True, cwd=directory, timeout=60)
        bad = subprocess.run([str(bad_output)], capture_output=True, text=True,
                             cwd=directory, timeout=30,
                             preexec_fn=lambda: resource.setrlimit(resource.RLIMIT_CORE, (0, 0)))
        assert bad.returncode != 0 and 'm->rw < 16' in bad.stderr, bad.stderr
        print('PASS: removed-credit negative control overflows finite RX FIFO')
        combined = directory / 'combined'
        subprocess.run(flags + [str(MODULE / 'geni_spi_pio.c'), str(MODULE / 'nvt_protocol.c'),
                               str(FIXTURES / 'test_nvt_transport.c'), '-o', str(combined)],
                       check=True, cwd=directory, timeout=60)
        subprocess.run([str(combined)], check=True, cwd=directory, timeout=30)


if __name__ == '__main__':
    main()
