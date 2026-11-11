#!/usr/bin/env python3
"""Host-only checks for the 0297 boot command plus `` sweetfb_stats=1``.

The candidate removes exactly one ``sweetwdtpet=0`` token from the real 0297
command and appends ``sweetfb_stats=1``.  This module checks the command text,
the packer's 608-byte field, the host trial-identity grammar, and the actual
GAUGUIN watchdog source functions that read the removed token.  The C functions
are extracted from the 0297 source tree and compiled against a parser that
implements the source's exact name/``=``/whitespace rules.

Scope: these are host/source checks only.  They do not establish that prebuilt
iOS userland or physical hardware interprets the command the same way, and they
do not prove a boot, a log line, or a watchdog reset.  In particular the
launchd boot-args text loses ``sweetwdtpet=0``; only kernel-source consumers
are covered.
"""
from collections import Counter
import difflib
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / 'tools'
sys.path[:0] = [str(TOOLS)]
import extract_cmd_db_snapshot as extractor  # noqa: E402
import mkpayload  # noqa: E402

COMMAND_PATH = Path(os.environ.get(
    'PRESENT_0297_COMMAND',
    ROOT.parent / 'gauguin-fault297-worktree-20261111/research/tmp/'
                  'dsh-fault297-native/image-result297.json'))
SOURCE_PATH = Path(os.environ.get(
    'XNU_SOURCE',
    ROOT.parent / 'gauguin-fault297-worktree-20261111/.deps-cache/'
                  'p0-20261105/source297'))

OLD_TOKEN = 'sweetwdtpet=0'
NEW_TOKEN = 'sweetfb_stats=1'
TRIAL = 'gwrt-0175-a1'
TRIAL_TOKEN = 'sweettrial=' + TRIAL
BOOT_LINE_LENGTH = 608
CMDLINE_OFFSET = 0x48


def load_command():
    """Load the recorded 0297 command and check its recorded byte count."""
    if not COMMAND_PATH.is_file():
        raise RuntimeError(
            f'requested 0297 command is unavailable: {COMMAND_PATH}; '
            'set PRESENT_0297_COMMAND to a real image-result JSON')
    result = json.loads(COMMAND_PATH.read_text())
    command = result['command']
    if result.get('command_bytes') != len(command.encode('utf-8')):
        raise ValueError('image-result command_bytes does not match the command')
    return command


def candidate(command):
    """Remove the one pet token and append the new statistics token."""
    tokens = command.split(' ')
    if tokens.count(OLD_TOKEN) != 1:
        raise ValueError(f'expected exactly one {OLD_TOKEN!r} token')
    if NEW_TOKEN in tokens:
        raise ValueError(f'command already contains {NEW_TOKEN!r}')
    return ' '.join([token for token in tokens if token != OLD_TOKEN] +
                    [NEW_TOKEN])


def remove_token(command, token):
    """Remove one exact whitespace-delimited token."""
    tokens = command.split(' ')
    if tokens.count(token) != 1:
        raise ValueError(f'expected exactly one {token!r} token')
    return ' '.join(t for t in tokens if t != token)


def token_map(command):
    """Map the candidate's tokens by name; duplicate names are not expected."""
    values = {}
    for token in command.split(' '):
        name, sep, value = token.partition('=')
        if not sep:
            continue  # boolean boot arguments such as -noprogress
        if name in values:
            raise ValueError(f'duplicate assignment token: {token!r}')
        values[name] = value
    return values


class BootCommandTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old = load_command()
        cls.new = candidate(cls.old)

    def test_exact_byte_token_and_order_difference(self):
        old_bytes = self.old.encode('ascii')
        new_bytes = self.new.encode('ascii')
        self.assertEqual(len(old_bytes), 603)
        self.assertEqual(len(new_bytes), 605)
        self.assertEqual(len(self.old), len(old_bytes))
        self.assertEqual(len(self.new), len(new_bytes))
        self.assertEqual(self.old.isascii(), True)
        self.assertEqual(self.new.isascii(), True)
        self.assertNotIn('\0', self.old + self.new)

        old_tokens = self.old.split(' ')
        new_tokens = self.new.split(' ')
        self.assertEqual(old_tokens.count(OLD_TOKEN), 1)
        self.assertEqual(new_tokens.count(NEW_TOKEN), 1)
        self.assertNotIn(OLD_TOKEN, new_tokens)
        self.assertNotIn(NEW_TOKEN, old_tokens)
        self.assertEqual(new_tokens,
                         [token for token in old_tokens
                          if token != OLD_TOKEN] + [NEW_TOKEN])
        self.assertEqual(Counter(old_tokens) - Counter(new_tokens),
                         Counter({OLD_TOKEN: 1}))
        self.assertEqual(Counter(new_tokens) - Counter(old_tokens),
                         Counter({NEW_TOKEN: 1}))

        index = old_tokens.index(OLD_TOKEN)
        self.assertLess(index, len(old_tokens) - 1)
        self.assertEqual(
            difflib.SequenceMatcher(None, old_tokens, new_tokens,
                                    autojunk=False).get_opcodes(),
            [('equal', 0, index, 0, index),
             ('delete', index, index + 1, index, index),
             ('equal', index + 1, len(old_tokens), index, len(new_tokens) - 1),
             ('insert', len(old_tokens), len(old_tokens),
              len(new_tokens) - 1, len(new_tokens))])

        removed = (' ' + OLD_TOKEN).encode('ascii')
        added = (' ' + NEW_TOKEN).encode('ascii')
        self.assertEqual(old_bytes.count(removed), 1)
        self.assertEqual(new_bytes, old_bytes.replace(removed, b'') + added)
        self.assertEqual(new_bytes[:-len(added)],
                         old_bytes.replace(removed, b''))

        old_values = token_map(self.old)
        new_values = token_map(self.new)
        self.assertEqual(old_values[OLD_TOKEN.partition('=')[0]], '0')
        self.assertNotIn('sweetwdtpet', new_values)
        self.assertEqual(new_values[NEW_TOKEN.partition('=')[0]], '1')
        for name, value in old_values.items():
            if name != 'sweetwdtpet':
                self.assertEqual(new_values[name], value, name)
        self.assertEqual(set(new_values),
                         (set(old_values) - {'sweetwdtpet'}) |
                         {'sweetfb_stats'})

    def test_encode_cmdline_and_608_byte_nul_field_roundtrip(self):
        self.assertEqual(mkpayload.BOOT_LINE_LENGTH, BOOT_LINE_LENGTH)
        self.assertEqual(mkpayload.CMDLINE, CMDLINE_OFFSET)
        old_encoded = mkpayload.encode_cmdline(self.old)
        new_encoded = mkpayload.encode_cmdline(self.new)
        self.assertEqual((len(old_encoded), len(new_encoded)), (603, 605))
        self.assertEqual(old_encoded, self.old.encode('ascii'))
        self.assertEqual(new_encoded, self.new.encode('ascii'))

        old_field = old_encoded + bytes(BOOT_LINE_LENGTH - len(old_encoded))
        new_field = new_encoded + bytes(BOOT_LINE_LENGTH - len(new_encoded))
        for field, encoded in ((old_field, old_encoded),
                               (new_field, new_encoded)):
            self.assertEqual(len(field), BOOT_LINE_LENGTH)
            self.assertEqual(field[:len(encoded)], encoded)
            self.assertEqual(field[len(encoded):],
                             bytes(BOOT_LINE_LENGTH - len(encoded)))
            self.assertEqual(field.split(b'\0', 1)[0], encoded)
            self.assertEqual(field.rstrip(b'\0'), encoded)
        self.assertEqual(len(new_field[len(new_encoded):]), 3)
        self.assertEqual(len(old_field[len(old_encoded):]), 5)

        payload = bytearray(b'\xa5' * (CMDLINE_OFFSET + BOOT_LINE_LENGTH + 32))
        payload[CMDLINE_OFFSET:CMDLINE_OFFSET + BOOT_LINE_LENGTH] = new_field
        self.assertEqual(
            bytes(payload[CMDLINE_OFFSET:CMDLINE_OFFSET + BOOT_LINE_LENGTH]),
            new_field)
        self.assertEqual(
            bytes(payload[CMDLINE_OFFSET:
                          CMDLINE_OFFSET + BOOT_LINE_LENGTH]).rstrip(b'\0'),
            new_encoded)

    def test_encode_cmdline_rejects_anything_beyond_the_field(self):
        # The candidate is 605 bytes, so two extra bytes fit and three do not.
        self.assertEqual(mkpayload.encode_cmdline(self.new + 'xx'),
                         (self.new + 'xx').encode('ascii'))
        self.assertEqual(len(self.new + 'xx'), 607)
        for over in (self.new + 'xxx', self.new + 'x' * 100,
                     self.old + 'x' * 5):
            with self.subTest(bytes=len(over.encode('ascii'))):
                self.assertGreaterEqual(len(over.encode('ascii')), 608)
                with self.assertRaisesRegex(
                        ValueError, 'boot command exceeds 607 UTF-8 bytes'):
                    mkpayload.encode_cmdline(over)
        with self.assertRaisesRegex(ValueError, 'embedded NUL'):
            mkpayload.encode_cmdline(self.new + '\0')

    def test_sweettrial_identity_survives_and_removal_is_rejected(self):
        self.assertTrue(extractor._valid_trial(TRIAL))
        self.assertEqual(self.old.split(' ').count(TRIAL_TOKEN), 1)
        self.assertEqual(self.new.split(' ').count(TRIAL_TOKEN), 1)
        self.assertEqual(token_map(self.old)['sweettrial'], TRIAL)
        self.assertEqual(token_map(self.new)['sweettrial'], TRIAL)

        def identity_log(command):
            return (b'<Notice>: boot-args = ' + command.encode('ascii') + b'\n'
                    b'[0] SWEET CMDB BEGIN: bytes=131072 sha256=' +
                    b'0' * 64 + b'\n'
                    b'[1] SWEET CMDB END: bytes=131072 sha256=' +
                    b'0' * 64 + b'\n')

        for command in (self.old, self.new):
            data = identity_log(command)
            self.assertEqual(extractor._complete_markers(data),
                             [TRIAL_TOKEN.encode('ascii')])
            extractor._check_identity(data, 1, 2, TRIAL)

        without_trial = identity_log(self.new).replace(
            TRIAL_TOKEN.encode('ascii'), b'')
        with self.assertRaises(extractor.Rejected):
            extractor._check_identity(without_trial, 1, 2, TRIAL)
        different_trial = identity_log(
            self.new.replace(TRIAL_TOKEN, 'sweettrial=other-trial'))
        with self.assertRaises(extractor.Rejected):
            extractor._check_identity(different_trial, 1, 2, TRIAL)
        duplicate_trial = identity_log(self.new) + (
            TRIAL_TOKEN.encode('ascii') + b'\n')
        with self.assertRaises(extractor.Rejected):
            extractor._check_identity(duplicate_trial, 1, 2, TRIAL)


