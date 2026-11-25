"""Decode the 32-second refresh marker from paired 0419 display CRCs."""

from bisect import bisect_right
from collections import Counter
from importlib import import_module
from itertools import pairwise
from math import isfinite
import re

import frame344_log as frame
import frame419_log as timeline


observer = import_module('run-frame417-trial')
SECOND = observer.SECOND
WORDS = (0, *(1 << bit for bit in range(12)), 0x735, 0xaca, 0)


def gray_to_frame(gray):
    number = 0
    while gray:
        number ^= gray
        gray >>= 1
    return number


def marker_log(text, *, calibrate_ids=True):
    def rows(pattern):
        return re.findall(r'^GAUGUIN MARKER: ' + pattern + '$', text, re.M)

    window, width, height, key = map(int, frame.one(
        r'^GAUGUIN MARKER: window=(\d+) width=(\d+) height=(\d+) key=([01])$',
        text, 'visible probe window'))
    begin, start, end, numer, denom, maximum, rate = map(int, frame.one(
        r'^GAUGUIN MARKER: begin=(\d+) start=(\d+) end=(\d+) numer=(\d+) denom=(\d+) max=(\d+) rate=(\d+)$',
        text, 'probe sampling span'))
    captured, stopped = map(int, frame.one(
        r'^GAUGUIN MARKER: status=complete count=(\d+) stop=(\d+)$', text, 'complete probe summary'))
    removed = int(frame.one(r'^GAUGUIN MARKER: removed=(\d+)$', text, 'probe cleanup'))
    calibration = [tuple(map(int, row)) for row in rows(r'cal=(\d+) gray=(\d+) tick=(\d+)')]
    callbacks = [(int(number), int(tick), float(target))
                 for number,tick,target in rows(r'id=(\d+) tick=(\d+) target=(\S+)')]
    frame.require(0 < width < height and not key and (numer,denom) == (625,12) and rate == 60
                  and 0 < maximum <= 120 and start - begin == SECOND and end - start == 32 * SECOND
                  and 229 * SECOND <= window < begin < start < end <= stopped < removed
                  and 234 * SECOND - SECOND // 10 <= begin < 235 * SECOND,
                  'unexpected probe window, timebase, requested rate or sample length')
    if calibrate_ids:
        frame.require([(i,word) for i,word,_ in calibration] == list(enumerate(WORDS))
                      and window < calibration[0][2] < calibration[-1][2] < begin
                      and all(SECOND // 10 < right[2]-left[2] < SECOND // 3
                              for left,right in pairwise(calibration)),
                      'held calibration records are incomplete or mistimed')
    frame.require(1 < len(callbacks) == captured < 4096
                  and all(0 < number < 4096 and start <= tick < end and isfinite(target)
                          for number,tick,target in callbacks)
                  and all(right[0] == left[0]+1 and right[1] > left[1]
                          for left,right in pairwise(callbacks)),
                  'display-link samples are incomplete, reordered or out of window')
    return dict(window=window, begin=begin, start=start, end=end, maximum=maximum,
                removed=removed, calibration=calibration, callbacks=callbacks)


def calibration_map(words):
    """The full-frame CRC is affine under Gray-cell swaps against a fixed scene."""
    frame.require(len(words) == len(WORDS) and words[0] == words[-1],
                  'CRC did not return to its calibration preimage')
    base = words[0]
    deltas = [base ^ value for value in words[1:13]]
    signatures = [base]
    for delta in deltas:
        signatures += [value ^ delta for value in signatures]
    frame.require(len(set(signatures)) == 4096, 'Gray-code CRC calibration aliases')
    frame.require(all(signatures[gray] == value for gray,value in zip(WORDS[13:15],words[13:15],strict=True)),
                  'two held Gray combinations did not verify the CRC mapping')
    return {value:gray_to_frame(gray) for gray,value in enumerate(signatures)}


def calibrate(probe, edges, valid):
    words = []
    stop_ticks = [tick for _,_,tick in probe['calibration'][1:]] + [probe['begin']]
    for (_,_,start), stop in zip(probe['calibration'], stop_ticks, strict=True):
        settled = [edge for edge in edges
                   if start + 3 * SECOND // 40 <= edge.a and edge.b < stop - SECOND // 100]
        # Use the final three complete scans in each deliberately held symbol.
        crc = [valid.get(edge.id) for edge in settled[-3:]]
        frame.require(len(crc) == 3 and crc[0] is not None and crc[0] == crc[1] == crc[2],
                      f'no three identical qualified scans for calibration slot {len(words)}')
        words.append(crc[0])
    return calibration_map(words), words


def measure(raw, userspace, plan):
    probe = marker_log(userspace)
    begin, end = probe['start'] + SECOND, probe['end'] - SECOND
    score = observer.measure(raw, plan, score_begin=begin)
    _, edges, _, valid = observer.display_evidence(raw, plan)
    decoder, held_crcs = calibrate(probe, edges, valid)
    callbacks = probe['callbacks']
    by_id = {number:(tick,target) for number,tick,target in callbacks}
    ticks = [tick for _,tick,_ in callbacks]
    around_score = [(left,right) for left,right in pairwise(edges)
                    if right.a < end and right.b >= begin]
    visible_ids = set()
    observations = []
    repeat_supply = Counter()
    repeats = set(score['repeated_scan_ids'])
    for left,right in around_score:
        prior, current = (decoder.get(valid.get(edge.id)) for edge in (left,right))
        frame.require(prior in by_id and current in by_id and prior <= current
                      and by_id[current][0] <= right.b
                      and by_id[prior][0] <= left.b,
                      'visible marker does not match the producer frame sequence')
        visible_ids.update((prior,current))
        observations.append((right.id,right.a,right.b,current))
        if right.id in repeats:
            if bisect_right(ticks, right.a) > current - callbacks[0][0] + 1:
                repeat_supply['newer callback had already run by the early scan edge'] += 1
            else:
                repeat_supply['no newer callback before the early scan edge'] += 1
    frame.require(observations and score['completely_measured_seconds'] == 30,
                  'one or more scored seconds lack paired display evidence')

    first, last = min(visible_ids), max(visible_ids)
    counts = [sum(begin + i*SECOND <= tick < begin + (i+1)*SECOND for tick in ticks)
              for i in range(30)]
    frame.require(score['score_seconds'] == len(counts) and sum(repeat_supply.values()) == len(repeats),
                  'marker and full-frame CRC repeat ledgers differ')
    return dict(scanout=score, new_images=timeline.whole_interval(raw,score,plan),
                calibration_words=list(WORDS), calibration_crc=held_crcs, all_score_scans_decode=True,
                sampled_seconds=32, score_ticks=[begin,end], screen_maximum=probe['maximum'],
                display_link_callbacks=len(callbacks), display_link_per_score_second=counts,
                display_link_mean_score_hz=sum(counts)/len(counts),
                visible_id_range=[first,last], confirmed_unseen_ids=sorted(set(range(first,last+1))-visible_ids),
                repeat_supply=dict(repeat_supply), observed_scans=observations,
                deadlines=timeline.measure(raw,score,plan))
