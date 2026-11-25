#!/usr/bin/env python3
"""Decode bounded SUBMIT328 CPU refusal metadata; never qualify frame rate."""
from collections import Counter
import re
PREFIX='SWEET GS328: '
LIMIT=PREFIX+'limit=64 coverage=incomplete'
FIELDS=('seq','tick','token','rc','stage','index','handle','requested','actual','bo_state','cmd_type','cmd_index','cmd_offset','cmd_bytes','bos','cmds','queue','flags','fence','pending','native','bytes')
HEX={'rc','requested','actual','flags'}
U64={'tick','token','bytes'}
ROW=re.compile(re.escape(PREFIX)+' '.join('('+('[0-9a-f]{16}' if name in U64 else '[0-9a-f]{8}')+')' for name in FIELDS))
STAGES={1:'client/owner gate',2:'dispatch pending completion',3:'runtime ready gate',10:'submit request shape/range',11:'submit pending completion',12:'descriptor allocation',13:'descriptor copyin',14:'BO handle/flags/presumed address',15:'duplicate BO handle',16:'command BO index',17:'command read permission/range',18:'surface CPU alias',19:'runtime issue/submit',20:'native fence validation'}
def analyze(text):
 rows=[];errors=Counter();limits=0;mentions=0;last_tick=last_token=0;late=False
 for line in text.splitlines():
  if not line.startswith(PREFIX):continue
  mentions+=1
  if line==LIMIT:
   limits+=1;continue
  if len(line.encode())+1!=235:errors['record_size_mismatch']+=1;continue
  m=ROW.fullmatch(line)
  if not m:errors['malformed_record']+=1;continue
  row={name:int(value,16)for name,value in zip(FIELDS,m.groups())}
  if any(row[k]>=2**(64 if k in U64 else 32)for k in FIELDS):errors['integer_overflow']+=1;continue
  if row['seq']!=len(rows)+1 or row['seq']>64:errors['sequence_or_record_limit']+=1;continue
  if row['stage'] not in STAGES or not row['rc'] or not row['tick']:errors['invalid_stage_result_or_clock']+=1;continue
  if row['tick']<=last_tick:errors['clock_order']+=1
  if row['token']:
   if late or row['token']<=last_token:errors['profile_token_order']+=1
   last_token=row['token']
  else:late=True
  last_tick=row['tick'];rows.append(row)
 if limits>1 or(limits and len(rows)!=64):errors['invalid_limit_marker']+=1
 header=re.findall(r'^SWEET GPU API PERF: valid=(\d+) pending=(\d+) selector=[0-9a-f]+ .*$',text,re.M)
 api=re.findall(r'^SWEET GPU API PERF: selector=46 calls=(\d+) failures=(\d+) queue_ns=\d+ held_ns=\d+ max_held_ns=\d+ wait_ns=\d+; held excludes unlocked wait$',text,re.M)
 counters=None;scoped=[r for r in rows if r['token']]
 if header!=[('1','0')] or len(api)!=1:errors['counter_prefix_missing_or_unqualified']+=1
 else:
  calls,failures=map(int,api[0]);counters=dict(calls=calls,failures=failures)
  if not 0<calls<2**64 or not 0<=failures<=calls:errors['invalid_counters']+=1
  if failures!=len(scoped):errors['failure_count_mismatch']+=1
 qualified=not errors and not limits and counters is not None
 state=('submit-refusals-classified'if scoped else'no-submit-refusals-in-counter-prefix')if qualified else'submit-refusal-coverage-unqualified'
 return dict(state=state,diagnostic_coverage_qualified=qualified,records=len(rows),prefix_records=len(scoped),post_prefix_records=len(rows)-len(scoped),limit_markers=limits,mentions=mentions,errors=dict(errors),counters=counters,stage_counts={str(k):v for k,v in sorted(Counter(r['stage']for r in scoped).items())},stage_meanings=STAGES,rows=rows,device_commands=0,physical_FPS_qualified=False,
  scope='Cached CPU metadata at rejected compositor async submissions; original return codes and validators retained. Token0 is outside the API profiling prefix. A missing/refused record does not establish the cause of unobserved failures. Successful submissions are not logged.')