def extract_function(source, name):
    """Extract one complete actual definition, including a split return type."""
    pattern = (r'(?m)^(?:static\s+)?(?:void|bool|BOOL)\s+'
               + re.escape(name) + r'\s*\([^)]*\)\s*\{')
    match = re.search(pattern, source)
    if match is None:
        pattern = (r'(?m)^(?:static\s+)?(?:void|bool|BOOL)\s*\n+'
                   + re.escape(name) + r'\([^)]*\)\s*\{')
        match = re.search(pattern, source)
    if match is None:
        raise ValueError(f'actual function definition missing: {name}')
    opening = source.index('{', match.start())
    depth = 0
    for index in range(opening, len(source)):
        if source[index] == '{':
            depth += 1
        elif source[index] == '}':
            depth -= 1
            if depth == 0:
                return source[match.start():index + 1] + '\n'
    raise ValueError(f'unterminated actual function: {name}')


# Every source file in 0297 that reads sweetwdtpet.  Dynamic discovery below
# rejects a new site rather than silently omitting it from the host harness.
PET_CONSUMERS = {
    'bsd/dev/gauguin_cx_power.c': ('gcx_flags',),
    'bsd/dev/gauguin_bcm_coordinator.c': ('bcm_flags',),
    'bsd/dev/gauguin_gmu_board.c': ('gpzb_flags',),
    'bsd/dev/gauguin_bcm_transport.c': ('gt_conflicts',),
    'bsd/dev/gauguin_pas_init.c': ('gpi_flags',),
    'bsd/dev/gauguin_wdt_test.c': ('wdt_conflict', 'wdt_bus_conflict'),
    'iokit/Kernel/arm/SweetWatchdog.cpp': ('sweet_wdt_thread_start',),
}

GATE_PARTS = {
    'bsd/dev/gauguin_wdt_test.c': (
        'sweet_wdt_test_requested', 'wdt_bus_requested',
        'sweet_wdt_exclusive_requested'),
}

HARNESS = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static const char *command;
static unsigned pet_queries, bus_queries, test_queries;
static char last_record[256];

