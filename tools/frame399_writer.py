"""Read bounded frontend receipts keyed by the retained command-buffer identity."""

import re

from frame344_log import require

PREFIX = 'GAUGUIN WRITER399: '
ROW = re.compile(r'object=(0x[0-9a-f]+) made=(\d+) tick=(\d+) tid=(\d+) surface=(\d+) layout=([0-3])')
MAX_ROWS = 2048


def decode(text):
    receipts,limit = {},False
    for line in text.splitlines():
        if not line.startswith(PREFIX):
            continue
        data = line[len(PREFIX):]
        if data == 'limit=2048':
            require(not limit and len(receipts) == MAX_ROWS,'unexpected writer receipt limit')
            limit = True
            continue
        match = ROW.fullmatch(data)
        require(not limit and len(receipts) < MAX_ROWS and len(line) < 160 and match,'invalid writer receipt')
        obj = match[1]
        made,tick,tid,surface,layout = map(int,match.groups()[1:])
        key = (obj,made,surface)
        require(key not in receipts and 220_000_000 <= made < 270_000_000 and int(obj,16) and
                tick and tid and 0 < surface <= 0xffffffff,'ambiguous or out-of-scope writer receipt')
        receipts[key] = dict(tick=tick,tid=tid,layout=layout)
    return receipts,limit
