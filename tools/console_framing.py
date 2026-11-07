"""Losslessly frame complete SWEET diagnostics interrupted into IOKit XML."""
import hashlib
import re
import xml.etree.ElementTree as et


class FramingError(ValueError):
    pass


def _need(value, message):
    if not value:
        raise FramingError(message)


def recover_records(raw):
    """Return virtual lines and hashes of each detached raw-line substring.

    Only a known diagnostic following an interrupted, otherwise valid IOKit
    IOServiceFirstMatch XML key is detached. Event fields are never repaired;
    callers still validate their full schema, uniqueness, order and failures.
    Ambiguous markers, invalid XML, arbitrary prefixes and unterminated inline
    events cannot supply a recovered record. The caller retains the raw bytes.
    """
    marker = re.compile(r'SWEET (?:BCM |BUS:|PAS |WDT |CX |GMU |GPU )')
    header = re.compile(r'IOK [A-Za-z0-9_.-]{1,64}: IOServiceFirstMatch ')
    chunks = raw.decode('utf-8', 'replace').split('\n')
    lines, recoveries = [], []
    for index, original in enumerate(chunks):
        line = original.removesuffix('\r')
        hits = list(marker.finditer(line)) if line.startswith('IOK ') else []
        if not hits:
            lines.append(line)
            continue
        _need(len(hits) == 1, 'ambiguous multiple inline diagnostic markers')
        cut = hits[0].start()
        prefix, event = line[:cut], line[cut:]
        match = header.match(prefix)
        _need(match is not None and index < len(chunks) - 1,
              'unrecognized or unterminated inline diagnostic framing')
        _need(prefix.isascii() and '\r' not in prefix and len(prefix) <= 16384,
              'invalid/oversize inline IOKit prefix')
        xml = prefix[match.end():]
        _need(re.match(r'<dict(?:\s|>)', xml) and re.search(r'<key>[^<>]*$', xml),
              'inline diagnostic is not at an interrupted XML key')
        try:
            parser = et.XMLPullParser(events=('start', 'end'))
            parser.feed(xml)
            stack = []
            for kind, element in parser.read_events():
                if kind == 'start':
                    stack.append(element.tag)
                else:
                    _need(stack and stack[-1] == element.tag,
                          'inconsistent inline XML nesting')
                    stack.pop()
            _need(stack and stack[0] == 'dict' and stack[-1] == 'key' and
                  all(tag in ('dict', 'array') for tag in stack[:-1]),
                  'inline event lies inside an XML value')
            # Closing just the open key/container tags rejects incomplete
            # entities/attributes as well as malformed or additional roots.
            parser.feed(''.join('</' + tag + '>' for tag in reversed(stack)))
            parser.close()
        except et.ParseError as error:
            raise FramingError('malformed inline IOKit XML prefix: ' + str(error)) from error
        lines.extend((prefix, event))
        recoveries.append({
            'raw_line': index + 1,
            'ascii_event_column': cut + 1,
            'prefix_sha256': hashlib.sha256(prefix.encode('ascii')).hexdigest(),
            'event_sha256': hashlib.sha256(event.encode('utf-8')).hexdigest(),
        })
    return lines, recoveries
