#!/usr/bin/env python3
"""Score annotated video-frame brackets for a warm Spotlight typing test.

Input JSON contains frame_pts_ns and warm_taps. Each tap has contact_frame,
expected, observed, and optional feedback_frame and character_frame marks.
The marks are zero-based first-visible frame indices. Use known test keys.
An optional opening object has gesture_frame and keyboard_frame.
"""

import argparse
import json
from math import ceil
from pathlib import Path
from statistics import median


def latency(pts, contact, response, next_contact=None):
    if (type(contact) is not int or type(response) is not int
            or not 0 < contact <= response < len(pts)
            or (next_contact is not None and response >= next_contact)):
        raise ValueError('each visible marker must follow contact and precede the next tap')
    lower = max(0, pts[response - 1] - pts[contact])
    upper = pts[response] - pts[contact - 1]
    return lower, upper


def summarize(brackets):
    if not brackets:
        return {'samples': 0}
    lows, highs = (sorted(values) for values in zip(*brackets))
    rank = ceil(.95 * len(brackets)) - 1
    return {
        'samples': len(brackets),
        'p50_ms': [median(values) / 1_000_000 for values in (lows, highs)],
        'p95_ms': [values[rank] / 1_000_000 for values in (lows, highs)],
    }


def measure(data):
    pts = data['frame_pts_ns']
    taps = data['warm_taps']
    if (len(pts) < 3 or any(type(tick) is not int for tick in pts)
            or any(left >= right for left, right in zip(pts, pts[1:]))):
        raise ValueError('video presentation timestamps must be increasing integer nanoseconds')
    contacts = [tap['contact_frame'] for tap in taps]
    if any(type(index) is not int or not 0 < index < len(pts) for index in contacts) or (
            any(left >= right for left, right in zip(contacts, contacts[1:]))):
        raise ValueError('warm taps must be strictly ordered video-frame marks')

    feedback, characters = [], []
    wrong_characters = 0
    for i, tap in enumerate(taps):
        contact = contacts[i]
        next_contact = contacts[i + 1] if i + 1 < len(contacts) else None
        expected, observed = tap['expected'], tap['observed']
        first_feedback, first_character = tap.get('feedback_frame'), tap.get('character_frame')
        if not isinstance(expected, str) or not expected or (
                observed is not None and not isinstance(observed, str)):
            raise ValueError('mark each tap with its fixed test key and visible character')
        if (observed is None) != (first_character is None):
            raise ValueError('observed character and its visible marker must be recorded together')
        if first_feedback is not None:
            feedback.append(latency(pts, contact, first_feedback, next_contact))
        if first_character is not None:
            bounds = latency(pts, contact, first_character, next_contact)
            if observed == expected:
                characters.append(bounds)
            else:
                wrong_characters += 1

    opening = data.get('opening')
    opening_ms = None
    if opening is not None:
        opening_ms = [value / 1_000_000 for value in latency(
            pts, opening['gesture_frame'], opening['keyboard_frame'], contacts[0] if contacts else None)]
    return {
        'opening_to_keyboard_ms': opening_ms,
        'warm_taps': len(taps),
        'missing_visible_feedback': len(taps) - len(feedback),
        'wrong_characters': wrong_characters,
        'unobserved_characters': len(taps) - len(characters) - wrong_characters,
        'contact_to_key_feedback': summarize(feedback),
        'contact_to_correct_character': summarize(characters),
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('annotation', type=Path)
    args = parser.parse_args()
    print(json.dumps(measure(json.loads(args.annotation.read_text())), indent=2))