/* Models PE_parse_boot_argn for the integer tokens used here: exact name,
 * '=' required, space/tab/NUL separators, and no write-back when absent. */
static bool pe_parse_int(const char *key, void *out, int size)
{
    assert(size == (int)sizeof(int));
    if (!strcmp(key, "sweetwdtpet")) ++pet_queries;
    if (!strcmp(key, "sweetbusvote")) ++bus_queries;
    if (!strcmp(key, "sweetwdttest")) ++test_queries;
    const char *p = command;
    while (*p) {
        while (*p == ' ' || *p == '\t') ++p;
        const char *end = p;
        while (*end && *end != ' ' && *end != '\t') ++end;
        const char *eq = memchr(p, '=', (size_t)(end - p));
        size_t name_len = eq ? (size_t)(eq - p) : (size_t)(end - p);
        if (name_len == strlen(key) && !memcmp(p, key, name_len) && eq) {
            char *stop = NULL;
            long value = strtol(eq + 1, &stop, 0);
            if (stop != eq + 1) {
                *(int *)out = (int)value;
                return true;
            }
        }
        p = end;
    }
    return false; /* absence must leave the caller's initialized zero */
}
#define PE_parse_boot_argn pe_parse_int

static void wdt_record(const char *line)
{
    snprintf(last_record, sizeof(last_record), "%s", line);
}

