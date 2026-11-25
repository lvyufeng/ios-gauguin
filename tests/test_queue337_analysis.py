#!/usr/bin/env python3
"""Loss and lifetime/FIFO oracles for the independent queue metadata."""
import importlib.util
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('q337',ROOT/'tools/analyze-queue337.py')
q=importlib.util.module_from_spec(spec);spec.loader.exec_module(q)

def buffer(obj,made,base,queue,ticket,retired):
    t=[base,base+10,base+20,base+30,base+50,base+60,base+61,base+70]
    rows=[f'GAUGUIN C4Q321: phase={i} object={obj} start_us={made} end_us={z} value={3 if i==4 else 0}'for i,z in enumerate(t)]
    rows.append(f'tl: M made {made} committed {base} done {base+65} gpu 20')
    for i,(tick,n)in enumerate([(base+5,retired),(base+15,ticket-1),(base+55,ticket)]):
        rows.append(f'GAUGUIN Q337: stage={i} object={obj} made_us={made} queue={queue} ticket={ticket} retired={n} tick_us={tick}')
    return rows

class Queue337(unittest.TestCase):
    def setUp(self):
        self.rows=buffer('0x100',220000001,220000100,1,1,0)+buffer('0x100',220000200,220000300,1,2,1)+buffer('0x200',220000201,220000300,2,1,0)
    def parse(self,rows=None):return q.analyze('\n'.join(self.rows if rows is None else rows))
    def test_complete_pointer_reuse_two_queues(self):
        r=self.parse();self.assertTrue(r['coverage_qualified']);self.assertEqual(len(r['queues']),2)
        self.assertEqual(r['metrics']['body_us']['median'],40)
    def test_missing_record_and_entire_metadata(self):
        for skip in [[9],[9,10,11]]:
            self.assertFalse(self.parse([r for i,r in enumerate(self.rows)if i not in skip])['coverage_qualified'])
    def test_duplicate_ticket_wrong_retire_and_time(self):
        variants=[self.rows+[self.rows[9]],
                  [r.replace('ticket=2','ticket=1')for r in self.rows],
                  [r.replace('ticket=2 retired=1','ticket=2 retired=2')for r in self.rows],
                  [r.replace('tick_us=220000355','tick_us=220000315')for r in self.rows],
                  self.rows+['GAUGUIN Q337: limit=32768 coverage=incomplete'],
                  self.rows+['GAUGUIN Q337: broken']]
        for rows in variants:self.assertFalse(self.parse(rows)['coverage_qualified'])
    def test_raw_interleaving_is_allowed(self):
        self.assertTrue(self.parse(list(reversed(self.rows)))['coverage_qualified'])
    def test_empty_is_unqualified(self):self.assertFalse(self.parse([])['coverage_qualified'])

if __name__=='__main__':unittest.main()
