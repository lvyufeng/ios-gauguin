import unittest

from tools.fault_profile_log import parse_fault_profile


def row(group, calls=2, ns=7):
    return f'SWEET GPU FAULT PERF: group={group} calls={calls} ns={ns}; all callers, CPU wall'


class FaultProfileTest(unittest.TestCase):
    def test_complete_unordered_with_optional_zero(self):
        text = '\n'.join([row(5, 0, 0), row(2), row(1, 0, 0), row(3), row(0), row(4)])
        result = parse_fault_profile(text)
        self.assertEqual([x['name'] for x in result['groups']],
                         ['global', 'settle', 'bank0', 'bank1', 'host', 'ao'])
        self.assertFalse(result['runtime_only_qualified'])
        self.assertFalse(result['hardware_performance_qualified'])

    def test_bad_rows_never_promoted(self):
        valid = [row(i) for i in range(6)]
        cases = [valid[:-1], valid + [valid[0]], valid + [row(6)],
                 [row(0, 0, 1)] + valid[1:], [row(0, 1 << 64, 1)] + valid[1:],
                 ['prefix ' + valid[0]] + valid[1:],
                 [valid[0].replace(' ns=', ' corrupted ns=')] + valid[1:]]
        for case in cases:
            with self.subTest(case=case), self.assertRaises(ValueError):
                parse_fault_profile('\n'.join(case))


if __name__ == '__main__':
    unittest.main()
