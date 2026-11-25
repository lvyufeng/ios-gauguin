#!/usr/bin/env python3
"""Recheck 0343 IO and queue timings independently of one failed wait partition."""

import hashlib
import importlib.util
import json
from pathlib import Path
import re

import core338_log as c338
import core339_log as c339
import core340_log as c340
import core341_log as c341
import core342_log as c342
import kernel342_log as kernel
from core343_scope import BASE, IMAGE, REFERENCE, REFERENCE_RESULT, WORK, load, require, sha

EXEC = BASE / 'execution'
RESULT = '018d75f33e0f961a0203393cd0ed28989e851e14cf6ae3036f36181bdc3f248d'
PROOF = '6a47535e64cca1492ec2f2c2f6e698896aa08705fcdf89bb25b06d100fe87f1c'
READY = '056c49bf51606abe1670ad41ddbd46d7d8a79644f637e5320082094444d797b4'
CORE_ERRORS = {'invalid_category_or_submit_partition': 1, 'extended_record_count': 1}
COLLECTION_ERRORS = {'core342-wait-execution-coverage', 'kernel-IO-identity-join-incomplete',
                     'core342-independent-record-count'}
RAW_PINS = {
    'kernel.log': '8dc7455b5b05563381c4f836e267ecd78a2a1a3aacfad619afd182081c82bd19',
    'kernel.log.bin': '79dea044a349b4d1c3d5275b3ce44bfc08e2ea596746535c9457b040fa0e4da1',
    'backboardd.log.current': '62317008ce07ad774c0ef9103e1b0534b56ccd82cad5feba599898c3a9be3539',
    'collection-analysis.json': '5cdd9504a7cab29ac1a74f812d93c6fcbda518399e68f60ca17f694e16ef05f8',
}
TARGET = (1, 798, 105881)
PROJECTION = 'IO-and-queue-timing-only'


