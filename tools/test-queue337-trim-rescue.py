#!/usr/bin/env python3
"""Fault injection against exact real preimages; memory writes only."""
import importlib.util
import json
from pathlib import Path


SPEC=importlib.util.spec_from_file_location('rescue337',Path(__file__).with_name('restore-queue337-trim.py'))
M=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(M)


class MemoryIO:
    model_only=True

    def __init__(self,plan,images,fail=None,rollback_fail=False):
        self.raw={row['block']*4096:bytearray(images[row['name']][0]) for row in plan['ranges']}
        self.before={key:bytes(value) for key,value in self.raw.items()}
        self.writes=0;self.fail=fail;self.rollback_fail=rollback_fail
        self.failed=False;self.rollback_failed=False;self.bytes=0

    def read(self,offset,n):
        return bytes(self.raw[offset][:n])

    def write(self,offset,data):
        self.writes+=1;self.bytes+=len(data)
        if self.writes==self.fail:
            self.raw[offset][:len(data)//2]=data[:len(data)//2]
            self.failed=True
            raise OSError('injected partial forward write')
        if self.failed and self.rollback_fail and not self.rollback_failed:
            self.raw[offset][0]^=1;self.rollback_failed=True
            raise OSError('injected partial rollback failure')
        self.raw[offset][:]=data

    def sync(self):pass

    def unchanged(self):
        return {key:bytes(value) for key,value in self.raw.items()}==self.before


def main():
    folder=M.BASE/'trim-rescue';raw,plan,images=M.read_plan(folder)
    successes=[]

    def verify(io):
        for row in plan['ranges']:
            assert io.read(row['block']*4096,row['bytes'])==images[row['name']][1]

    io=MemoryIO(plan,images)
    result=M.apply_ranges(plan,images,io,lambda _:None,lambda:verify(io))
    assert result['state']=='0337-six-files-and-original-C4-allocation-restored'
    assert io.bytes==M.WRITE_BYTES and io.writes==14;successes.append('success-exact-targets')
    for fail in range(1,15):
        io=MemoryIO(plan,images,fail)
        result=M.apply_ranges(plan,images,io,lambda _:None,lambda:verify(io))
        assert result['state']=='rescue-failed-preimages-restored' and io.unchanged(),fail
        assert io.bytes==result['forward_bytes']+result['rollback_bytes']<=M.WRITE_BYTES*2
        successes.append('partial-write-'+str(fail))
    io=MemoryIO(plan,images)
    def failed_verify():raise OSError('injected final validation failure')
    result=M.apply_ranges(plan,images,io,lambda _:None,failed_verify)
    assert result['state']=='rescue-failed-preimages-restored' and io.unchanged()
    assert io.bytes==M.WRITE_BYTES*2;successes.append('final-verification-failure')
    io=MemoryIO(plan,images)
    def failed_report(value):
        if value['state']=='0337-six-files-and-original-C4-allocation-restored':
            raise OSError('injected success receipt failure')
    result=M.apply_ranges(plan,images,io,failed_report,lambda:verify(io))
    assert result['state']=='rescue-failed-preimages-restored' and io.unchanged()
    successes.append('success-receipt-failure')
    io=MemoryIO(plan,images,5,True)
    result=M.apply_ranges(plan,images,io,lambda _:None,lambda:verify(io))
    assert result['state']=='rescue-failed-rollback-incomplete' and not io.unchanged()
    journal=next(row for row in plan['ranges'] if row['kind']=='journal')
    assert io.read(journal['block']*4096,journal['bytes'])==images[journal['name']][1]
    assert any('kept empty' in row['error'] for row in result['rollback_failures'])
    assert not result['reboot_permitted'] and io.bytes<=M.WRITE_BYTES*2
    successes.append('rollback-failure-keeps-journal-empty')
    # A changed first range is detected before a mutation and before rollback.
    io=MemoryIO(plan,images);io.raw[journal['block']*4096][0]^=1
    result=M.apply_ranges(plan,images,io,lambda _:None,lambda:verify(io))
    assert result['state']=='rescue-failed-preimages-restored' and io.writes==0
    successes.append('changed-preimage-zero-writes')
    question=['request_user_input_async','model-question-not-real',0]
    fixture=dict(approved=True,plan_sha256=M.sha(raw),review_sha256='model-review',
                 source='actual-user-q337-trim-rescue-reply',provenance='async-question-reply',
                 question_item_id=question,exact_answer='MODEL ONLY NEVER AUTHORIZATION',
                 answer_sha256=M.sha(b'MODEL ONLY NEVER AUTHORIZATION'),fixture_only=True,
                 **{flag:True for flag in M.FLAGS})
    cases=[{},fixture,dict(fixture,fixture_only=False,source='actual-user-q337-trial-reply')]
    for key in ('plan_sha256','review_sha256','question_item_id','answer_sha256',*M.FLAGS):
        bad=dict(fixture,fixture_only=False);bad[key]=False;cases.append(bad)
    for bad in cases:
        try:M.approval_gate(bad,M.sha(raw),'model-review')
        except M.Refused:pass
        else:raise AssertionError('accepted missing/fixture/old/mutated approval')
    successes.append('approval-rejection-'+str(len(cases)))
    j=(M.BASE/'execution/allocation-inspection/journal-full.bin').read_bytes()
    info=(M.BASE/'execution/allocation-inspection/journal-info-block.bin').read_bytes()
    mutations=[]
    for offset in (0,8,36,4910592+8,4910592+94208):
        bad=bytearray(j);bad[offset]^=1;mutations.append((bytes(bad),info))
    bad=bytearray(info);bad[3]^=2;mutations.append((j,bytes(bad)))
    for bad,ib in mutations:
        try:M.journal(bad,ib)
        except M.Refused:pass
        else:raise AssertionError('accepted journal mutation')
    successes.append('journal-rejection-'+str(len(mutations)))
    result=dict(state='model-0337-trim-rescue-passed',plan_sha256=M.sha(raw),
                successful=True,checks=successes,all_14_partial_write_failures_restored=True,
                rollback_failure_reported=True,rollback_failure_keeps_empty_journal=True,
                maximum_forward_and_rollback_bytes=M.WRITE_BYTES*2,
                fixture_writes_only=True,device_writes=0,device_boots=0,
                source_sha256=M.sha(Path(__file__).read_bytes()))
    M.save(folder/'model-result.json',result)
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