typedef void *thread_call_t;
typedef void (*thread_call_func_t)(void *, void *);
static void sweet_wdt_sample(void *a, void *b) { (void)a; (void)b; assert(0); }
static void sweet_wdt_pet_sample(void *a, void *b) { (void)a; (void)b; assert(0); }
static thread_call_t sweet_wdt_call, sweet_wdt_pet_call;
static unsigned sampler_allocs, pet_allocs, schedules, diag, delayed;
static thread_call_t thread_call_allocate(thread_call_func_t fn, void *arg)
{
    assert(arg == NULL);
    if (fn == sweet_wdt_sample) { ++sampler_allocs; return (thread_call_t)(uintptr_t)1; }
    assert(fn == sweet_wdt_pet_sample);
    ++pet_allocs;
    return (thread_call_t)(uintptr_t)2;
}
static void sweet_wdt_schedule(void) { ++schedules; }
static void sweet_secure_diag_start(void) { ++diag; }
static void clock_interval_to_deadline(unsigned n, uint64_t scale, uint64_t *out)
{
    assert(n == 1 && scale == UINT64_C(1000000000));
    *out = 42;
}
static void thread_call_enter_delayed(thread_call_t call, uint64_t deadline)
{
    assert(call == (thread_call_t)(uintptr_t)2 && deadline == 42);
    ++delayed;
}
static void IOLog(const char *format, ...) { (void)format; }
#define NSEC_PER_SEC UINT64_C(1000000000)
bool sweet_wdt_exclusive_requested(void);
@PARTS@
int main(int argc, char **argv)
{
    assert(argc == 2);
    command = argv[1];

    last_record[0] = 0;
    bool wdt = wdt_conflict();
    char wdt_reason[256];
    snprintf(wdt_reason, sizeof(wdt_reason), "%s", last_record);
    last_record[0] = 0;
    bool wdtbus = wdt_bus_conflict();
    char wdtbus_reason[256];
    snprintf(wdtbus_reason, sizeof(wdtbus_reason), "%s", last_record);

    bool gcx = gcx_flags();
    bool gt = gt_conflicts();
    bool bcm = bcm_flags();
    bool gpzb = gpzb_flags();
    bool gpi = gpi_flags();

    pet_queries = bus_queries = test_queries = 0;
    sweet_wdt_thread_start();

    printf("CONSUMERS gcx=%d gt=%d bcm=%d gpzb=%d wdt=%d wdtbus=%d gpi=%d\n",
           gcx, gt, bcm, gpzb, wdt, wdtbus, gpi);
    printf("WDT=%s\n", wdt_reason);
    printf("WDTBUS=%s\n", wdtbus_reason);
    printf("GATE sampler=%u pet=%u schedule=%u diag=%u delayed=%u "
           "pet_queries=%u bus_queries=%u test_queries=%u\n",
           sampler_allocs, pet_allocs, schedules, diag, delayed,
           pet_queries, bus_queries, test_queries);
    return 0;
}
'''


def parse_harness_output(text):
    """Return the consumer, gate, and reason records from the harness."""
    consumers = re.search(
        r'^CONSUMERS (\w+=\d+ \w+=\d+ \w+=\d+ \w+=\d+ \w+=\d+ \w+=\d+ '
        r'\w+=\d+)$', text, re.MULTILINE)
    gate = re.search(
        r'^GATE sampler=(\d+) pet=(\d+) schedule=(\d+) diag=(\d+) '
        r'delayed=(\d+) pet_queries=(\d+) bus_queries=(\d+) '
        r'test_queries=(\d+)$', text, re.MULTILINE)
    wdt = re.search(r'^WDT=(.*)$', text, re.MULTILINE)
    wdtbus = re.search(r'^WDTBUS=(.*)$', text, re.MULTILINE)
    if consumers is None or gate is None or wdt is None or wdtbus is None:
        raise AssertionError(f'harness output is incomplete:\n{text}')
    result = dict(part.split('=') for part in consumers.group(1).split(' '))
    return ({key: int(value) for key, value in result.items()},
            tuple(int(value) for value in gate.groups()),
            wdt.group(1), wdtbus.group(1))


class WatchdogSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not SOURCE_PATH.is_dir():
            raise RuntimeError(
                f'requested 0297 source is unavailable: {SOURCE_PATH}; '
                'set XNU_SOURCE to the complete GAUGUIN source tree')

        found = sorted(
            str(path.relative_to(SOURCE_PATH))
            for path in SOURCE_PATH.rglob('*')
            if path.suffix in ('.c', '.cpp', '.h', '.hpp') and
            'sweetwdtpet' in path.read_text(errors='replace'))
        cls.found = found
        if set(found) != set(PET_CONSUMERS):
            raise AssertionError(
                'sweetwdtpet consumer set changed: found '
                f'{found!r}, expected {sorted(PET_CONSUMERS)!r}')

        cls.parts = []
        cls.bodies = {}
        for relative, names in PET_CONSUMERS.items():
            text = (SOURCE_PATH / relative).read_text()
            for name in names:
                body = extract_function(text, name)
                cls.parts.append(body)
                cls.bodies[name] = body
        for relative, names in GATE_PARTS.items():
            text = (SOURCE_PATH / relative).read_text()
            for name in names:
                body = extract_function(text, name)
                cls.parts.append(body)
                cls.bodies[name] = body

        total_sites = sum(
            (SOURCE_PATH / relative).read_text().count('sweetwdtpet')
            for relative in PET_CONSUMERS)
        extracted_sites = sum(body.count('sweetwdtpet')
                              for body in cls.bodies.values())
        if total_sites != extracted_sites:
            raise AssertionError(
                'an extracted consumer is missing: source has '
                f'{total_sites} sweetwdtpet sites, harness has {extracted_sites}')

        cls._temporary = tempfile.TemporaryDirectory(
            prefix='present-boot-args-')
        cls.build = Path(cls._temporary.name)
        cls.exe = cls.build / 'readers'
        cls.source = cls.build / 'readers.c'
        cls.source.write_text(HARNESS.replace('@PARTS@', '\n'.join(cls.parts)))
        cls.compile = subprocess.run(
            ['clang', '-DGAUGUIN=1', '-std=c11', '-O1', '-g',
             '-Wall', '-Wextra', '-Werror', '-Wno-unused-function',
             '-pedantic', str(cls.source), '-o', str(cls.exe)],
            capture_output=True, text=True)
        if cls.compile.returncode:
            raise AssertionError(
                'watchdog harness did not compile:\n' + cls.compile.stderr)

    @classmethod
    def tearDownClass(cls):
        cls._temporary.cleanup()

    def run_command(self, command):
        result = subprocess.run([str(self.exe), command],
                                capture_output=True, text=True)
        if result.returncode:
            raise AssertionError(
                f'watchdog harness failed for {command!r}:\n{result.stderr}')
        return parse_harness_output(result.stdout)

    def test_all_source_pet_consumers_and_gate_compare_zero_with_absent(self):
        old = load_command()
        new = candidate(old)
        old_decisions, old_gate, old_wdt, old_wdtbus = self.run_command(old)
        new_decisions, new_gate, new_wdt, new_wdtbus = self.run_command(new)
        absent_only = remove_token(old, OLD_TOKEN)
        (absent_decisions, absent_gate, absent_wdt,
         absent_wdtbus) = self.run_command(absent_only)

        # Isolate the pet deletion first, then confirm the candidate's added
        # statistics token changes none of these watchdog readers.
        self.assertEqual(old_decisions, absent_decisions)
        self.assertEqual(old_wdt, absent_wdt)
        self.assertEqual(old_wdtbus, absent_wdtbus)
        self.assertEqual(old_gate, absent_gate)
        self.assertEqual(old_decisions, new_decisions)
        self.assertEqual(old_wdt, new_wdt)
        self.assertEqual(old_wdtbus, new_wdtbus)
        self.assertEqual(old_gate, new_gate)

        # Independent source expectation for the exact command: the bus-vote
        # gate is true, so the gate returns before reading sweetwdtpet; all
        # conflict readers see the same other flags, and wdt_conflict's first
        # nonzero flag is sweetpasprobe=1.
        self.assertEqual(old_decisions, {
            'gcx': 1, 'gt': 0, 'bcm': 1, 'gpzb': 1,
            'wdt': 1, 'wdtbus': 0, 'gpi': 1})
        self.assertEqual(old_gate, (0, 0, 0, 1, 0, 0, 1, 1))
        self.assertIn('conflict sweetpasprobe=1', old_wdt)
        self.assertEqual(old_wdtbus, '')

        # Control: value 1 is rejected by every consumer that reads the token.
        pet_one = old.replace(OLD_TOKEN, 'sweetwdtpet=1')
        pet_decisions, _, pet_wdt, pet_wdtbus = self.run_command(pet_one)
        self.assertEqual(pet_decisions, {
            'gcx': 0, 'gt': 1, 'bcm': 0, 'gpzb': 0,
            'wdt': 1, 'wdtbus': 1, 'gpi': 0})
        self.assertIn('conflict sweetwdtpet=1', pet_wdt)
        self.assertIn('conflict sweetwdtpet=1', pet_wdtbus)
        for name in ('gcx', 'gt', 'bcm', 'gpzb', 'gpi', 'wdtbus'):
            self.assertNotEqual(pet_decisions[name], old_decisions[name], name)
        self.assertNotEqual(pet_wdt, old_wdt)

        # Remove the bus-vote early return so the gate actually reads the PET
        # token.  Explicit zero and absent must produce identical counters.
        no_bus_old = remove_token(old, 'sweetbusvote=1')
        no_bus_new = remove_token(new, 'sweetbusvote=1')
        _, zero_gate, _, _ = self.run_command(no_bus_old)
        _, absent_gate, _, _ = self.run_command(no_bus_new)
        self.assertEqual(zero_gate, absent_gate)
        self.assertEqual(zero_gate, (1, 0, 1, 1, 0, 1, 1, 1))

        pet_one_no_bus = no_bus_old.replace(OLD_TOKEN, 'sweetwdtpet=1')
        _, pet_gate, _, _ = self.run_command(pet_one_no_bus)
        self.assertEqual(pet_gate, (1, 1, 1, 1, 1, 1, 1, 1))

    def test_gate_source_orders_exclusive_return_before_pet_read(self):
        gate = self.bodies['sweet_wdt_thread_start']
        self.assertEqual(gate.count('sweetwdtpet'), 1)
        self.assertLess(gate.index('sweet_wdt_exclusive_requested()'),
                        gate.index('PE_parse_boot_argn("sweetwdtpet"'))
        self.assertLess(gate.index('int pet = 0;'),
                        gate.index('PE_parse_boot_argn("sweetwdtpet"'))
        exclusive = self.bodies['sweet_wdt_exclusive_requested']
        self.assertIn('sweet_wdt_test_requested()', exclusive)
        self.assertIn('wdt_bus_requested()', exclusive)
        self.assertIn('||', exclusive)
        self.assertIn('int test = 0;', self.bodies['sweet_wdt_test_requested'])
        self.assertIn('== 1', self.bodies['sweet_wdt_test_requested'])
        self.assertIn('int bus = 0;', self.bodies['wdt_bus_requested'])
        self.assertIn('== 1', self.bodies['wdt_bus_requested'])
        for name in ('gcx_flags', 'gt_conflicts', 'bcm_flags', 'gpzb_flags',
                     'wdt_conflict', 'wdt_bus_conflict', 'gpi_flags'):
            self.assertIn('sweetwdtpet', self.bodies[name], name)


if __name__ == '__main__':
    unittest.main()