def tool(leaf):
    spec = importlib.util.spec_from_file_location(leaf, WORK/'tools'/(leaf+'.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def save(out, name, value):
    data = (json.dumps(value, indent=2) + '\n').encode()
    require(len(data) <= 8_000_000, 'bounded projection artifact exceeded')
    with (out/name).open('xb') as stream:
        stream.write(data)


def key(row):
    return row['queue'], row['ticket'], row['job']


def validate_rejected_row(raw_line, base):
    """Check every timing field used by the independent projection."""
    n341 = c342.normalize(raw_line).strip()
    n340 = c341.normalize(n341).strip()
    n339 = c340.normalize(n340).strip()
    head, sep, tail = n339.partition(' counts=')
    identity = c338.CR.fullmatch(head.replace(c339.PREFIX, c338.CR_PREFIX))
    parsed = c339.EXTRA.fullmatch(sep+tail)
    require(identity is not None and parsed is not None
            and (identity[1], int(identity[2])) == (base['object'], base['made_us']),
            'flagged row no longer matches validated Core identity')
    fields = parsed.groups()
    counts, execution, wait, maximum = [list(map(int, field.split(','))) for field in fields[:4]]
    info = dict(zip(c339.SCALARS, map(int, fields[4:13])))
    submit = list(map(int, fields[13].split(',')))
    flag = int(fields[14])
    require(key(base) == TARGET and flag == 4
            and all(0 <= v < 2**64 for v in counts+execution+wait+maximum+submit+list(info.values()))
            and sum(wait)-base['busy_wait_ns'] == 52, 'unexpected prefix-flag shape or discrepancy')
    require(sum(counts) == base['jobs'] and counts[6:] == [1,0]
            and sum(execution) == base['own_exec_ns']
            and execution[6] == maximum[6] == base['end_ns']-base['start_ns']
            and all((n==s==m==0) or (n>0 and m<=s<=n*m) for n,s,m in zip(counts,execution,maximum)),
            'independent own-body accounting differs')
    require(info['max_class'] == 6
            and (info['max_job'], info['max_enq_ns'], info['max_start_ns'], info['max_end_ns'])
            == (base['job'], base['enq_ns'], base['start_ns'], base['end_ns'])
            and max(maximum) == maximum[6] and base['start_ns']-base['enq_ns'] <= base['max_queue_ns']
            and base['start_ns'] <= info['submit_begin_ns'] <= info['submit_end_ns'] <= base['end_ns']
            and sum(submit) == info['submit_end_ns']-info['submit_begin_ns']
            and (info['submit_mask'],info['submit_outcome']) == (255,0),
            'independent submit accounting differs')
    row = dict(base, counts=counts, exec_ns=execution, max_exec_ns=maximum, submit_ns=submit, **info)
    for decoder, text in ((c340,n340), (c341,n341), (c342,raw_line)):
        x = decoder.parse_extra(text)
        require(x is not None and decoder.valid_extra(row,x), 'IO timing/identity field failed validation')
        row.update(x)
    return row, dict(queue=base['queue'], ticket=base['ticket'], job=base['job'],
                     producer_flags=flag, scalar_busy_wait_ns=base['busy_wait_ns'],
                     category_wait_sum_ns=sum(wait), category_excess_ns=52,
                     invalid_category_partition_used=False,
                     raw_row_sha256=hashlib.sha256((raw_line+'\n').encode()).hexdigest())


def projection(userlog, strict):
    n338 = c339.normalized(c340.normalize(c341.normalize(c342.normalize(userlog))))
    base = c338.analyze(n338)
    require(base['coverage_qualified'] and not base['errors']
            and base['core_records'] == base['complete_count'] == 773,
            'independent queue-time decode not complete')
    rows = {key(row):row for row in base['rows']}
    accepted = {key(row):row for row in strict['rows']}
    require(len(rows)==773 and len(accepted)==772 and set(rows)-set(accepted)=={TARGET}
            and all(all(row[field]==accepted[k][field] for field in
                        ('object','made_us','enq_ns','start_ns','end_ns','notice','commit_done_us',
                         'core_queue_wait_us','core_commit_execution_us'))
                    for k,row in rows.items() if k in accepted),
            'independent timing disagrees with fully accepted rows')
    matches = [line for line in userlog.splitlines()
               if line.startswith(c342.PREFIX) and ' queue=1 ticket=798 job=105881 ' in line]
    require(len(matches)==1,'flagged Core row not uniquely present')
    row, evidence = validate_rejected_row(matches[0], rows[TARGET])
    accepted[TARGET] = row
    use = ('object','made_us','queue','ticket','job','enq_ns','start_ns','end_ns',
           'core_queue_wait_us','commit_done_us','io_identity','io_begin_ns','io_end_ns',
           'io_ns','bo_unique','cpu_ns','newbo_counts','newbo_max','newbo_begin','newbo_end',
           'newbo_max_cpu','newbo_max_envelope')
    return dict(state=PROJECTION, coverage_qualified=True, errors={},
                rows=[{field:row[field] for field in use} for row in accepted.values()]), evidence


def display_evidence(text):
    shape = re.compile(r'^SWEET FB STATS: attempts=(\d+) copied=(\d+) zero=(\d+) invalid=(\d+)'
                       r' bytes=(\d+) layers=(\d+) guards=(\d+) refused=(\d+); CPU, not scanout$',re.M)
    samples = [tuple(map(int,m.groups())) for m in shape.finditer(text)]
    require(samples and all(s[0]==s[1]+s[2] and s[3]==0 and s[5]>=s[1] and s[6]>=s[7] for s in samples)
            and all(all(x<=y for x,y in zip(a,b)) for a,b in zip(samples,samples[1:])),
            'framebuffer software-copy counters not qualified')
    return dict(zip(('attempts','nonzero_copy_attempts','zero_byte_attempts','invalid_timing','bytes',
                     'layers','GPU_read_guards','GPU_read_refusals'),samples[-1]),
                evidence_scope='last sampled cumulative prefix of actual CPU copies, not the final total or optical FPS')


def main():
    require(sha(EXEC/'result.json') == RESULT and sha(EXEC/'independent-restore.json') == PROOF
            and sha(BASE/'ready.json') == READY and sha(REFERENCE/'result.json') == REFERENCE_RESULT,
            'original denied verdict, restoration or control receipt changed')
    require(all(sha(EXEC/name)==digest for name,digest in RAW_PINS.items()), 'original raw capture changed')
    result=load(EXEC/'result.json')
    proof=load(EXEC/'independent-restore.json')
    plan=load(BASE/'trial-plan.json')
    ready=load(BASE/'ready.json')
    require(all(result[k] for k in ('restored','independent_restore_verified','static_root_comparison_passed',
                                     'observer_group_clear'))
            and result['observer_exit']==0 and result['boot_attempts']==1
            and all(proof[k] for k in ('misc_original_4096_bytes_match','all_original_slot_bits_allocated','journal_empty'))
            and len(proof['files'])==6 and all(r['original_logical_and_allocated_bytes_match'] for r in proof['files'].values())
            and proof['install_plan_sha256']==ready['install_plan_sha256']==plan['install_plan_sha256']
            and load(EXEC/'observer-process.json')['image_sha256']==IMAGE
            and sha(BASE/'trial-plan.json')==ready['trial_plan_sha256']
            and result['legacy_observation_state']=='BC336-cache-reuse-observed-root-restored',
            'restoration, image or baseline configuration verdict differs')
    for name, digest in ready['input_pins'].items():
        require(sha(name)==digest,'frozen input differed: '+name)
    evidence_pins = {str(EXEC/f):sha(EXEC/f) for f in (
        'result.json','independent-restore.json','kernel.log','kernel.log.bin','collection-analysis.json',
        'queue-identity-analysis.json','kernel-IO-analysis.json','kernel-IO-identity-analysis.json')}
    before=load(EXEC/'fresh-before/result.json')
    after=load(EXEC/'post-capture/result.json')
    for path, preserved in result['other_log_prefix_preserved'].items():
        name=before['files'][path]['output']
        old,new,tail=(EXEC/'fresh-before'/name, EXEC/'post-capture'/name, EXEC/(name+'.current'))
        data, prior = new.read_bytes(), old.read_bytes()
        require(preserved and data.startswith(prior) and tail.read_bytes()==data[len(prior):]
                and hashlib.sha256(prior).hexdigest()==before['files'][path]['sha256']
                and hashlib.sha256(data).hexdigest()==after['files'][path]['sha256'],
                'lost original log prefix or changed tail')
        for stream in (old,new,tail):
            evidence_pins[str(stream)]=sha(stream)
    require(len(result['other_log_prefix_preserved'])==4,'original log-prefix coverage differs')
    collection=load(EXEC/'collection-analysis.json')
    require(not collection['coverage_qualified'] and set(collection['errors'])==COLLECTION_ERRORS
            and collection['C4_complete']==collection['notice_records']==773
            and collection['kernel_lost']==collection['SB_lost']==0 and collection['kernel_version']==2,
            'strict verdict changed or there is additional loss')
    t=(EXEC/'kernel.log').read_text()
    require(t.splitlines().count(plan['kernel_banner'])==1,'kernel boot identity differs')
    parsed=kernel.parse(t,(EXEC/'kernel.log.bin').read_bytes())
    require(parsed['coverage_qualified']
            and json.loads(json.dumps(parsed))==load(EXEC/'kernel-IO-analysis.json'),
            'kernel raw/decoded ring or CPU records differ')
    backboard=(EXEC/(before['files']['/private/var/log/backboardd.log']['output']+'.current')).read_text()
    strict=c342.analyze(backboard)
    require(strict['errors']==CORE_ERRORS and strict['complete_count']==772,
            'strict Core decoder no longer reproduces original rejection')
    reduced, flagged=projection(backboard,strict)
    joined=kernel.join(parsed,reduced,collection['script_window_us'])
    require(joined['coverage_qualified'] and not joined['errors'] and joined['complete_submit_count']==732
            and joined['program_maximum_join_count']==20,'independent kernel join incomplete')
    original=load(EXEC/'kernel-IO-identity-analysis.json')
    matched={key(row):row for row in joined['submits']}
    require(original['errors']=={'unqualified_user_core':1}
            and len(original['submits'])==731 and len(matched)==732
            and set(matched)-{key(row) for row in original['submits']}=={TARGET}
            and all(row==matched[key(row)] for row in original['submits'])
            and sorted(original['program_maxima'],key=key)==sorted(joined['program_maxima'],key=key),
            'independent join altered existing valid records')
    flagged['kernel_token']=matched[TARGET]['kernel_token']
    identity=c342.identity(backboard)
    require(identity['coverage_qualified'] and not identity['errors'] and identity['records']==2319
            and identity==load(EXEC/'queue-identity-analysis.json'),'independent front-end identities differ')

    output=BASE/'post-analysis-prefix-v1'
    output.mkdir()
    view=output/'comparison-inputs'
    view.mkdir()
    save(view,'collection-analysis.json',dict(collection,state=PROJECTION,coverage_qualified=True,
                                             errors=[],original_full_collection_qualified=False))
    save(view,'core-wait-execution-analysis.json',reduced)
    save(view,'kernel-IO-identity-analysis.json',joined)
    (view/'kernel.log').symlink_to(EXEC/'kernel.log')
    (view/'queue-identity-analysis.json').symlink_to(EXEC/'queue-identity-analysis.json')
    compare=tool('compare-runtime343')
    report=compare.compare(view,result)
    comparison=load(view/'runtime343-comparison.json')
    comparison.update(state='0343-IO-and-queue-projection-compared-with-0342',
                      full_capture_verdict_retained=collection['state'], projection=PROJECTION,
                      includes_rejected_wait_classification=False)
    save(output,'runtime343-comparison.json',comparison)
    display=display_evidence(t)
    require(all(sha(name)==h for name,h in evidence_pins.items()), 'original evidence changed during projection')
    summary=dict(state='0343-original-restoration-verified-IO-queue-projection-complete',
                 scope=PROJECTION, full_capture_qualified=False, strict_core_errors=strict['errors'],
                 ready_pins_verified=len(ready['input_pins']), core_records=773, submit_joins=732,
                 program_maximum_joins=20, flagged_row=flagged,
                 comparison={k:v for k,v in report.items() if k!='state'},
                 copy_evidence=display, optical_measurement='not-recorded-by-user',
                 physical_FPS_qualified=False, input_pins=evidence_pins,
                 original_logs_and_strict_verdict_unchanged=True, device_commands=0)
    save(output,'result.json',summary)
    print(json.dumps({k:v for k,v in summary.items() if k!='input_pins'},indent=2))


if __name__=='__main__':
    main()
