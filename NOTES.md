# iOS 16 on gauguin (Redmi Note 9 Pro 5G, SM7225) - working notes

## Agent handoff / active work

### 2026-11-07 — 0134 CM3 NMI-clear candidate committed; all61 hosts/two native TUs pass; full build next

THIS goal turn is progress: complete133 native build/image/readers passed;
ONE real133 boot advanced to CM3_CFG store59, captured4052->52, and native
adreno.c proved NMI bit9. Codex wrote134 and DSH validated it. Full daily-use/
GPU/Metal/RAM/storage/peripheral/high-refresh goal remains ACTIVE/incomplete.
No firmware execution/reset release/ACKs or GPU/Metal hardware qualification.

Private code46e3506494eeb1150130b80d21d4b35171ee2b87 adds128th patch
0134-gauguin-cm3-config-nmi-field.patch. Fresh source134-codex5282files SHA
9d388676f51a88d2fcefb1b86d5b2472d1ccb102d322e3c29d1659a3fe9e9b51.
Exactly firmware.c/h and board.c differ from frozen133acc6af6d...a6822.
ONLY CSR CM3_CFG off20b4 keeps native4052 and same guarded write/barrier/read,
requires documented NMI9 clear (mask200/expected0), rejects all-ones and IO/
guard failures. Other fields, including bit14, remain UNQUALIFIED; no invented
ffffbfff mask/read-only claim. Every other config/reset/GX/IRQ/fault/budget/
TCM/ACK check unchanged, public receipt unchanged. Private valid/raw cache
emits SWEET GMU CM3 CFG after AO row on completion or AFTER quarantine on
failure. No new MMIO/retry; original135? NO: candidate is134, do not rename
physical131-page counts when migrating metadata.

DSH41780 actual validate134.py0, normal FIVE actual zero results: pristine
replay, full61 hosts, original-model I/O equivalence, real firmware/board TUs.
validation-result.json inputs/source/baseline unchanged. Exact native NMI
adreno.c SHA7d8a0cc4a93144a31724f1c6e910dca41f1fae2a317a8636dcdca328763c9a5a
and native/source-pin.json are input-pinned along with existing references.
GMF ASan/UBSan1,669,246 checks; board2840+91. Tests physical52,original4052,
SYNTHETIC extra high bit; NMI set/all-ones refuse after copy/before release,
cache/repeat/output and every original callback failure pass. Board tests
full/partial cache logs/quarantine. Frozen ORIGINAL129 fixture versus baseline
133/134 has identical1,009,420 I/O requests/digestf8383376e7a1a07b. Actual
native firmware48784B SHAb18a8bbbea8a28c7e54a80e333e6be03d732ee264b7bf58bffd03a558d4674fc;
board68312B SHA828ba80405b828771217e0bcf393207c4c89d2d9889b906ce347611657d9f97a,
using CURRENT133 F4oxTo recipe/source. All owned handles CLOSED.

133 physical handoff pushed/verified publiclybe2e7676a45a0db0e4e63df2e983233ae9f20c84,
sole parent6b403b0bb84c825fb4f919239b02ba998f65ab17, two text paths, private
head7c6371e not pushed. Next sanitized134 source/notes snapshot on be2e767;
publication report research/tmp/dsh-0134/public-snapshot-0134.json. Never
push private ancestry, dumps/serials or downloaded/binary assets.

NEXT: full134 standard local build/qualification retaining every133 check;
require installed CM3 CFG record and source-bound NMI-clear flag. Pack/
independent review, unique134 trial. Full reader must require exactly one
CM3 row AFTER AO/PDC6/hidden3, BEFORE adapter completion: off20b4, requested
4052,checked_mask200,expected0,raw!=ffffffff and NMI9 clear; all other bits
explicitly UNQUALIFIED. Keep all previous FW-result/copy/INIT/version/reset/
OOB and other all-ones checks; AO mask fullffffffff stays valid for its own
requested-mask word. Test NMI set/all-ones,52/4052/other bits, wrong request/
mask/expected/offset/false-qualified/missing/duplicate/order records, then ONE
coherent temporary134 boot. No134 full build/image/reader/phone IO yet. Phone
last TWRP after133, reset attribution unknown, no new user UI/touch result.
Original mkadt seven-line diff untouched; no flash/format/GPT/destructive
action. Codex core/review/Git, DSH exact full-access compile/test/boot tasks.

### 2026-11-07 — actual133 reaches CM3 CFG store59; documented NMI-clear field candidate next

DSH31093 ONE actual133 temporary boot observer0/full verifier2; original full
rejection retained. Start2026-11-06T21:12:01.498708Z,finish21:14:13.279471Z;
Send19088KB0.442s/Boot0.135s/total0.580s, recovery observed130s. Products and
routine recovery-latch readback passed. No new user manual/reset attribution.
Fresh4044lines/454212B logp3-gmuf-0133-native-observer-20261107.txt SHA
44f203b6d9eac80a895784f0f02e8da9b80cf14f19b0a5e4a28d8d338645e8c4;
cycle991B SHA8ce27e2d9bffb54ca5a69a2bce40fdcb64c20b0ce3407323ae891f228777bfc4.
Same-boot CMDDB131072B SHA236cb2b9152314a2435e7110b396cb283874ddd0f4ad989a4a726e4255d255f5.

SMMU131/140, PDC six named fields and full8192-word TCM write/readback again
complete. AO mask raw3f/check3b passes. Next exact READBACK refusal: phase0,
GMF6, writes59/polls0,CSR window0 off020b4/PA03d7e0b4, CM3_CFG(native1f82d),
requested4052/actual52 (bit14 differs). Reset1/release0/OOB0,FW0/version0;
no firmware execution/ACK/GPU/Metal. GFSR0,FSR400/400,AO status0/info0.
DSH59205 audit_failed_trial133.py actual0 -> failed-trial-audit.json state
bound-TCM-copy-AO-mask-CM3-config-refusal, all inputs unchanged. SMMU prefix,
raw named-field records and cached refusal are stage subsets; full rejection
kept. Reader SHA471a48eb46ee535b86155192599efe2b6ff425bf362317ff790b77f35e0be619.
PhoneTWRP; all handles closed. No new UI/touch/hardware reset-cause claim.

Pinned native a6xx_gmu.c1099-1104 explains4052 restores CM3 configuration to
avoid starting in NMI. Newly fetched exact19b63c8 drivers/gpu/msm/adreno.c
defines GMU_CM3_CFG_NONMASKINTR_SHIFT9 and sets bit9 to send NMI (lines364-380).
Cached research/tmp/dsh-0134/native/adreno.c115732B SHA
7d8a0cc4a93144a31724f1c6e910dca41f1fae2a317a8636dcdca328763c9a5a,
Git blob bde230310e4a0fbcf32a00f2b5bb6b63ff0dd2dc matches present exact entry
in saved source-tree listing. Listing ref19b63c8 is TRUNCATED; only this target
entry is verified, not a complete repository tree. First download precondition
incorrectly expected an untruncated tree SHA, stopped before fetch/write;
then scoped check to exact present blob + immutable raw URL, saved source-pin.
Bit14 and other CM3 fields remain undocumented; do not invent maskffffbfff or
read-only semantics. Actual52 has bit9 CLEAR. Next134: keep native4052 write
and existing write/barrier/read order for ONLY CM3_CFG, require documented NMI
bit9 clear, reject all-ones/IO/guards, cache raw value with other bits explicitly
UNQUALIFIED; fresh FW result/ACKs still required. All other comparisons and
public receipt unchanged. Test NMI set/all-ones,52/4052/synthetic other bits,
cache/repeat/output and callback failures, all61 hosts and current133 F4oxTo
native TUs. No134 code yet. Goal ACTIVE; original mkadt seven-line diff intact;
no flash/format/GPT/destructive action.

### 2026-11-07 — complete133 native kernel/image/runtime readers qualified; one physical trial next

Previous goal turn was progress: actual132 full TCM copy/readback then AO
mask refusal;133 code tested/committed/pushed. THIS turn DSH31554 actual
standard local build0/qualification0, gauguin.F4oxTo, captured HEAD
727b267985916ed61cfaac7acb8c097b1ba4e3fc. Exact127-patch sourceacc6af6d...a6822,
5282files. Native installed kernel16905504B SHA
d2b8659469267c7f1dbe5b6a2b6c4b46f81a23eb46c96cd241a9077d04e05c69,
IDxnu-6a2dc5a2f0d041ba8542aa15af19b543. Manifest SHA
f44fac92cbd82c708b75eb5dbea6c319c055b10b77c9a5c9bdbf21103b3b2786;
qualification SHAe2fe0482c50834f9c11446d7e5a2c8010470681a928722e7c7135117e67f1758.
Every132 check retained plus ao_irq_named_sources_source_bound TRUE and
installed AO-format check. Current native recipe/source now133 F4oxTo,
do not reuse132 InoCAW after shared Makefile replacement. No CI used.

DSH64173 actual package0/independent review0, all input hashes unchanged.
Normal package-review-execution-result.json passed; newly authored wrapper
uses exact native133 result filename, no metadata execution failure this time.
Image shim/out/shim-p3-gmuf-0133-native-20261107.img19546112B SHA
cae0af455a7c3e1ecf5bcc2ce2849f2f3c201266ed4401a8ac241e763a238493;
payload19218432B SHA025d5ed1004515c78b930065fb6c2e68847faf8fd008f3799861de568943546b.
Evidence SHA984482f1cb34229749f6464bde3e0dfc2daa5caa22923da7f91f77314a1bd1e6.
Unique sweettrial=gmuf-0133-20261107-a1,539bytes; same asset source placement
NVT182558000/MDT18257c000/GMU182580000. All older132/131/etc pins preserved.

DSH91516 runtime_validate133.py actual0, normal three actual zero results,
inputs unchanged. Clock4/95,FW17/276,full explicitly SYNTHETIC11/47. Reader SHA
471a48eb46ee535b86155192599efe2b6ff425bf362317ff790b77f35e0be619.
Requires one AO mask row after hidden3/PDC6 before adapter completion, requested
ffffffff, checked_mask3b, all five named bits set, other bits UNQUALIFIED;
allows fullffffffff for THIS requested-mask word. All original FW/ACK/copy/
reset/OOB and other all-ones/status/IRQ checks retained. Tests cover named
source missing, zero, raw3f/full mask/synthetic other bits, false-qualified/
wrong mask/request/offset/order/missing/duplicate records. Numeric values,
complete131-page/140-ATOS strings and original SHA pins preserved. All these
handles CLOSED; no133 phone proof yet at THIS checkpoint.

Phone last TWRP. Reviewed boot133.py/run_hardware133.py prepared for ONE
image-pinned temporary boot, unique recoverygauguin/fastbootgauguinpro and
routine latch readback, unchanged180s observer/freshpull. Next execute exact
execute-hardware.txt via DSH; bind actual refusal or real FW-result/ACKs.
Whole goal ACTIVE, original seven-line mkadt diff untouched; no flash/format/
GPT/destructive action. No new user UI/touch/reset-attribution evidence.

### 2026-11-07 — 0133 AO named-source mask candidate committed; all61 hosts/two native TUs pass; full build next

THIS goal turn is progress: complete132 native kernel/image/readers passed;
ONE real132 boot completed PDC programming and full8192-word TCM copy/readback,
then exposed AO mask width/equality refusal. Codex wrote133 and DSH validated
it. Full daily-use/GPU/Metal/RAM/storage/peripheral/high-refresh goal stays
ACTIVE/incomplete; firmware has still NOT executed, no reset release/ACKs.

Private code737e6c41d50d7c586a48daed084cd0dc3b04dfcf adds127th patch
0133-gauguin-ao-interrupt-mask-fields.patch. Fresh source133-codex5282files SHA
acc6af6d7f023b530643d93442cc46d73fd5892911c0bf9e51f1f17dfcfa6822.
Only firmware.c/h and board.c differ from frozen1326ca52236...5c689.
ONLY AO HOST_INTERRUPT_MASK off2c18 keeps fullffffffff write and identical
guarded write/barrier/read, checks all five native named sources mask3b;
other bits UNQUALIFIED, no inferred width. A fullffffffff read remains valid
for this requested mask (same as old store); all OTHER register/status/IRQ/
GIC/deadline/TCM/reset/ACK checks unchanged, CSR mask untouched. Private
valid/raw cache logs SWEET GMU AO MASK after PDC rows on completion, or AFTER
quarantine on failure. Public receipt unchanged; no new MMIO or retry.

DSH98990 actual validate133.py0, normal FIVE actual zero results: pristine
replay, full61 host files, original-model I/O equivalence, real firmware/board
native TUs. validation-result.json inputs/source/baseline unchanged. Primary
kgsl_gmu.h SHA5f08ed0eed8118068a66e5596612a5ac9d00e410c6a1920fd7a85fbb12ad3d8b
is input-pinned together with earlier PDC/native references. GMF ASan/UBSan
1,657,593 checks; board2840+90. AO tests physical3f, named3b, fullffffffff
and explicitly SYNTHETIC extra high bit; every named bit missing and zero
refuse after copy/before release, repeat/output/cache preservation and all
original callback failures pass. Board checks full/partial cache rows and
quarantine. Frozen ORIGINAL129 fixture against baseline132/133 has identical
1,009,420 requests/digestf8383376e7a1a07b. Actual native objects firmware
46984B SHAabfa79e4a7dd1ec21ffb935d49f19cefa2cf8883e2e4734fc2a415f9c68deee3,
board67008B SHAd89949c9bbcc02fbdf944bcd1d53098c99ac5b8475aa9dacd828369e97a7f8ec,
using CURRENT132 InoCAW recipe/source. All owned handles CLOSED.

132 physical handoff pushed/verified publiclye0b5fd270a21db704d56e4a5db8ff6ad09501c8d,
sole parentdd3ad8bb9a72b9b879a8d8c3e37c0414ec777f94, two text paths, private
head e0569a3 not pushed.133 sanitized source/notes pushed/verified
6b403b0bb84c825fb4f919239b02ba998f65ab17, sole parent e0b5fd2, eight text
paths, same tree as private fd5228e. Publication report
research/tmp/dsh-0133/public-snapshot-0133.json. Never push
private ancestry, device dumps, serials or binary assets.

NEXT: full133 standard local native build/qualification retaining every132
check; require installed AO-mask record and source-bound named-sources flag.
Pack/independent review, unique133 trial; full runtime reader must require
exactly one ordered AO row AFTER hidden3/PDC6 and BEFORE adapter completion:
off2c18, requestedffffffff, checked_mask3b, all named sources set, other bits
explicitly UNQUALIFIED. Allow fullffffffff for THIS mask read; other all-ones
refusals stay intact. Keep original131-page/140-ATOS strings and numeric data
when changing version labels. Require all prior FW-result/copy/INIT/version/
reset/OOB checks. Test each missing named source, zero, raw3f/full mask/other
bits, false-qualified/wrong-mask/request/duplicate/order records, then ONE
coherent temporary133 boot. Watch metadata filenames:132 package/audit wrappers
initially used stale131 filenames before any action; preserved failed originals
and separate corrected wrappers/reports. No133 full build/image/reader/phone
IO yet. Phone last TWRP after132, reset attribution unknown, no new user UI/
touch result. Original seven-line mkadt diff untouched; no flash/format/GPT/
destructive action. Codex core/review/Git, DSH executes exact full-access tasks.

### 2026-11-07 — actual132 completes PDC programming and full8192-word TCM copy/readback; AO interrupt-mask comparison next

DSH85774 ONE actual132 temporary boot observer0/full verifier2, original full
rejection retained. Start2026-11-06T20:52:52.069838Z,finish20:55:03.861661Z;
Send19088KB0.446s/Boot0.135s/total0.583s, recovery observed131s. Unique recovery/
fastboot products and routine latch readback passed; no new user reset fact.
Fresh raw log4087lines/459092B SHA
5102a8d7e25977d484d6a3f258bbf4b16bf6f580f05db5619878a0e3214c91c6,
p3-gmuf-0132-native-observer-20261107.txt. Cycle1163B SHA
2d2482587f35ad5a682545108816325bf41f7ee7d0034201a239c23f96dac74d.
Same-boot CMDDB131072B SHA981691dfd383b7fcc9cd4f1b33a899decae19a4cb8693093dafe020777cf1dd5.

Cold SMMU131/140 complete. All six PDC MSGID raw values10100 pass named
WRITE/RESP_REQ checks; RSC/PDC register programming completes, other-field
semantics/actual PDC command execution remain UNQUALIFIED. Physical TCM
copy_issued8192/copy_compared8192: all32768 pinned firmware bytes written and
read back under reset. No reset release, OOB, firmware execution or ACKs.
Next real refusal at store51: phase0/GMF6, AO window1 off02c18/PA03d8ec18,
GMU_AO_HOST_INTERRUPT_MASK, requestedffffffff, actual0000003f. CSR host-mask
store50 already passed full comparison (source-bound). GFSR0, FSR400/400 with
no named fault flags, reset1/GX00222001, AO status0/info0. No FW/GPU/Metal claim.

DSH41417 first audit wrapper failed BEFORE reader import (stale filename
verify_gmuf131.py under dsh-0132); original script/log retained. DSH31992
audit_failed_trial132_v2.py corrects only both reader filenames, pins original
failure files and itself, actual0 -> failed-trial-audit.json state
bound-native-SMMU-PDC-TCM-complete-AO-mask-refusal, all inputs unchanged. Full
rejection kept; SMMU prefix and raw ordered hidden/PDC records plus source-
bound copy counts are stage subsets, never full FW success. All handles closed.

Pinned kgsl_gmu.h23-27 SHA5f08ed0eed8118068a66e5596612a5ac9d00e410c6a1920fd7a85fbb12ad3d8b
defines AO WDOG0/RSCC_COMP1/FENCE_ERR3/DBD_WAKEUP4/HOST_AHB_ERR5. Union3b,
errors29 matches existing guard. Actual3f has ALL named sources masked. Do
NOT infer a six-bit implemented width or general reserved/read-only behavior.
Next133 candidate: ONLY AO mask word keeps fullffffffff write and existing
guarded write/barrier/read, checks all named3b mask bits, privately caches
raw result and logs other bits UNQUALIFIED. Fullffffffff read remains valid
for this word: it is the requested mask and was already accepted; other
register/all-ones/error guards unchanged. Keep CSR mask/store full-width.
Test each of five named bits missing, physical3f, fullffffffff and synthetic
other bits, repeat/cache/output preservation, all61 hosts, original-model I/O
equivalence, native TUs using CURRENT132 InoCAW. No133 code yet. PhoneTWRP,
reset attribution UNKNOWN; goal ACTIVE, original mkadt diff untouched, no
flash/format/GPT/destructive action.

### 2026-11-07 — complete132 native kernel/image/runtime readers qualified; one physical trial next

Previous goal turn was progress: real131 PDC MSGID refusal bound,132 code
tested/committed/pushed. THIS turn DSH51033 actual standard local build0/
qualification0, gauguin.InoCAW, captured HEADc8a8eb3449a532b83de1494c3818f36e452921ed.
Exact126-patch source1326ca52236...5c689/5282files. Native installed kernel
16905432B SHA18940ccb1f019ca2fa2ae79cad296ec6f83eb1f5f23404c7dc7f9c41150ab27e,
IDxnu-55987b2e8f5d4087b72e0e70232ec3a0. Manifest SHA
45babf98ba23ea965b9b173288fd7ca4d5bdf1f6f515507b55119d8340a64b08;
qualification SHAb5952bf68feb377dacd3adbd324de0e9d9d82630af3c65e2198f6a3b209a15c2.
Every131 check retained plus pdc_msgid_named_fields_source_bound TRUE and
installed PDC-format verification. Current native recipe/source now132
InoCAW, do not reuse131 SM6zJz after shared Makefile replacement. No CI used.

DSH35304 packaging wrapper actually exited1 BEFORE reading build input or
packaging: stale filename native131-execution-result.json under dsh-0132.
Original wrapper/log retained. DSH86518 explicit package_and_review132_v2.py
corrects ONLY that input pathname; pins original failure files and itself,
then actual package0/independent review0, all inputs unchanged. Normal
package-review-execution-result.json passed. No image from failed wrapper.
Image shim/out/shim-p3-gmuf-0132-native-20261107.img19546112B SHA
ff7b40c7760beb1a35fb3174863c1c4406cb5a74a6da54381dc0bd61f9a96cef;
payload19218432B SHAa225850dfba07a30691a5fbfa68ff45114f36d00095f4055a3b82fdd5a6bc9c4.
Evidence SHA841e94e02c346e78bf23a7e491b8fdf6f331004863e4422acbbe22519f721196.
Unique sweettrial=gmuf-0132-20261107-a1,539bytes; assets unchanged at
NVT182558000/MDT18257c000/GMU182580000. All prior131/130/etc image pins intact.

DSH76499 runtime_validate132.py actual0, normal three-zero result report,
all input pins unchanged; clock4/95,FW14/261,full explicitly SYNTHETIC8/41.
Strict reader SHA02ee85b190305218b43cb7de9ebc52c3b14dd71dad81abf42b6e27847c965338.
Requires six ordered MSGID rows, native requested10108, checked_mask10100,
raw!=ffffffff with WRITE/RESP_REQ present, other bits UNQUALIFIED. All earlier
FW/ACK/full-success checks preserved. Tests reject each absent control bit/
all-ones, wrong mask/request/label/order/missing/duplicate rows, keep raw
other-bit scope unqualified. Numeric constants, actual complete131-page log
strings, original asset pins and dynamic payload/asset fixture layout retained.
All these handles CLOSED; no132 hardware proof yet at THIS checkpoint.

Phone last observed TWRP. Reviewed boot132.py/run_hardware132.py prepared for
ONE image-pinned temporary boot with unique recoverygauguin/fastbootgauguinpro
and routine recovery-latch readback, unchanged180s observer/freshpull. Next
execute execute-hardware.txt via DSH; bind actual failure or all actual FW
ACKs. Goal ACTIVE/incomplete; original seven-line mkadt diff untouched, no
flash/format/GPT/destructive action. No new user touch/UI/reset-attribution.

### 2026-11-07 — 0132 PDC MSGID named-field candidate committed; all61 hosts/two native TUs pass; full build next

THIS goal turn is progress: complete131 native build/image/readers passed,
actual131 advanced to PDC store27, audit bound the real MSGID difference;
Codex wrote132 and DSH validated it. Full daily-use/GPU/Metal/RAM/storage/
peripheral/high-refresh goal remains ACTIVE/incomplete; no firmware execution.

Private code199597858f1d558da559183021a2ea3c8a65a3a3 adds126th patch
0132-gauguin-pdc-msgid-control-fields.patch. Fresh source132-codex5282files SHA
6ca52236e335909dbc7d3b09ba7b520764e99163249c31347cce41ba1e55c689.
Only firmware.c/h and board.c differ from frozen131fb3e3f59...a6e0c.
Six fixed PDC MSGIDs at15d4/15e4/15f4/1764/1774/1784 still receive native10108
in the same guarded write/barrier/read positions. Header mask10100 names
WRITE16/RESP_REQ8 from pinned native rpmh-rsc.c. Missing either refuses with
that mask; all-ones still full-width refusal. Other bits explicitly UNQUALIFIED,
not called read-only. All other PDC/BCM/register/TCM/reset/fault/IRQ/budget/ACK
checks and public receipt unchanged. Private valid mask + six raw values
emit SWEET GMU PDC MSGID after hidden rows, after completion or quarantine.

DSH46970 actual validate132.py0, five normal actual zero results: pristine
replay, full61 host files, original-model I/O equivalence, real firmware/board
native TUs. validation-result.json inputs/source/baseline unchanged. Native
primary rpmh-rsc.c SHAf8a17b18d747ba6abf1a127a4f4a2f5aa229657931753fcd643fa9953440eb9d
and adreno_a6xx_gmu.c SHAd3cb5a1c14a6cde2794ef3e4e268220a738a15420ad74faa7b09aa1c9e7a6f86
are included in input pins. GMF ASan/UBSan1,640,823 checks; board2840+89.
Each of six MSGID slots tests WRITE missing, RESP_REQ missing and all-ones
before copy/release; positive10100 matches actual131, extra high bit is a
SYNTHETIC unqualified-value case. Repeat/output/cache preservation and
fail-every-callback pass. Frozen ORIGINAL129 fixture against baseline131/132
has identical1,009,420 requests/digestf8383376e7a1a07b. Actual native objects:
firmware45320B SHAb964fa7f8f9b8576252dcb1fe19424fdca7b5ed11db771355b1e158466653020,
board65744B SHA4f185edea25a7f6a721a771443c9d5626d305b87792ce61870eb7c90c7cb51e7,
using CURRENT131 SM6zJz recipe/source. All owned handles CLOSED.

131 physical handoff pushed/verified publicly5fa388920dc4e1f3861edc8d9615b7a1d858721c,
sole parenta65270aadc12ffe88651fccf11a379db23fc3053, two text paths, private
head a27110bf not pushed.132 sanitized source/notes pushed/verified
dd3ad8bb9a72b9b879a8d8c3e37c0414ec777f94, sole parent5fa3889, eight text
paths, tree equals private2fa7ae1. Original publisher stopped BEFORE commit-tree/
push because its allowlist retained the old patch suffix; original script
kept, publish132_v2.py changes only that pathname and passed all guards.
Publication report research/tmp/dsh-0132/public-snapshot-0132.json. Never push
private ancestry, device dumps, serials or binary assets.

NEXT: standard full132 local kernel/qualification retaining all131 checks,
require installed PDC MSGID format + source-bound named-fields flag. Pack/
independent review, new unique132 trial; strict runtime reader must require
six ordered distinct PDC MSGID rows after three hidden rows and before adapter
completion, native requested10108, checked_mask10100, raw!=ffffffff and both
named bits present, explicit other-bits-UNQUALIFIED. Preserve all existing
SMMU/FW-result/copy/INIT/version/reset/OOB checks; field readback is not PDC
command, FW/GPU/Metal execution proof. Test malformed/duplicate/order/wrong
mask/request/missing bits/all-ones and false-qualified labels plus dynamic
synthetic payload extent/asset location, then ONE coherent temporary132 boot.
No132 full build/image/reader/phone IO yet. Phone last TWRP after131; manual
reset attribution unknown, no new user UI/touch result. Original seven-line
mkadt diff untouched; no flash/format/GPT/destructive action. Codex core/review/
Git; DSH full-access relay CLI executes exact reviewed compile/test/boot tasks.

### 2026-11-07 — actual131 passes RSC/SEQ and reaches first PDC MSGID;132 field-scoped comparison next

DSH5505 ONE real131 temporary boot observer0/full verifier2, original full
rejection retained. Start2026-11-06T20:33:10.773604Z,finish20:35:22.542410Z;
Send19088KB0.448s/Boot0.134s/total0.584s, recovery observed131s. All identity/
routine latch checks passed. Fresh4024lines/452444B raw log
p3-gmuf-0131-native-observer-20261107.txt SHA
43d4d1e35e6d24ff36e1d74562f8d208261b12e0a9086c5a1b3a190015527611;
cycle991B SHAe0894b9e77ea6ae13423ae78572cb3970f0de9a4ab7c5d125c2c3640f5c553b5.
Same-boot CMDDB131072B SHAc297d6bba3ccbe1bd09d6b378f58f0de24d042c407bbd74236802e46d80ca010.

Cold SMMU131/140 again completes. All three hidden-address writes returned
82204514/82204510/82204520, recorded as equality UNQUALIFIED; native RSC and
PDC sequence-memory stores finish. Next failure is write27, phase0/GMF6:
PDC window2 off015d4/PA0b2955d4, native TCS1 CMD0 MSGID(word1575), requested
00010108, actual00010100, difference bit3. No polls/TCM copy/reset release/
OOB or FW/ACK/GPU execution. Cached FSR400/400 has no named fault flags.
DSH87951 actual audit_failed_trial131.py0 -> failed-trial-audit.json state
bound-native-SMMU-RSC-complete-PDC-MSGID-refusal, all inputs unchanged. Strict
131 reader SHAf0542b513b4b50fa5fb3b65ac94f91c40c8b8d3b1401f632c92b8c3889deee33;
SMMU stage prefix only, plus raw ordered three policy rows and PDC refusal;
full-success rejection retained. PhoneTWRP; manual/no-reset attribution131
UNKNOWN, no new user UI/touch or hardware reset-cause claim. All handles closed.

Native pinned rpmh-rsc.c61-63 defines CMD_MSGID_LEN8, RESP_REQ BIT8, WRITE
BIT16; GPU native a6xx_load_pdc_ucode writes10108 to six TCS1/TCS3 MSGIDs.
Native generic RPMh synchronous BCM transport CAN echo LEN8; its resource is
different from GPU PDC and must not be weakened. PDC field semantics beyond
named WRITE/RESP_REQ are undocumented. Do NOT call bit3 read-only or infer a
general hardware mask solely from the observed difference. Next132 candidate:
only six fixed PDC MSGID writes retain native10108 and existing write/barrier/
read order; require named WRITE/RESP_REQ mask10100 and reject all-ones/IO/
guard failures; privately cache/log complete raw values with other bits
UNQUALIFIED. Every other PDC value, register predicate, TCM/reset/fault/ACK
guard remains unchanged. Test each missing control bit and all-ones at each
slot, original-model I/O equivalence, all61 hosts and current131 native TUs.
No132 code yet. Whole goal ACTIVE; original mkadt seven-line diff untouched;
no flash/format/GPT/destructive action.

### 2026-11-07 — complete131 native kernel/image/runtime readers qualified; physical trial next

Previous goal turn was progress: actual130 read82204514 and tested/committed/
pushed scoped131 policy. THIS turn DSH81260 actual standard local build0/
qualification0, gauguin.SM6zJz, captured HEAD0b8cd7fce17ab2ebd61f94b4d5fcb3dfce6b9b80.
Exact tested125-patch sourcefb3e3f59...a6e0c/5282files. Installed native
kernel16905400B SHA98904a25ae6885148f12af8545c57b13977f6302611a4054e47af045e902fc9b,
IDxnu-4274c5f2ff97423ab0d30a3ea65f4601. Manifest SHA
b81f64b870446e131cefeb03d7ad296b451200a098a0181d45575d4273ff6bd2;
qualification SHA08ac7f86a3feecf3a8b400dca0f8fa84f758729da29ae26a7031b7c27b8c14c7.
Every130 qualification retained plus native_hidden_address_write_policy_linked
TRUE, installed format present. Current native recipe/source now131 SM6zJz;
do not reuse130 xs5x0H after shared Makefile replacement. No CI used.

DSH46930 actual package0/independent review0, all pins unchanged. Image
shim/out/shim-p3-gmuf-0131-native-20261107.img19546112B SHA
618bd22ea5d2ddb519daac773b9d4a8ce93b1ca2b16a49f6a17425f999526644;
payload19218432B SHAe78580f9382621d39bd54cc3422699d0bb55fb05f03bc270feec3a51d0ce202d.
Evidence SHAe25fcfcaafb39032f66cd14bc378fd1deec81ec3fbb500bb74ae2e98fd84729d.
Unique sweettrial=gmuf-0131-20261107-a1, same539-byte command line. Assets
NVT182558000/MDT18257c000/GMU182580000; all old130/129/etc pins preserved.

DSH67587 runtime_validate131.py actual0, all inputs unchanged; clock4/95,
FW12/218,full explicitly SYNTHETIC6/23. Normal runtime-parser-result.json
three actual zero exits. Production verify_gmuf131.py adds exactly three
ordered native policy rows1034/103c/1044 with requested0, raw!=ffffffff,
explicit equality UNQUALIFIED; keeps all existing full-success/FW/ACK guards.
Every new row missing/duplicate/reordered/malformed, all-ones, wrong zero
request or false-qualified label rejects. Full/record tests assert returned
per-field bitwise_qualified FALSE; dynamic synthetic payload extent and GMU
location inherited from130_v3, original negative integer values and all asset
SHA pins preserved during migration. Clock fixture's printed actual130 label
is cosmetic; execution/input hash bind actual131 reader. No hardware proof.

All these handles CLOSED. Phone last observed TWRP; boot131.py/run_hardware131.py
prepared for ONE image-pinned temporary boot, unique recoverygauguin/fastboot
gauguinpro + routine latch readback, unchanged180s observer/freshpull. Next
execute reviewed execute-hardware.txt via DSH; preserve full result then audit
actual failure or require all real firmware ACKs. No131 device IO yet at THIS
checkpoint. Whole daily-use goal ACTIVE; no flash/format/GPT/destructive step,
original seven-line mkadt diff unchanged.130 reset attribution still unknown.

### 2026-11-07 — 0131 scoped native hidden-address policy committed; all61 hosts/two native TUs pass; full build next

Private code75dd82b1d45ad9901ba80019d3983084d124f85a implements125th patch
0131-gauguin-rsc-native-hidden-address-writes.patch. Fresh source131-codex
5282files SHAfb3e3f5916706440687b6d2cd153d386099cbcb0fcc27925feabb65f225a6e0c.
Exactly firmware.c/h and board.c differ from frozen1309eb26716...8a42b.
ONLY AO1034/103c/1044 (native words0xd/0xf/0x11) use fixed zero writes with
equality UNQUALIFIED. Existing guarded write/barrier/read order unchanged;
all-ones still GMF_READBACK with exact diagnostic, IO/guard failures still
stop. Every other store, copy/readback, reset/GX/IRQ/fault/deadline/ACK guard
unchanged. Public receipt unchanged. Private three-value cache + valid bits
emit SWEET GMU FW IMPL rows after transaction completion, or AFTER quarantine
on failure. Partial failures can have fewer rows. No inferred bit mask or
write-only/read-only claim, no retry/MMIO addition.

DSH38555 actual validate131.py0: pristine replay0, all61 hosts0, IO-equivalence0,
native firmware0/board0; authoritative dsh-0131/validation-result.json has FIVE
actual zero results (normal schema, no retained-components workaround), all
inputs/source/baseline unchanged. GMF ASan/UBSan1,624,969 checks; board2840+88.
Three nonzero hidden reads succeed in the host model (first82204514 matches
real130; other12345678/60001000 are SYNTHETIC), each all-ones refuses before
copy/release, unrelated DATA and OOB-clear errors still refuse; repeat/output
preservation and fail-every-callback pass. Board tests full/partial cached
logs and quarantine. Frozen ORIGINAL129 fixture against baseline130 and131
has identical1,009,420 I/O callbacks/digestf8383376e7a1a07b. Actual native
firmware43608B SHA921d912bc9c4e6ba0cac60926a4fe23c11de6de671fcc5e25de6a6ecbf3e90a8;
board61536B SHA88348177381932a6c19a271dc0f8cd9e02657f3e064b36fa964d33fd73d9f90c,
using CURRENT130 xs5x0H recipe/source. All handles CLOSED.

130 physical handoff pushed/verified publicly47a835f027f94b6e6d97ccfe3e7fb3a45e11acf8
on89f11c676099c7f7e155a4b4a8222ff6d81b15a9, two text paths.131 sanitized
source/notes pushed/verified a65270aadc12ffe88651fccf11a379db23fc3053,
sole parent47a835f, eight text paths, same tree as private dc6cea34. Report:
research/tmp/dsh-0131/public-snapshot-0131.json. Never push private ancestry.

NEXT CONCRETE ACTION: standard local131 kernel build/qualification; retain
all130 checks and require linked SWEET GMU FW IMPL format/new source flag.
Then pack/independent review with new unique131 trial; strict runtime reader
must require three ordered distinct offsets1034/103c/1044, requested0, raw
read!=ffffffff, explicit equality-UNQUALIFIED, PLUS unchanged FW/INIT/version
checks. Reject extra/malformed/duplicate policy records; full receipts must
never become GPU/Metal proof. Adapt130_v3 synthetic fixture's dynamic payload
extent AND GMU location (original/v2 fixtures were stale). ONE coherent
temporary131 trial after all checks; preserve original130 rejected report.
No131 full build/image/reader/phone IO yet at THIS checkpoint. Phone TWRP;
130 manual/no-reset attribution unknown, no new UI/touch result. Whole goal
ACTIVE/incomplete. Original seven-line mkadt diff untouched, no flash/format/
GPT/destructive action. Codex critical code/review/Git; DSH compilation/tests/
boot in full-access headless relay mode, exact reviewed task only.

### 2026-11-07 — actual0130 captures RSC address readback82204514; native three-address policy next

DSH64473 ONE physical130 temporary boot: observer0/full verifier2, original
hardware-full-verification.json remains evidence-rejected. Start
2026-11-06T20:15:28.542239Z,finish20:17:45.340473Z; Send19088KB0.444s,
Boot0.134s,total0.580s, recovery observed135s. Unique recoverygauguin /
fastbootgauguinpro and routine recovery latch readback passed. Raw log
research/tmp/p3-gmuf-0130-native-observer-20261107.txt4046lines/454374B SHA
2f6298d4547211b759e8c8b8d64b49933a3a6ccde4ed7f7bb015d52602e7b2ef;
cycle991B SHA9c5335f0feece67aa7514c2212eb4e2854ad3f4a8efab1280de83614c6cac08c.
Same-boot CMDDB131072B SHA7506468c005bd57778fb2152806b81fc0bc00d3da8a14eb8a5508233cc2b6f49.

Real cold SMMU again completes131 mapped/140 ATOS, owned stream4/5 routes and
resume. GMF6/phase0,writes5,polls0,copy0/0,reset1,release0/OOB0; no firmware
execution or INIT/version ACKs. NEW physical row3937:
SWEET GMU FW READBACK: phase=0 check=1 window=1 off=01034 mask=ffffffff expected=00000000 actual=82204514
WindowAO03d8c000 yields PA03d8d034, native RSC HIDDEN_TCS_CMD0_ADDR. This is
the actual cached failed sample, not synthetic12340000. FSR400/400 has zero
named fault flags; no new hardware reset-cause, secure ownership or UI claim.
DSH65209 audit_failed_trial130.py actual0 -> failed-trial-audit.json state
bound-native-SMMU-complete-cached-firmware-READBACK, all inputs unchanged.
Strict reader SHA1a41e64b5ac68e67545046d0924080dc0c9afafd13f49153bd3aa8b377e29103.
Stage-subset evidence only; whole failed result kept. All handles CLOSED.

Address derivation checked against pinned native kgsl_gmu.c/gmu_core.c:
resource03d6a000 maps directly; raw rscc=reg_virt+23000 BYTES, then word0xd*4,
so current PA matches native path. Native19b63c8 a6xx_load_rsc_ucode performs
fixed zero writes to HIDDEN_TCS_CMD0_ADDR/+2/+4 with no equality requirement.
Neither native header nor upstream v6.12 XML documents per-bit echo semantics.
Do NOT invent a mask, claim these registers read-only, or infer a hardware
write failure solely from mismatch.131 proposed next: only these three fixed
zero address writes use explicit native-write/equality-UNQUALIFIED policy,
cache existing reads for logs, reject all-ones/IO/guards, retain every other
readback/TCM/reset/fault/ACK check. Validate original-model I/O equivalence,
focused negatives/all61 hosts and current130 xs5x0H native TUs before commit.
No131 code/build/phone yet. PhoneTWRP.130 manual reset attribution unknown;
older125/126/128/129 questions remain pending. Goal ACTIVE, no flash/format/
GPT, original seven-line mkadt diff unchanged.

### 2026-11-07 — 0130 complete local kernel/image/readers qualified; one physical cached-readback trial next

DSH46985 actual build0/qualification0, standard local gauguin.xs5x0H.
Captured HEAD38365e5fc8c0aaa69e05e6ed5651cfc10765aae4; source130 exact9eb26716...8a42b.
Installed kernel16905368B SHAec3fb0fa7e0428a1ab8104e0961317108735f38e8ad1e5fd1b994c2a0859b1d1,
IDxnu-911401120c7f4ba49496a32cb26052f1. Manifest SHA
3e91d339835249003566415ed620e26b616c6bdd84680a5780a57c20c7e5aca7.
Qualification SHA0c25505fba58b1fcd10df208d2be94e5faa9f6c918224b89b2b4b194ef183178,
retains every129 check plus cached_firmware_readback_diagnostics_linked TRUE.
Uses authoritative130 validation-result-v2.json SHA62e9f82199029ccc55ba68e720c312be2e1c5d44b6a22a3d365d435a28f92278.
Future native probes must use CURRENT130 xs5x0H recipe/source.
No CI build used. Sanitized public89f11c676099c7f7e155a4b4a8222ff6d81b15a9
pushed/verified on a45b92575fd3c5cf54d798480479f44396f75f62, nine text paths.

DSH60227 package0/independent review0, all pins unchanged. Image
shim/out/shim-p3-gmuf-0130-native-20261107.img19546112B SHA
3a8edd99f69ca099e26e6f628e0e5585fa36ba74ce3cf52f890227e3888bd194;
payload19218432B SHA5a6fc933eba086f6395a2c0c9a1dec94ae40e8d95779d80406eafacf12b5ee3b.
Evidence SHA0d2f36bbba597d0aee6bfe77270da879782795916866e314fa6524fe1816717e.
Unique sweettrial=gmuf-0130-20261107-a1,539bytes. Kernel grew16KiB, so
packaged source assets move16KiB: NVT182558000/MDT18257c000/GMU182580000;
same-kernel no-GMU control, all old assets/image pins and ten segments pass.

DSH8380 runtime tests clock0/FW0/full1: synthetic125-derived fixture retained
old PAS payload extent. DSH45243 v2 clock0/FW0/full1: extent corrected, but
synthetic old GMU asset marker was still stale. BOTH failures/logs/scripts/
inputs retained unchanged. No kernel or production verifier relaxation.
DSH6785 runtime_validate130_v3.py actual0/all inputs unchanged: clock4/95,
FW10/199,full explicitly SYNTHETIC4/20. v3 fixture adapts payload extent/input
and GMU source placement from actual130 package; tests reject stale fields.
Authoritative runtime-parser-result-v3.json has three actual zero exits and
pins previous failures. Strict verify_gmuf130.py requires new diagnostic flag
and rejects READBACK namespace in full-success traces. No firmware/GPU proof.

All these handles CLOSED. Phone last TWRP; boot130.py and run_hardware130.py
prepared for ONE image-pinned temporary boot, unique recoverygauguin / fastboot
gauguinpro, routine recovery-latch readback, unchanged180s observer/freshpull.
No130 phone IO yet. Next execute reviewed execute-hardware.txt via DSH, bind
fresh log/tuple and preserve strict full result. Whole goal ACTIVE, no flash/
format/GPT. Original seven-line mkadt diff still untouched.

### 2026-11-07 — 0130 cached firmware refusal diagnostics validated and committed; full kernel build next

Private code bffa9d9183e30ed86040e8ad8f7361e45d7bd5dd adds124th patch,
0130-gauguin-gmu-firmware-readback-diagnostics.patch. Fresh source130-codex
5282files SHA9eb267166486743bc70beaf015f91b01f59878f5242ccc40eda18d54c488a42b.
Only firmware.c/h and board.c differ from129. Private diagnostic cache records
the ALREADY READ failed comparison, including valid/phase/check/window/byte
offset/mask/expected/actual. Board prints it AFTER quarantine. Public receipt,
all predicates and I/O callbacks unchanged; no retry or new MMIO.

DSH46617 completed strict replay and all61 host files, then the wrapper raised
a Python TypeError in constructing the IO-comparison command. Original failed
report/logs retained. DSH65411 separate validate130_v2.py retained those TWO
completed components under original-report SHA72e9d3d3c7ca8bb95f75845f2d12507f0d6975553fa6fa5c642d338aa1feb752,
then actually ran THREE remaining IO/native steps, all0. The authoritative
research/tmp/dsh-0130/validation-result-v2.json is passed, inputs/source/base
unchanged. Future consumers must check3 results+2 retained_components, not5
results. GMF ASan/UBSan1,620,905 checks; board2840+87. Original129 fixture
versus130 has1,009,420 identical ordered I/O requests/digestf8383376e7a1a07b.
Both actual native firmware/board TUs pass with current129 DhXMEk recipe.
No130 complete kernel/image/device trial at THIS checkpoint.

Actual129 partial-stage audit now completed: DSH46617 audit_failed_trial129.py
returned0, failed-trial-audit.json state bound-native-SMMU-complete-firmware-READBACK.
All original input hashes preserved; uses unchanged strict-reader SMMU prefix
only and retains full-verifier rejection.131 mapped/140 ATOS and source-bound
owned routes/resume complete. GMF6 phase0 writes5/polls0,copy0,reset1,release0/
OOB0; no firmware execution/GPU/Metal. AO1034/PA03d8d034 requested0 is inferred
from the frozen fifth-store order; actual readback UNKNOWN until130 trial.
Synthetic fixture12340000 is NOT a physical observation.

Next: sanitized text-only public snapshot on a45b92575fd3c5cf54d798480479f44396f75f62,
standard local130 build/qualification with linked diagnostic format check,
independent pack/review, strict runtime readers, then ONE coherent temporary
fastboot boot. No source repair/manual objects/warning bypass. Phone last
observed TWRP after129;125/126/128/129 reset-attribution questions pending.
All previous handles closed; whole daily-use goal stays ACTIVE. Original
seven-line mkadt diff untouched; no flash/format/GPT or destructive action.

### 2026-11-07 — actual129 completes native SMMU; firmware ucode setup refuses fifth store;130 diagnostics being prepared

THIS turn is concrete progress.129 complete local kernel/image/runtime reader
qualified, then ONE real129 temporary boot completed cold SMMU publication/
micro-MMU resume and entered the native firmware initializer. Firmware has NOT
executed: engineGMF_READBACK6,phase0,only5writes/0polls,copy0/0,CM3reset1,
release0/OOB0. No GPU/Metal/daily-use qualification. Whole goal stays ACTIVE.

Private code10e5fe08fa701dc9dde0170130ff6d0f5728a58b/build-captured handoff
b5c8292775b97e34a463f799c3723edf8206c47c. Sanitized public
a45b92575fd3c5cf54d798480479f44396f75f62 pushed/verified, sole parent
5d1902606b86bd3d4d6b346959abe71e52026872, eight text files only.
DSH69004 actual build0/qualification0, standard local gauguin.DhXMEk,
source1298e914058...ee224/5282files. Kernel16888984B SHA
dcafffa973c764f4eb5c575434668e8a09e7766e0c870528124fd19fb3e0abd7,
IDxnu-c620dfcfb7c6434cb7f6be9911c77833; manifest SHA
ac3bb13f9799fade78468f111da83db02ad1b23d1d187d5396c04bad56dced16.
Qualification SHAd333f799910f250decf86000d42d4b3255cab26f79f3e2f000816e5ec5d027ed,
context_fsr_fault_mask_source_bound TRUE; no hardware FW claim from build.
Future native probes MUST use CURRENT129 DhXMEk recipe/source, not128lYYurL.

DSH64975 package0/review0, frozen inputs unchanged. Image19529728B SHA
bdd19cfeaa8e68f4df111cd68834333ee3e5c2ba352eb61b586f95ef33319421,
shim/out/shim-p3-gmuf-0129-native-20261107.img. Payload19202048B SHA
c202b9d42bf7a2f6d741c548a995c1a3c536e65f71d6a5ed5f1adb2461ccae0e;
evidence SHA2400956c611d795dd7dff1ab407878c282afb79089c2a7f24b3eb0038e808ca7.
sweettrial=gmuf-0129-20261107-a1,539bytes; same three pinned asset addresses.
Prior128 and all older pinned images preserved. DSH12182 runtime-reader0,
runtime-parser-result.json pass,clock4/95,FW10/197,full synthetic4/17,
all inputs unchanged. Strict verify_gmuf129.py SHA
9d6bc2cf8ef42475aac3e6ed9c29bb7e4461e88ff691bc00b821846d6a040bec,
requires source-bound FSR correction and all earlier full-success conditions.

DSH38009 actual observer0/full verifier2, original evidence-rejected report
preserved. Start2026-11-06T19:45:06.308841Z,finish19:47:18.054672Z,
Send19072KB0.449s/Boot0.134s/total0.585s, observed recovery131s. Product
gauguin/recovery,gauguinpro/fastboot and routine13-byte recovery latch verified.
Log has4046lines.131mapped/140ATOS complete; actual SID4slot0/CB0/ASID1,
SID5slot1/CB1/ASID2; TTBR user00010000aa20a000/aa20b000,kernel
00020000aa204000/aa209000. All five firmware narrow-map markers reached.
Actual GMB11/smmu0 then FW phase0/engine6,reset1,gx00222001,release0/oob0,
GFSR0,rawFSR400/400(no named fault flags),AO0/info0. Partialwrites5,polls0,
copy_issued0/copy_compared0,FW0/version0. Source-bound fifth store is AO
R(0xd):off1034,PA03d8d034,requested0, native HIDDEN_TCS_CMD0_ADDR. Its
actual readback is UNKNOWN. Do NOT replace it with synthetic fixture12340000.

Codex started130 metadata-only candidates under research/tmp/dsh-0130/combined:
gmf private valid/phase/check/window/byte-offset/mask/expected/actual cache for
every existing READBACK path (store32 and OOB-clear). Public receipt/predicates/
callbacks unchanged. Board logs cache AFTER quarantine. Host fixture edits
are present but NOT YET TESTED, no130 patch/replayed source/build/image/task
yet. Next finish strict129 partial-stage audit preserving full rejection, then
130 focused/full61 tests, original129-fixture IO-equivalence and real firmware/
board TUs using129 recipe; commit validated code. No need a mapping-only boot.
Phone nowTWRP; THIS129 reset question pending,125/126/128 also unanswered.
No new manual/no-reset, touch or UI claim. All completed handles above closed.
Original7-line mkadt diff untouched; no flash/format/GPT changes.

### 2026-11-07 — 0129 both context-FSR checks fixed; all61 hosts and two native TUs pass; full build next

Previous turn was concrete progress: real128 completed140 ATOS then refused
FSR400 (RO Format2). Sanitized public handoff5d1902606b86bd3d4d6b346959abe71e52026872
pushed/verified on3c5c862. THIS turn Codex authored129 core correction,
commit10e5fe08fa701dc9dde0170130ff6d0f5728a58b. New shared header constant
GSM_FSR_FAULT_MASK=c00001fe contains all documented MULTI/SS/UUT/ASF/TLB/
external/permission/access/translation flags, excludes generated Format[10:9]
and reserved bits. gsm finalize and gfw_faults BOTH use the mask. Raw FSR,
existing W1C writes, global-FSR check, context/CBA2R/TCR identity, all140 probes,
owner/deadlines/IRQs/CM3/GX guards and opaque06b68 limitation preserved.
READBACK diagnostic retains actual raw FSR and now reports the true fault mask.
No extra MMIO, retry, timeout, public receipt or success-log change.

Host SMMU and board models now generate AArch64 RO Format2 from CBAR/CBA2R.
Context W1C only clears writable fault bits, never SS or format. Tests exercise
all10 named fault/stall bits as sticky faults and clearable statuses, persistent
read-only SS and all-ones. Healthy firmware model keeps both raw FSR400 values;
old context-FSR reserved-bit0 negative case now uses actual TF bit1.
DSH21114 actual validation0: fresh123-patch source129-codex5282files SHA
8e91405840ef766a3d6f21328331ed74cd1160d440c103a4551f3c50163ee224,
only board.c/smmu.c/h differ from unchanged128 sourceea4f87af...20cbc. All61
host files PASS, SMMU3,540,699 ASan/UBSan checks; board2840+86. Two actual
ARM64 TUs compile with CURRENT128 lYYurL recipe. All inputs unchanged in
research/tmp/dsh-0129/validation-result.json. Same independent updated model
against original128 returns GSM7,mapped131/ATOS140; candidate129 returns GSM0,
mapped131/ATOS140. This proves the software regression, not129 hardware or FW.
DSH handle closed0. No129 full build/image/phone IO yet at this checkpoint.

Next standard local129 build/qualification, source-bound FSR-mask metadata,
pack/review and strict new runtime reader; ONE coherent firmware trial. Preserve
all128 rejected reports/raw proof. PhoneTWRP after128, no new phone IO this
milestone.125/126/128 reset attribution questions still pending; no manual/no
reset claim. Whole daily-use/GPU/Metal/RAM/storage/peripherals/high-refresh
goal remains ACTIVE/incomplete. Original user7-line mkadt diff unchanged.
No flash/format/GPT or destructive step. Codex core/review/Git;DSH execution.

### 2026-11-07 — actual128 completes all140 ATOS; final FSR check mistakes RO AArch64 Format2 for a fault;129 next

THIS goal turn made major concrete progress: actual126 ATOS132 refusal,
127 cached-PAR diagnostics and128 architectural decoder correction were
committed/tested, full128 native kernel/image/runtime reader qualified, then
ONE actual128 temporary boot completed all140 hardware translations. Final
SMMU publication/resume and firmware/GPU/Metal are STILL INCOMPLETE. Whole
daily-use/GPU/Metal/RAM/storage/peripherals/90–120Hz goal stays ACTIVE.
Code79aa204479ac089c1960e2da4dda2c4a56f8150c, build-captured/private handoff
8c8fe963e3303893daf88050277b81a26b320420. Sanitized public
3c5c86234d0c5476a0c1aba4632894257ede10e6 pushed/verified, sole parent
9398974ba5e6fa3fed1cb270045eefe07fb78af6, nine text paths only.

DSH45658 actual build0/qualification0, standard local build/dSYM/strip/install
gauguin.lYYurL; exact tested122-patch sourceea4f87af...20cbc/5282 files.
Kernel16888984B SHAe06db5df7966dc2dd05b17874d998fad02376a17c4e4579248c05c03040a4beb,
IDxnu-54965b2965ed4622bd8cdeffa0ca48d5; manifest SHA
1c18fafebd16947e5c550ee879710d262bde77268efc3bca5ee15b663aef2308.
Qualification p3-native-0128-qualification-20261107.json SHA
0dd821218f72ccbc08fa69a1fc39ebfef11c6e02aaee0069075824d472112205,
retains126 provenance/SDK/install/symbol/archive checks plus actual linked
ATOS-level diagnostics; architected_smmu_fault_format_linked TRUE, hardware
firmware qualification FALSE. Future native probes must use CURRENT128
lYYurL source/recipe, not126 EXvD1e after shared generated Makefile replacement.

DSH75952 package0/review0, package-review-execution-result.json passed/all
inputs unchanged. Image shim/out/shim-p3-gmuf-0128-native-20261107.img19529728B
SHA1ed47463d68dbfe719a95b978a38860ce6604ea8435b95b17c1adf58227d2879.
Payload19202048B SHAd699ce30f3f9a1fc740e752f4b019ae6ac81278e85fe82e2738506bf716582a6.
Evidence SHA659e19a70a92f16e124edef8ceb5cc19c09529421a1b6b0ddd3c29d062bd8d8d;
sweettrial=gmuf-0128-20261107-a1,539-byte bootargs. Independent10 native
segments/wrapper/ADT/2MiBzero-tail/three-asset checks; old126/125/124 and
older baselines intact. NVT182554000/MDT182578000/GMU18257c000 are packaged
source addresses. No code/object repair, warning bypass or system install.

Codex strict verify_gmuf128.py SHA
1b8cc045bdf7c81d88f362237cfd3aa23108baa06555fc475f33a8bd2568d0a9
requires exact source/marker + qualified architectural decoder, rejects new
ATOS-failure namespace, retains every earlier full-success requirement and
opaque-fields bitwise UNQUALIFIED scope. AST digest comparison confirms ONLY
source SHA differs from126: same four asset pins. DSH2517 runtime-parser-result.json
passed/all inputs unchanged, clock valid4/rejected95, FW valid10/rejected196,
full SYNTHETIC common+FW trace valid4/rejected17 with actual128 artifacts.
These host records alone are not hardware proof.

DSH9061 actual observer0/full verifier2. ONE temporary128 boot: Send19072KB
0.443s/Boot0.135s/total0.580s; start2026-11-06T19:20:24.510332Z,
finish19:22:36.287794Z, observedTWRP130s. Unique recoverygauguin / fastboot
gauguinpro and13-byte routine recovery-latch readback passed. Fresh3993lines/
449087B log SHA240e6988aa35c7989f41e5fbbef70e7f844a8f9212031ec33d85d62b5aa6e663;
991B cycle SHA57e95646be961586a9688b8eeecf19a0273092f916875f044dacb5abdd2db9eb.
Same-trial CMDDB131072 SHAe8554cbaeebcb4092d1e58fffe76ed328c953e49542567f411df6da92c7defdd.
Original hardware-full-verification.json remains evidence-rejected. DSH53845
audit_failed_trial128.py actual0 -> failed-trial-audit.json, all original input
hashes unchanged; binds image/banner/marker/source and actual140 counter.

Actual first refusal line3925 GMB9/GSM7=READBACK. phase8/check6/final context
fault, off08058(PA03d48058,first owned bank0),maskffffffff,expected0,actual400.
Cached writes187,polls144,ATOS140; id48016605/20008005/00007511,
cr0before00200626/after00e01e36,microbefore2378/afterUNSET0,IAS39/OAS36.
Source-bound phase8 implies all131 positive leaves and9 correctly typed/leveled
negative probes accepted; individual successful PAR values not raw-logged.
No ATOS rejection row. Opaque06b68 requested9a82a382/read0a800082 still
bitwise UNQUALIFIED. Final first-bank FSR check happens BEFORE owned route
publication/resume, so do not claim complete SMMU or any firmware execution.

Primary Arm IHI0062D.c16.5.9 pp16-299/300 visually checked in the same pinned
PDF5f12c28c...ca7e9d. FSR Format[10:9] is READ-ONLY, generated from CBA2R.VA64
and TCR.EAE;400 means AArch64 Format2, not a fault. Named fault bits union
c00001fe (MULTI31,SS30,UUT8,ASF7,TLBLKF6,TLBMCF5,EF4,PF3,AFF2,TF1) gives
ZERO for observed400. Native pinned arm-smmu-regs.h FSR_FAULT and driver
checks agree. Full-zero FSR comparison is a second definite software bug;
W1C cannot clear generated RO format. Exact126 PAR remains unknown, not
reconstructed from128's successful probes. Independent reset cause unproven.

Next129: use documented fault-bit masking in BOTH gsm finalize and gfw_faults
context checks (currently rejects any nonzero FSR too). Preserve raw FSR;
GFSR remains a separate register. Keep SS/real-fault/all-ones refusals, context
configuration verification and all140 probes. Model generated RO Format2
after context setup with W1C fault-only semantics; update old host negative
case injecting context FSR bit0 (reserved) to actual TF bit1, and add readonly
format/stuck fault/real fault variants. Independent updated model should
reproduce128's final failure then let129 proceed; native compile against128
recipe, all61 tests, then full129 build/package/readers/ONE coherent FW boot.
No129 code/build/image/task exists yet. No need another mapping-only boot.
Phone nowTWRP. THIS128 autonomous/manual question pending,125/126 also
unanswered; do not reuse124's explicit answer. No128 touch/UI claim beyond
raw process markers. All owned handles closed. No flash/format/GPT changes.

### 2026-11-07 — 0128 architected PAR decoder passes independent regression, all61 host files and two native TUs

THIS turn is concrete progress: actual126 stopped at ATOS132;127 diagnostics
committeddf9e6c2098e13d3b68e4a3cea2a22ed72f18d1f6; primary Arm fault-format
bug identified and128 correction committed79aa204479ac089c1960e2da4dda2c4a56f8150c.
No127 full build/image/phone trial was spent. Exact real126 PAR remains UNKNOWN;
do not retroactively invent it from the architectural model. PhoneTWRP after126;
THIS126 and125 reset-attribution questions still pending. Full goal ACTIVE.

128 accepts a hole only when documented SMMU PAR fields show S1,generated
AArch64 Format2,F1/TF1,other named fault flags0 and the exact expected PLVL.
Mask0x0000000ba00003ff comes from IHI0062D.c16.5.14, not a hardware readback.
Reserved bits are ignored. First four kernel holes must be L3, last two L1;
all three empty user roots L1. Positive physical-address checks and131+9
probe list unchanged.127 cached rejected PAR/IOVA/stream/bank/mapped fields
retained, plus requested expected level in128. Opaque06b68 fields still
bitwise UNQUALIFIED; no other acceptance, MMIO, clock, owner or retry change.

DSH95172 actual validation0: fresh122-patch source128-codex5282files SHA
ea4f87af1ec6eeb3f0ebbd1bcb27eb15325b319b6b8d2410512f1e815dd20cbc,
only board.c/smmu.c/h differ from frozen127. All61 host files passed, SMMU
3,509,619 ASan/UBSan checks including20 wrong mapped/hole variants; board2840+75.
Both actual128 ARM64 TUs compiled against CURRENT qualified126 EXvD1e recipe.
Independent software page walker generates SMMU PAR flags/level from actual
missing descriptors. Same model against ORIGINAL127 code returns GSM9,
mapped131/ATOS132; against128 returns GSM0,mapped131/ATOS140. This proves
the software predicate regression, NOT real126's missing PAR or GPU readiness.
Unlike diagnostic-only127,128 intentionally changes hole acceptance, so no
unchanged128 IO-sequence claim. Source127 unchanged; all current128 input pins
unchanged in research/tmp/dsh-0128/validation-result.json. DSH handle closed0.

Next standard full128 local kernel build/qualification, preserving every126
provenance/defined-symbol/archive check plus actual linked ATOS-level diagnostics
and new fault-decoder source pin. Then package and strict unique128 runtime
reader with ATOS-failure namespace rejection, no relaxation of140 checks or
fresh FW/INIT/version replies; ONE temporary boot. No128 build/image/phone IO
yet at this checkpoint. Preserve124/125/126 raw failures and all old images.
Keep recovery/bootloader/modem/persist/backups and original7-line mkadt diff.
No format/flash/GPT changes. Codex critical code/Git/audit, DSH execution.

### 2026-11-07 — actual0126 reaches ATOS132;0127 cached-PAR diagnostics tested; architectural decoder bug found

Previous turn was progress: source126/image/full reader qualified, public
9398974ba5e6fa3fed1cb270045eefe07fb78af6 Notes handoff pushed on944f4c3.
THIS turn DSH51951 actual observer0/full verifier2 after ONE exact126 temporary
boot. Send19072KB0.441s/Boot0.134s/total0.578s; started2026-11-06T18:56:27.811355Z,
finished18:58:39.602999Z, recovery131s. Identity/latch checks passed. Phone now
TWRP; THIS126 autonomous/manual attribution question pending, do not reuse124
or still-pending125 answer. No flash/format/GPT, GPU/Metal still unqualified.
Raw4014lines/451228B SHA356a6184377b1062493084d0d73e5311bda7477545e7d478d206a7db2fc5aa2f;
same-trial CMDDB131072 SHA32333cf7c607ca244c90ccc9b8f05c420bb9e1354a7bc3b526dfe29bf940dd95.
Original hardware-full-verification.json stays evidence-rejected. Separate
audit_failed_trial126.py / failed-trial-audit.json binds actual image/banner/
marker/source/CMDDB and exactfailure, all original inputs unchanged.

Actual GMB9/GSM9=TRANSLATION, phase7/check0/unset zero comparison tuple,
id48016605/20008005/00007511, cr0before00200626/after00e01e36,
microbefore00002378/afterUNSET0, IAS39/OAS36,writes178,polls136,ATOS132.
Opaque06b68 requested9a82a382/read0a800082 remains bitwise UNQUALIFIED.
Pinned source loop has131 positive leaf checks before holes, so counts/phase
infer first131 accepted and failing IOVA0. This is source-bound inference,
not a logged PAR or explicit mapped counter. Exact126 PAR is UNKNOWN. No final
SMMU route publication/resume or firmware path occurred. PMIC cause unproven.

Codex authored127 diagnostics only in board.c/smmu.c/h: retain already-read
rejected PAR, expected address, stream/bank/IOVA and prior mapped count in a
private sample; log after quarantine. No extra MMIO, changed hole predicate,
timeout, retry or public receipt. DSH74220 audit0 + validation0: fresh121-patch
source127-codex5282 files SHA
971a22d0d851f9ffe5462f8df725707bbeac39b3496aaad04486d58018e4c232,
all61 host files, SMMU3,491,581 ASan/UBSan checks, board2840+75, both actual
ARM64 TUs against CURRENT qualified126 EXvD1e recipe. Baseline126 unchanged.
Original126-fixture IO trace6,497,973 callbacks/equal digestf4c607ba64593379.
No127 full kernel/image/device trial. All current handles closed.

Primary-source research found a DEFINITE software error in old hole predicate:
SMMU PAR does not use CPU-style six-bit FST. Arm IHI0062D.c16.5.14 pages16-308/
309 defines separate F/TF/AFF/PF/EF/TLB/ASF/ICF/ATOT flags, format[9:8],
PLVL[33:32],STAGE[35]. Downloaded official public PDF2344855B SHA
5f12c28c3a449381913112ac15cc914cfe2ea1a98ce3685f3ef079b247ca7e9d,
ignored research/tmp/dsh-0127/arm-ihi0062dc.pdf. Read both full rendered pages
with bundled PDF runtime; no system installation. This source proves the
predicate bug, NOT the missing real126 PAR or sole physical failure cause.
Next128 should keep127 diagnostics, replace ONLY hole decoding with documented
S1/AArch64 pure TF and expected table level, update independent host walk
model, retain every mapped/foreign-route/fault/lease check, then full build and
one real128 boot. No need to spend a127 diagnostic-only boot first. Do not
invent observed PAR or relax to any fault. Whole daily-use goal ACTIVE.

### 2026-11-07 — 0126 complete local native kernel/image and strict full runtime reader qualified; exact boot next

THIS goal turn made concrete progress: physical125 failure identified at
06b68, tested126 experiment code156a62d/handoff0095fb1 committed. Sanitized
public944f4c306e26f1acd34a9bfe5f0cd4ea51c982ad pushed/verified, sole parent
a8a7c783630911290cab6b5d0749b80bd161297d, eight text paths only. Full daily
GPU/Metal/RAM/storage/peripherals/90–120Hz goal stays ACTIVE/incomplete.

DSH73504 actual build0/qualification0 in gauguin.EXvD1e, captured private
0095fb1459db23bf98ef5e73b99bb235468ee165. Standard local native kernel,
dSYM/strip/install; exact tested120-patch source258f3be2...d5b16/5282files
unchanged. Kernel16888984B SHA
67769371585373600431fbc7d431fbed6547c92828adb750f6b62db3b82cb787,
IDxnu-d3768bb45ecf441eacedf9efa2c6d78a. Manifest SHA
7fc5ff0a1a34c335149b5146a3a7dbaef1ee66a64d2ef4a5ef977a7ae32a2078.
Qualification p3-native-0126-qualification-20261107.json SHA
2b97bc05c035ceb0910b1305a9b85ba6ea117564bc2f8aa2a9ff5a5b6ebd6864,
retains every120 provenance/SDK/install/defined-symbol/archive check plus20
GMU symbols/six native members, actual linked failure and opaque-policy strings.
Both cached_smmu_diagnostics_linked and opaque_implementation_write_policy_linked
TRUE; firmware_hardware_qualified FALSE. Future single-file probes must use
THIS126 EXvD1e recipe, not125 zy6VU9 after shared BSD Makefile replacement.

DSH26111 packaging first attempt actual1 BEFORE packaging: Codex wrapper
retained two old125 filenames. Original script/log preserved. Separate reviewed
package_and_review126_v2.py / DSH5580 actual package0/image-review0; frozen
package-review-execution-result.json passed, all inputs unchanged. Native
kernel/source never changed. Image shim/out/shim-p3-gmuf-0126-native-20261107.img
19529728B SHA4f607d193827a7d43a5b1dc3f655158e54fe23154723f2f317d163eb4b53f4c6.
Payload19202048B SHAd4ba078ee5a744a5f54617e43036321f6cda67031573f6bed782f05815e5439b.
Evidence SHA86fd98432a8c2f59ade9bec9e3b3e5f21ce59fa6cb0fa867a9c4fe70cd6c5db4;
unique sweettrial=gmuf-0126-20261107-a1,539-byte bootargs. Independent review
checked actual10 kernel segments, wrapper/ADT/PAS2MiBzero tail and three assets;
NVT182554000/MDT182578000/GMU18257c000 remain source package addresses.
Prior125/124/120 and older pinned images preserved. No126 phone access yet.

Codex strict verify_gmuf126.py SHA
83f47a62a9b8d4cd002cd6dcfec622737a59c3af3e131a3cf3dd12317760d8dc
requires exact new source/marker and qualified opaque policy, unique ordered
IMPL row requested9a82a382 with non-all-ones readback, mandatory140 ATOS and
all earlier contexts/routes/fault/clock/CMDDB/ARC/asset/INIT/version checks.
Opaque readback is explicitly bitwise_qualified FALSE, even on full success;
zero/non-echo values are never treated as known masks or qualified fields.
Original full-firmware rejection policy remains; GPU/Metal still not qualified.

Initial runtime-parser-result.json failed before record checks because Codex's
script migration accidentally changed MDT SHA constant. Initial verifier saved
as verify_gmuf126.initial.py; original failure/logs kept. Restored exact original
MDT pin; AST digest comparison confirmed ONLY source SHA differs from125.
Separate v2 failed ONLY the full host fixture's stale-banner negative case:
fixture called record-only helper without production main's preceding banner
check. Saved verify_full126_host.initial.py and v2 report; corrected HOST parse
seam to apply existing main identity check. Production verifier/native/image
unchanged by that fixture fix. DSH24797 runtime-parser-result-v3.json PASS,
all inputs unchanged: clock valid4/rejected94; FW/SMMU/opaque valid10/rejected194;
full SYNTHETIC common+firmware trace valid4/rejected17 with actual126 qualified
artifacts and actual125 stale-runtime rejection. These are NOT hardware proof.
All owned build/package/parser handles closed. Only original7-line mkadt diff.

Phone remainsTWRP after125. THIS125 manual/autonomous question is pending;
latest user explicitly answered124 only. Do not reuse attribution across trials.
Next prepare ONE exact126 temporary boot from reviewed125 boot wrapper/body,
using runtime-parser-result-v3.json, current image/hash/head and distinct
recovery productgauguin / bootloader productgauguinpro. Read back routine BCB
recovery latch; no flash/format/GPT. Bounded observer then strict full126 reader.
Keep strict rejection if new stage fails. A separate126 failed-stage reader,
if needed, must account for opaque sample/order and must never label failure
as firmware success; do not blindly reuse125 diagnostic grammar. Preserve raw
logs and original125 proof. Ask THIS126 reset attribution only for an actual
new boot. Keep current experiment's undocumented-field limitation explicit.

### 2026-11-07 — 0125 physical failure identified; 0126 native-write experiment passes61 host files and two native TUs

Previous checkpoint was progress:125 complete local kernel/image and strict
runtime readers qualified. THIS turn DSH48522 closed0 after ONE actual125
temporary boot: Send19072KB0.447s/Boot0.134s/total0.583s, start
2026-11-06T18:31:35.476737Z, finish18:33:47.526698Z, recovery131s/observer0.
Unique recovery productgauguin / fastboot productgauguinpro and13-byte routine
recovery latch readback all passed. Phone nowTWRP. No flash/format/GPT change.
Strict hardware-full-verification.json remains evidence-rejected/exit2.
Separate hardware-diagnostic-verification.json exit0 means ONLY a verified
failed-predicate capture, never firmware/SMMU/GPU success. Original logs kept.
Fresh4026lines/450423B p3-gmuf-0125-native-observer-20261107.txt SHA
63098de2bf563afa83a3392f57622140f8659ab04ef2d00a46b1f0517ce7cdc1;
991B cycle SHAea28838a95260deb510fc30a65555c60e5feb453f08ef34587de0ab958a2208e.
BuildIDxnu-35e8ee3b79544eba9a9ed80d8d3bccb3, gmuf-0125-20261107-a1 and
e545fa47...541c9 image match the qualified125 package. Same-trial CMDDB131072B
SHA64dfc9cee0e4f102ebe6a8381ada050f91ddd7aada4477a7b85ffdbfb909f5cc.

Exact real failure: phase4/global check1/store32 off06b68, PA03d46b68,
mask00000000ffffffff, requested000000009a82a382, actual000000000a800082.
Cached id48016605/20008005/00007511, cr0before00200626, microbefore00002378,
IAS39/OAS36, writes13/polls1/ATOS0. Zero after fields are UNSET, not observed.
Contexts/ATOS/firmware path had not started. Not the synthetic6960/3f example.
THIS125 autonomous/manual attribution question is pending; do not reuse124's
answer. Latest user reply explicitly confirmed124 only. PMIC cause unproven.

Pinned native arm-smmu.c19b63c8 lines4766–4771 writes DT attach-impl-defs
without readback-equality checks. Actual device DT has06b68/9a82a382. Neither
source documents bit masks: no claim that the missing bits are reserved,
write-only or secure. Codex authored0126 native-write experiment, code commit
156a62d7b34246c43ec84ff2d0de111124338edd: only06b68 uses exact native write
and SAME guarded write/barrier/read sequence, retaining raw readback without
per-bit acceptance. No write-value tuning/mask invention/retry/other predicate
change; all-ones and callback/owner failures still stop. Unknown opaque write
effects remain UNQUALIFIED even if later ATOS passes. All other controls,
fault checks and140 ATOS stay mandatory. Private cached sample logs after
failure quarantine or with SMMU receipts before firmware windows on success.
Public success receipt unchanged. Full daily-use goal stays ACTIVE/incomplete.

DSH71985 actual validation0: strict fresh120-patch source126-codex5282 files
SHA258f3be295363d721df43229f210a7322f71ce0ef6e3b1be833d4ec4236d5b16,
only board.c/smmu.c/h differ from frozen125. All61 host files passed, SMMU
3,482,273 ASan/UBSan checks incl2541 callback failures x echo/non-echo and
independent architected-control/ATOS refusals; board2839+75 cases. Original
125 frozen fixture baseline/candidate3,259,083 IOcallbacks identical digest
b627036027cd4225. Both real ARM64 TUs compiled using CURRENT qualified125
gauguin.zy6VU9 manifest/recipe; no manual objects or warning bypass. All input
pins/source125/source126 unchanged in research/tmp/dsh-0126/validation-result.json.
No126 full build/image/boot yet. Next standard local126 kernel build, strict
qualification/package/runtime reader with explicit opaque-field limitation,
then ONE exact temporary boot. Preserve all125 rejected proof and oldimages.
User mkadt original7line diff untouched. Codex core/Git/audit; DSH execution.

### 2026-11-07 — 0125 complete local kernel/image and both runtime readers validated; diagnostic boot next

Previous goal turn made concrete progress: ONE124 real trial failed at SMMU
READBACK and source125 cached diagnostics were committed95e8574/handoff5aca48b,
sanitized publica8a7c783630911290cab6b5d0749b80bd161297d pushed/verified.
THIS125 full native build/dSYM/strip/install and qualification both actualexit0
in gauguin.zy6VU9, captured private5aca48b0a41cdf56ec1c05a8fbdc01db72cda644.
Exact host-tested119-patch sourcef5376027...b4fda/5282files unchanged. Standard
build only; no CI, manual object repair, warning bypass or stripped substitute.
Same20 required symbols/six GMU archive members verified. Both new failure
format strings are present in the actual installed kernel. DSH68845 closed0.

Kernel16888944B SHA8e4c8c07b7c4878f8a1e5b03dea054a81f953e469bc86b898a696546b10fae5e,
IDxnu-35e8ee3b79544eba9a9ed80d8d3bccb3. Manifest SHA
128ed162c445a6a303ed574df332e7757d4b6aaf8ff5e5555bf3a66648c6fd32.
Qualification p3-native-0125-qualification-20261107.json SHA
0c760267d5d2dd337c37a457cb339d37fb3818cff7045080eb2c886687250e7d.
DSH59884 package/review both actualexit0; image-parent-review.json PASS and
package-review-execution-result.json passed, frozen inputs unchanged.
Image shim/out/shim-p3-gmuf-0125-native-20261107.img19529728B SHA
e545fa47d44388de435d7d0dd082823329203a32923c51d2e2cab176f00541c9,
539-byte bootargs, unique sweettrial=gmuf-0125-20261107-a1. Three source assets
retain NVT182554000/MDT182578000/GMU18257c000; all older image pins intact.

Codex prepared strict verify_gmuf125.py (SHA0114ea671ac472fb15a2708829605c0603705fa289ce31384214b133cc3f34a5)
with exact new source/marker and required linked diagnostics; prior full-FW
success checks remain. Separate verify_smmu_diag125.py (SHA5bc9f65e9c106a8edd1cedbeea147a25f95a9d738b7208055fd75fd667044d28)
verifies ONLY a failed predicate capture: typed phase/check/offset/mask/value,
native geometry/widths, source bounds and exact refusal/quarantine order,
same-trial asset/CMDDB/image identity. CONFIG is a CPU field, not an MMIO
offset. It always reports SMMU/FW/GPU/Metal completion FALSE and preserves
the strict full-verifier rejection. Zero after fields remain unqualified.
No parser relaxation that labels a failed SMMU transaction as successful.

DSH33149 runtime-parser-result.json PASS, all pins unchanged: retained full
clock/FW suites plus separate diagnostic valid8/rejected60, including an
explicitly synthetic full trace with ACTUAL125 package binding and stale124
runtime rejection. These are HOST tests, never125 hardware evidence.
No125 phone access/boot yet at this checkpoint; last phone stateTWRP after
user-confirmed autonomous124 recovery. Next exact125 temporary image boot,
using recovery productgauguin / bootloader productgauguinpro separately;
read back the non-destructive recovery BCB request before switching modes.
Then unchanged bounded observer body and strict full verifier; if rejected,
separate diagnostic reader must capture the exact failing tuple. Never infer
it from the synthetic6960/3f formatter example. THIS125 reset attribution is
still required separately. Full daily-use/GPU/Metal/RAM/storage/peripherals/
90–120Hz goal remains ACTIVE/incomplete. No flash/format/GPT changes.

### 2026-11-07 — 0124 actual trial stops on SMMU READBACK; autonomous131s recovery confirmed

Previous turn was progress:124 complete native kernel/image plus sanitized
publicebb3abcaf4f3e76125009d7ce20d828d263a170c. THIS turn completed the strict
runtime verifier and ONE actual temporary124 image boot. No firmware/GPU/Metal
qualification: original hardware-data-verification.json is evidence-rejected,
actualexit2, because line3865 says GMB9/GSM7 (SMMU READBACK). CM3 reset1 was
observed before SMMU access. SMMU did not complete; firmware/TCM/OOB/HFI path
was never entered. Do not guess the failed register or weaken its mask.

Real boot from restored fastboot: Sending19072KB0.444s/Booting0.134s/total0.585s.
Started2026-11-06T17:37:43.972045Z, finished17:39:56.096630Z; observerexit0,
backTWRP131s. Exact xnu-3cd3c8e985a94570bdd8c654f4515c98 and
gmuf-0124-20261107-a1, image7f156ffd...066bc match qualified124 artifacts below.
Fresh4036-line/452276B p3-gmuf-0124-native-observer-20261107.txt SHA
6a211e7b4de82f3845e4acb61c6514a5fd4ea3de59dd287847babbb965492464;
ready-v2 cycle991B SHAad6cd1dc8b81081bbaf94596b85fd63b1b1efb60fa374bac1bec68d129d1d5a8.
Same-trial CMDDB131072B SHA2c507d183626004b8b2e4ac3268f226f88b298c58424790b87bdf1d83e005afe;
all four exact ARC policies independently decode correctly. Prior clock receipt
directly logs configured200MHz/direct6/holds2/polls6; this failure audit does
not silently turn partial earlier-stage records into full technical success.

User explicitly answered THIS trial's call_6f46b6d16f3f4b198c44e84355e9ee43:
“是，自行重启，我没有操作”. DSH97775 generated failed-trial-audit.json,
binding/rechecking all original inputs, actual banner/image/marker/CMDDB/cycle,
stage failure and user attribution. All inputs unchanged. Autonomous recovery
is confirmed; independent PMIC/reset cause remains unproven. Original rejected
report and unknown-attribution observer record remain unchanged. DSH63096
terminal0, inner observer0/verifier2; DSH CLI status alone is not success.
Phone nowTWRP; no touch-regression claim is made. Full goal ACTIVE/incomplete.

Two SETUP failures preceded the sole actual boot and must NOT be counted as
kernel failures. First setup adb recovery/product passed, issued recovery BCB
request and reboot-bootloader, but fastboot absent for60s; observerexit1 and
NO fastboot boot. User then confirmed fastboot+USB replug. Read-only inventory
found one fastboot device, vendor18d1/productd00d. Second ready setup stopped
BEFORE cycle creation because Codex incorrectly required fastboot product
gauguin. Actual bootloader product is exactly gauguinpro; TWRP product is
gauguin. fastboot-product-audit.json records the fresh exact query; do not
conflate these two strings. Third setup fixed only that guard and used the
unchanged observer BODY from tools/sweet-observe.sh, with already-fastboot
entry and explicit exit on fastboot-command failure. Both earlier reports/logs
preserved; setup-failure-audit.json source-binds verified-not-booted. No flash,
format, GPT change, retry of an actual image boot or new user approval needed.

### 2026-11-07 — 0125 cached SMMU failure diagnostics pass focused checks and all61 host files

Code commit95e85743901230c6d9491d2dc292fcb9385fdcf8. Codex authored three
native changes under research/tmp/dsh-0125/combined:
gauguin_gmu_smmu.c/.h and gauguin_gmu_board.c. Private diagnostic adds stage,
comparison kind, byte register offset (CONFIG uses field index), mask and exact
expected/actual from every existing READBACK failure. Config mismatch identifies
which of nine fields; store32/64, invalid poll, fault, final route/control and
micro-MMU mismatches retain their original predicates/results. No added MMIO,
callback, timeout, register mask/value, retry or public-receipt change. Cached
identity/control/counts log AFTER board/WDT quarantine. Zero not-yet-filled
after fields are not observations. Synthetic fixture6960/3f is ONLY a formatter
test; it is NOT the124 failed hardware address/value. Exact real address is
still UNKNOWN until the next diagnostic-enabled real trial.

diagnostic-validation.json: SMMU1,741,165 ASan/UBSan checks and board2839+75
cases PASS; independent ORIGINAL-fixture comparison of124/candidate passes
3,257,598 callbacks with identical request digest613f7c79ae2e7d66. Native probe
then rejected OLD120 reference recipe before compilation because124's full
build replaced shared generated BSD Makefile. Original report/log kept. No
source change or guard bypass: separate diagnostic-validation-v2.json PASS
uses CURRENT qualified124 gauguin.dNjjd4 manifest/source124, both actual SMMU
and board ARM64 TUs; three host components retained only after all input pins
rehash. DSH13551 terminal0. Future probes must use the current qualified recipe,
not stale gKuZ8y metadata.

119th patch0125-gauguin-gmu-smmu-failure-diagnostics.patch prepared, strict
fresh replay source125-codex5282 files SHA
f537602732d8e5701eca2aa17a518cdc44b85b5ee64dc501d339f11429cb4fda;
three native paths exactly equal reviewed bytes, source124 baseline unchanged.
DSH83628 finished actualscript0: all61 host files PASS, tested source and124
baseline unchanged in replay-full-host-result.json. Handle closed0. No125 full
kernel/image/boot task exists at this checkpoint. Sanitized publication is
recorded in research/tmp/dsh-0125/public-snapshot-0125.json when pushed;
sole public parentebb3abcaf4f3e76125009d7ce20d828d263a170c, not private ancestry.
Next one full125 local build/package/review and strict diagnostic-receipt
verifier before temporary boot. Preserve124 failing hardware proof unchanged.
Default coherent firmware initializer remains; do not spend a mapping-only boot.
Codex authors/reviews/interprets; DSH executes scripts with full access.

### 2026-11-07 — strict0124 runtime verifier validated; first coherent firmware trial next

Previous goal turn was concrete progress: codea263288/privatec514be5, public
ebb3abcaf4f3e76125009d7ce20d828d263a170c pushed/verified (soleparent713a869aa...).
Full goal remains ACTIVE/incomplete. Native/image bytes from0124 remain frozen.
No device IO in this verifier milestone; highest hardware still0120.

Codex authored research/tmp/dsh-0124/verify_gmuf124.py SHA
14b87de117ad7d1b3dd9f76d64e0b724ee3cd39c30682ef4b88504436193a351.
Retains120 identity/image/CPU-stage/CMDDB/WDT/BCM/CX/clock checks, updates only
exact124 source/flag/terminal and adds exact four-ARC policy, actual pinned GMU
segment binding, capability-derived SMMU geometry/dynamic banks/ASID/roots,
131mapped/140ATOS, fixed narrow maps, reset/copy/OOB/HFI INIT+version receipts,
NS masks including core332 and source-derived counter bounds. Rejects missing/
duplicate/stale/failure/extra/out-of-order records. Distinguishes configured
clocks, GMU firmware/ACKs and GPU/Metal/normal HFI_ON. No hardware claim from
host records. Per-access guard/fault details are honestly SOURCE-bound control
flow, while raw contexts/ACK/final-state fields are directly parsed.

DSH72322 original runtime-parser-result.json FAILED only because the host
mutation selector sctlr=00c01067 matched both contexts, not one. Codex narrowed
the selector to the user context; production verifier/native source unchanged.
Original report/logs/verify_fw124_host.initial.py retained. Separate DSH50269
runtime-parser-result-v2.json PASS, all input pins unchanged: retained clock
valid4/rejected93; firmware/SMMU valid8/rejected185 plus ACTUAL qualified-package
binding and metadata-negative cases. Actual GMF+GGH model separately compiled
with sanitizers:1,617,941 checks,1385 failure boundaries; debug0 writes82/polls5/
messages0 and debug1 writes84/polls5/messages4. Those are host model results.
Verifier bounds82..142stores/5..5000polls/0..90debug are independently derived
from fixed source, not tuned to hardware. Native driver/image need no rebuild.

Codex also rechecked pinned native arm-smmu.c lines5448–5457: ID1NUMPAGENDX2
with4KiB registers gives CB base+8000 and total10000; existing geometry is
correct (no source change). Next ONE bounded temporary boot of the exact
7f156ffd...066bc image below, then read fresh logs and run strict verifier.
Require a separate THIS-trial reset attribution; never reuse0120's answer.
DSH executes reviewed boot script, Codex interprets. Preserve all baselines,
original mkadt diff and all rejected evidence; no flash/format/GPT changes.

### 2026-11-07 — 0124 full local kernel/package/independent image review PASS; runtime verifier next

Codea26328873f64b0ffb55e18408e9e29db54d8d49e, build-captured/handoff commit
4803df62ac1d14b7f0e1c84cc8516b4206054f5b. Normal local build/dSYM/strip/install
and extended strict artifact qualification both actualexit0 in gauguin.dNjjd4.
No CI run, manual object repair, substitute stripping or warning bypass. Source
is the exact118-patch5282-file host-tested54ead7a4...19f92 tree below; full61
suite was already passed, so standard builder SKIP_TESTS1 was explicitly gated
on unchanged test/source evidence. Kernel includes all20 new required defined
symbols and exactly one of each actual memory/HFI/SMMU/board/asset/firmware
archive member. These are BUILD proofs, not firmware/GPU hardware evidence.

Native installed kernel16888944B SHA
07670bfbd5f68272b3d9d5a2b61f9e36bb2056477ed552cf86a721529956c2bc;
IDxnu-3cd3c8e985a94570bdd8c654f4515c98, Nov7 01:00:07CST banner. Manifest SHA
3fa3202837ffa37db8526acb47d030324ddfb5a94b388c56a3aee2719d6eb096.
Artifacts under .deps-cache/p0-20261105/build/runs/gauguin.dNjjd4/install and
research/tmp/p3-native-0124-20261107-out. Qualification
research/tmp/p3-native-0124-qualification-20261107.json SHA
54465cb56bbe8d4d55e657e25871926749a2a70bd11abb587081b02d3704405b;
DSH41408 terminal0 and native124-execution-result.json qualified-not-packaged.

Subsequent separate DSH1772 package+independent review BOTH actualexit0,
package-review-execution-result.json passed/inputs unchanged. Image
shim/out/shim-p3-gmuf-0124-native-20261107.img19529728B SHA
7f156ffd38f1b8d0b999734ca2410394e50548885531a902082ddd66460066bc;
payload19202048B SHA
0e1f6c925061f9cab4e452d088ad84308229a4a7cefa058bf52d02c106bf899f.
Actual539-byte0x48/608 command line adds sweetgmufw1 and unique
sweettrial=gmuf-0124-20261107-a1 to the existing clock/CX/BCM diagnostic flags.
PAS INIT/MEM/otherprobes/PET/reboot remain0, NVT1/hz30/cpus8/sampler disabled.
NVT sourcePA182554000/MDT182578000/GMU18257c000; same-kernel no-GMU control
preserves earlier NVT/MDT placement/content exactly. Private pinned GMU32KiB
is two16KiB pages after MDT. These are package source addresses, not the low
runtime1MiB owner or GPU virtual addresses. No binary/dump/serial is in Git.

Independent image-parent-review.json PASS, SHA
186062f19416d1dfa6e60b105a6881a0405a3f08d3b8c66ec8259139cee2fcbb:
exact proven wrapper/actual commandline,10 normalized native kernel segments,
three pinned assets/ADT descriptors, pending PAS slots and2MiB zero tail;
all113–118 and120 baseline pins preserved. Original mkadt seven-line diff
still SHAa74a0418...454860. DSH36768 integration and1772 package handles closed0.

Phone has NOT been accessed/booted in0124; last observedTWRP. Highest physical
result remains0120 clock profile, not SMMU/FW/HFI/GPU/Metal. Full goal ACTIVE
and incomplete. Next author/test strict verify_gmuf124.py retaining120's actual
identity/image/CPUstage/CMDDB/WDT/BCM/CX/clock checks, updating exact source/
flag/terminal, and adding real SMMU mapping/ATOS/routes/context and firmware
reset/copy/OOB/HFI INIT/version receipts. Reject partial/failure/duplicate/stale
logs; no parser relaxation to accept a failed hardware trial. Review that
failure diagnostics will identify the first rejected hardware stage. Only then
execute one already-authorized temporary fastboot boot with the exact image
pin and bounded observer; NEVER flash/format. Attribution of a future recovery
requires THIS-trial user confirmation, not0120's answer. No user action yet.
Sanitized publication outcome/new SHA goes into
research/tmp/dsh-0124/public-snapshot-0124.json; sole public parent713a869aa...
e046d, never private ancestry. Codex authors/reviews/interprets, DSH executes.

### 2026-11-07 — 0124 native firmware adapter/coordinator pass all61 host files; full local build next

Previous goal turn was progress:0123 code259a27f/handoffa05a605, sanitized
public713a869aa5772f9674fefe8a2f62fcecb6ee046d pushed/verified with soleparent
8a7c7ed2...b62da. Full daily-use/GPU/Metal/RAM/storage/peripherals/90–120Hz goal
remains ACTIVE/incomplete. Highest hardware remains0120 configured200MHz/
native branchesON and user-confirmed autonomous recovery131s. No0121–0124
physical SMMU/firmware/HFI/GPU/Metal result yet. Last observed phoneTWRP;
no device IO this turn. Original mkadt diff/all113–120 artifacts preserved.

Codex code commit a26328873f64b0ffb55e18408e9e29db54d8d49e adds118th patch,
five changed native paths, no new native TU. Firmware adapter stays INSIDE
the sole board TU, calls existing cold SMMU transaction and reuses private
CSR/SMMU/NC aliases. Adds only narrow AO/RSC/PDCcfg/PDCseq/TCM/GBIF apertures
specified in docs/gauguin-gmu-firmware.md. Revalidates real asset before board
maps and again before TCM load. Fresh8s CPU deadline/initial13s WDT margin,
3s per-access budgets; never rearm/PET. Checks NS IRQ policy including core332
before SMMU mapping and throughout execution. Live clock helper preserves
strict quiet behavior; allows GX power/branch changes only after owned OOB.

Phase checks latch reset-release/OOB intent BEFORE each single Device store,
complete write barriers before post-checks, enforce reset1 before own release
and reset0 after. Every live guard checks current SMMU global/CB faults,
micro-MMU, routes, SCTLR/ACTLR, TTBRs, TCRs, MAIRs and CBAR/CBA2R. Actual TCM
copy touches only[1000,9000), compares8192 words with guards each1KiB chunk;
HFI uses retained NC reservation, no aliases/raw pointer exports. Failure
quarantines both owners/shared WDT BEFORE synchronous logs and records partial
issued/compared counts; no retry/reset assertion/rollback. Public outputs are
unchanged on failure. Software timeouts cannot cancel stalled MMIO.

New sweetgmufw=1 coordinator mode requires gmuclk/CX/BCM/CPU-stage prerequisites,
PAS INIT/MEM disabled. Actual immutable CMDDB ARC entries and pinned GMU asset
are checked BEFORE watchdog/RSC writes. Then BCM/ARC/CX/clocks -> coherent
SMMU/firmware/HFI bootstrap; raw receipts logged, bounded reset wait retained.
Default0 invokes no new firmware APIs. Unstarted refusal also consumes WDT
authorization. Success means only FW result + INIT/version replies, not DCVS/
BW/TEST/normal HFI_ON/SQE/CP/ZAP/GPU commands/Metal. Do not claim host modeled
receipts as physical firmware ACKs.

DSH board-validation.json/V2 passed before later review changes; originals
retained. Final integration-validation.json PASS: actual board2839 old+75 new
map/copy/IRQ/phase/ignored-reset/fault/owner/budget cases; actual retained clock
162 cases; actual coordinator261 retained+24 firmware cases (285 total); three
real ARM64 TUs (board/CX/coordinator), qualified0120 make context. Source remains
frozen after final six checks. No DSH edits/repairs/hand-written results/warning
bypass. All61 host files then PASS on fresh strict118-patch replay5282 files:
.deps-cache/p0-20261105/source124-codex SHA
54ead7a46a93affcfbc97e73ff30d3f627631a9585ba5a35cd7d1a8195a19f92.
Exact five native paths match reviewed combined; tested source/source123 baseline
unchanged in research/tmp/dsh-0124/replay-full-host-result.json. DSH36768 final
integration handle; earlier89038/27761/35016 closed0, actual reports audited.

Prepared reviewed local build124.py and strict qualify_native0124.py under
research/tmp/dsh-0124. Qualifier retains EVERY120 artifact/provenance/SDK/
identity/install/archive check, adds20 required defined symbols and six actual
GMU archive members, exact tested source/all61 host evidence. Next execute ONE
normal deps/build-macos.sh run with committed head, then qualify; no manual
object repair/strip substitute. Exact run/results go into
research/tmp/dsh-0124/native124-execution-result.json when executed. No CI run.
Then pinned GMU-asset package, independent image review and strict fresh runtime
verifier BEFORE a single already-authorized temporary boot. Preserve proven
loader/wrapper/NVT/MDT/storage boundaries; add only the GMU asset/flag/unique
trial. No flash/format/GPT changes. Codex authors/reviews; DSH executes scripts
in full access with existing0121 relay/local-tools overlays. Public parent is
713a869aa...e046d; never push private ancestry. No user action required yet.

### 2026-11-07 — 0123 pinned GMU asset and native firmware/HFI engine pass all61 host files

Previous0122 milestone completed at private21a8487; sanitized public
8a7c7ed2c96e553dfbfc86e9c94c7eb9618b62da was pushed/verified with sole parent
6057db67...7e4b9. Full daily-use/GPU/Metal/RAM/storage/peripherals/90–120Hz goal
remains ACTIVE and incomplete. Highest hardware is still0120 configured200MHz/
branchON and user-confirmed autonomous recovery131s. No0121–0123 physical SMMU,
firmware, HFI ACK, GPU commands or Metal qualification. Last observed phone is
TWRP; no device IO, full kernel build, CI run, image or boot in0123.

Codex code commit259a27f1b6dc1a1e22b9d20d10686d1497682d15 adds117th patch:
gauguin_gmu_firmware.c/.h pure bounded native-order bootstrap, native
gauguin_gmu_asset.c/.h reader, read-only same-boot immutable CMDDB ARC exporter,
and optional mkpayload --gmu-firmware. Exact32768B asset SHA
9ef10b2b179054fb57af25008e29feb24300c2eaaeabf907bd741786bbacbf2e;
ADT /chosen/memory-map/A619GMUFirmware is LE64 physical address/32768B length.
Two16KiB pages follow existing assets; prior topOfKernelData reports and PAS
tail remain consistent. Default layout unchanged. Native reader rechecks
boot_args/DRAM/kernel bounds, ADT, contiguous direct-map endpoints and actual
SHA256, then returns a const data view. No asset binary is in Git.

Engine consumes exact real cx/mx/gfx/xo entries (owner3/version1000/aux32,
addresses30000/30010/30050/300a0). Bounded diagnostic upper-envelope GFX/MX7/7
policy is not measured voltage or daily DVFS. Asset/cold state precede writes;
native five-word RSC/PDC/TCS programming,8192-word copy/readback, actual five
legacy TCM version words, TCM_BOOT2/CM3_CFG4052/chip06019000/fence80a008a0/
queue/log/cache/IFPC/RPMh then GBIF halt clear. A619 HAS GBIF. Single reset
release must yield fresh babeface; boot-slumber OOB uses request bit22/ACK30.
HFI INIT and version requests use actual ggh rings and require exact echoed
headers/v1ACKtype2, native INIT non-ffffffff and version status0, major1/minor11+.
Known debug packets are bounded; stale/error/fault/timeout/guard loss permanently
quarantines. Model-generated replies are HOST evidence, never hardware ACKs.
No DCVS/BW tables/TEST/normal HFI_ON/SQE/CP/ZAP/Metal result is claimed.

DSH asset-validation.json PASS covers new and three retained packer files.
firmware-validation.json PASS:1,617,938 ASan/UBSan checks,1385 ordinary and1721
debug fail-every-callback boundaries, actual firmware ARM64 TU. Real platform
CommonCrypto SHA256 asset-consumer-validation-v2.json PASS:23 synthetic cases,
23 actual private-asset cases with UNMODIFIED production pin and native ARM64 TU.
Initial synthetic host fixture declared16MiB while its packer-emitted asset
was beyond16MiB; real reader correctly rejected it. Codex corrected only the
fixture DRAM to32MiB matching synthetic ADT. Original failed report/logs retained.
bus-export-validation.json PASS:106 retained+56 CX cases including atomic ARC
export/retained-copy negatives, three actual RAW roundtrips, actual bus ARM64 TU.
All frozen report inputs rehashed unchanged before commit. No DSH source/object
repair, hand-written result, crypto replacement or warning bypass.

Eight native primary files reverified independently against fixed kernel
19b63c8192b1c9b7c4d931d7d3be92024bc2d778 and actual root tree465f20ae...125c:
research/tmp/dsh-0123/native-source-pins.json. Fresh strict117-patch replay
.deps-cache/p0-20261105/source123-codex has5282 files SHA
f18b5f85ef458d73263972baf1989ed152d01f2eb6ee70cef80630497b41a3d2;
exact seven native paths match reviewed combined bytes. DSH9987 actual script0:
all61 host test files PASS, tested source and source122 baseline unchanged in
research/tmp/dsh-0123/replay-full-host-result.json. Public contract is
docs/gauguin-gmu-firmware.md. Original seven-line mkadt diff SHAa74a0418...
454860 and all113–120 artifacts preserved.

Execution incident: a Codex Python task-writer syntax error prevented creation
of execute-firmware.txt, but an unconditional launcher still started DSH99057.
It attempted broad read-only file discovery; Codex terminated its exact observed
process tree. No compile/source change/device IO was observed from that launch.
Original events-firmware.jsonl retained. Correct specification was written and
separately run as56254/events-firmware-v2.jsonl. Future launches are conditional
on successful task creation; prompts explicitly say missing task/script means
stop immediately without searching. Closed prior handles18470/99057/56254/
68833/90060/46241/98575; CLI exit0 is not proof of inner script success.

Next: native physical firmware adapter and coherent coordinator. Reuse retained
0122 private CSR/SMMU/NC mappings; add ONLY narrow AO/RSC03d8c000+4000,
PDCcfg0b294000+4000, PDCseq0b490000+4000, TCM03d6c000+c000 and
GBIF03d0c000+4000. Need phase-aware reset/GX and clock checks after owned reset
release/OOB; old reset1/GX-off guard is invalid then. Check live SMMU faults,
fresh CPU/WDT margins and masked NS IRQs, additionally GPU core332/word10bit12.
Copy only TCM[1000,9000), reuse actual HFI NC reservation, no broad aliases/raw
pointer exports. Bind actual asset/ARC/board owners and one-shot failure policy,
then one full local build/package/strict-verifier/temporary-boot trial. Do not
spend a mapping/copy-only boot. ZAP belongs at its native later stage. Codex
authors/reviews/interprets, DSH executes exact reviewed scripts with full access.
Sanitized publication/new SHA is recorded in
research/tmp/dsh-0123/public-snapshot-0123.json when pushed. Never push private
ancestry or firmware/dumps/serials. No new user action is required yet.

### 2026-11-06 — 0122 cold SMMU transaction and real board adapter pass focused validation

Previous goal turn was progress:0121 codea3a426f/handoffaf2d081, public
6057db67fedbb9ba6a9122200371d3861db7e4b9 was pushed/verified with soleparent
1f1b3bc...; all55 host files passed. The user explicitly reactivated the FULL
daily-use/GPU/Metal/RAM/storage/peripherals/90–120Hz goal. Keep it active and
incomplete. Highest hardware remains0120 configured200MHz/branch ON/autonomous
recovery; no new firmware/GPU execution has been attempted in0121/0122.

Codex authored gauguin_gmu_smmu.c/.h, a complete cold callback transaction:
qualify fixed64KiB/4KiB SMMUv2 capabilities/ATOS, capture all routes/CBs, reject
any enabled/stalled context, resolve/allocate exact GMU streams4/5 without
assuming bank4/5, preserve other routes/controls, prepare actual table memory,
recheck snapshots, halt Qualcomm micro-MMU, program12 native implementation
values while retaining halt, clear/sync faults/TLB, configure both native
S1 contexts, perform131 mapped-page plus9 hole/user-root ATOS checks, publish
routes, recheck unrelated state and resume local halt. External-abort/all-ones
PAR cannot satisfy an expected translation fault. No reset release/firmware/PAS.
Cold-only: active handover, EXIDS, unsupported geometries/ATOS are rejected.

New gauguin_gmu_board.c/.h is the actual native adapter, still WITHOUT a boot
hook/flag. Same-boot CPU-stage CLAIMED owner is revalidated by its owner API:
all64 unmanaged NC pages plus unchanged MDT hash/zero tail. Retained clock
owner supplies current fixed-profile/CX/GX-off checks independently of its old
deadline. PE GIC helper reuses existing mapping, NS ISENABLER8/10/12 masks
a0/30000/ff000 (global SMMU261/263, GMU336/337, CB396..403); secure state remains
unproven. Eight-second new CPU deadline, initial13s WDT margin and fresh3s
access guards. CM3 reset must already read1; an inherited running CM3 stops.

Narrow reset03d7c000+4000 RW and GPU SMMU03d40000+10000 RW maps are checked for
unmanaged Device attributes, all16KiB endpoint translations and virtual-range
overflow, retained on any outcome. No broad GMU/GPUCC alias or pointer export.
NC owner mapping starts AFTER the old protected first16KiB PAS map. Ordinary
64KiB scratch contains expected tables/HFI; bounded4KiB chunks zero/copy/compare
only named reservations/table bytes with live guards. Metadata/gaps/arena tail
are untouched; scratch freed, physical owner/maps retained. Failure latches
board/WDT quarantine; no retry/rollback/PET/new watchdog arm. No caller yet.

Native reference fixed19b63c8192b1c9b7c4d931d7d3be92024bc2d778 arm-smmu.c and
arm-smmu-regs.h verified by Git blob hashing AND fresh commit/contents API calls:
actual root tree465f20ae4183ed1dbb51f45a921de736a082125c. Machine pins in
research/tmp/dsh-0122/native-source-pins.json. Older recursive source-tree.json
is truncated and its sha field equals the requested commit, not the actual
root tree hash; do not use it as a complete inventory. Explicit native blobs
still match:469649eb...b2fb3/bed45ecf...4efe3. Stage1 output uses ID2.IAS
(native ipa_size), not downstream ID2.OAS. Public contract docs/gauguin-gmu-smmu.md.

DSH smmu-validation.json PASS:1,738,000 ASan/UBSan checks, indexing userCB1/
kernelCB2 and matching userCB6/kernelCB4, actual independent software walks
behind140 modeled ATOS operations, fail-every-callback2541 boundaries and real
ARM64 TU. board-validation-v2.json PASS: real IRQ102 bit/address cases, retained
clock117 cases, original PAS staging plus per-page owner negatives, board2837
mapping/owner/reset/budget/failure cases, native clock/PAS/board TUs and PE
pe_fiq using its actual PE make recipe. Initial board-validation.json failed
only because an existing Python test expected the old C success string; all
C checks passed. Codex restored that string plus a separate new owner line.
Original failure retained. No production source repair was needed for it.

Review then added board VA-overflow checks and a directly captured reset sample.
board-validation-v3.json PASS:2839 board cases plus fresh actual board ARM64 TU;
V2 unchanged components are retained only after rehashing every unaffected pin.
No DSH source/object repair, crypto substitute or warning bypass. SMMU and all
adapter results are host/native compile evidence, NOT hardware qualification.

Fresh strict116-patch replay source122-codex5278 files SHA
4cba3656b1bf5871e719005ddf233b5683340e9b59776416dfadd78df6475485:
exact ten native paths match reviewed bytes; source121 baseline unchanged.
DSH7972 complete58-file suite PASS: actual host_exit0/source_unchanged true,
baseline unchanged in replay-full-host-result.json. Code committed5a39a54.
Git format check caught blank context spaces in the unified patch; the shell
continued to that local commit despite the check's nonzero exit. Codex fixed
the patch representation only (two context lines; no trailing blank spaces).
Fresh strict final-format replay source122-format-codex is byte-identical to
the tested5278-file source, SAME SHA4cba3656...75485; replay-format-result.json
PASS and git diff --check from public parent PASS. No host/native rerun was
needed for identical source bytes. No0122 full kernel/CI/image/device trial.
No device IO this turn; last observed phone state remainsTWRP. Preserve all
113–120 qualified images/data and original seven-line mkadt diff SHAa74a0418...
454860. Private HEADaf2d081 at start; current public6057db67...7e4b9.

Final patch-format commit c206700; sanitized publication outcome/new SHA is
recorded in research/tmp/dsh-0122/public-snapshot-0122.json when pushed;
never push private ancestry.
Next: implement the pinned32768-byte
legacy GMU asset/ADT contract, narrow TCM+GMU AO/PDC/RSC owners, native ucode/
power/boot/version and reset/FW result, followed by A619 GX/OOB/HFI ordering and
real request/ACK. Integrate in one bounded initializer before a temporary boot;
do not spend mapping/copy-only boots. ZAP remains at its native later point.
Codex authors/reviews/interprets; DSH executes reviewed local scripts with
provider-existing-relay.patch.yml/local-tools-only.patch.yml from0121, full access.

### 2026-11-06 — 0120 autonomous reset confirmed; 0121 memory/HFI modules validated locally

THIS0120 user explicitly answered “是，自行重启，我没有操作” to question
call_fbc0f6320a4142dcbca7ca51884f69ee. New machine-generated parent record
research/tmp/dsh-0121/hardware0120-attribution.json binds that answer to the
original0120 technical report SHA58301c6a...bcf97 and rehashes ALL10 unchanged
inputs. Original unknown-attribution report is preserved. Thus131s recovery is
user-confirmed autonomous; no PMIC cause is available, so reset cause itself is
not independently proven. Configured200MHz/branch ON remain the highest actual
hardware result, not measured frequency or firmware/GPU/Metal execution.

Codex authored CPU-only gauguin_gmu_memory.c/.h and gauguin_gmu_hfi.c/.h,
now in0121-gauguin-gmu-memory-hfi.patch with two standard build entries. No
runtime hook or boot flag is added. Exact native reference remains19b63c8192b1c9b7c4d931d7d3be92024bc2d778;
new kgsl_hfi.c/h and io-pgtable-arm.c Git blobs independently verified in
research/tmp/dsh-0121/native/pins.json. Public design contract is
docs/gauguin-gmu-memory-hfi.md. No firmware binary/dump/serial in this change.

Memory image uses the existing1MiB low owner, protects its first16KiB PAS page,
and distinguishes CPU16KiB reservations from SMMU4KiB granules. Eight table
pages map exactly131 cache/dummy/HFI/dump/log pages with native NC/RW/AF/nG/
outer-shareable and IOMMU_PRIV permissions; separate user roots are empty.
No metadata/table/gap/padding page is mapped. HFI keeps native216-byte table,
224-byte ring start, four legacy IDs0/4/5/1 and disabled fourth queue. Pure
emitters validate fixed ranges/overlaps/IAS/OAS before writing; they confer no
physical ownership, coherency or SMMU authority.

HFI channel binds once, serializes host ownership by CAS, sends only queue0,
receives1/2, explicitly selects qualified major1/2, checks table/header/indices,
reserves one DWORD and uses native v2 four-DWORD padding. Guarded NC RAM
callbacks order payload/index/readback; receive output appears only after
successful consumption publication. IO/corruption permanently quarantines;
partial index publication may already have happened. Board adapter must retain
the lease through its later doorbell. No IRQ/ACK/firmware qualification here.

DSH memory-validation.json PASS: 7,936,295 independent walker/policy/failure
checks with ASan/UBSan, actual ARM64 TU against qualified0120/gKuZ8y context.
DSH hfi-validation-v2.json PASS:22,084 checks, fail-every-callback bind165/send69/
receive66 boundaries, both protocol layouts/wrap/max packet/full/empty/capacity/
quarantine and real ARM64 TU. Initial HFI fixture incorrectly used read index10
in its protocol2 success case; Codex corrected it to aligned12. Production
source was unchanged; original failed hfi-validation.json/logs are retained.
No warning bypass, object repair or DSH source edits.

Fresh strict115-patch replay source121-codex5274 files SHA
4f866fc0f1b82b203b5e6204c7cde9cf8a54c3489bb7511df5242da9f4b4e87c;
exact five native paths equal reviewed bytes, qualified source120 unchanged.
Complete55-file host suite PASS via DSH47927: actual host_exit0, tested source
unchanged and qualified source120 unchanged in replay-full-host-result.json.
No0121 full kernel,
CI run, image or device trial; phone has stayedTWRP throughout this work.

DSH old /private/tmp overlays no longer exist. Failed launches stopped before
any test execution. Reconstructed ignored overlays under research/tmp/dsh-0121
disable remote MCP/web/subagent tools and use the existing configured relay's
credential reference (no credential copied). NativeLAN route failed transport;
existing relay works. Current invocation uses provider-existing-relay.patch.yml
and local-tools-only.patch.yml with DSH_PERMISSION_MODE=danger-full-access.
Sessions45441(memory) and71993(HFIv2) terminal0. Codex writes/reviews, DSH executes.

Completed code committed a3a426f (seven text paths); private16c001f at start.
Sanitized single-parent publication uses previous public
1f1b3bc5892d7a257b1415c7149a82cc94e7bcfb; exact new commit/push outcome is
recorded by research/tmp/dsh-0121/public-snapshot-0121.json. Never push private
ancestry. Preserve original seven-line mkadt diff SHAa74a0418...
454860 and all113–120 artifacts. Then implement the actual board adapter:
narrow controller/reset/IRQ ownership, runtime SMMU stream/context/IDR
qualification, page-table publication, native PDC/RSC, pinned legacy32768-byte
ITCM image and reset/boot/version/HFI handshake in ONE bounded initialization.
Do not assume DT stream4/5 are CB4/5 or firmware zero version words mean v1.
Avoid extra mapping/copy-only reboots. Full daily-use/GPU/Metal/RAM/storage/
peripherals/90–120Hz goal remains incomplete; user resumed with “继续”.

### 2026-11-06 — 0120 native GMU clock/CX technical verification PASS; reset attribution PENDING

Full strict research/tmp/dsh-0120/hardware-data-verification.json passed all
identity/image/source/CPUstage/CMDDB/WDT/BCM/CX and new GMC checks. Actual exit3
means ONLY that THIS0120 user reset attribution is still pending, not a technical
failure. A question was sent asking whether131s recovery was autonomous; no
answer yet when this entry was written. Do not reuse118's answer. Preserve the
original unknown-attribution report; combine a future answer with unchanged
input hashes in a separate record. All10 bound inputs rehashed unchanged.
No log-framing exception needed this trial; no embedded core diagnostics found.

One19024KB temporary boot send0.444s/boot0.135s/total0.582s, observer0/no timeout,
backTWRP131s. Start12:52:53.128737Z, finish12:55:09.734624Z. Fresh4063-line/455948B
research/tmp/p3-gmuc-0120-native-observer-20261106.txt SHA
06d1c3b87fe05d66b0ba401c120c25899c27b30bb6a21d4a492f9cf2362a4cf1;
cycle1120B SHA3e9ba061efbb0025a6e617bed1d6be1694373c6e324fd37122b3cab65da01f54.
Exact xnu-e9c9211bdc96471489b2cd0fd06e7d86/gmuc-0120-20261106-a1 and qualified
image12dfc3ef...dfde28 match. CMDDB extraction0,131072B SHA
f8144f3079109cf2d6c784e9b81f7f3c969008978aebf051e1e88cc48da3c8a0, saved as
research/tmp/p3-gmuc-0120-native-cmd-db-20261106.bin. Raw tables/CPUstage/BCM/CX
and normal-runtime WDT readiness checked. Arm1758314364/ready1777615915/count32934,
EN3/BARK655300/BITE753595/CPU19.2MHz. Bootreason properties empty, no PMIC cause.

GMC before→after (hex; IDs documented in gauguin_gmu_clock.h):
MODEd010003d/L1f/FRAC4000/DIV1 unchanged; gate9/AHB1/GDSCf8228000 unchanged;
PLLvote1→1 (already held); GPU_DIVvote1e→11e (preserves old bits);
CMD80000000→0; CFG0→602; CX_GMU80004220→4ff1; GX_GMU80000000 unchanged;
CXO1 unchanged; DDRSS_AXI80000000→1; MEMNOC80004220→4221.
All FOUR branches satisfy native ON status in actual final values; none relies
only on HWCG skipping. Complete receipt configured_hz200000000/direct_writes6/
hold_requests2/polls6. Direct count excludes shared-owner stores; two hold calls
do not mean two stores. Configured rate is source-derived600MHz/2/(3/2), not a
frequency-counter measurement. No explicit firmware/reset-release/PAS/GX/GPU
operation; inherited CM3 state, GPU execution and Metal remain unqualified.

NVT hardware regression: bootstrap result0/ready1,96936bytes written+verified,
9165 transfers; then packet counters998/1996/2994 each equal accepted, rejected0,
mask0. Shared GCC migration did not prevent NVT bootstrap or normal report
reads. No user touch input requested, so do not claim an interaction/unlock test.
Sessions68498/91008 terminal0; phone leftTWRP, no subsequent device IO.

Code919a6a1, nativegKuZ8y, pretrial private4fc4cf3/publicc2fee4d3603921d827c9478272668b8a115f44c1,
solepublicparent63b693a...; original mkadt diff and all113–118/0120 artifacts kept.
Full GPU/Metal/all usable RAM/reliable storage/peripherals/90–120Hz/daily-use goal
remains active. Real progress this turn is qualified native clock configuration.

Next: combine THIS0120 reset answer if/when supplied, then implement the coherent
native GMU initialization path. Read research/tmp/dsh-0120/next-gmu-fw-contract.md
and gmu-native-source-pins.json (all7 exact19b63 blobs). A619 is615_family and
uses legacy32768B a619_gmu.bin, not a640 block-stream firmware. Exact image SHA
9ef10b2b179054fb57af25008e29feb24300c2eaaeabf907bd741786bbacbf2e. Native AHB
offsets are GPU-relative words: SYSRESET03d7e000, TCM copy03d6d000..03d75000.
Broad GMU DT mapping would alias retained GPUCC: keep narrow page ownership.
Before reset release, qualify CM3 containment/IRQ state, PDC/RSC, GMU SMMU
backing/coherency and HFI/log IOVAs;0120 does not supply those. Avoid extra
copy-only probes/reboots; read accepted inherited predicates then act in the
same bounded coherent initialization trial. Do not move ZAP AUTH before the
native GPU AWARE/GX/SMMU/SQE/CP_INIT point. Codex authors/interprets; DSH executes.

### 2026-11-06 — 0120 local full build, package and independent image review PASS

Code919a6a1ec79784d89a154456d04e5dc6726c5f72; sanitized public
63b693ad2666a6987d18151a38496fe65884f3e5 (singleparent051a0bd...,10textpaths).
Normal local build/dSYM/strip/install/qualification/package succeeded in native
gauguin.gKuZ8y. Source120-v2 SHAdebd4b4edf9648071570b18fca0291aed3a0886eb0eeb9e47bc055d0d72b436b,
5270 files, already passed53 host files. Manifest SHA
52fdd5db7b24beffe9460ac3c63bdff5935b304a023c4e0bf421c682b6dd894d.
Kernel16869040B SHA99c241436cba4873a8fd9693c1e71c005936a443cbfdc585ddb85956b2e2a2a5,
IDxnu-e9c9211bdc96471489b2cd0fd06e7d86, Nov6 20:49:30CST banner.

Image shim/out/shim-p3-gmuc-0120-native-20261106.img19480576B SHA
12dfc3ef94c2746830b7b0713716b9e0239f5ef80aa061dd87a50c4f84dfde28;
payload19152896B SHA0f267efac6825ba8f2367a84773931e093ecf775c90cd5e8d57a2fd28590b400.
Actual526-byte0x48/608 command line sweetgmuclk/CXpower/busvote/PASprobe/PASstage1,
PASinit/mem/otherprobes/PET/reboot/wdttest/touchmode0, NVT1/hz30/cpus8/sweetsample=-,
unique sweettrial=gmuc-0120-20261106-a1. NVTasset182550000/MDTasset182574000;
runtime low reservation remains dynamically selected, these are package sources.
Independent image-parent-review.json PASS: exact wrapper/actual cmdline/ADT,
10 native segments/assets/2MiB zero tail, original mkadt diff and113–118 pins.
Reports native120-execution-result.json, p3-native-0120-qualification-20261106.json,
p3-gmuc-0120-native-evidence-20261106.json. DSH19923/23130 terminal0.

Codex authored verify_gmu120.py, retaining118 identity/CPU/CMDDB/WDT/BCM/CX
checks with source5270/new flags/RW map/new terminal; adds before/after16 GMC
registers, native tuple/parent/root/branch requests, direct-vs-shared accounting,
HWCG request vs observed ON and configured-vs-measured limits. Parser host
4 valid/93 rejected cases PASS, runtime-parser-result.json; DSH74820 terminal0.
VerifierSHAa16b3449f7a64dcc44b5f669c657b45223b1d34555ab0123f4eafbc13a5672ad.
No0120 hardware result yet; phone previouslyTWRP. Next: boot120.py once with
fresh recovery preflight/180s observer, then read-only verifier/extractor. Require
THIS0120 reset attribution. Never reuse118 confirmation or qualify GPU/Metal.
Full goal active; original mkadt edit and all qualified artifacts preserved.

### 2026-11-06 — 0120 GMU clock implementation, native TUs and all53 host files PASS

119 prerequisite committed97c6bfc039a9ca709923e7f3cf0589f8a1d166cb, sanitized
public051a0bd97037d156427c2bf6736cb4b39a049a42 with soleparentcaf7c3b...;
9text paths, no private ancestry. 119 deliberately had no mapping-only boot.
118 remains the highest real hardware result. Full original goal stays active.

Codex implemented the complete fixed clock path in the SAME CX translation
unit to reuse private GPUCC/GCC mappings; new gauguin_gmu_clock.h receipt/API.
sweetgmuclk1 requiresCX1/PASoff and chooses GCC144000 RW once (old CX mode still
RO). New PLL100000 RO/AXI12c000 RW pages have unmanagedDevice7/endpoint checks;
shared GCC150000 uses119's owner, never an overlapping NVT alias. Runtime
requires same-boot BCM/ARC/CX COMPLETE, fresh8s lease entry,3s later guards and
one5s CPU deadline. Fixed GPLL0 FSM600MHz L1f/FRAC4000/divider1 is checked,
no PLL retune; parent holds then RCG602/UPDATE then native CX_GMU/CXO/AXI/MEMNOC
requests. Inherited active CX/GX sibling, root force/update/unknown dirty/mode,
unsupported rate or lost access must stop; no retry/rollback/PET/branch disable.
No explicit GMU firmware/reset release/PAS/GX/DMA/SMMU operation is added.
Enabling clocks does not prove inherited CM3 state or absence of execution.

Shared GPU hold API now requires the caller guard before store and following
readback; delayed reads cannot bypass the clock deadline/WDT margin. GPU
uncertainty remains separate from touch. Receipt direct_writes excludes shared
owner stores; hold_requests counts its two calls (already-held votes may skip
stores). Configured200MHz follows the native tuple, NOT frequency measurement.
Before/after16-register snapshots and coordinator fields form later raw proof.

Focused host results: shared GCC25 cases, actual GMU clock73, coordinator261
(all241 retained+20 clock), CX104 (all103 retained+RW-map opt-in). Original
NVT/BCM/PAS/ARC regressions retained. Real native TUs for clock/CX, guarded-GCC
and coordinator PASS against qualified118/Y1TL15 context. Reports under
research/tmp/dsh-0120/{guard-host-result.json,coordinator-validation-result.json,
native-tu-v2-result.json,v2-execution-result.json}. DSH53453/2753/7513/39593 terminal.

Initial source120-codex SHA54f3f212e2cb771548ad2630a268b5aea3722e8c30b335073981dece5808a01e
and its53-file PASS are retained as history. Subsequent source review found
DIRTY_CFG must be allowed AFTER OUR OWN CFG write before UPDATE, while other
dirty/force fields remain rejected. V2 adds a clean-CMD check before consumers
and dirty/no-dirty/ignored-UPDATE tests. Self-clear plus raw controls does not
prove a measured or effective frequency; ignored writes with indistinguishable
register observations remain outside that guarantee.

Fresh strict114-patch V2 replay source120-v2-codex5270 files SHA
debd4b4edf9648071570b18fca0291aed3a0886eb0eeb9e47bc055d0d72b436b;
exactly5 native paths match reviewed combined bytes vs unchanged119. All53 host
files PASS and tested source unchanged. Machine replay-full-host-v2-result.json.
No0120 full kernel/image/device trial yet. Phone remainsTWRP; no new device IO.

Next concrete action: commit/push tested0120 text paths, execute the prepared
standard local research/tmp/dsh-0120/build120.py using that commit; source pin
now bound. qualify_native0120.py adds all GMC/GCC defined symbols. pack/review
scripts are ported with sweetgmuclk1 and sweettrial=gmuc-0120-20261106-a1,
preserved113–118 assets/baselines, but must be reviewed before execution.
Prepare an identity/CMDDB/WDT/BCM/CX+GMU16-register runtime verifier before one
integrated temporary boot. It must accept the new GCC RW map, no old CX terminal
marker, parse configured vs measured rate/hold_requests precisely, and use only
THIS0120 user reset attribution. Existing118 verifier cannot qualify0120.
Keep original mkadt diff and all113–118 images/data. Full objective unchanged.

### 2026-11-06 — 0119 shared GCC vote owner and NVT migration PASS; no device boot

Previous goal turn was progress:118 actually qualified CX ARC/PWR_ON and
user-confirmed autonomous recovery. Full daily-use/GPU/Metal/RAM/storage/
peripherals/90–120Hz goal remains active and incomplete. Phone staysTWRP.

Codex authored shared GCC150000+4000 permanent Device RW owner, replacing NVT's
overlapping152000+1000 map. Fixed touch word152000 retains its6/7/10 masked
updates/restoration under the original NVT mutex; future GPU has distinct
152008 bit8 and152010 bit0 hold-only interfaces. No exported MMIO pointer or
caller-chosen GPU address/mask/value. Mapping state is one-shot CAS with pmap
unmanagedDevice7 and exact endpoint checks; partial map failure never retries.
GPU write uncertainty latches quarantine before store, serializes GPU writers,
preserves caller output on failure and leaves the separate touch word usable.
Native NVT now also rejects all-ones vote reads before wrapper/SE accesses.

DSH gcc-validation-result.json passed shared-owner host fixture, ALL retained
actual NVT adapter host cases, plus both real ARM64 TUs. No object/source repair.
Source candidates in research/tmp/dsh-0119/combined. Strict113-patch replay
source119-codex5269 files SHA
df7bd9cf7b13d847de9e854bafb64dd9e283317cf56f9c0e94fb3eed52b3bc88.
Exactly4 native paths differ from preserved118 and equal reviewed candidate
bytes. All52 public host files PASS; source118/tested119 unchanged. Machine
research/tmp/dsh-0119/replay-full-host-result.json; sessions70484/67737 terminal0.
No119 full kernel/image/device trial: this is a necessary mapping dependency,
and its hardware regression belongs in the next integrated clock trial, not a
standalone mapping-only reboot. Original mkadt edit and all113–118 artifacts kept.

Next critical code is drafted but UNVALIDATED in research/tmp/dsh-0120:
combined/bsd/dev/gauguin_cx_power.c, gauguin_gmu_clock.h and gmu_clock_body.c.
It retains private CX maps, selects GCC144000 RW only for sweetgmuclk1, maps
PLL100000 RO/AXI12c000 RW, then fixed600MHz tuple/divider/RCG200MHz/native four
branch sequence with same-boot BCM/ARC/CX/WDT guards. No coordinator hookup,
host fixture, native compile, patch, full build or image yet for this draft.
It MUST be reviewed/fixed before execution, especially fresh lease/deadline
checks inside shared GPU vote RMW, precise direct-vs-shared write accounting,
and final inherited RCGuard stability. Do not infer qualification from119 tests.
Plan stays research/tmp/dsh-0118/gmuc-clock-next-plan.md; exact native sources
in native-clock/pins.json. Integrate clocks in one future boot after repeated
BCM→CX ARC→CX power. CM3 inherited reset state remains a review boundary before
firmware/DMA. Codex authors; DSH executes reviewed compilation/tests/boots.

### 2026-11-06 — 0118 native CX ARC completion, PWR_ON and autonomous reset VERIFIED

THIS118 user explicitly confirmed: “是，自行重启，我没有操作”. Authoritative
research/tmp/dsh-0118/hardware-framed-verification.json and
hardware-framed-execution.json PASS: original identity/CPUstage/CMDDB/WDT/BCM
checks plus CX ARC and GDSCR receipt checks, actual observer131s recovery and
new user attribution. Full GPU/Metal/RAM/storage/peripherals/90–120Hz/daily-use
goal remains active. This trial does not execute GMU/GX/PAS/GPU or prove voltage,
bandwidth, frame rate, arbitrary-MMIO/secure-hang containment or touch regression.

One temporary19008KB boot, send0.444s/boot0.134s/total0.582s; observer0, no timeout.
Start12:09:40.133799Z, finish12:11:56.719557Z. Unique cxpower-0118-20261106-a1 and
banner xnu-bdef4e55eb0049fdb45ba87361ca914c match qualified image dc883ec6...3c461a.
Fresh4021-line/451794B log research/tmp/p3-cxpower-0118-native-observer-20261106.txt
SHAb4179c9491326e474b1fb86e1db08d92114265941273dc292adf01a605414646;
cycle1037B SHA5f0cd139b207df52882413af47c5ca2b4af21cf0ecbf5f92e99d9f24af7593da.
CMDDB131072B extracted SHA9ad405cafa24f0bf1c8a65fe3cca48c4a2e6e448973726f8adf9c2997edd7306,
path research/tmp/p3-cxpower-0118-native-cmd-db-20261106.bin. Same-boot CX32-byte
table and all6 BCM/four ARC rows validated. CPU stageAA200000/6860/16384,
64 unmanaged NC pages; WDT EN3/BARK655300/BITE753595, arm1759668925,
ready1778973746/count32941,19.2MHz CPU timebase. Bootreason properties empty.

BCM complete slot1/config80008104/IRQ1→1/new2; statuses10101,10101,00101,
10101,10101,10101hex. CX ARC reused the same mapping/owner after BCM cleanup:
selector6/level384, WAIT0/ENABLE1 with response required, freshIRQ2/status10101,
ownIRQ restored1, held request retained. GCC CFG_AHB00000009. CX GDSCR
before00222001 (PWR_ON0/collapse1), configured00228001 (wait8), finalf8228000
(PWR_ON1/collapse0/mode0/wait8); finalAHB00000001. Two masked writes, one poll.
OFF-to-ON was observed during this sequence; exclusive causal ownership is not
claimed. Helper and coordinator raw fields agree. No failure/PET/PAS/survived30.

Strict verifier first exited2 because complete BCM receipt at line3836 follows
one255-byte unterminated IOK SpringBoard fragment. Preserve that original
hardware-data-verification.json and raw log. New verify_cx118_framed.py only
recognizes this exact prefix plus complete strict receipt, records original
line/line number, rejects other embedded core diagnostics and changes no input
bytes or fields. Independent review found no blocker;3 valid/11 rejected framing
cases passed before the full verifier0. Both script hashes, original failed
report and unchanged actual inputs are recorded. Sessions83214/2326/11788 terminal;
no observer/build/phone task remains. Phone leftTWRP; no subsequent device IO.

Code59f4986, pretrialhandoff6bdec10, nativeY1TL15. Public pretrial snapshot
7c33f51cbc3830f0f344d694fb3d909a6e1df3ce had soleparentc90545f... and13textpaths;
post-result snapshot IDs are in dsh-0118/public-result-snapshot-0118.json.
Preserve all113–118 qualified images, fresh evidence and original mkadt edit.

Next concrete action: implement the reviewed GMU200MHz clock path from
research/tmp/dsh-0118/gmuc-clock-next-plan.md, repeating BCM→CX ARC→CX power
in the SAME future boot before guarded parent/RCG/branch operations. Read live
rate/ownership predicates and act in that one bounded trial; no probe-only reboot.
First resolve mapping ownership: reuse retained GPUCC, share the GCC144000 page
deliberately for MEMNOC RW, and reuse NVT's existing GCC152000 mapping for152008/10
votes rather than creating aliases. Do not expose unrestricted MMIO pointers.
Pinned Fabia L1f/FRAC+38=4000 and XO76.8MHz/4 imply GPLL0 600MHz; divider raw1
means /2; RCG mask10371f/value602 gives200MHz. Unsupported live tuples/modes or
active siblings must stop, never retune shared PLLs. Exact clock files are bound
by dsh-0118/native-clock/pins.json. CM3 inherited/reset state remains a separate
boundary before firmware/DMA. Codex authors/reviews; DSH runs reviewed commands.

### 2026-11-06 — 0118 local full build and independent image review PASS

Code59f4986df940f32bb1a6437fcddf1dc8b0686999; normal local make/dSYM/strip/install
completed in run gauguin.Y1TL15. Source118 SHA9923370484996862a1019ecd35114ce3793327add4d1f57650f7af12aa19eb84,
5267 files; all51 host files and isolated native TUs passed. Manifest SHA
276d09311c3a45c3d77633c3d03671cdc209a82da638b9e59330b378b74a9f82.
Installed kernel16851680B SHAfa6fa1e77b906ab5cc9908644ff6fd0dadb1d16eecafe57f7d0cd714e3f579af,
ID xnu-bdef4e55eb0049fdb45ba87361ca914c, Nov6 20:05:04CST banner.

Image shim/out/shim-p3-cxpower-0118-native-20261106.img19464192B SHA
dc883ec60f05d3cba5fdc53ffc3c8f7f0047761cf08bfb5351728b1c743c461a;
payload19136512B SHA5da9b14b9604a0f248f097789788b8b30bb29aba66569cc623126f90fe9c182e.
Actual0x48/608 command line515B: sweetcxpower/busvote/PASprobe/PASstage1,
PASinit/PASmem/otherprobes/PET/reboot/wdttest/touchmode0, NVT1/hz30/cpus8,
sweetsample=-, unique sweettrial=cxpower-0118-20261106-a1. NVTasset18254c000 and
MDTasset182570000 unchanged; runtime low reservation is still selected at boot.

Independent image-parent-review.json PASS: exact wrapper/actual flags/ADT,
10 native segments, asset pads/2MiB zero tail, all113–117 baseline pins and
original mkadt diff. Native qualification retains provenance and all new defined
symbols. Reports research/tmp/dsh-0118/native118-execution-result.json,
research/tmp/p3-native-0118-qualification-20261106.json and
research/tmp/p3-cxpower-0118-native-evidence-20261106.json. DSH10747/20542 terminal0.
Root initially supplied wrong checker option --out; argparse rejected before
checking/writing. Correct --report run passed; original error log retained.
CX verifier additionally passed8 valid/99 rejected synthetic cases, parser-host-result.json;
DSH81382 terminal0, source SHA05e74caaa3ccc981053b727bf53ba6a3decfed9b765f2070b8e9bb6df1602d62.

Next: sanitized13-text-path snapshot from publicc90545f..., then boot118.py once
with180s observer. No118 device boot yet; phoneTWRP. Require fresh THIS118 logs
and user reset attribution, never reuse117 confirmation. Trial proves at most
native ARC completion/CX PWR_ON, not GMU/GX/GPU/Metal. Parallel next-clock research
uses6 exact19b63 GitHub blobs in dsh-0118/native-clock/pins.json; earlier
native-clk-* copies were a different revision and are not authoritative here.

### 2026-11-06 — 0118 strict replay and all51 host files PASS; ready for local build

Fresh112-patch replay produced source118-codex5267 files, SHA
9923370484996862a1019ecd35114ce3793327add4d1f57650f7af12aa19eb84.
Exactly9 expected native paths differ from117; all equal reviewed combined
candidate bytes. Baseline117 and tested118 unchanged. Full51 public host files
PASS, report research/tmp/dsh-0118/replay-full-host-result.json; DSH85101 terminal0.
Public fixtures match frozen candidates and use XNU_SOURCE/temporary outputs;
no private raw capture is required by public tests. Private pure-plan115-case
run additionally checks the pinned actual117 capture (public synthetic93 cases).

Final focused results also include bus162 (106 retained+56 CX), three exact
RAW/extractor round-trips, coordinator241 (149 retained+92 CX). All five changed/
new native C TUs compile. Bus57976B object SHA4bc384a5e66e39385a6923db4189a4dda8382144d463b00948d8674319a0f2eb;
coordinator32256B SHA5e480315288c5332529a70f8cdfcfc05fc6125c879ecd727edc118a1ad19f1a3.
Machine joint-host-validation-result.json/coordinator-tu-validation-result.json
PASS; sessions77890/30901 terminal0. Codex independent review found no blocker.

Next: commit13 reviewed text paths, standard local build118.py/qualification/
packaging and independent image review. These scripts now pin fresh118 SHA.
verify_cx118.py preserves117 identity/CMDDB/CPU/WDT/BCM checks and adds exact
ARC+CX log order, raw registers/receipt agreement, bounded counts, PAS exclusion.
It distinguishes initial PWR_ON from observed OFF-to-ON without claiming causal
ownership. Parser-focused host checks are being authored; no118 image/boot yet.
After review, publish only a sanitized single-parent snapshot from public
c90545fcee0e4d3f8ca278f2aa69e376396c7c56, then one authorized temporary boot.
Phone remains TWRP. No destructive partition action. Full goal remains active.

### 2026-11-06 — 0118 CX power candidate; focused checks in progress, NOT BOOTED

117 remains the highest verified PAS result below. Next trial follows native
GPU AWARE prerequisites rather than calling AUTH on an unpowered GPU. Reviewed
primary source is LineageOS/android_kernel_xiaomi_gauguin at
19b63c8192b1c9b7c4d931d7d3be92024bc2d778. Local contracts:
research/tmp/dsh-0118/{arc-native-contract.md,cx-clock-plan.md,header-source-pins.json}.
Actual117 CMDDB CX is address30000, slave3, bankver1000, aux32 bytes, levels
0/16/64/128/192/256/384 then nine zero u16s. Initial candidate mistakenly
required aux16; actual-RAW host replay rejected it before build/boot. Root
corrected to strict32 and added all padding-byte rejection cases. Original
failed reports remain in transport-validation-result.json and component logs.

Selected temporary policy is selector6/level384, the highest supported legal
same-table CX request, permitted by captured DT max65535. It dominates legal
inherited same-table DRV requests; it is NOT a current floor/voltage reading,
proof of opaque secure ownership, or a daily thermal policy. Retain through
qualified WDT reset; no lower/release/rollback. One synchronous ARC command
after BCM cleanup uses the same private RSC map/atomic owner, ADDR30000/DATA6/
MSG10108/WAIT0/ENABLE1, mandatory ISSUED+COMPL and a fresh own completion IRQ.
Separate ARC state/receipt preserve completed BCM history. Owned uncertainty
quarantines controller/lease; non-owner BUSY changes neither.

Then CX checks GCC CFG_AHB00145004 via aligned RO00144000+4000 before GPUCC
RW03d90000+4000. Only GDSCR106c is written: reject HW_CONTROL/SW_OVERRIDE,
masked CLK_DIS_WAIT8 then clear SW_COLLAPSE; native bounded500us PWR_ON poll
and settle, final AHB1078 read. No GMU/GX/SMMU/CP/PAS/GPU execution. Actual DT
has hw-ctl-addr, while pinned driver looks for hw-ctrl-addr, so native polls
GDSCR106c, not syscon1540. Future GMU200MHz/SMMU/SQE/CP_INIT precede native ZAP.

DSH read-only inventory completed in7s, all22 recovery checks good,140 DT
properties, required_unavailable empty:
research/tmp/dsh-0118/twrp-power-inventory-uv68hdbn/inventory.json.
Both clk_summary/regulator_summary unavailable; no mount/fallback/device open.
This captures DT/Linux state, not XNU voltage. No118 boot has occurred.

Focused DSH results: CX power103 sanitizer cases and its native TU PASS;
shared BCM+ARC280 cases (all147 old cases retained) PASS; pure CX plan115 cases
including exact117 raw snapshot PASS; corrected plan and transport native TUs
PASS. Machine reports initial-validation-result.json and
transport-v2-validation-result.json. DSH sessions7305/51362/46083/70960 terminal.
First ARC failure was a fixture expecting ALREADY instead of OFF with bus flag
disabled; production behavior was correct. No warning/object/source repair by DSH.

Candidates are under research/tmp/dsh-0118/{shared,plan,arc-transport,cx-power,
bus-prepare,coordinator}. Root wrote core; fix_bus_host_fixture independently
reviewed ARC and is extending bus/coordinator fixtures. Root-authored public
test runners are being staged; full patch/replay/link/boot NOT YET qualified.
Next: complete focused bus/coordinator validation, generate9-path112th patch
(four new files, expected fresh source5267), full51-file host suite, commit,
normal local build/package/review, sanitized single-public-parent push and one
temporary sweetcxpower=1/busvote=1/PASinit=0/PASmem=0 trial. Build/review scripts
still contain UNBUILT_SOURCE118_PIN until fresh replay establishes source hash.
Keep original tools/mkadt.py diff and all113–117 artifacts; no destructive step.
Full GPU/Metal, RAM/storage, peripherals,90–120Hz and daily-use goal stays active.


### 2026-11-06 — 0117 PAS MEM_SETUP and autonomous normal-runtime reset VERIFIED

THIS117 user confirmed: “是，自行重启，我没有操作”. Parent rehashed every technical
input and combined that new fact in research/tmp/dsh-0117/hardware-parent-verification.json.
INIT and MEM_SETUP both returned full64 transport0/service0; native BCM completion
and autonomous recovery after131s are verified. This proves acceptance of INIT
and the4096-byte MEM_SETUP, not b02 execution, AUTH_RESET, GPU/Metal, effective
bandwidth or recovery from an arbitrary nonreturning secure call. Goal remains active.

One temporary boot accepted19008KB, send0.454s/boot0.134s/total0.597s. Observer0,
explicit back-in-TWRP131s/no timeout; start11:04:06.011394Z, finish11:06:22.533364Z.
Fresh3934-line/445773B log research/tmp/p3-pasmem-0117-native-observer-20261106.txt
SHA3efdf420cbcfc014bb9c54bd4211023d9f0c014b180432a214654b387370ab1d.
Cycle1036B SHA0a4531a04c5c46c693aaa1645f4e9a40a6b9370159008b62d894a8fc335e2b00.
Exact banner xnu-119adf637ad14a8d9a6b2c692ab94838 and unique trial
pasmem-0117-20261106-a1 match imageaa2e6fa6...49bc79e9. All seven boot-progress
markers yes. No touch interaction was requested during this expiry experiment.
Bootreason properties were empty; no PMIC cause code is claimed.

Dynamic CPU-stage PA AA200000, metadata6860/reserved16384,64 unmanaged NC pages
and pinned metadata/zero-tail verified before INIT. Full CMDDB RAW extracted:
research/tmp/p3-pasmem-0117-native-cmd-db-20261106.bin131072B SHA
 dde122f958d8ad8852d1b8d8206f6153d270acd4177eae875b118974e550ad33.
Four banks, six BCM and four ARC entries validated. WDT armedEN3/BARK655300/
BITE753595; arm_at1758541248, ready_at1777826672, readycount32907, timebase19.2MHz.
BCMslot1/config80008104/IRQbefore1/after1/completed2; statuses10101,10101,00101,
10101,10101,10101hex. Successful controller cleanup and held-request markers present.

INIT: one fresh request,2 continuations/3 SMC entries, final raw x0..x6 all0,
terminalrc0/returned1. MEM_SETUP: one fresh request,0 continuations/1 SMC entry,
frame42000202/3/13/AA200000/4096/0/0; final raw x0..x3=0,x4=1000hex,x5/x6=0;
terminalrc0/returned1, coordinator same PA/4096/calls1. The private successful INIT
PA publication is matching-code evidence; both actual premarkers/receipts agree.
Intermediate continuation registers were not individually logged; counts and
reviewed binary control flow establish that path. No BUSY retries this trial.
No failure/PET/panic/survived30 record. Sampler explicitly off; core logs retained.

DSH executed reviewed verify_pas117.py once, actualexit3 because user confirmation
was pending then. Authoritative technical report hardware-data-verification.json
and verify-observed.log preserve that state; parent report adds the explicit answer
without rewriting history. Both phase parser checks and all prior identity/CPU/
CMDDB/WDT/BCM checks passed. DSH extractor exit0. Sessions91179 and32597 terminal0;
no build/observer/extractor remains live. Phone leftTWRP; no subsequent device IO.
Code8c527d7/native7tVAmW; pretrialhandoff1af541a. Publicsnapshot
c90545fcee0e4d3f8ca278f2aa69e376396c7c56 has solepublicparent
22a18e463155bbaeac52620899893f1d040ba2d0;7textpaths, no private ancestry.
Preserve original mkadt edit and all113–117 qualified artifacts.

Next action changed based on actual native call-chain review:
research/tmp/dsh-0117/next-auth-plan.md documents b02=1984bytes, SHA
61be42f041eb6051eb9f56beb1f98ed97ab21faf2ef2df6b9151ba1a46aae878, destinationoffset0,
BSSzero-count0, existing retained pst_mapping suitable for a narrow owner-local
copy/readback API (no new alias, no pending-MDT restage). AUTH frame is
42000205/1/13/0/0/0/0. Do NOT infer that zero per-PIL clock/regulator lists make
AUTH independent of GPU resources: native a6xx_rb_start starts SQE, completes
CP_INIT, then calls a6xx_zap_load; outer adreno_start first enters GPU AWARE.
HLOS ordering is proven, secure-handler necessity is not (PAS13 handler source
is unavailable). CP_INIT does not need ZAP, so there is no circular dependency.

Next real GPU work: qualify native parent ARC rails, CX/GPUCC access and the
GMU/SMMU/SQE/CP_INIT path; then combine b02 copy/readback and AUTH at the native
ZAP point. Do not add a standalone copy-only reboot, and do not present an early
bare AUTH as source-equivalent sequencing. Native AUTH continuation count has no
8-call guarantee; our8 cap is diagnostic, not inferred from small image size or
INIT behavior. All memory/storage/peripheral/90–120Hz/daily-use requirements remain
part of the full goal; none are waived by these PAS milestones. Codex authors,
reviews and interprets; DSH executes only reviewed commands and actual reports.



### 2026-11-06 — 0117 normal native build and independent image review PASS

Code8c527d79caf7b69cac148c9a3102952c0fba5e96; full49 host files passed on fresh
source117-codex5263 files SHA7fc320d69c15d3e2f548f0e20d10ec14644b30eaf3fcb295d5178c5e15a1139d.
DSH standard local make/dSYM/strip/install succeeded, run gauguin.7tVAmW.
Manifest SHAfc2c4d220301a2bb92b93a730b480ec85c835644eef0963e53e2413c86b0678d;
installed kernel16850744B SHA0db53c680525f7e93183b05bd33a440540a96c2b301dc75efe627306094f5335.
BuildID xnu-119adf637ad14a8d9a6b2c692ab94838, banner Nov6 19:01:58CST.
Qualification preserved all source/input/SDK recorded-input/revision/original
mkadt/kernel/archiveversion.o checks and adds the three MEM API defined symbols.

Image shim/out/shim-p3-pasmem-0117-native-20261106.img19464192B SHA
 aa2e6fa6e235e3fc41e746cbbf76c7e4e1babcfc86a916d5c1996b4649bc79e9;
payload19136512B SHA90e16aa6d847442084e13cae2725354883bb8070442228a46ffc3c205ac7df29.
Actual0x48/608 command line499B: unique sweettrial=pasmem-0117-20261106-a1,
sweetbusvote/sweetpasinit/sweetpasmem/PASprobe/PASstage=1, other probes/PET/reboot/
wdttest/touchmode=0, NVT1/hz30/cpus8, sweetsample=- with three sampler timings
removed. This is an intentional complete-token change; core log/UI/root flags
retained. Loader optional diagnostics now have room again. Do not require them
as runtime qualifications for the new worker.

Old shim/DTB/baseADT/NVT/MDT pins intact; independent boot/header/actual cmdline,
ADT,10 native segments, asset pads and2MiB zero tail checked. Baselines113–116
preserved. NVTasset18254c000/MDTasset182570000 remain package sources, not runtime
low reservation claims. Records research/tmp/dsh-0117/native117-execution-result.json,
research/tmp/p3-native-0117-qualification-20261106.json,
research/tmp/p3-pasmem-0117-native-evidence-20261106.json,
research/tmp/dsh-0117/image-parent-review.json PASS. Build73083 terminal0; independent
image checker finishedPASS. No117 boot or MEM_SETUP hardware call yet; phoneTWRP.

Next: sanitized7path single-parent snapshot from public22a18e... and one temporary
boot with180s observer. Prepared verify_pas117.py binds the exact tested source,
image/log/trial and both native PAS phases; bounded BUSY/continuation behavior is
checked from per-fresh raw chain records/counters, finalfull64 x0/x1=0 and matching
coordinator receipts. Intermediate continuation registers remain bound-code evidence.
Only user evidence for THIS117 trial can qualify autonomous reset; 116 confirmation
cannot be reused. No b02 load/AUTH_RESET/GPU/Metal/high-refresh proof in this phase.
Keep the full goal active and original mkadt edit untouched.



### 2026-11-06 — 0117 MEM_SETUP implementation, native TUs and full 49-file suite PASS

Previous goal turn made real progress: 0115 native BCM completion and 0116 PAS
INIT_IMAGE acceptance (three continuations), both followed by user-confirmed
normal-runtime watchdog reset. Full daily-use/GPU/Metal/high-refresh goal remains
active and incomplete. Phone remains in TWRP; no 0117 device operation yet.

Codex authored/reviewed 0117, extending the existing PAS C/header and coordinator
(three XNU paths, no new native files). INIT and MEM_SETUP share one private SMC
engine. Successful INIT publishes an immutable private PA before release COMPLETE;
MEM acquires that state and takes no caller PA/size/receipt input. Separate MEM
latch allows one attempt; MEM failure preserves INIT history and quarantines MEM
and WDT authorization. No buffer read/write/remap/restage/free, b02 load, AUTH_RESET
or GPU command is added. New sweetpasmem=1 requires sweetpasinit=1; invalid flags
are rejected before the whole experiment. Zero/absent preserves 0116 behavior.
Enabled coordinator logs MEM_SETUP pending; disabled path retains the old text.

Pinned native source/ELF/DT evidence in research/tmp/dsh-0117/
mem-setup-native-evidence.md confirms frame 42000202/3/13/same dynamic PA/4096/0/0,
extra_size=0, and the same region_start for INIT then MEM_SETUP. The 4096-byte ELF
span is distinct from the 1MiB owner allocation and 16KiB staging page. Shared
engine preserves full x0..x6 continuation, low32 signed BUSY-12 fresh retry,
68 fresh/8 continuation limits, separate 5s transaction deadlines and fresh
10s entry/3s later WDT budgets. No software bound cancels a nonreturning SMC.

Frozen helper C SHA d62a14094a1e86882360e87308bb288c5079dc87eb07ba5b4596cfe42d180816;
header SHA 1b25730874b35ce4b5b139542524ea99945136c84ac10ef92039ac0a95e2ba62;
coordinator SHA 2320dab5041b9a30f2c96f3b9c488337c1cf84cc2b386fb6613f1b84215788ec.
DSH executed reviewed native TUs against 0116/XShBw1: helper24952B object SHA
 aad122b9d013e2de04d35b3437aeaf52d3f8a45760825a470043cc38e4129f63,
report research/tmp/gauguin-nvt-p1/pas117-init-tu/run-ugv3q8rc/compile.json;
coordinator28328B object SHA61cb747696bc4501d1a288084b0e35d45346e718d0d6678172ff4ba1012bc9d5,
report research/tmp/gauguin-nvt-p1/pas117-coordinator-tu/run-4_ah1d9k/compile.json.
These are isolated TU results, not full linking or hardware evidence.

Focused ASan/UBSan PASS: PAS133 cases (69 retained INIT +64 additions, actual
INIT-to-MEM publication/transaction) in pas-mem/host/logs/pas-mem-38ydfbs7/result.json;
coordinator149 (100 retained +49 MEM) in coordinator-host/logs/coordinator-shzotezr/result.json.
Both under research/tmp/dsh-0117. Public fixtures equal the frozen candidates;
public runners use XNU_SOURCE and temporary outputs, no private runtime dependency.

Fresh strict111-patch replay and all49 test files PASS. source117-codex has5263
files, SHA7fc320d69c15d3e2f548f0e20d10ec14644b30eaf3fcb295d5178c5e15a1139d.
Exactly the three dev files changed vs116 and match combined candidate bytes;
source116 unchanged and tested117 unchanged. Authoritative machine report:
research/tmp/dsh-0117/replay-full-host-result.json, host_exit0/statepassed.
Task text accidentally named prepare_and_test116.py inside dsh-0117; actual DSH
bash event invoked the reviewed existing prepare_and_test117.py once. Root checked
that actual command, script, fresh source and result; no second replay/test run
was needed, and the original task/event record is preserved. All DSH handles
45679/42672/11891/24217 terminal0. DSH remains executor only; Codex interprets.

Next: commit tested changes, standard local full build/qualification/package and
independent image review, then one controlled MEM_SETUP trial. Prepared117 packer
explicitly replaces whole sweetsample=names with sweetsample=- and removes its
three now-unused timing options before adding sweetpasmem=1. Omitting sweetsample
would enable defaults, so '-' is deliberate; core logging/UI flags remain.
Source sweet_sample.c:70-78 proves '-' returns before timing-option parsing.
Verifier verify_pas117.py now pins the tested source SHA and supports both phases'
actual bounded BUSY/continuation paths, complete raw records per chain and final
full64 x0/x1 zero. Intermediate continuation values remain source-bound evidence.
No117 full image/boot/PAS MEM_SETUP hardware result yet. Preserve original mkadt
edit and all113–116 artifacts. Public branch is still22a18e... (116); never push
private ancestry. No new permission is needed for authorized temporary boots/push.



### 2026-11-06 — 0116 PAS INIT_IMAGE success and autonomous normal-running reset VERIFIED

User confirmed THIS116 trial: “是，自行重启，我没有操作”. Parent rechecked all
technicalinputhashes and combined this newfact in
research/tmp/dsh-0116/hardware-parent-verification.json. Authoritative outcome:
one PAS13 INIT_IMAGE request,3nativecontinuations/4SMCentries, finalfull64x0=0
ANDx1=0; controllercompletion andactualautonomous131s recoveryverified. This is
INIT_IMAGE acceptance only, NOT MEM_SETUP/AUTH_RESET/GPU/Metal/measuredbandwidth.
Resetoccurred afterthecallreturned; arbitrarynonreturningSMCcontainmentunproven.

One temporaryboot accepted19008KB/send0.446s/boot0.135s,total0.588s. Observer0,
explicitbackTWRPafter131s/no timeout; start10:31:49.861156Z,
finish10:34:06.729807Z. Fresh4422line/490785B log
research/tmp/p3-pasinit-0116-native-observer-20261106.txt SHA
bd72b9c44729b6046dba67754d9aeec090477df180bf704d5d9e9952807fd715.
Cycle1123B SHAc6064d9384b5a416f7808e9f8ce9678900dc7b1cf61bd08780e59c8c36e307a7.
Fullbannerxnu-cbe548b930ef405d997c9827399f659d anduniquetrialpasinit-0116-20261106-a1
matchqualifiedimage8bb846dc...339bb9b. Allsevenbootprogressmarkersyes;
no touchinteractionrequested onthis deliberateexpirytrial. Bootreasonpropsempty.

SamebootCPUclaimAA200000/metadata6860/reserved16384,64unmanagedNCpages andpinnedMDT
hash/zero-tail valid beforecall. CMDDB131072B SHA
2cc33dbb89e0f18e7d9f9b13ece29c61ee00f614c760e1e6e126fea24e50f1d0; nativebanks/
6BCM/4ARC validated. Extractedbinary preserved at
research/tmp/p3-pasinit-0116-native-cmd-db-20261106.bin. Comparedwith115,2598bytes
differonlyoutsidealldeclaredheader/entry/auxextents; declaredtablesunchanged.
WDTEN3/BARK655300/BITE753595; arm_at1763637454,readback1763637548,
ready_at1782946490,count32948,timebase19200000Hz. BCMslot1 config80008104,
IRQbefore1/after1/completed2 andsixstatuses10101,10101,00101,10101,10101,10101hex.
Successfulcleanup/heldrequestsmarkerspresent. No failure/PET/panic/survived30.

PASrawlines4037-4041: beforefresh1 fn42000201 arginfo82 pas13 paAA200000;
terminalrawcalls4 hasALLx0..x6zero, fresh1/continuations3; terminalrc0/returned1;
coordinatorPASsuccesscalls4 andretainedbuffer/resetwait. This isONEfreshrequest,
not4INITrequests. The3intermediatefullx0==1 results/full7registerpreservation are
boundreviewedcode+countercontrolflow evidence, notindividuallyrawlogged traces.
The69hosttests hadalreadyvalidatedtightcontinuation andglobal8bound. Independent
Codexreview checkedactualboundC/image/manifest/log andthesequalificationlimits.

Original verify_pas116.py deliberatelyacceptedONLY1SMC/0continuation; DSH ranit
unchanged, exit2scope rejection saved in hardware-data-verification.json. No input,
source oroldreportwasaltered toforcePASS. Separate Codex-authored/reviewed
verify_pas116_continuation.py accepts1fresh+1..8continuations withcalls=1+count,
exactraw/terminal/coordagreement, fullx0/x1zero andallpreviousidentity/resource
checks. DSHactualexit3 (manualunknownthen) inhardware-continuation-verification.json;
parentconfirmednewuserfactabove. Originalrejection remainsvalidforitsnarrow scope.
DSHextractor exit0. Allbuild/observer/verification/extractor sessions terminal;
phoneleftTWRP. No furtherdeviceactionafterautomaticpull.

Codeaebabc2; localpretrialhandoff329a084. Publicsnapshot
22a18e463155bbaeac52620899893f1d040ba2d0 singleparent
41ea3be0b21ca3a887315820a08d1455a8025fa5,7textpaths/privateancestryexcluded.
Currentnativecontextsource116-codex/gauguin.XShBw1. Preserve113/114/115/116images,
allfreshlogs, original7-linemkadtedit. Codexauthors/interprets; DSHonlyexecutes
reviewedcommands andusesmachine-generatedreports, nohandwrittenNOTES/results.

Next concretework: implement a separatelyopted-in PAS MEM_SETUP stage after THIS
BOOT successfulINITreceipt +sameclaimedregion+freshWDTbudget. Pinnednative
subsys-pil-tz.c:656-677 usesx0=42000202,x1=3,x2=PAS13,x3=dynamicbase,x4=size+
extra_size,x5=x6=0. Reconfirm nativeELFspan4096 andextra_size0 fromsavedfirmware/DT
beforeuse; preserve full64return/continuation/BUSY semantics. KeepfirstMEM_SETUP
trial freeof b02load/AUTH_RESET/GPUoperations. Laterb02is1984bytes atsamebase,
onlyaftersuccessfulINIT/MEM_SETUP; do not overwrite/re-stage pendingSCM_RWbuffer.
116cmdlinealready597/608bytes: addinganotherflagrequires intentionallyremoving
unneededwhole sampleroptions or anotherreviewedcompactmode, nevertruncatingtrial.
Normal-runtime reset isqualified; requirefreshbudgets, noPET/rearm/cleanup guesses.
BroaderGPU/Metal/highrefresh/peripheral/daily-usegoalremainsactive andunfulfilled.



### 2026-11-06 — 0116 normal native build and independent image review PASS; trial next

Code aebabc2ad551020e6860163b92e2a682cd557be9. DSH normal local build
run gauguin.XShBw1 make0/dSYM/strip/install, source116-codex5263files
SHA978ca9142745ed6f3bdcae1ba52a8df544169e361a6e448218e89cb7e0fa86e4.
Manifest SHAe296e3faf9d53349962cc714bd3e276630cbc053070e1d1379429648cef30b09;
installedkernel16850456B SHA6aa0674cd4909a6475ee5f1c540b10070560d1b3835de00d3af19c857fedc553.
IDxnu-cbe548b930ef405d997c9827399f659d, banner Nov6 18:29:25CST.
Source/input/SDKrecordedinputs/HEAD/originalmkadt/kernel/archiveversion.o/defined
symbols qualified including3newPASINITAPI symbols. Full49hostfilesPASS beforehand.

Image shim/out/shim-p3-pasinit-0116-native-20261106.img19464192B SHA
8bb846dc1e2e5be6ceb1c9385b3a65251a1f3e2486792da46297e95eb339bb9b;
payload19136512B SHA816dcaec7f99a9513545328114f2557a24f15030d5a06a474e121791bb94a510.
Actual0x48/608cmdline597B hasuniquetrialpasinit-0116-20261106-a1 andsweetpasinit1,
busvote1, PASprobe/stage1, otherprobes/PET/reboot/wdttest/touchmode0, NVT1/hz30/cpus8.
No optionalloaderwdtpre/SCM tokensfit; thisisboundedomission, nottruncatedtrial.
Oldshim/DTB/baseADT/NVT/MDT pinsunchanged;10kernelsegmentscompared, assetpads/
2MiBtailzero,115(and113/114)imagespreserved. No dynamicruntimePAclaim frompackage.

Records research/tmp/dsh-0116/native116-execution-result.json,
research/tmp/p3-native-0116-qualification-20261106.json,
research/tmp/p3-pasinit-0116-native-evidence-20261106.json and
research/tmp/dsh-0116/image-parent-review.json PASS. Build23221terminal0;
independentimagecheckscriptfinishedPASS. No116bootornewSMCyet, phoneTWRP.
Next sanitized7textpathpublicsnapshot parent41ea3be... thenone180s temporaryboot.
No destructivepartitionchange; originalmkadteditpreserved.

Verifierprepared/readreviewed: research/tmp/dsh-0116/verify_pas116.py
SHAe986aeb737bb3a36f53f118691b207de2a8d567a7c608450be3f24230faedba2.
Itbindsfreshimage/log/CMDDB/CPUstage/WDT/BCM andcertifiesonly1fresh/1SMC/0continuation
withfull64x0/x1bothzero, exactPAS13/PA/precall/terminal/coordrecords. Anyotheroutcome
isrejectedwithactualPASdiagnosticsretainedforseparateanalysis. Resetattribution
requiresTHIS116userconfirmation, neverreuse115answer. INITsuccessisnotAUTH_RESET,
GPU/Metal ormeasuredBW. NonreturningSMCcontainment remainsunproven. Goalactive.



### 2026-11-06 — 0116 PAS INIT_IMAGE offline implementation and full49 host suite PASS

No116 image or hardware trial yet. Phone remainsTWRP after the verified115 trial.
Codex authored/reviewed fixedSCM64 PAS INIT_IMAGE helper and optional coordinator
path; DSH executed only reviewed focusedtests, nativeTUs and strictreplay/fullsuite.
The existing115 baseline remains unchanged. Next: commit reviewed116 source,
normal local fullbuild/qualification/package/image review, then controlledtrial.

Patch0116-gauguin-pas-init-image-trial.patch changes exactly4XNU paths:
bsd/conf/files, bsd/dev/gauguin_bcm_coordinator.c, newgauguin_pas_init.c/.h.
New sweetpasinit1 requires samebootCPUclaim + BCMCOMPLETE + freshWDTbudget;
0/absent retains115, invalidnonzero rejects beforetheexperiment. No secondworker.
ExactfirstSMC x0=42000201 x1=82 x2=13 x3=claimedPA x4..x6=0; noMDTlengtharg.
Fixed64ABI is based on historical0110 boardquery andnativecaller, not a newly
validatedsamebootavailability/PAS13-permission claim. DSBsy beforeSMC; existing
NormalNCbufferretained withnoalias/restage/free/postcallimmutabilityassumption.

Full64 x0==1 continuation preservesallx0..x6 withnoUFS/sleep inchain; native
signedlow32 BUSY-12 startsfreshregs/x6zero after30ms. Bounds:68freshattempts,
8totalcontinuations,5sdeadline, initialfresh10sWDTbudget and3s perentry/afterrawlogs.
No softwarebound cancancelnonreturningSMC. Onlyfull64 x0=0 ANDx1=0 qualifiesINIT;
noMEM_SETUP/AUTH_RESET/b02load/GPUexec. Oneattempt; errorquarantinessoftwareonly.
Receipt copiedbeforeterminalreleasepublication. Off/null/alreadyleavesoutuntouched.
OldSCMprobeoff; SECLOGisreadonly/noSMC; CPU_ONisstartup-only; GAUGUINNO_MONITOR1.
Native/code/integrationreviews: research/tmp/dsh-0116/pas-init-review-constraints.md
andparent-plan.json. FinalPAS C SHA95e0f7f6ecc429bed222611c7c744c377da71b1e121e475b64eea41017f2acc1;
header2672196b925a0d849697e4a3d7b7c822dc7f7a43a9a44e5de94c2b01ca36eec6;
coordinator6450a6d5f38a96e1019d63958b37b2defd42e1fd87d652cedd7cf59be33b907b.

ActualDSHexecution: PAS69hostcasesPASS (pas-init/host/logs/pas-init-03mdig3p/result.json),
coordinator58old+42new=100PASS (coordinator-host/logs/coordinator-whcgcwvl/result.json).
StrictASan/UBSan; actualC+explicitSMC/DSB/platformseams, neverphysicalSMCproof.
NativeARM64TUsPASS against115/MRqCtP context: PASobject20256B SHAe69aa1cc...4a33ec,
report research/tmp/gauguin-nvt-p1/pas116-init-tu/run-23kprnbx/compile.json;
coordinator26144B SHA49730713...9f6e6ec,
report research/tmp/gauguin-nvt-p1/pas116-coordinator-tu/run-n3_ay746/compile.json.
These machine-generatedreports are authoritative; DSH's hand-written tu summary
contains an invalid placeholder timestamp and is not used as time evidence.

Freshstrict110patch replayPASS frompinnedupstream; source116-codex5263files SHA
978ca9142745ed6f3bdcae1ba52a8df544169e361a6e448218e89cb7e0fa86e4. Exactlythe4paths
above differfrom115 andmatchfrozencandidates. All49testfilesPASS, hostexit0,
sourceunchanged, baseline115unchanged. Records research/tmp/dsh-0116/
replay-full-host-result.json, replay116.log, full-host116.log. NativeTU1797,
PAShost14443, coordinatorhost1573, fullsuite6281 areallterminal0.

Public116 tests use XNU_SOURCE andrepo fixtures/temporaryoutputs, noignoredlocal
runtime dependencies. Originalmkadteditstillpreserved. PublicHEAD41ea3be... is115;
neverpushprivateancestry. Latest115hardwarehandoff b867024. Broadergoalactive.



### 2026-11-06 — 0115 native BCM completion and autonomous normal-running reset VERIFIED

User confirmed THIS115 trial: “是，自行重启，我没有操作”. Parent combined this
new fact with unchanged input hashes of the successful technical verifier;
research/tmp/dsh-0115/hardware-parent-verification.json is authoritative.
Technical verifier99be6e74...a1c0c7 executed byDSH once, actualexit3 solelybecause
manual-resetwasunknown then; preserved hardware-data-verification.json and
verify-observed-dsh-result.json are history. AlltechnicalchecksPASS.

One temporaryboot accepted19008KB/send0.444s/boot0.134s,total0.583s. Cycle explicit
backinTWRPafter131s, observer0/no timeout; start10:00:29.771168Z,
finish10:02:46.485701Z. Freshlog4376lines/484692bytes SHA
 d295a99eadc898d6189959b7112befcff938f6110ef16ca713d8d6ed36f2e18d;
research/tmp/p3-bcmsubmit-0115-native-observer-20261106.txt. Cycle SHA
 c1cff853bcd9f0fe0e17abba5eba0e9000ef50260ef87e49d2a411bb57319511.
Unique actualtrial bcmsubmit-0115-20261106-a1 and fullbanner
xnu-754aa35e66a84ffa8cfc01e09ea7b7b6 matched qualifiedimage83b0bf1b...b92a2b.
Allsevenbootprogressmarkersyes; no touchinteractionasked onthisdeliberateexpirytrial.

CPUstage: dynamicownerpaAA200000,1MiB, inputA91BF000+1240000 tail1040000;
64unmanagedpages WIMGd0000006. MDT6860bytes+zero9524 verified before oneREADYclaim.
CMDDBtwofullcopiesstable65536reads, reconstructed131072bytes SHA
 e59408f8032cf567ef0a5db6cd95bef15cc2ae7d1c511e8232482cd496f1e788.
Fourbanks/6BCM/4ARC metadata validated; versus113 RAW575bytes differ, alloutside
anydeclaredheader/entry/aux extent (first2142,last1fa96); alldeclaredtablesidentical.
This is observedbytecomparison, not an explanation of unused-region contents.
DSH extractor executedonceexit0; binary preserved at
research/tmp/p3-bcmsubmit-0115-native-cmd-db-20261106.bin (same131072bytes/SHA);
research/tmp/dsh-0115/extract115-dsh-result.json recordsactualresult.

WDT legacyPET excluded; rawNS GICenable0, initialEN0; programmedEN3/BARK655300/
BITE753595. arm_at1759664573, rawreadback1759664668, readiness1778959663,
readycount32924; CPUtimebase19200000Hz. Readinessdelta1.0049526s agrees with
32924/32765=1.0048527s. BCM ACTIVE1 preflightstable, NSINTID37quiet0;
nativecompletion receipt slot1 config80008104 IRQbefore1/after1/completed2.
Six actualstatuses:10101,10101,00101,10101,10101,10101hex, exact6BOOTdata/wait3b.
AllISSUED +5requiredCOMPL checked; successfulcontrollercleanup marker present,
requestshelduntilreset. No failure/PET/software-reboot/panic/survived30 record.
Per-stepbudget/laterGIC/cleanupreadback success is boundbinarycontrolflow evidence,
not individuallyrawlogged measurements. Bootreasonpropertiesempty; noPMICcauseclaim.

Publicsnapshot41ea3be0b21ca3a887315820a08d1455a8025fa5 has singlepublicparent
 d3cd94b0b771ea8403ca92ed76adc8592363ade9,16textpaths; private d609742 ancestry
notpushed. PhoneTWRP. Fullnativecodefb8041b, runMRqCtP; originalmkadteditpreserved.

Executorinterpretationcorrection: DSH added unsupportedtwo-boot/ring-wrap guesses
to its ignored publish-boot115-dsh-result.json and draftNOTES. Parent andindependent
Codexreview rejected those guesses. Actualfreshlog has ONEbanner/ONEtrial and
NO obs.replay marker. arm/readback95counterticks=4.9479microseconds, notbootduration;
armabsolute91.649s +1.005sready +continuednormalexecution whileawaiting23s expiry
is compatiblewith131sobserverrecovery. No secondboot or repull is indicated.
Rawexecutorcommandexits/hashes retained; its speculativeverdict is not authoritative.
Parentreportrecords thiserrata. DSHmustexecuteonly; Codex interprets andupdatesnotes.

Next: retain115controllerbaseline and prepare reviewed source-correct PAS INIT_IMAGE
using samebootCPUclaim+BCMcompletion+freshWDTbudget; no newSMChasrun in115.
Controllercompletion is NOT measuredBW, PASauth, GPU/Metal, highrefresh or dailyuse.
Normalruntimewatchdogreset does NOT prove arbitrarysecureworldhangcontainment.
Broadergoalremainsactive. No deviceoperationafterautomaticlogpull is required.


### 2026-11-06 — 0115 normal native build and package PASS; hardware trial pending

Code fb8041b941f1dd92229590eaef79240bf6678a1c; source115-codex5261files
SHAa6634f4a8913181ab29ee477ed31abf0b0de92bbfc479428e0e7d70130d35cc8.
All48hostfiles passed before fullbuild. DSH executed reviewed build115.py once,
normal make0/dSYM/strip/install, run gauguin.MRqCtP. Manifest SHA
 a21a22d9a106400d0c5826cfb0b0c90d297e03639dba6556b17498becf0112c0.
Installed kernel16850240bytes SHA
 dc7d872f0c6c8f0f9effd91869e773f0f9e39c37322b86eec69d1abc576a44f4,
buildID xnu-754aa35e66a84ffa8cfc01e09ea7b7b6, banner Nov6 17:55:18CST.
All original qualification checks and new PASclaim/lease/CMDDBprepare/GIC/
transport/coordinator definedsymbols passed. Source/input/SDK recordedinputs,
installedkernel/archiveversion.o/committedHEAD/originalmkadtdiff qualified.

Image shim/out/shim-p3-bcmsubmit-0115-native-20261106.img19464192bytes
SHA83b0bf1bf8d469af87ed227919ab34bd8bb9df0fb573b4485696c76dadb92a2b;
payload19136512bytes SHAb87bb135775772b8ed9523875634eaa0cdee390084476d7e93ecc54b1689ca85.
Initialcmdline584bytes contains unique sweettrial=bcmsubmit-0115-20261106-a1:
busvote1, PASprobe/stage1; wdttest/PET/reboot/busprobe/GPUprobe/SCMprobe/
touchmode0, NVT1/hz30/cpus8. Optional later SCM diagnostic tokens may be omitted
for space; initial marker is preserved. Baseline shim secure-WDT attempt remains.
No new worker PAS/SMC/GPU call. Runtimeclaims dynamic lowCPUstage; packagedMDT
at182570000 is a sourceasset, NOT the lowclaimedPA. NVT sourceasset18254c000.

Records research/tmp/dsh-0115/native115-{execution,dsh}-result.json,
research/tmp/p3-native-0115-qualification-20261106.json,
research/tmp/p3-bcmsubmit-0115-native-evidence-20261106.json.
DSHprocess88269 terminal0; no build remains live. Phone lastTWRP; no115bootyet.
Independent read-only image review PASS: boot-v2/rawpayload0x48/608/ADT,
10native kernelsegments, allpinnedassets, zero2MiBtail, unchanged113/114baselines
andoriginalmkadtdiff. Report research/tmp/dsh-0115/image-parent-review.json;
DSH reviewedscript oneexecution exit0 (image-review115-dsh-result.json).
Next: sanitized16textpath publicsnapshot with parent
 d3cd94b0b771ea8403ca92ed76adc8592363ade9, one temporaryboot with180s observer.
Retain originalmkadtedit and113/114images. Require fresh trial/banner, CPUclaim,
fullCMDDB, WDTready, nativecompletion/receipt + explicit actualrecovery evidence.
Controller completion is not measured bandwidth or GPU/Metal execution.
Normal-runtime114 autonomousreset verified; broadergoal remainsactive.



### 2026-11-06 — 0115 strict replay + full host suite PASS on fresh source115-codex (DSH)

DSH executed the reviewed `research/tmp/dsh-0115/execute-replay-full-tests.txt`
command EXACTLY ONCE (no retry, no edits, no repair, no full build, no device,
no network, no git changes): `PYTHONDONTWRITEBYTECODE=1 python3
research/tmp/dsh-0115/prepare_and_test115.py > replay-full-host-executor.log 2>&1`.
Actual script exit0, state `passed`; started09:17Z finished09:18:49Z.

Preconditions seen by DSH before running: source115-codex/pristine115.tar/record
absent; source114-context SHA256 `738fda98...…3a9557a3` intact; pinned upstream
`1b191cb5…` (tree `5c0fc728…`) present. Strict replay PASSED:109patches from
`git archive` of that upstream, fresh `.deps-cache/p0-20261105/source115-codex`,
5261files, source SHA256
`a6634f4a8913181ab29ee477ed31abf0b0de92bbfc479428e0e7d70130d35cc8`. Exactly the
14 expected paths differ from114 (listed in the result file), baseline114
unchanged, no failure/warning/skip in replay115.log. Full host suite PASSED:
`tests/run-all.sh` with XNU_SOURCE=source115-codex, host_exit0, all48 test files,
101 unittest cases ok/0 fail, terminal line `all host tests passed`, tested source
hash unchanged. `test_bcm_guards.py` (never executed before) PASSED controller
guards rsc-helper15 / legacy-gate-gauguin8 / legacy-gate-other8. New tests
re-passed on this fresh tree: coordinator58, transport147, lease190,
pas_staging3, bus_probe/Loader/86PAS cases.

OBSERVED vs GUESS: this is host/test evidence only (no full link, image or boot)
and the guard test still uses a deliberate sentinel for the non-prefix legacy
path. Record research/tmp/dsh-0115/replay-full-host-dsh-result.json (with log
SHA256s); replay115.log, full-host115.log,
replay-full-host-result.json. Next (Codex/parent): commit tested source, then
normal full build/qualification/package before any hardware trial. Phone last
confirmed TWRP; no115 hardware operation has occurred.


### 2026-11-06 — 0115 bounded BCM transport integrated as draft; offline checks PASS

Next: commit the reviewed/tested0115 changes, then normal local build/qualify/
package and independent image review before any hardware trial. 114 autonomous normal-running reset is now confirmed by
user (no manual action), but does not prove arbitrary secure-world hang recovery.
No115 full kernel/image/boot or bandwidth/PAS/GPU hardware operation yet.

Authoritative candidate research/tmp/dsh-0115/combined; tracked draft
0115-gauguin-bounded-bcm-transport.patch covers14paths (6newfiles), with tests.
One coordinator waits45s, claims actual CPUstage READY (bounded5s wait), prepares
this boot's CMDDB from two complete readonlycopies, arms/observes WDT once, then
submits the exact six-command native BCM batch onACTIVE1. Old RSC entry is hard
excluded beforelock/map when sweetbusvote1; old WDT sampler/PET excludedtoo.
FreshGICNSINTID37(bit5)quiet guard, ownRSCIRQbit1 acquire/newcompletion,6ISSUED/
5COMPL, exactpayloadreadback, nativecleanup andownbitrestore required. NoCMD_STATUS
clearguess, maskedIRQfallback, retries or vote rollback. Anyuncertain write
quarantines untilreset. Transaction10s +freshWDTbudget15sstart/3sstep guards.
COMPLETE meanscontrollerrequestcompletion, not measuredBW/GPUexecution.
Successful requests remainheld untilreset; no sleep/wake/PDC program orPAS/SMC.

PAS READY API preservesdualparamstageABI; releasepublishedimmutable dynamicPA,
6860raw/16384reserved, oneacquireclaim onlyafterfullcopy/readback. WDTlease shares
oneattempt with114test; native4writesunchanged, one1sadvancement, freshthreshold/
monotoniccounter/CPU23swindow budget. NoPET/disable/rearm; successfulbudgetreadonly.
Coordinator claimsREADY beforeCMDDB andWDT, avoiding asynchronous45s-stage race.
Newstage/watchdogAPIs andcontrollerenginehavebeenCodex-reviewed.

DSH validation: PASrealpacker3testsPASS (includingoldrawlengthnegative and
8concurrentclaimants); transport147casesPASS; lease87old+103new=190PASS;
coordinator58PASS; CMDDBprepare70old+36new=106PASS andbothactualRAWlogs roundtrip.
NativeARM64 singleTUs PASS fortransport, PASready, lease, coordinator against
114/qsECQd context. These are not full linking/hardware proofs. Initialtransport
fixture compile failedunusedhas helper; correctedfixture nowasserts accurate
completionlog; strictwarnings/sanitizers retained, originalfailurepreserved.
Records research/tmp/dsh-0115/component-validation-result.json,
offline-first-dsh-result.json and individual.log/uniquehostresultdirectories.
Controllerguardtestauthored (actualreadonlyGIChelper +actual
legacyentryprefix; remainder deliberatelyfallbacksentinel, wholeoldbodyhash
preserved) and now PASS (see later executorentry); publictestpinsbaselinelegacySHA
instead ofdependingonignoredtree.

All changes authored byCodex; DSH onlyexecutedreviewedtests/TUs. PhoneTWRP;
no livejob, currentnativecontext still114/qsECQd. Preserveoriginalmkadt edit,
all113/114qualifiedimages and private/public history separation. Fullgoalactive.


### 2026-11-06 — 0115 BCM transport host fixture FAILED TO COMPILE (stopped for Codex)

DSH ran the reviewed `research/tmp/dsh-0115/transport/host/run_tests.py` EXACTLY ONCE
(no retry, no edits, no repair/object patch, no network/device/full build).
actual_exit=1, cases executed0. clang (Apple21.0.0) error:
`transport_test.c:500:13: error: unused function 'has' [-Werror,-Wunused-function]`,
originating from fixture `transport/host/transport_host.c:237` (`static bool has(...)`,
never referenced; real assertions use CHECK()). Binary/mock/ASan run never started,
so there is no result for the C+31 write oracle, the native flow, or new IRQ
failures either way. First python run created `transport/host/logs/`; the sole run
dir is logs/transport-run-ql829y7r (run.log, result.json state `failed`). Record:
research/tmp/dsh-0115/transport-host-dsh-result.json; top log transport-host.log.
RESOLVED: see the later 0115 rerun entry below.


### 2026-11-06 — 0114 autonomous normal-running watchdog reset VERIFIED

User answered the pending attribution question: “是，手机自行重启，我没有操作”.
Parent rechecked unchanged image/log/cycle hashes against the technical report
and combined that explicit fact in
research/tmp/dsh-0114/hardware-parent-verification.json. Result is now verified
normal-running expiry/autonomous recovery after131s. The earlier unknown/exit3
report remains unchanged history, not silently relabeled. EN3/native20sBARK23sBITE,
five enabled increasing counters, explicit observer back-in-TWRP, no PET/software
reboot/panic, full banner and unique trial all checked. This does NOT prove
containment of arbitrary secure-world hangs. Device remains TWRP.

Current115 work (offline, not booted): root authors bounded BCM transport;
Codex agent prepares explicit PAS CPU-stage READY/one-way claim; another prepares
one-attempt watchdog arm/budget API preserving114 diagnostics. DSH will execute
reviewed tests/builds. Native BCM batch semantics: MSGIDs10108,10108,10008,10108,
10108,10108; WAIT3b,ENABLE3f. DRV2 IRQ is actual DT thirdtuple SPI5/INTID37,
GIC NS ISENABLER1 bit5 (distinct from WDT bits0/1). No new hardware write yet.
Keep0113 UI/touch and0114 reset baselines. No GPU/Metal completion claim.



### 2026-11-06 — 0114 timer/automatic-recovery data verified; manual-action confirmation PENDING

Observer saw recovery after131s (not a timeout); fresh114log was automatically
pulled and matched the exact image. Technical verifier checks PASS, but the
user has NOT yet answered whether any button/manual restart was used. Its
honest status is reset-attribution-unverified, --manual-reset unknown, exit3.
Do NOT promote this to qualified hardware reset until that explicit answer.
Pending question: “0114在约131秒后回到了TWRP，日志已自动读回；是否手机自行重启、期间没有按键/手动重启？”
If user confirms no manual operation, combine that new fact with unchanged
verifiedlog/image/cycle hashes for the normal-running-reset qualification.
If manual, preserve this trial and repeat a distinct trial marker if needed.
No fresh trial needed merely to repeat already-passed data checks.

Temporary boot accepted once:18976KB send0.442s/boot0.134s,total0.580s.
Cycle started 2026-11-06T07:34:26.379684+00:00, finished 2026-11-06T07:36:43.035174+00:00;
cycle research/tmp/p3-wdtexpiry-0114-native-cycle-20261106.log explicitly says
back in TWRP after131s; observer0, no timeout/fallback. Fresh log
research/tmp/p3-wdtexpiry-0114-native-observer-20261106.txt,
145871B/2243lines, SHAb0f8998f4680a18c8fc235cdb4f14514eae9843f3f7aa7162dc47f51f085988a.
Full banner xnu-917c2bd2614f4ad78ff771c72785854d, unique actual
sweettrial=wdtexpiry-0114-20261106-a1. Initial commandline569B preserved; later
optional loader-announced diagnostics end afterscmstep3, so this114 log does
not establish secure-watchdog SMC success/status. No such success is assumed.

Exact WDT evidence: legacy sampler/PET excluded; GIC NS ISENABLER1=0 quiet1;
initialEN0/STS0/BARK524287/BITE1048575. Armreadback EN3/BARK655300/BITE753595/STS0,
at1753534148ticks. Samples1..5 EN3, decodedcounts
32872,65750,98589,131463,164336; at
1772798503,1792065310,1811308827,1830573273,1849836554ticks respectively.
Reported kernel timebase19200000Hz. All five count/STSmatches and monotonic
time/count checks passed. Terminalcounter-advancing/awaitingactualreset marker
present; no survived30s, failure, PET, debug-reboot, or panic(cpu) record.
SecondGICguard passage is controlflow evidence from the matching image, not
a second rawGIClog. Pre/post TWRP bootreason properties were empty; do not
invent a PMIC/firmware reset-cause code. Physical attribution awaits user.

Verifier/report: research/tmp/dsh-0114/verify_wdt114.py and
hardware-data-verification.json; DSH actualexpectedexit3 recorded in
verify-observed-dsh-result.json. Parent independently read the fresh records.
No device operation followed the automaticpull except read-only bootreasonprops.
Phone is currentlyTWRP; all DSH/build/observer handles terminal, no live job.
Published114 code snapshot d3cd94b0b771ea8403ca92ed76adc8592363ade9 (single public parent
d9cc88b77311059a053fa8a077bde7773d3e678e), matching privatehandoff69819e3 tree;
no privateancestry/dumps/firmware/serials. Code6f3f067, normalnativeqsECQd.
Original mkadt edit remains uncommitted.

Next stateful step after normal-reset attribution is established: bounded
same-boot BCM transport with exclusive HLOS writer/slot checks, then explicit
PAS-stage READY publication and source-correct INIT_IMAGE ABI. Review
research/tmp/dsh-0113/next-pas-parent-plan.json; idleTCS does not prove current
bandwidth. This expiry experiment is not proof of containing arbitrary secure
world hangs, and no GPU/Metal/bandwidth/PAS auth operation has occurred.
Goal remains active; current work materially advanced timer programming and
actual recovery evidence, not merely a plan. Codex codes; DSH executes.



### 2026-11-06 — 0114 normal native build/image qualified; expiry trial next

Code commit6f3f067bad26d8bb18818a3aa9f7c8f7d4574099. source114-context:
5255files SHA738fda981dbee40acd133f2542e05cb3db5d26ac292e61ccb86a06fe3a9557a3;
full45hostfiles PASS, including87actualworker/helper/legacy-gate cases. Stronger
context fixture catches oldsource114-codex's invalid-context UFS mark at runtime;
fixed source prints but never persists in invalid context. No source-only PASS
has been mistaken for hardware reset qualification.

DSH normal local build gauguin.qsECQd:make0,statebuilt, normaldSYM/strip/install.
Manifest SHA6f1c86cf6bc59277ae1737ae2e0e1407e4d63efae35384971d35785b75c92a26;
installed kernel16816136B SHAe99b9312fdefcffd73f1a3203d174489a07f02228b4652014810217ae28ea8b9,
ID xnu-917c2bd2614f4ad78ff771c72785854d, banner Nov6 15:30:37 CST.
Full source/recordedinputs/SDKinputs/HEAD/originalmkadt/ARM64/symbols/version.o
qualified in research/tmp/p3-native-0114-qualification-20261106.json.
Image shim/out/shim-p3-wdtexpiry-0114-native-20261106.img,
19431424B SHA13b95042ce14961a0560b86cfefde862beaf971c68b87fe747c9f9cbb9caaec3;
payload SHAef9d36eb66fb72f08c7149ebd03b893c25a5cb17bdfda41c3288c27ad2e09284.
All old shim/DTB/ADT/NVT/MDT pins and payload bounds checked; parent independently
reparsed image and its569B command-line field. sweetwdttest1, PET/reboot/bus/GPU/
SCM/touchmode/PASprobe/PASstage0; NVT1/hz30,cpus8, unique
sweettrial=wdtexpiry-0114-20261106-a1. 0113 image unchanged.
Report research/tmp/dsh-0114/image-parent-review.json PASS. No114 boot/arming yet.

Next: sanitized single-parent public push, temporary boot once/180s observer.
Tell user this round intentionally expires the APSS watchdog and not to press
buttons. Actual reset requires the observer's explicit back-in-TWRP record,
not merely exit0 (timeout then manual recovery can also yield0). Require a
fresh fullbanner/unique-trial log, legacy exclusion, raw firstGICquiet, exact
EN3/BARK655300/BITE753595, five enabled strictlyincreasing decoded counters,
no failure/PET/software-reboot/panic, AND explicit user no-manual-reset evidence.
Second GIC check is inferred from boundimage controlflow, not a second logged
raw value. Verifier prepared dsh-0114/verify_wdt114.py, not yet executed.
If success, claim only normal-running expiry; secure-world hang containment is
still unproven. No GPU/bandwidth/PAS authentication happens in this experiment.

Phone last confirmedTWRP. No native build remains live. Current generated native
context is source114-context/gauguin.qsECQd; prior113 retained as baseline.
Original mkadt.py edit remains uncommitted. Codex authored/reviewed; DSH executes.
Broader daily-use/GPU/Metal/peripherals/high-refresh goal remains active.



### 2026-11-06 — 0114 native build/qualification/packing PASS; not booted

DSH ran the reviewed `research/tmp/dsh-0114/build114.py` EXACTLY ONCE from the
repo root at HEAD 6f3f067bad26d8bb18818a3aa9f7c8f7d4574099 (only `M tools/mkadt.py`
dirty, preserved). Process exit0 and script exit0; no retry, no source edit,
no repair, no manual strip, no DSYM disable, no network/CI/git mutation, no
device access. All three steps passed:
- build_exit0, new run gauguin.qsECQd (exactly one new run), manifest state
  built, make_exit0, normal dSYM/strip/install. Manifest source SHA256
  738fda981dbee40acd133f2542e05cb3db5d26ac292e61ccb86a06fe3a9557a3 equals the
  tested source114-context (wrapper asserts it).
- qualification_exit0, BUILD QUALIFIED, final_kernel_produced true; kernel
  16816136B SHA256 e99b9312fdefcffd73f1a3203d174489a07f02228b4652014810217ae28ea8b9,
  ID/banner xnu-917c2bd2614f4ad78ff771c72785854d (Nov6 15:30:37 CST).
- package_exit0, state `packed-not-booted`.
Image shim/out/shim-p3-wdtexpiry-0114-native-20261106.img, 19431424B,
SHA256 13b95042ce14961a0560b86cfefde862beaf971c68b87fe747c9f9cbb9caaec3 (rehashed
by DSH); payload research/tmp/p3-wdtexpiry-0114-native-20261106.bin 19103744B
SHA256 ef9d36eb66fb72f08c7149ebd03b893c25a5cb17bdfda41c3288c27ad2e09284; evidence
research/tmp/p3-wdtexpiry-0114-native-evidence-20261106.json. Evidence cmdline
569B: sweetwdttest=1 with PET/reboot/bus/GPU/SCM/touchmode/PASprobe/PASstage all 0;
marker sweettrial=wdtexpiry-0114-20261106-a1 (one occurrence in image strings);
ZAP MDT PA182568000/raw6860/res16384 zero-padded. Boot field "NOT BOOTED".
DSH record research/tmp/dsh-0114/native114-dsh-result.json (logs
native114-build/qualification/package/executor.log, native114-execution-result.json).

OBSERVED vs GUESS: host build/qualification/packing success is not hardware
evidence. The actual watchdog expiry/reset is UNQUALIFIED; it needs a separate
Codex-reviewed temporary boot with a fresh log matching the full
xnu-917c2bd2... banner AND the unique trial marker, and the image still carries
the baseline loader secure-WDT SMC attempt (no whole-boot SMC-free claim).
Phone last confirmed TWRP. Next: independent image review, then one temporary
expiry trial (no flash/format/partition writes).


### 2026-11-06 — 0114 watchdog expiry candidate authored, not yet qualified

Previous goal turn made verified hardware progress:0113 CMDDB/DRV2/touch PASS.
The current task qualifies a real automatic reset before stateful GPU bring-up.
Codex has authored research/tmp/dsh-0114/candidate/ and integrated draft patch
0114-gauguin-watchdog-expiry-test.patch (not yet committed). Preserve113 baseline.
Default-off sweetwdttest=1 starts one delayed kernel thread. SweetWatchdog startup
excludes its old sampler/PET before any callout allocation when the flag is set,
while retaining userland IOWatchdog/PMU stubs and read-only secure diagnostics.
The worker rejects nonzero PET/reboot/bus/GPU/SCM/touchmode/PASprobe/PASstage flags;
PASworker ALSO waits45s asynchronously, so do not assume it completes first.
This dedicated114 image will turn both CPU PAS flags off.

Native-sourced thresholds:32765Hz, BARK655300 (20s), BITE753595 (23s), EN3 then
one RST1. EN1 is NOT proven to mean bark masking. A new read-only pe_fiq helper
reuses GICD mapping, validates PA17a00000, reads ISENABLER1@104 and requires NS
SPI32/33 enable bits clear; no GIC writes, no claim of secure IRQ ownership.
WDT17c10000+1000 must be unmanaged/Device, translate exactly and startEN0;
thresholds read back before enabling. Five finite counter samples, then no pets,
no cleanup writes, no software reboot fallback. 30 requested seconds without
reset logs failure, not success. Real automated recovery plus fresh unique-trial
log required; this will only qualify normal running reset, not arbitrary
future secure-world hang containment. Existing shim still makes a pre-kernel
secure-WDT SMC attempt (113 returned-2), so do not claim the wholeboot is SMC-free.

Code/source review closed the concrete context bug: wdt_record now prints but
never synchronously marks/flushes UFS in invalid context. The stronger fixture
rejects the old source114-codex at runtime (bad context after delay / synchronous
mark requires preemptible thread context), after successful compile. Fresh
source114-context strict replay PASSED all108 patches;5255files SHA256
738fda981dbee40acd133f2542e05cb3db5d26ac292e61ccb86a06fe3a9557a3; exactly5 source
changes vs113, preserved113 unchanged. Full45 test files PASS, including87actual
worker/helper/legacy-gate cases, ASan/UBSan; tested source unchanged. Prior
87/45 passes on oldsource lacked the new context assertions and are not final
qualification. Reports dsh-0114/context-tests-dsh-result.json and
replay-full-host-context-result.json. Initial ARM64 singleTU PASS before the
PAS flag/context-log fixes (historical only), report
research/tmp/gauguin-nvt-p1/wdt114-codex-compile/run-itbjzet3/compile.json;
no current full114 build/image/boot/arming. Next: commit this tested source,
DSH normal local full build/qualification/packing, then independent image review
and one temporary expiry trial. Do not equate host success with hardware reset.
Current native build context remains113/67UNbi. Phone lastconfirmedTWRP.

DSH executorcontextturns(tests/testwdt_expiry.py):
observed: oldsource114codex (precontextfix) compiles (clangexit0)
but runtime FAILS line175 "synchronous mark requires preemptible thread
context", test exit1, as Codex review predicted (expected negative, not a
compile failure). Fresh strict replay to .deps-cache/.../source114context:
exactly5diffs vs113, api hash738fda98...(5255 files), baseline
unchanged; tests/runall.sh exit0, 45sections, WDT fixture PASS (87 cases),
tail "all host tests passed". Record
research/tmp/dsh0114/contexttestsdshresult.json; logs
oldcontextregression.log / replaycontextexecutor.log /
replay114context.log / fullhost114context.log. History preserved (old
45file PASS untouched). No build/device/network/git/source edits.
Note: source114context was replayed from the current working-tree patch set
(uncommitted tests + draft0114), not from a committed state; old
source114codex tree is unchanged and still contains the invalid-context bug.
Last public handoff d9cc88b77311059a053fa8a077bde7773d3e678e (parent586ae424...),
local baseline handoff534fbc45472f9af90424543b0f10e04bfac6285f.
Original mkadt.py edit remains untouched. See dsh-0114/parent-state.json for jobs.



### 2026-11-06 — 0113 real CMDDB/DRV2 readback VERIFIED; touch unlock retained

Next concrete action: preserve0113 and qualify an actual enforced reset path
before any maximum BCM vote/PAS INIT_IMAGE. The previous WDT PET path only
writes RST while EN=0; stopping it is NOT a proven timeout. Audit all writers,
use an exclusive opt-in watchdog test with native-sourced configuration and
counter/readback evidence, and require an observed automatic recovery plus
fresh same-trial logs before calling a later stateful operation time-bounded.
Then implement the bounded BCM transport/SCM READY interface per
research/tmp/dsh-0113/next-pas-parent-plan.json. Idle TCS state is not a current
vote floor or controller lease. No BCM submission, PAS authentication/reset,
GPU execution, Metal acceleration or high-refresh qualification is complete.

0113 trial accepted once (send18976KB0.442s, boot0.134s,total0.582s).
Observer finished182s/exit4, no recovery detected and removed failed log output.
The user then explicitly confirmed THIS trial still touch-unlocks and manually
returned TWRP. DSH fresh read-only pull succeeded; parent independently verified
full banner xnu-966ac3a2b60d46a49c0f2124f4a1f028 AND the unique actual
sweettrial=cmddb-0113-20261106-a1. No stale observer output was reused.
Phone currently TWRP; no observer/build/DSH job remains live.

Fresh log research/tmp/p3-cmddb-0113-native-recovered-20261106.txt,
597248B/5715lines, SHA4df4747997a44ffacdedf52fb99e17e55a915e6b33fbd0c22c509348356fc66d.
Complete RAW extraction131072B at
research/tmp/p3-cmddb-0113-native-cmd-db-20261106.bin,
SHA76634d6f254ff6436b10ce723550edc5b7d2f5e675b5cee38e01339b820ba441.
All2048 contiguous chunks and BEGIN/END hashes verified. CMDDB both copies
matched after65536 aligned loads; pmap/readonly map gates passed on8 CMDDB
pages and1 RSC page. All6 BCM rows exactly match the reviewed board constants;
BCM bank version is observed0x1000. Actual banks: ARC3/count22/version1000,
ARC3/count9/version1000, BCM5/count40/version1000, VRM4/count65/version0100.
The four ARC tables match the prior recovery text. No checksum validation was
invented (native CMDDB parser ignores that field).

DRV2 config80008104 => count8,ncpt16,end20cc; irq_enable1,irq_status0.
Both full whitelist captures matched. All TCS0..7: WAIT0/CONTROL0/STATUS1/ENABLE0;
therefore ACTIVE0/1 are two **candidate** idle slots, no ownership established.
Six PLAN ONLY data words:6fffffff,6fffffff,2fffffff,6fffffff,6fffffff,60000008;
waitmask3b. Terminal exact record says no bandwidth submitted/no GPU execution.
0112 CPU staging still completed6860 MDT/9524zero-tail with the pinned SHA.
Last NVT17952accepted/0rejected; last PETcount240 en0/sts0; no captured panic(cpu).
Physical touch is user-confirmed, not inferred solely from these counters.
Reports: research/tmp/dsh-0113/hardware-recovered-result.json and
hardware-parent-review.json (PASS); cycle p3-cmddb-0113-native-cycle-20261106.log.

Code commit f805edadc44f8a71302201f26b6428076dfca3ec, native source/build
source113-codex/gauguin.67UNbi; exact qualified image/hashes are below.
Published sanitized snapshot586ae424ef8aea7b0a7a75b5220b7c86c857d9b1,
single parent4f254bee8c295f1b522e6c2c7ea985a77a7897c7, treefa97560663f1c163deb3015799915ded57b2b4e2
matched private handoff8bf51773a1f37d9a1912f5bbccbd50c4fc33594a's tree. Only10
reviewed text files; no private ancestry, firmware, dumps or device serials.
No CI. Original tools/mkadt.py seven-line edit remains uncommitted.
User's current division: Codex writes critical drivers/tests; DSH executes
reviewed commands with full filesystem access and local-tools-only overlay.
Active daily-use/GPU/Metal/RAM/storage/peripheral/high-refresh goal unfinished.



### 2026-11-06 — 0113 native build/image qualified; hardware pending

Code f805edadc44f8a71302201f26b6428076dfca3ec; all44 host files PASS on fresh
source113-codex,5254files, SHA25625e512230ac39005af541a11cc57add56b7bb7222d07a9ec1a87dcdf4fcc9f8e.
DSH normal native build gauguin.67UNbi finished make0/statebuilt, normal dSYM,
strip/install. Manifest SHA06d8539c8a86d72fb0a8b06a498b1834a9ac6f6bbd42a7db569dc9fd5d4fc0d9.
Kernel16815816B SHA26694e5d88e9c29495c317adb14f48a9f6688622390d802c34bb0b645334e906,
ID xnu-966ac3a2b60d46a49c0f2124f4a1f028, banner Nov6 14:45:30 CST.
Qualification research/tmp/p3-native-0113-qualification-20261106.json verifies
source/all recorded inputs, HEAD/original mkadt diff, installed ARM64 kernel,
defined0113/NVT/PAS/SHA symbols and matching archive version.o. No hardware claim.

Image shim/out/shim-p3-cmddb-0113-native-20261106.img,19431424B,
SHA7615dd2a0295760f8b76d50c661c0023a66079aa961fb1fa8f5780c32523fe73;
payload research/tmp/p3-cmddb-0113-native-20261106.bin,
SHA83fc542aa9f5e41b49e8e87b31924cd80c1b35e7b00c6218aff64d96629dff77.
Same verified shim/DTB/baseADT/NVT/MDT pins. NVT PA182544000/raw139264/res147456;
MDT PA182568000/raw6860/res16384; all padding and runtime request bounds checked.
Actual payload command-line field536B (not an ADT boot-args property):
sweetbusprobe1, sweettouchmode0, NVT1/hz30, GCC/SCM0, PASprobe/stage1, cpus8,
sweettrial=cmddb-0113-20261106-a1. Parent independent image/command-line review
PASS (research/tmp/dsh-0113/image-parent-review.json); baseline112 image unchanged.
Initial packaging stopped before writing because its report path still named112;
protection preserved112 evidence. Codex corrected only the path; DSH repack exit0
(native113-repackage-result.json). The failed pipeline record remains unchanged;
no rebuild was required. Full image evidence: p3-cmddb-0113-native-evidence-20261106.json.

Phone last confirmed TWRP; **0113 NOT BOOTED yet**. Next: sanitized public
snapshot (never private ancestry), temporary boot once/180s observation, user
touch check/manual TWRP, then fresh log matched by full banner plus unique trial.
Use tools/extract_cmd_db_snapshot.py on that fresh log and inspect actual BCM/ARC
metadata plus DRV2. This image submits no bandwidth, PAS call or GPU operation.
Native generated context now source113-codex/gauguin.67UNbi, not112/fbWj14.
Codex writes critical code; DSH executes reviewed build/test/boot commands with
full filesystem access and local-tools-only overlay. Original mkadt edit remains
uncommitted; no CI run. Broader GPU/Metal/daily-use goal remains active.



### 2026-11-06 — 0113 native build+qualification PASS; packaging FAILED (path collision)

DSH ran the reviewed `research/tmp/dsh-0113/build113.py` exactly once from the
repo root at HEAD f805eda with only `M tools/mkadt.py` dirty; wrapper exit1;
NOT retried and NOT fixed. Exact codes from native113-execution-result.json:
build_exit0 (`gauguin.67UNbi`, manifest state built, make_exit0, created
06:43:10Z/finished06:45:41Z, verified0113 source 25e51223..., committed head
f805eda), qualification_exit0 (BUILD QUALIFIED, final_kernel_produced true;
kernel 16815816B SHA256
26694e5d88e9c29495c317adb14f48a9f6688622390d802c34bb0b645334e906),
package_exit1, final state `package-failed`.

Failure: `AssertionError: preserve any prior images` at
pack_native0113.py:50. Verified cause: OUT and PAYLOAD are absent, but
EVIDENCE (line15) points at the pre-existing qualified0112 file
research/tmp/p3-passtage-0112-native-evidence-20261106.json (mtime11:56,
untouched); line177 would write the0113 report there. That is the only tripped
term; the qualification-prefixed asserts passed. No0113 image/payload was
written, nothing was deleted, and the shim/baseline/ADT/MDT hash asserts were
never reached (DSH checked those four separately: all match). No boot, no
device access, no CI/network, no source edits. Build output of67UNbi is
preserved and reusable. DSH record research/tmp/dsh-0113/native113-dsh-result.json
(ignored, like all research/). Next: Codex repoints EVIDENCE to a new0113 path,
then reissue the executor task. Approved hardware-trial command
(EXACT once, no second boot, no flash/format/partition writes):
`fastboot boot shim/out/shim-p3-cmddb-0113-native-20261106.img`. After the
temporary boot, ask the user to confirm touch unlock and manually return to
TWRP, then pull a fresh log; treat the result only as read-only evidence.

### 2026-11-06 — 0113 read-only bus qualification in progress; division of work updated

Latest user instruction supersedes the older DSH-authoring preference below:
**Codex writes critical drivers and reviews; DSH executes compilation, tests and
boots**, with danger-full-access retained. Baseline remains the verified0112
image/source above; phone last confirmed in TWRP. No0113 boot, bandwidth vote,
PAS call or GPU execution has occurred. The active goal remains unfinished.

Current work is a default-off, one-shot `sweetbusprobe=1` worker: copy reserved
CMDDB80860000+20000 twice using aligned read-only loads, validate the six BCM
rows/four ARC tables from normal memory, then inspect only the native-backed
DRV2 register whitelist at18220000+4000. It emits a complete bounded RAW dump
and a PLAN ONLY result. Empty/idle TCS observations cannot recover inherited
bandwidth votes and do not grant ownership. No commands are submitted.

Source review and focused execution now PASS. Codex removed the uninitialized
offsets comparison and corrected exclusive end to20cc. Worker SHA256
8e71b4e9f7e19c8b71e6861af0399b66c6b21348a3fbb5835c4a02ab3ba13eea;
DSH native ARM64 single-TU exit0, object48896B/e49f4f6b48dcf42efd2a5fe26208aadf94582e7990ff79dbbc03512c2740cd81,
report research/tmp/gauguin-nvt-p1/cmddb113-worker-codex-compile/run-rrv95zgc/compile.json.
The parser and planner separately passed the same112/fbWj14 build context.
DSH ran70 actual-worker host cases with ASan/UBSan and strict platform seams;
actual worker RAW -> real image/trial-bound extractor -> exact131072B synthetic
fixture succeeded (sha72ef88e51effc3c7e832816e4390299909deddd6dd8ec036917351e2af7d80b3).
Report research/tmp/dsh-0113/flash-high-worker/logs/worker-run-ha_z9vlu/result.json.
Native crypto is seamed in host tests, not independently exercised there.
Earlier j5fa7iug run aborted before entering tests because Apple arm64 lacks
LeakSanitizer; platform-corrected runner retains ASan/UBSan. No object rewriting.
Extractor66tests PASS after Codex corrected fixture/expectation bugs; strict
production extractor stayed unchanged. Earlier19failure records are preserved.

0113 patch now integrates five new source/header files plus three build entries
and one GAUGUIN init hook. Public tools/tests contain only synthetic fixtures.
Fresh strict replay to source113-codex PASSED:107 patches,5254 files, SHA256
25e512230ac39005af541a11cc57add56b7bb7222d07a9ec1a87dcdf4fcc9f8e. Exactly the
seven intended source paths differ from112, which remains unchanged. DSH full
host suite PASSED all44 test files, including70 worker cases and66 extractor
tests; tested source unchanged. No full113 build/image exists yet. Results live in ignored
research/tmp/dsh-0113/replay-full-host-result.json and full-host113.log.
Active candidate code is flash-high-worker/bsd/dev/; the other older
candidate/bsd/dev/gauguin_bus_probe.c remains a rejected draft.
Future max-vote/PAS work still needs reset qualification: current WDT EN=0;
stopping PET is not a proven reset, and a software timeout cannot cancel a
secure call that never returns. Maximum numeric BOOT plan is not a daily
thermal/power policy and is NOT submitted by0113.

DSH execution policy: use the private provider-flash-high and local-tools-only
patches in /private/tmp/ios-gauguin-dsh-nPDRPy. Unrelated remote tools are disabled
after an out-of-scope read-only probe (no observed remote modification; no
remote inventory belongs in Git). A prior generated test attempted assembly/
object rewriting and is rejected; no successful runtime proof came from it.
No hand crypto, object rewriting or sanitizer bypass is permitted. Codex now
owns code changes; DSH receives reviewed exact local execution commands and
must stop on failures. Old Pro/Flash authoring jobs are terminal. Completed focused execution is recorded in ignored worker-tu-dsh-result.json,
worker-host-codex-dsh-v2-result.json and extractor-codex-dsh-result.json.

Next: commit this reviewed/tested0113 change, then run the normal local full
build/qualification and temporary read-only hardware trial. Preserve original unstaged tools/mkadt.py seven-line
edit. Local HEAD at entry d81fde38b7575af28177b1443215ac59ff5b9b63;
public branch codex/gauguin-p0-ci-20261105 at4f254bee8c295f1b522e6c2c7ea985a77a7897c7
(tree108df7f1d52559cb1f96233d5cd4df7b18e771b3). Never push private ancestry;
continue sanitized single-parent snapshots only. No new CI run was started.


### 2026-11-06 - 0112 CPU staging: fresh-log VERIFIED; probe + stage gates pass

Next concrete action: treat0112 as the working baseline and preserve it. Do the
next work offline: audit and prepare a bounded, read-only, same-boot CMDDB
identity/bank-bounds check plus the actual DRV2 inherited state/ownership/
aggregation, BEFORE any new RPMh/BCM vote or PAS INIT_IMAGE. Native
msm_bus_fabric_rpmh.c does read BCM aux data and the real prior recovery cmd-db
text already carries BCM aux, so do NOT claim aux is absent; the open questions
are bank identity/version/bounds and inherited DRV2 floor at the same boot. Base
facts are verified in ignored research/tmp/dsh-gpu-bus-audit/REPORT.md; its old
numeric models are withdrawn and NO executable vectors are approved (any vote
needs a reviewed numeric vector first). A successful CPU stage does NOT qualify
PAS authentication or any GPU operation. User DSH fullaccess for implementation
and Codex plans/reviews remains.

Status: PASS on a fresh log. The published0112 image was temporarily booted
once, the user confirmed physical touch unlock in THAT trial, then manually
returned the phone to TWRP; the fresh read-only pull now shows the exact build
identity, the complete owner record (64 pages, wimg=d0000006) and the complete
stage record (6860/9524, pinned sha256). The parent's independent hardware log
review PASSED (research/tmp/dsh-0112/hardware-parent-review.json). No new
boot/flash/build/code/push was done for this verification; no observer or build
is live. Phone is currently TWRP. User preference retained:
DSH runs with danger-full-access for implementation/build, Codex plans and
reviews. Broader goal unchanged: real GPU/Metal is NOT implemented.

Fresh log (this boot only; the observer removed its failed output, so nothing
was reused): research/tmp/p3-passtage-0112-native-recovered-20261106.txt,
3750lines, 275714B, SHA256 201e59867baafe4feee97d19b105f7c02878e0ff1c40f93836d704514477334b,
ring4194304/total275959/flush235, read-only dd from /dev/block/sda35
(userdata114919714816B, blocks28055546..). `adb get-state` was recovery on the
first check (no retries). identity: tools/kernel_banner.py against the image
returned0; line1 carries the full xnu-dc38b2a01c6f471fa523f9f9cdab1f4e and
boot-args on line411 contains exactly one
sweettrial=passtage-0112-20261106-dsh-a1 (the only sweettrial= anywhere), with
sweetpasprobe=1 sweetpasstage=1. This is the actual boot-args of this boot, not
a reused banner.

Raw records (no failures, in order):
- `SWEET PAS PROBE: owner pa=00000000aa200000 bytes=100000 input=00000000a91cb000+1234000 tail=1034000`
- `SWEET PAS PROBE: provenance fdt=00000000a8fca000+44137 shim=00000000a2480000+39000`
- `SWEET PAS PROBE: complete unmanaged_pages=64 wimg=d0000006; metadata only, buffer/PAS/GPU untested`
- `SWEET PAS STAGE: pinned MDT verified; mapping first16KiB NC/RW only`
- `SWEET PAS STAGE: before zero/copy; reserved first16KiB only`
- `SWEET PAS STAGE: complete metadata_bytes=6860 zero_tail_bytes=9524 sha256=6f2a0e35325097f98fded6123d755266cdbb44caa932be61251b65b5c516ac7b`
(lines1947-1952). None of the invalid/mapping-failed/readback-mismatch/
missing-asset stops appear. Last PET `count=200 at=4151740440 en=0 sts=0`; last
NVT `packets=13960 accepted=13960 rejected=0 mask=0`; strict `panic(cpu` count0
(the gPanicBase/exec DumpPanic strings are not panics); last HB
`4 wdt=4 tick=875229 exp=859984 call=15250`. PET units are ticks; a conversion to
seconds is NOT assumed.

The owner PA this boot is whatever the shim placed (0xaa200000 here); it is a
result of this boot, not a fixed address. Hard limits: the probe line itself says
metadata only, buffer/PAS/GPU untested; the stage covers only the first16KiB
metadata page (zero/copy + readback+tail equality in the consumer). This0112
staging path invokes no PAS auth/reset, no SCM call and no GPU/power vote; the
prior0110 SCM64 query probe exists in the source but was disabled for this trial
(sweetscmprobe=0), and the RPMh/touch code is unrelated to staging. GPU/Metal
execution is not implemented. User touch
unlock is USER-confirmed; the log does not independently prove touch.
Record research/tmp/dsh-0112/hardware-recovered-result.json (supersedes the
earlier interim hardware-trial-result.json).

Publish (this session): local HEAD764cd9d8c68d4a5a9049f4e2901197e9c61eab7f
with only the preserved original tools/mkadt.py edit dirty. Sanitized public
snapshot 0e38d207d7089b2cbe657fc290d175b3ca7a6838, single parent public
2084afaf556e57623cf92b7ed48add5c86815509 (verified both local ref and remote
ls-remote before the push; no force, no private ancestry, not HEAD), tree
20c9e36e... identical to HEAD^{tree}. Exactly9 changed files, all text, no
firmware/dumps/serials: NOTES.md; tests/fixtures/gauguin_pas_probe_host.c;
tests/fixtures/gauguin_pas_stage_host.c; tests/test_pas_owner_probe.py;
tests/test_pas_staging.py; tests/test_payload_zap_asset.py; tools/mkpayload.py;
xnu/patches/0112-gauguin-pas-cpu-staging.patch; xnu/patches/series. Pushed only
the new SHA to refs/heads/codex/gauguin-p0-ci-20261105, remote re-verified at
the new SHA and the local branch ref moved2084afa->0e38d20 (guarded). Public
push targets only `main` for workflow, so NO CI was dispatched. Record:
research/tmp/dsh-0112/public-snapshot-0112.json.

Image identity re-verified before the boot: shim/out/shim-p3-passtage-0112-native-20261106.img,
exact19415040B, SHA256 17af66bf150a20a62673d5d0593512d6ae9478dd79598e8dc5cff6ab04e0e847,
full kernel ID xnu-dc38b2a01c6f471fa523f9f9cdab1f4e and one occurrence of
sweettrial=passtage-0112-20261106-dsh-a1 in the cmdline. No earlier0112 boot
and no pre-existing output files.

Code (commit65c12fbd623dbd2a030e547debd5b06aa45658e5): the packer emits the
A615ZapMDT descriptor second word as the reserved16KiB descriptor page, not the
raw6860 MDT length. The consumer in xnu/patches/0112-gauguin-pas-cpu-staging.patch
accepts `reserved_bytes == PST_PAGE` (same alignment/bounds) and still pins the
first raw6860 bytes by SHA256. Corrected contract tests: tests/test_pas_staging.py
runs the real packer on synthetic MDT bytes and feeds its emitted descriptor and
16KiB page to tests/fixtures/gauguin_pas_stage_host.c, which stages the emitted
descriptor and rejects raw6860/16383/16385 before mapping; a mutant consumer
requiring PST_BYTES aborts at its first positive case. Focused3/3, payload2+9
and the full41-file host suite pass on source112-dsh-contract (5249 files, SHA
7b408015fc035412822c2b87d4d3a7f7fc2b2f538614fa8643617de83fe97283): logs
contract-focused-stage.log, contract-payload.log, contract-full-host.log
(contract-result.json). Only tracked change left: the original mkadt.py edit.

Build: run gauguin.fbWj14 (unique invocation ID; build IDs are not source-config
hashes), standard `deps/build-macos.sh` in the user-approved danger-full-access
mode, no BUILD_DSYM=0 and no manual strip. make exit0, state built, dSYM and
strip ran normally. Manifest .deps-cache/p0-20261105/build/runs/gauguin.fbWj14/build-manifest.json
captured HEAD65c12fbd; kernel16798800B SHA
8267eb949254736ba5cc7583c13ad25a16a166e98b77cc0829855e1d42419fdc, ARM64,
ID xnu-dc38b2a01c6f471fa523f9f9cdab1f4e, banner "Darwin Kernel Version 22.6.0:
Fri Nov  6 11:51:35 CST 2026; baai:xnu-dc38b2a01c6f471fa523f9f9cdab1f4e". The
current generated native context is this112-contract/fbWj14 build, not the old
111 manifest. Earlier run gauguin.Qz3IuF was an earlier0112 compile attempt (not
111) that failed at make2; it stays as history, manifest unchanged (ad7d22d0...,
failed) with its unstripped object in ignored
research/tmp/dsh-0112/contract-preserve/failed-Qz3IuF-kernel.unstripped.
Parent qualification: research/tmp/p3-native-0112-fullaccess-qualification-20261106.json.

Image: shim/out/shim-p3-passtage-0112-native-20261106.img,
19415040B SHA 17af66bf150a20a62673d5d0593512d6ae9478dd79598e8dc5cff6ab04e0e847;
payload research/tmp/p3-passtage-0112-native-20261106.bin SHA
27947b6e431416e46c3cb80f37c7843032be91081e50d92964c66911a47869b6; evidence
research/tmp/p3-passtage-0112-native-evidence-20261106.json. Proven shim
b5ba7764..., original DTB, base ADT7d6d93be..., NVT007143e7... (PA
0x182540000,147456 reserved), raw MDT6860 pin6f2a...16ac7b in a16KiB page
(PA0x182564000, zero padding), pending PAS request with a 2MiB zero tail
(runtime selects1MiB); flags NVT1/hz30, GCC/SCM0, pasprobe1/passtage1; marker
sweettrial=passtage-0112-20261106-dsh-a1; cmdline527B. Packed by
research/tmp/dsh-0112/pack_native0112_fullaccess.py (parent-corrected copy; the
original helper is preserved). The real low-PAS PA was unknown at packaging
time; this boot selected AA200000+100000 as recorded above, which is that
boot's allocation, not a fixed address.

Hardware trial (EXACT once; no second boot, no flash/format/partition writes):
preflight `adb get-state` returned recovery. tools/sweet-observe.sh was run
unmodified, which armed misc boot-recovery, rebooted to the bootloader and issued
the temporary `fastboot boot` (send18960KB0.438s, boot0.134s, total0.579s - the
image was ACCEPTED). At181s the observer exited4 ("no recovery detected after
181s") and its log pull failed, so it removed OUT by design; an `adb get-state`
right after reported no device, which was only "no ADB observed" and was NOT
proof of progress or of the kernel being stuck. The user later confirmed touch
unlock and returned TWRP, and the subsequent fresh pull (above) identified this
trial and passed both gates. Cycle log
research/tmp/p3-passtage-0112-native-cycle-20261106.log (finish2026-11-06T04:03:18Z,
12:03:18 CST). No GPU/PAS/SMC operation was invoked by this trial.

Local commit: only this NOTES.md handoff (parent9946819); original tools/mkadt.py
edit untouched and left uncommitted. Prior public sanitized snapshot
0e38d207d7089b2cbe657fc290d175b3ca7a6838 on codex/gauguin-p0-ci-20261105 was
pushed before this handoff. Native build context is still source112-dsh-contract
/ gauguin.fbWj14 (kernel16798800B SHA8267eb94...9fdc, ID
xnu-dc38b2a01c6f471fa523f9f9cdab1f4e).

Reminder for the next stage: the staged16KiB metadata page is not firmware
loaded and is not PAS owned-for-execution. Real PAS authentication/reset is a
separate step needing its own review and must not start with a naive secure call.

### 2026-11-06 —0111 real low-PAS ownership/pmap check VERIFIED

User confirms physical touch unlock; manually returned TWRP. First pull
preceded USB enumeration (no device); fresh get-state then returned recovery,
retry pull and full banner verification succeeded. No observer/build/CI live.
Log p3-low-pas-0111-native-recovered-20261106.txt matches full ca43a06c... ID
and unique sweettrial=pasowner-0111-20261106-a1. Actual runtime record:
selectedAA200000+100000, inputA91CF000+1230000, tail offset1030000;
FDT A8FCE000+44137, shimA2480000+39000. All64 pages unmanaged, raw pmap cache
attribute d0000006; exact complete marker present. This PA is a result of
this boot's ABL allocation, NOT a fixed address for later boots.

Last PET3330 at64307117566 ticks; NVT325084 accepted325084/rejected0;
no captured panic(cpu...) line. Hash/counters/probe lines saved in ignored
p3-low-pas-0111-native-evidence-20261106.json. Actual buffer bytes have not
been mapped/read/written; secure firmware/PAS/GPU remain untested. Touch
confirmation belongs to this111 trial, unlike earlier pending entries.

Next: source-backed WC mapping/lifetime and CPU staging/readback, plus actual
recovery config/native bus-provider audit for the crypto-to-DDR bandwidth
prerequisite. Do not issue PAS immediately merely because owner metadata
passed. Phone currently TWRP; preserve all qualified images and original
unstaged mkadt edit. Latest public handoff2084afa, code publice665e50.

### 2026-11-06 —0111 enabled trial booted; manual TWRP/fresh log PENDING

Current phone state UNKNOWN: temporary0111 image was accepted (send18944KB
0.445s, boot0.134s, total0.585s); observer27767 ended181s/exit4 without
recovery. No observer/native build/CI remains live. Output log was removed
by the observer on failed pull, so there is no fresh0111 runtime result yet.
User has been asked to confirm touch and manually return TWRP. Do not reuse
the previous default-loader trial's touch confirmation or its same-phone log.

Code local a5d353e, qualification handoff5bcbe27; sanitized public
e665e5030127c2bc3b01781e3d67ab06837002a2 (parent3ef39bc) pushed successfully.
Cycle research/tmp/p3-low-pas-0111-native-cycle-20261106.log; evidence
p3-low-pas-0111-native-evidence-20261106.json. After user returns TWRP, pull
fresh p3-low-pas-0111-native-recovered-20261106.txt and require both full
xnu-ca43a06cd2de44cc9bd6f092ea45f636 identity and
sweettrial=pasowner-0111-20261106-a1. Actual ownership PA and pmap result remain
UNKNOWN. Success requires valid owner provenance plus complete unmanaged_pages=64
wimg=d0000006. UI alone does not prove reservation. Buffer/PAS/GPU remain untested.

Next-stage native-source audit recorded in ignored
p3-pas-owner-probe-20261106/next-pas-prerequisites.json: actual pil_gpu has no
per-device proxy clock/regulator/bus properties, but pil_init_image_trusted
still calls the global scm_pas_enable_bw before MDT/INIT_IMAGE. Its crypto
master-to-EBI usecase advertises IB3936000000/AB393600000 bytes/sec. Inspect
actual bus provider/config and inherited ownership before PAS operations;
do not treat successful reservation as readiness for authentication/reset.
No new power, bandwidth, firmware, secure or GPU operation has been executed.
Original uncommitted tools/mkadt.py edit remains preserved.

### 2026-11-06 — native0111 build qualified; first enabled reservation image ready

Native build32110 exit0, no CI. Manifest
.deps-cache/p0-20261105/build/runs/gauguin.W1dBXN/build-manifest.json.
Kernel16798560B SHA2be023bbf91416c9137dbb654eb525a85c5b1d85e42172cf47e2f645dd099422,
full ID xnu-ca43a06cd2de44cc9bd6f092ea45f636 (Nov6 09:12:46 CST).
Source/all build inputs unchanged;105patches/5248files, required PAS/pmap and
prior input/GPU/SCM symbols defined, ARM64/entry/segments/ADT bounds pass.
Qualification p3-native-0111-qualification-20261106.json. Shared generated
native build context is now111/W1dBXN; do not reuse110/liFpTf TU commands.

Build capture started while the111 change was staged, before local a5d353e
commit completed: captured HEAD23340e4 + tracked diff SHA
f0042a098afbf523d9adf6579cd1e9e5b8b5911f306e2b9fb9d7257a8faadc84.
Exact `git diff --binary <captured HEAD>` was rehashed after commit and matched
that record, reconciling the build to committed a5d353e plus the original
preserved mkadt edit. This is recorded explicitly, not relabeled a clean build.

Prepared shim/out/shim-p3-low-pas-0111-native-20261106.img,19398656B,
SHA a57b7194e31ab8bfb7e386d140018ec0552cdf306d37aec0b190ca58b9b2dac5.
Same hardware-qualified new shim b5ba7764... and same original DTB; NVT
assetPA182540000/raw139264/reserve147456 unchanged. Optional2MiB initrd tail
is enabled; runtime must select/validate1MiB below4GiB and publish owner/pmap
metadata. sweetpasprobe=1, NVT1/hz30, GCC/SCM probes off. Unique actual-log
marker sweettrial=pasowner-0111-20261106-a1 required in addition to full ID.
No buffer access/map, firmware loading or PAS/SMC operation is implemented.
Host preflight on the real packed payload passes using synthetic handoff
addresses; actual runtime PA/result are UNKNOWN until fresh hardware log.
Evidence p3-low-pas-0111-native-evidence-20261106.json. Phone TWRP; next
temporary180s boot and manual touch/recovery/log qualification.

### 2026-11-06 —0111 readonly ownership consumer ready for native build

Added0111 gauguin_pas_probe: default-off sweetpasprobe=1 creates its own
post-root worker, waits45s, validates exact owner/pmap metadata and checks
all64 selected16KiB pages via pmap_valid_page/pmap_cache_attributes. Only
kernel metadata is inspected; no PA dereference, mapping, allocation, firmware,
SMC or power operation. Checks context again after delay and fails closed on
missing/pending/invalid metadata, a managed page or any wrong cache attribute.
The successful log explicitly says buffer/PAS/GPU remain untested.

Freshsource111 strictly replayed105patches/5248files. Exact differences from
qualified110: bsd/conf/files, bsd/kern/bsd_init.c, bsd/dev/gauguin_pas_probe.c.
ProbeSHA ebf3fa828e321c709cba9a61f0716db7c987c05cf1edec018d5b05cec0788f57.
Full hostsuite on111 passes (p3-pas-owner-probe-20261106/full-host.log).
Consumer host fixture uses actual shim prepare/commit output, checks default
off/start/context errors, missing/pending/malformed/overflow metadata and
each of64 managed-page/cache-attribute failure positions under ASan/UBSan.
SCM integration test now checks its shared GAUGUIN guard membership rather
than requiring its call to be the last entry in that block.

Phone remains TWRP after qualified default-loader log capture. No observer,
CI or full native111 build live yet. Next commit/build locally; shared native
generated context is still110/liFpTf until the new build starts. Qualify full
link/manifest, then package the already proven new shim with --pas-reservation
and sweetpasprobe=1. Require a fresh unique trial marker and actual owner/
64-page completion log; do not infer reservation success from UI alone.

### 2026-11-06 — new loader default boot and physical unlock VERIFIED

User confirms physical touch unlock still works; manually returned TWRP.
Fresh log p3-low-pas-default-20261106-recovered.txt matches the full kernel110
banner AND unique sweettrial=lpdefault-20261106-a1 (one occurrence).
No PAS reservation was requested; no SCM/GCC worker ran. Observer22293 ended
181s/exit4 and fresh pull was performed only after manual recovery.

Log: 30666 lines, ring1178184B/flush14559; last PET24360 at468429862902 ticks,
last NVT2427654 accepted2427654/rejected0. These are captured counters; the
phone was not continuously inspected throughout that full interval. No
captured panic(cpu...) line. Full SHA and package fields are in ignored
p3-low-pas-default-20261106-package.json. Local loader commit23340e4 and
sanitized public3ef39bc68601801303c829130ff2dabc3c17dd9a (parentbc7f72d)
are committed/pushed. Only original tools/mkadt.py is dirty.

Next: readonly owner/pmap-attribute kernel probe candidate in ignored
p3-pas-owner-probe-20261106/gauguin_pas_probe.c. Real kernel ARM64 TU passes
(20208B object, source ce74cdfe6dddcad4b3dc343e3f96646957b944dfbf4ff0ed417fb1f89c8b2944).
Initial TU exposed hidden BSD pmap declarations; exact canonical externs
added and retry passed. Candidate not integrated/built as full kernel yet.
Validate host failure paths before adding0111. Future enabled trial must
verify exact 128B ownership record, matching pmap tuple and all64 unmanaged
16KiB pages' cache attributes; no buffer mapping/access, firmware or PAS call.

### 2026-11-06 — low-PAS loader integrated; default-only image qualified

Integrated optional pending-request/owned-initrd-tail contract in mkpayload
and shim loader, plus corrected downward stack placement. Both Linux/macOS
shim build lists include the parser; macOS supports isolated --out and --dtb.
Runtime accepts lagoon or the exact gauguin/SM7225 pair. It never accesses
the selected PAS bytes or performs firmware/PAS/GPU operations. Invalid
input stops explicitly instead of entering the old UFS diagnostic fallback.
The existing qualified images remain intact.

Verification: full hostsuite on source110 passes; committed portable suite
has 86 ASan/UBSan actual-C metadata cases and actual-loader segment/zero-fill/
ADT/boot_args checks, with 10 malformed/default stop cases. Pre-integration
audit also compared old/new valid-loader destinations byte for byte (87 cases
including optional saved recovery metadata). Eight synthetic default packer
goldens and real109 payload identity pass. Original wrapper tree with only
synthetic memory/initrd handoff values passes bounded parsing; this is a host
test, not evidence of actual ABL handoff values. ARM64 links with no undefined
symbols or C ABS64 relocations; measured conservative stack bound 4736B/32KiB.

Prepared default-only trial: shim/out/shim-p3-low-pas-default-20261106.img,
17289216B SHA a8fb8907ea070a20dd4b2bc70746ff5481cb676b8531b73e57f2eed1087b1797.
New shim 233472B; kernel110 and NVT firmware unchanged. No PAS request/tail/
pmap reservation enabled. SCM/GCC probes off, touch on, software-copy cap30.
Require actual log marker sweettrial=lpdefault-20261106-a1 as well as full
xnu-b89c8584e8904e069641abfe9a973a8b banner. Package/qualification evidence:
research/tmp/p3-low-pas-default-20261106-package.json. No new boot yet;
phone last read as recovery. Next temporary 180s boot, touch confirmation,
manual TWRP and fresh log before optional reservation/readonly kernel check.

### 2026-11-06 — resumed: fix low-PAS board matching before integration

Phone is in TWRP (fresh `adb get-state`: recovery). No kernel build, CI or
boot observer is running. Latest verified kernel remains native0110,
xnu-b89c8584e8904e069641abfe9a973a8b; no actual PAS operation or GPU execution.

Review found a concrete candidate compatibility blocker: the tested wrapper
DTB has `xiaomi,gauguin\0qcom,sm7225\0`, whereas the candidate accepted only
`qcom,lagoon`. Root is correcting the ignored candidate to also require that
exact board/SoC pair, with positive and malformed/unpaired negative cases.
Do not infer the static wrapper memory size (zero placeholder) is the ABL
handoff size; ABL supplies actual memory/initrd values. First hardware trial
will retain kernel110 and disable PAS reservation, with a unique `sweettrial`
boot argument required in the recovered log. A previous same-kernel banner
alone cannot identify this new loader trial.

Optional Linux KGSL reference proposal is complete under ignored
p3-kgsl-reference-20261106/PROPOSAL.md. It has not been implemented or run.
Opening KGSL can start GPU/GMU/PAS; submission errors may still queue work,
and context destruction does not independently prove quiescence. Keep this
optional experiment separate from the XNU GPU qualification path.

### 2026-11-05 —0110 SCM64/PAS API availability VERIFIED; lowPAS contractnext

Userconfirms0110physicaltouchunlockstillworks, manuallyreturnedTWRP.
PhoneTWRP; noobserver/nativebuild/CI live. Observer58937 terminal181s/exit4;
fastbootsend16868KB0.397s,boot0.134s,total0.539s. Freshlog
p3-scm-0110-native-recovered-20261105.txt matches fullxnu-b89c8584... ID:
6659lines,ring362481B/flush2109,SHAfc887acb22ae672035b7042cdd4e15a7b62ac4e7ca7dbfc55ea4d655fdad9dd9.
PET2130 at41107987449ticks (~2141.04s);
NVTlast[205428, 205428, 0],bootstrapREADY/fff/PID5937/1080x2400v16type1.

AllfiveINFOcallsreturnedfirstattempt/resume0: x0=0,x1=1,x2=0,x3=0.
Self:c2000601 query82000601 validatedSMC64. NormalINFO42000601 queried
02000201/02000202/02000205/02000206, availability_mask=f. These aregeneric
APIcapabilities, NOTPAS13authorization/authentication, DMAapertureproof orGPU
firmwareexecution. No actualPAS/reset/poweroperationwasperformed.

Currentlocalcode95cbf8c/publicbc7f72d; local0bdfae6handoffwasfoldedinto95cb.
SCM/GCCdiagnosticsemanticallyqualified; keepold images/110kernelunchanged.
Nextreview/integration: newshim correctedstack+defaultloader behavior before
optionalLowPASReservation. Candidateandseparatelinkerfix frozen in
p3-low-pas-memory-20261105/CANDIDATE.md,candidate-freeze.json;
latestcontractSHAe9e190f7bcc1b005e4eaa2d19f931a434db16c9c433a324463e3d6af6cf4306a,
stackSHA bb91fea6c9802e40e3d29044fec18655d5fd3f33c92cf49afae193e1f2862df2.
Independentreviewfoundpre-derefRAMcheckgap;fixedbeforefreeze.79ASan/UBSan
cases,actual-loader10stop/defaultcomparisons,real109defaultpayloadbyteidentity,
isolatedARM64shimlink and4736Bstackbound pass. No trackedshimchangesyet.
Validdefault behaviorretained; givenmalformed/non-XNUinitrdnewcandidatehalts
beforelegacyUFSfallback. Featurefailurealsohaltsbeforecopies/ownedpublication.
Oldshim ignorespendingrequest andcannotpublishactualownership.

CommandDBparser/ARCpolicy frozen in p3-gpu-resources-20261105/cmd-db/.
No rawbinarycapture wasobtained; native8KiBtextexportisreferenceonly. NoARC
writesapprovedasready: inheritedDRV2aggregatefloorunknown. Conservative
boot-lifetime maximumcorner ownershipis a conditionalresearchroute, notyet
qualifiedforwrites (sameboottable/completebounds/DRVexclusive/constraints).
P3 ownedbuffer,CPpacket/oracle andfirmwareloadplan remainofflineonly.


### 2026-11-05 —native0110 SCM-query build passes; imageprepared

Local95cbf8c published safely asbc7f72dbd81283b5a24913bd768e6eeb0d457a91,
parent3cc8ef8. Nativebuild5043 terminalexit0; noCI. Manifest
.deps-cache/p0-20261105/build/runs/gauguin.liFpTf/build-manifest.json,
104patches/5247sourcefiles, exactsource/allinputs match, onlypreservedmkadt
trackededit, make0/ARM64, INFOprobeandpriorNVT/GCC symbolslinked.
Kernel16798400B SHAb3635652da961f911fb7856f9c8140981ede32b00a4d6f66fa84af17c849ae26.
FullbuildIDxnu-b89c8584e8904e069641abfe9a973a8b checkedinmanifest/kernel/image.
Qualificationp3-native-0110-qualification-20261105.json; hosttestsseparately
passed(p3-host-tests-0110-retry-20261105.log),SKIP_TESTS1avoidsduplicate.
Nativecontext now110/liFpTf, oldtY4dndrecipecontextstaleforfutureTUchecks.

Preparedshim/out/shim-p3-scm-0110-native-20261105.img,17272832B,
SHA574b4c46d31088b97f845c62e882eeb0c88e49887dfa1abccee2b8701dad5567;payloadSHA278e554f896b7f71a39ac50bd6115565cfa0c35cdce1952e828ae49c6b42ce9f.
Exactknownshim/DTB/header and NVTassetPA0x182540000 retained. FlagsNVT1,
hz30,GPUprobe0,SCMprobe1. No PAS operations/buffers orGPUregisteraccess.
Notyetbooted; phoneTWRP. Nexttemporary180s observationandfreshlog.

Native readonlycmd_db export successfullycaptured in
p3-gpu-inventory-20261105/cmd-db-native.txt(8187B). ARCcx30000levels0,16,64,
128,192,256,384;mx30010adds320;gfx30050levels0,64,128,192,256,320,384,416.
Otheridsinfile. Debugfs*.molauxisUNTRUSTWORTHY: showfunctionlosesentrybank
foraddress0 andreadswrongdataoffset, unlikeget_header/read_aux_data. NoMOL
or inheritedvotefloor inferredfromit. Attemptedboundedread ofactualDT128KiB
cmdDBvia/dev/mem failedbecause/dev/memabsent; toolreturnedtextdespiteexit0,
strictlength/magic validationrejectedandNO.binwaswritten. Neveruseitassnapshot.
No newdevice/registerwrites beyondvirtualdebugfsmount andnormaltemporaryboot.

LowPAS candidate addsoptionalownedinitrdtail contract; independentlynoticed
shim.ld `_stack_top` before32KiBstackallocation. Proposedseparatecandidate
movesstack_toptoitsend(samesectionsize/_end),requiresstack/framevalidation
anddefaultvalidbootregression. No trackedshim/payloadchangesyet.


### 2026-11-05 —0109 GCC snapshot verified;~68min touch stability;0110 SCM query ready

User confirms0109 stillphysicallyunlocks, manuallyreturnedTWRP. PhoneTWRP;
noobserver/nativebuild/CI live. Fresh p3-gcc-0109-native-recovered-20261105.txt
matches fullxnu-a948... ID:12551lines,ring647684B/flush4347,
SHAf92cbdc77c2e62cd4c48c47a0f85aab910a93525977508a77d84015fe077510d.
PET4060 at78200473955ticks (~4072.94s/67.88min), NVT398634packets,
accepted398634/rejected0; bootstrapREADY/fff,PID5937,geometry/version/typeOK.
No capturedpanic/UFS/logtransfererror; genericbootgPanicBasewarnings and
execDumpPanic arenotcrashes. Raw multi-slot masksappear,butnoexplicitmulti-
touchgesturequalification. Userunlockafterlongrun isconfirmed.

AllfiveGCCreadscomplete:52008GPU_GPLL0_VOTES=0000001e (GPUbits7/8clear),
45004GPU_CFG_AHB=00000009,4500cGPU_MEMNOC_GFX=80004220,
45014GPU_SNOC_DVM_GFX=80000000,2d038DDRSS_GPU_AXI=80000000.
These namedregisteraccessesarenowhardwareverified;threebranchCLK_OFFbitsset.
This doesnotqualifyGPUCC/GDSC/GMU/SMMU/GX orparentrailownership. Do notenable
anythingbasedonlyontheseclockvalues.

0110 integratesdefaultoff sweetscmprobe1 worker,45safterroot. Only INFO self/
ABI detection thenINFOqueriesofPAS APIcmd1/2/5/6 availability; PAS13operations
areNOTinvoked,noDMA/buffers/GPU MMIO/powervotes/watchdogcalls. NativeSMC64/32
x0..x6continuationsbounded8entries, freshEBUSYretrybounded4; unfinishedresume
neverfallsback32. Rawx0..x3persistedaftereachreturn. Scalarcapabilitydoesnot
provePAS13authorization orhigh-PA support. SourceSHA1ac17e40f73906e6af6900b147f1d44cd7dd47819a6cb1e7da372aa6cfc68841.
ActualARM64TU20608B and14kerneldependenciespass using109context; independent
ABI/ASM reviewpassed. Freshsource110104patches/5247files differsfrom109only
newSCM C+bsd/conf/files+bsd_init. Fullhostsuitepasses onretry: initialfailure
wasGPUtestrequiringitsdeclaration/calltobealoneinsharedGAUGUINblock; testnow
checksactualguardmembershipanduniquenesswithoutrejectingtheSCMneighbor.
Reportsp3-source110-comparison-20261105.json,p3-host-tests-0110-retry-20261105.log.
Nextcommit/localbuild,thenquery-onlybootwithGPUprobeoff tokeepresultsseparate.

LowPASowner candidate inprogress (ignoredp3-low-pas-memory-20261105/candidate):
optionalzero-tail WITHIN ABL-ownedinitrd, runtimechecked1MiBsubregion<4GiB;
actualFDT/shim/reservationsoverlapvalidation andADTownership/cachehandoff.
No fixedPA,managedRAMexpansion,PASoperationorbufferusage. Defaultcompatibility
andfailure-stopbeforeoldshimfallback required. Notintegratedorbooted.


### 2026-11-05 —0109 GPU clock observation ended; manual TWRP/log pending

Native0109 imagecc180743... was temporarily accepted (send16868KB0.392s,
boot0.135s,total0.533s). Observer97197 ended182s/exit4 withoutrecovery; no
observer/nativebuild/CI live. Userhasbeenasked toconfirmtouchunlock andreturn
TWRP. This answer/freshlog is PENDING. Do not bootanotherimage ormistake the
previous30Hz TWRPreplyforconfirmationofthis109trial. Cycle
p3-gcc-0109-native-cycle-20261105.log; evidencep3-gcc-0109-native-evidence-20261105.json.
No GPUregistersnapshotresult knownyet. Lastverifiedinputbaselineis108.

Next offlinework: reset_evidence preparingdefaultoff scalarSCM capability
probe (INFOqueriesonly, neverPASactions) perSCM-RPMH-AUDIT. patch_repro auditing
lowPAownership; liveDTremoved_region@c0000000 is123MiB [C0000000,C7B00000),
so blindlymovingmanagedbaseC0000000 wouldincludeexplicitno-mapregion. NoPA
selected/reserved/written andnoADT/RAMexpansionchange. Firmwareloadplan now
frozenunderp3-gpu-firmware-20261105:16hosttests,all7stockhasheschecked;
SQEskip4,GMUlegacywhole32KiB,ZAPonly1984Bsegment withMDT6860B and1MiBdynamic
allocation/4KiBauthspan. No realfirmwareloading/PASauth/GPUexecutionoccurred.


### 2026-11-05 — native0109 full build/qualification passes; firstGCC image prepared

Nativebuild81419 terminalexit0; manifest
.deps-cache/p0-20261105/build/runs/gauguin.tY4dnd/build-manifest.json.
103patches/5246sourcefiles, exactsource/allcapturedinputhashes unchanged,
make0/ARM64, requiredsweet_gpu_probe_init linkedalongwithexistingNVT/HID.
Unique buildIDxnu-a94808142aa743bbac89d9c04b2ef0c9 matchesmanifest/kernel/image.
Kernel16798272B SHAb203e1f068d9f335ff8554fb620c18db6c6dcfdf7272fca71c6877c6e1f1c9fa.
Qualification research/tmp/p3-native-0109-qualification-20261105.json;
outputp3-native-0109-20261105-out; sharednativecontext now109/tY4dnd.

Prepared shim/out/shim-p3-gcc-0109-native-20261105.img17272832B,
SHAcc180743ec84dc12e2b7c06375ba0b5fcdd579548f6e67f292c95595ddccf4df;payloadSHAac79e42135ee74ddba5f612cbd1897b5c6943deb3e163e6baeecacbfbe9e4de4.
Testedshim/DTB/headergeometryretained, NVTassetPA0x182540000/raw139264/
reserve147456 unchanged; bounds/bytes/padding/fullbannerpass. Bootargsretain
workingNVT+sweetfb_hz30 andaddsweetgpuprobe1. NoGPUFWloaded/intialized/commands.
NoCIorobserverliveyet; phoneTWRP. Nexttemporary180sobservation, manualrecovery
forfiveGCCnamedrawvalues. This image doesnotyettestGPUCC/GMU/SMMU/GXaccess.

SCM sourceaudit correction: oldbootargsstep3/abi40/rc-2/ret-4belong specifically
tosecurewatchdogdisable. The shim firstsuccessfully detectedSMC64 andperformed
INFOavailabilityquery. Do not labelallSCMbroken. ExistingXNU RPMhMMIOonly
supportsldoa6VRM; it isnot a CX/MX/GX ARC corner-voter. Furtherauditcontinues.


### 2026-11-05 — local0109 build running; current phone TWRP

Local232bc24 (GCC-onlyGPUprobe) published as sanitized snapshot
3cc8ef8499e07baeba4f55f3097bed95c5cb7c4d, parent402e272. Pushsucceeded.
Fullnativebuild **session81419** is running withsource109 andexistingisolated
buildroot, outputresearch/tmp/p3-native-0109-20261105-out/; log
research/tmp/p3-native-0109-build-20261105.log. NoCI dispatched. Hosttests
already passed onexactsource109;SKIP_TESTS=1 avoidsrepeat. Generatednative
context is busy until this build terminates; no concurrent oldKBwKVM TU runs.
No GPUprobeimage packaged/booted yet. PhoneisTWRP aftercaptured30Hzcomparison.

Parallel firmwareaudit correction: existing8KiB gpu_region mustnotbeassumed
PILtarget. The actualpil_gpu node doesnotreferencethatpool; nativeZAP loader
requests1MiB contiguous dynamicregion for4KiB authenticatedspan. ExactPIL
allocation/relocation/cache/SCMcontract stillbeingchecked, noimagesloaded.


### 2026-11-05 — hz30 only slightly helps; user prioritizes real A619/Metal;0109 ready

User reports same-native108 hz30 control somewhatbetter butstillunresponsive,
and wantsGPU/Metal mainline. ReconfirmedTWRP, freshlog matchesbuildID AND
actualsweetfb_hz=30 bootargs. Observer35148 terminal181s/exit4; noobservers,
CI ornativebuild live. PhoneTWRP. Log
research/tmp/p1-nvt-0108-native-hz30-recovered-20261105.txt:4288lines,
SHA256d06785e3b98558427760e87ff705c950318938f7e6f4d28bdbb34b1700fd6854,
PET500 at9781269844ticks (~509.44s). BootstrapREADY/validfff,9165transfers,
resetA0,PID5937,1080x2400/version16/type1. Lastpackets43874/accepted43874/
rejected0. Hz30 remains softwarecopycap, not hardwarehighrefresh orGPUproof.

Current localHEAD829e733 / public402e272191456a2585a2b42ae41bde04617285d8
are documentationchildren of tested108 code1f51599 / publicd51a9c2.
No newCI needed for debugging; use localbuild. Main nextphaseP3a: realA619
CP_MEM_WRITE+canary/timestamp readback, thenMetal/IOSurface+composition. P1
basicphysicalunlock/HOME nowpasses; multitouch/latency/endurance remainopen.
P2fullcapacity/memory work also remains; do not markoverallgoalcomplete.

Separatelag evidence frozen in ui-perf-0108-20261105/FINDINGS.md,freeze.json
andnotification-rootfs-audit.txt. EarlySB fence/BBDrender threads wait behind
EDR client mutex; EDRGetDefaultMinScalingFactor sends customrequest0x12 with
5000msMach timeout tocom.apple.libEDR.Notification. Existingofflinejob/cache
assignthatservice tobackboardd itself. This is a serverresponse question, not
proofanindependentdaemonisabsent. EmptylateSMPstacks coincidewithdisplayoff;
nointeraction samplescoverlaterdisplayon. Exactelapsedtimeout notmeasured.
NotificationsABI72/fourinputs andcallbackshapearecorrect;68isSetParameter.
TheobservedCADisplayTimer/Machtimer path legitimatelyhasno72registration.
Do not change72orforcefakeGPU/SDRsuccess. RealGPUaloneisnotprovedtofixEDRwait.

Read-only nativeGPU inventory: p3-gpu-inventory-20261105/. Adreno619v1,DT
chipid06010900. Mountedvirtualdebugfs, readclk/regulator summaries. Vendor
ext4wasmountedro,noload andmodemvfat ro undernew/tmp paths, filescopied toignored
inventory/firmware, thenbothunmountedsuccessfully. No partitiondata/regwrites.
a630_sqe.fw32304B SHAa0e1b583f620fabe32729ce367959d1960638663244d7d0cfc21b9a5215a018b;
a619_gmu.bin32768B SHA9ef10b2b179054fb57af25008e29feb24300c2eaaeabf907bd741786bbacbf2e;
a615_zap.elf14272B SHAd1e0dbbfe4a9c68935d38eadaf9a508e3b43c48e5c7f15e9580dd583cd2c0652,
plusmdt/b00..b02. Completeprovenance firmware-capture.json. GPUcfgAHB/GPUCCAHB
nativeprepare/enablecounts2;otherGPUnodesmostly0. CachedPLLratesandLinux
regulatorcountsareNOT XNUhandoffpower/fabric proof. Parentrailvoteisrequired
by native evenforGDSC reads; no GPUCC/GMU/SMMU/GX reads authorizedbyclockbits.
A619 nativeprofilehasADRENO_64BIT: initial<4GiB IOVAisconservativepolicy,
not a provenhardwarelimit. Data coherence andnoncoherenttablewalksdiffer.

0109 nowstages firstGPUhandoffprobe: defaultoff sweetgpuprobe=1, independent
post-rootworker45s,exact5namedGCCreads/3maps,markersbeforeeachoperation. No
MMIOwrites/votes/rangescan orotherGPUbankaccess. ActualCprobeTU/15symbols
pass usingnative108context; sourceSHA564b9da4baca335872e6694b57d2bf65e139a8c5385c3c5b77b569881000e0fe.
Freshsource109replays103patches/5246files, exact3changes (bsd/conf/files,
bsd/kern/bsd_init.c,newgpu_probe);fullhostsuitepasses. Reports
p3-source109-comparison-20261105.json,p3-host-tests-0109-20261105.log and
p3-gpu-resources-20261105/probe/qualification.json. Nextcommit/localbuild,
thenoneGCCsnapshotboot. NoGPUexecutionqualificationexpectedfromthisprobe.

Parallelofflinecandidates: owned16K-buffer adapterandA6CPpacket/oracle under
p3-gpu-abi-20261105 (realTUs/hostpass, notintegrated). ExistingABI1backendis
A740specific andcannotbechipid-renamedtoA619. Firmwareformat/PAS13loadplan
isbeingprepared in p3-gpu-firmware-20261105; no loading orsecurecalls.


### 2026-11-05 — same-native108 hz30 comparison started; observer35148 live

Image71937a60... temporarily accepted: send16868KB0.395s,boot0.134s,total0.538s.
Observer **35148** now observes180seconds. Cycle
research/tmp/p1-nvt-0108-native-hz30-cycle-20261105.log. Onlynewargument
sweetfb_hz=30, exactsamekernel/firmware and otherwiseidenticalpayload. No UI/
performance report orfreshlog yet. Preserve this boot until userchecks and
logrecovery; verify bootargs because buildID is shared with baseline108.
Physicaltouchunlock/HOME is already verified on the preceding default-hz108.
No CI/nativebuild is live. Do not accidentally repeat old0107 CRC experiment.


### 2026-11-05 — P1 physical swipe unlock/HOME VERIFIED; severe lag is next blocker

User explicitly confirms native0108 physical touch swipe unlocked to HOME;
both clicks and animations are extremely laggy. User tried settings/return/
swipes, then manually returnedTWRP. Observer87761 terminal181s/exit4; noCI or
nativebuild live. Fresh log matches fullxnu-4b17c6ad... ID:4339lines,
ring314707B/flush422, PET350 at6898054722ticks (~359.27s).
Log research/tmp/p1-nvt-0108-native-recovered-20261105.txt
SHA25604ccad12d883e39c7d6e3f8d52ebce57bdf4b77862607ad24c9badfdf0454495.

Hardware now confirms fullbootstrapREADY/validfff/result0/callback0,
96936bytes written/readback,9170transfers,3.171824s. ActualCRCstatus4,
resetA1,PID5937,FWINFO1080x2400/version16/type1. Bothpost R_DLM andG_DLM now
readb0183db6 while ILM remains15fe9c6d. Bank reuse remains interpretation;
unsupported post-start identity check was the obstacle, not failed data upload.
Realcontact mask down/up events and userunlock provide end-to-end input proof.
Lastpacket28915/accepted28915/rejected0, typically996–998samples/10s. accepted
includes no-change and does NOT prove every event queued/consumed. Multitouch,
latency, suspend/recovery and endurance are still unqualified.

Known display limit: SweetFramebuffer.cpp523 defaults sweetfb_hz10 => one
flush every6timer callbacks. Existing args omit it. Timer callbacks around
17.6ms; present attempts may be far belowcap (latecounts18to36 over~100s), so
this cap alone is not established as the dominant lag cause. Actualcopy is
CPU dirty-rect memcpy; physicalpanelWC, IOBuffer source cached. NoGPU/Metal.
SMP sampling interrupts/stops threads every10s for16rounds and producesheavy
logs; it is a finite overhead, not proof of ongoing late-frame stalls.
An independent log/DSC analysis is finding earlySpringBoard fence/EDR waits;
exact causality remains under review, not a verified patch.

Prepared samekernel one-variablecontrol: shim/out/shim-p1-nvt-0108-native-hz30-20261105.img
SHA25671937a6024d6b4ad126b869d2643ec2d0867ae4c93c2c68749186b0a0ac53f19. Only extraargument sweetfb_hz=30;
payload bytes outside command-line field EXACTLY identical to previous108.
No samplersetting/driver/code/GPU flag change. SamebuildID cannot distinguish
these boots: require freshcycle/log and actualboot-args sweetfb_hz=30 as well.
Next: temporary180s control; userperformswipes and report relative latency;
collectfreshlog before anotherboot. Changing softwarecopycap is not hardware
90/120Hz support. PhonecurrentlyTWRP, control not yetbooted.


### 2026-11-05 — local0108 temporary boot accepted; observer87761 live

Native0108 image493cdf7e... temporarily started: send16868KB0.391s,
boot0.135s,total0.532s.180s observer **87761** live; cycle
research/tmp/p1-nvt-0108-native-cycle-20261105.log. No screen/touch/fresh log
result yet. Do not duplicate the boot; phone currently owns XNU/USB.
Native build1043 and CI42021243212 are completed, not live. Next user check:
try actual touch/swipe then returnTWRP to recover this exact build's log.


### 2026-11-05 — local0108 full build passes; image ready for second physical-input trial

Local1f51599 was published safely asd51a9c25960c133746ad852c67c76ab6598e3202,
parentb7d836a. No CI dispatched. Full nativebuildsession1043 is terminalexit0.
Manifest .deps-cache/p0-20261105/build/runs/gauguin.KBwKVM/build-manifest.json:
make0/ARM64/5245sourcefiles, sourceSHA42ad8af3d1c1967c040b277cb7e60066a55ec88e2e637099670823e720e7eeb0.
Source and all captured build inputs match after build; only known mkadt.py
worktree edit. All host tests passed separately on exact source108, so this
invocation usedSKIP_TESTS=1. Previous link/version.o were preserved and relinked;
unique IDxnu-4b17c6ad3770401b95f86c3750d8ed82 is in manifest/kernel/image.
Native generated build context now belongs to source108/new manifest, not99.
Kernel16798048B SHA8501ee056cd49869e240c1752085d84534156f5da037f278842e3adfa81e08dc.
Output research/tmp/p1-native-0108-20261105-out/; qualification
p1-native-0108-qualification-20261105.json. Build log356172340B has interleaved
compiler warnings/source strings containing 'error:'; use make/manifest result,
not broad grep of those echoed source lines, for the build verdict.

Prepared shim/out/shim-p1-nvt-0108-native-20261105.img,17272832B,
SHA256493cdf7e521dd83b024b93f4926de2db903400874f5a4ed7aac50c1a0af9c76b; payloadSHA2563b94ed3c7906c689c451c24aa163e36692d396007dade0ead5ac4bc8f81a429a.
Exact0104shim/DTB/header geometry retained. AssetPA0x182540000,raw139264,
reserve147456; bytes/padding/bounds and fullbanner checked. Same0107 arguments
(sweetnvt=1,probes/legacy0). Not booted yet; nextone180s temporary observation.
Evidence p1-nvt-0108-native-evidence-20261105.json. PhonecurrentlyTWRP.

Offline GPU owned-buffer candidate is now frozen and independently reviewed:
p3-gpu-abi-20261105/buffer-freeze.json,buffer-compile-qualification.json,
OWNED_BUFFER.md. Host fixtures and two actualARM64TUs using new108contextpass,
9external dependencies supplied; no generated files changed. Still noGPU/SMMU
activity, service, import or realhardwarecache/quiescence proof. Not in108.


### 2026-11-05 — physical SPI/full firmware readback works; native CRC gate fix0108 ready

User confirms0107 remains at iOS lock screen with no touch, then manually
returned to TWRP. Observer59631 ended181s/exit4; no live observer/CI. First pull
briefly saw no USB, retry succeeded after enumeration without user action.
Fresh log p1-nvt-0107-recovered-20261105.txt matches complete xnu-93babaf... ID:
3751lines,ring283996B/flush256,PET230 at4592702331ticks (~239.20s).
SHA256a5c9597f074cf6b67e057aecdc7c21d20ad1d500356fd0db3097b7ab7ff444cc.

Actual new hardware milestone: assetSHA verified; bus/config/pins and raw SPI
work. Realtrim0c0000726603;96936bytes written AND entirely read back in3.206132s,
9160transfers. CRCbefore0/status4 (DONE, no error), resetA1; ILM15fe9c6d matches.
Post-start R_DLM reads b0183db6, equal to the file's Info12 CRC rather than the
initial DLM golden90fe20f8.0107 aborts atphase15/result-8,validc3f BEFORE reading
post golden/FWINFO/PID or polling/HID. No physical touch report was delivered.
PIO0/callback0; final restore-8 is expected quarantine from explicit upper-layer
abort, not evidence of a new SPI error. One UFS1000-spin busy notice, but no
captured transfer timeout/poison/panic. This is not fault-recovery qualification.

Pinned native fw_update.c939-1001 breaks on reset-ready success; R/G checksums
are read only in failure diagnostics after retry exhaustion. They have no
source-established post-start stability contract. Firmware reuse of the DLM
result slot is a plausible interpretation of the Info12 match, not proved.
Two independent reviews verified addresses, raw RX+2, little endian and actual
preboot bank programming; no offset/partition mix-up was found.

0108 removes ONLY unsupported post-start R/G equality gates, retaining actual
reads/validity logs and all SPI-error handling. It does NOT whitelist Info12.
PinnedSHA/full SRAM comparison/preboot bank readback/CRC status/reset/FWINFO/
version/type/PID gates remain. Fresh source108102patches differs from107 only
in bootstrap C, SHA0d82ffb3e741665ba38098d16e7cc6eea8f009dcc78e38f28a5803a84edb8ae7.
Full host suite and staged real-file bootstrap tests pass. New test permits
arbitrary later R/G observations but still rejects actual preboot corruption,
CRC errors/unready/FWINFO/PID errors; the old0107 fails this regression control.
Real changed ARM64 TU passes in crc108-compile/run-clk08lp_, object32104B
SHA78b23cbd63f51325d7984c14b9369ce1e51cd6816aafbc451bf454903ea47882.

User questioned Actions instead of local builds. Response committed to local
full/incremental builds for this debugging loop, CI for stable regressions.
Use existing deps/build-macos.sh with source108 and isolated
.deps-cache/p0-20261105/build, separate output p1-native-0108-20261105-out.
This will update the old native99 generated context: agents must NOT run old
HsArvW crosscompile helpers concurrently; wait for the new successful manifest.
Phone currently TWRP. Next: commit, local full build, identity/geometry check,
temporary0108 boot. Preserve0104/0107 images and all previous source trees.

Separate future P2 VFS helper integration is frozen only in ignored
p2-vfs-test-20261105/candidate-p2-vfs-after-root.patch;3files, defaultoff,
full report integration-qualification.json. It has NOT been included in108.
P3 owned-GPU buffer adapter is being prepared offline in p3-gpu-abi-20261105;
no real GPU activity. Neither task establishes additional hardware milestones.


### 2026-11-05 — first0107 real-input temporary boot accepted; observer live

0107 image9593097b... was temporarily booted: fastboot send16796KB0.392s,
boot0.134s,total0.534s. Observer **59631** is observing180s, still live at the
latest check. Cycle research/tmp/p1-nvt-0107-cycle-20261105.log; evidence
p1-nvt-0107-evidence-20261105.json. Do NOT duplicate a boot or replace its log.
No actual SPI/firmware/input result is available until the screen is checked
and fresh log recovered. No automatic recovery has been detected so far.
CI42021243212 is already completedSUCCESS, not a live job. Preserve0104 fallback.


### 2026-11-05 — 0107 complete CI passes; first physical-input image prepared

CI **42021243212** succeeded at exact public headb7d836a1a0c294721fa417228ea911dd783683dd.
101patches/allhosttests/make_exit0;5245source entries match source107 except
four exactly reproduced pinned dxb path adaptations. Ten required linked
symbols include actual bootstrap/bus/PIO/runtime and whole-frame HID. Full
qualification: research/tmp/p1-ci-0107-artifacts/qualification.json. No CI live.
Kernel17284168B SHA2566a11f250c79f3b9edafb7f2696f8a0c09f44b07fa696e9262d3c957d11d82ccc.
Complete build IDxnu-93babafdaaa64b119359ccf984e658a3; banner matches manifest and image.

Prepared shim/out/shim-p1-nvt-0107-20261105.img (17199104B),
SHA2569593097b74ce48fc467e861a85573a0fe0f04f0d8a1e74faa2e3c43f53f86ed9. PayloadSHA2561bf7204ade0fba3ec6314f8cdd5701b94fc5f8fac12ab4174eb1bb8922fb39fe.
Exact tested0104 shim/DTB/header geometry retained; baseline ADT plus reserved
NovatekFirmware. Asset PA0x18252c000, raw139264/reserve147456; boundaries,
actual asset bytes/zero padding and full image banner independently checked.
Baseline args plus sweetnvt=1, with sweetnvtprobe=0/sweettouchmode=0. No synthetic
input flags. Evidence research/tmp/p1-nvt-0107-evidence-20261105.json.
Image has NOT booted yet. Next: one temporary180s observation, user screen/
touch report, manual TWRP recovery and fresh exact-ID log. First physical SPI/
firmware/gesture result is unknown; do not infer input from these build checks.


### 2026-11-05 — 0107 pushed; complete kernel CI42021243212 running

Local3a317bf (23files) is published as sanitized public snapshot
b7d836a1a0c294721fa417228ea911dd783683dd, parent1f988a6. Push succeeded.
Exactly one gh workflow dispatch: CI **42021243212**, currently in the Build
kernel step, not yet qualified:
https://github.com/lvyufeng/ios-gauguin/actions/runs/42021243212
Artifacts/expected source and input snapshots: research/tmp/p1-ci-0107-artifacts/.
Do not dispatch a duplicate or use previous successful0104 output. Phone stays
TWRP, no observer or newer image boot. pack_ci107.py is prepared but must only
run after matching successful CI qualification. Latest hardware baseline0104.

Final integration single-TU report:
gauguin-nvt-p1/integration-compile/qualification.json. Eight ARM64 MH_OBJECTs
pass;70 distinct undefined symbols have providers in tested CI104, new objects
and the verified matching SweetHID object. This is still not a full kernel link.
Independent integration review confirms GAUGUIN-only bus/runtime, exclusive
startup, actual export/include paths, final status lifetime and valid-bit logs.


### 2026-11-05 — real NVT stack staged; complete local tests and eight ARM64 TUs pass

HID/asset tooling local commitbcc0a63 was published safely as
1f988a686337add3f822fc9fdad879e9093588a5 (parent e42a664). No private history
was pushed. New0107 now integrates the actual protocol/PIO/setup/kernel-bus/
firmware/bootstrap/runtime modules and exclusive startup hook. Driver default
is off. sweetnvt=1 takes the init path before probes/legacy and never falls
through; runtime rejects conflicting flags before creating its worker.

Fresh source107 applies101patches;5245files. Exact comparison with
source106-export shows only14new module files plusbsd/conf/files and
bsd/dev/sweet_touch.c; report p1-source107-comparison-20261105.json. Existing
storage/HID code is unchanged from the prior qualified stages. Source/input
snapshots are prepared in research/tmp/p1-ci-0107-artifacts/ for the next CI.
Full host suite passed (p1-host-tests-0107-20261105.log). Separate staged
bootstrap/parser/runtime tests with the exact local firmware also passed;
logs p1-staged-{bootstrap,firmware,runtime}-real-20261105.log. Public CI uses
synthetic bytes: runtime first proves the unchanged production pin rejects
those bytes, then tests a clearly labeled temporary synthetic-pin copy with
actual XNU SHA code; there is no production hash override or digest stub.

All eight actual changed/new BSD C TUs compile for ARM64 from source107,
including the runtime and hook, with the canonical IOKit header. Reports under
gauguin-nvt-p1/integration-compile/. Native generated build inputs were not
modified. Full-kernel CI/link and first physical SPI/input boot remain pending.

The bus rechecks the observed XO19.2MHz profile, configures960kHz SPI and owns
clocks/pins across bootstrap/polling. Fixed-file SHA/bounds precede hardware;
actual trim must match before SRAM loading. Native reset sequence,96936bytes
written and entirely read back, CRC/reset/FWINFO/version16/type1/PID5937 gates
precede67byte physical packets. Type1 is observed in recovery, not invented.
Bootstrap valid bits distinguish unread fields from actual zero responses;
compact final reports include actual CRCs, phases and PIO/setup fault state.
Failure stops SPI, attempts bounded release of previously accepted HID contacts,
then quarantines the bus; no automatic reset/reupload. No synthetic tap/unlock.
Documentation: docs/gauguin-nvt.md. Firmware/raw device evidence stay ignored.

Phone remains TWRP, read-only connection/battery check succeeded (100%). No
image has been booted since0104 and no observer/CI is live. Next: commit/push
sanitized0107 snapshot, run gh kernel CI, verify exact source and build identity,
pack the pinned firmware as reserved data and temporarily boot sweetnvt=1.
Physical touch, unlock, GPU, full memory/storage and high refresh remain unproven.


### 2026-11-05 — whole-frame HID and firmware packaging integrated locally

0104 remains the latest hardware-qualified normal-I/O lock-screen baseline;
phone is in TWRP after the confirmed manual return. No CI/observer is live.

0105 adds atomic whole-frame digitizer delivery and allocation failure handling;
0106 makes client close allocation-free and protects admitted callback targets.
The shared C ABI is now iokit/IOKit/SweetHIDTouchFrame.h, exported by the actual
IOKit header build and listed as private, rather than copied into BSD. Fresh
source106-export replays100patches and differs from source104 in exactly four
files (two HID C++ files, the new header and IOKit/Makefile). Comparison report:
research/tmp/p1-hid-source106-export-comparison-20261105.json. Final SweetHID
SHA256ddcaf8b03fb6c0b1e83a919c79abd73bcbf5a7a69427688589fbff339ffbc9a7;
actual ARM64 C++ TU passes in hid-frame/kernel-crosscompile/run-wlz0w1ia,
object382240B SHA9185ca4c302ca2f5f8eaffeb4c1e57538ffe9def708f540aecd821e4f889fb4c.
IOHIDEvent TU was separately qualified unchanged. Full host suite passes in
p1-host-tests-0106-export-20261105.log, including real-method OOM/concurrency/
release/reentry negative controls. No synthetic gesture or physical input is
activated by these patches. Full kernel CI and hardware regression are pending.

mkpayload now optionally accepts --nvt-firmware, pinning local raw139264bytes
SHA256007143e7d0a816e4ef228b5a08bf3132285230a5cd16164e8086696115d60f88.
It reserves147456bytes in16K pages and sets NovatekFirmware=<PA,rawsize>;
default output is byte-identical to the prior packer. Nine host test groups
pass using synthetic data, with pre-change output hash/info golden fixtures.
The firmware binary remains ignored. Actual CI104/local-asset packing was
qualified at PA0x182524000/top0x182550000, not booted. Payloadv1 has no mapping
permissions; the kernel consumer must verify bounds/hash and use the existing
RWNX reserved RAM mapping. No firmware flashing or partition change occurred.

Real NVT driver integration is in progress in ignored gauguin-nvt-p1 candidates:
bounded PIO, qualified bus ownership, native reset/trim, all-segment SRAM
write/readback96936bytes, CRC/reset/FWINFO/PID gates, then real67byte polling.
Actual bus and setup TUs pass; bootstrap/runtime final reviews and staged build
are pending. These host checks do not establish real SPI communication or touch.


### 2026-11-05 — controller access verified; P2 storage kernel passes normal-I/O baseline

Both pending hardware logs are now recovered after user-confirmed lock screens
and manual TWRP returns. Phone is currently TWRP; no CI/observer is live.

0102 mode2 log `research/tmp/p1-nvt-stage1-0102-recovered-20261105.txt`:
8666lines, ring518411bytes/flush2740, PET2740 at~2751.68s. Stage1 completed and
GCC added bits4c0 restored from9c000003 back to9c000003; no captured panic,
shutdown or UFS errors. Log SHA25665792124111042c1a071c96dee3bf6c1e74390aa90005e2ae7362e0865a7deec.
Observed wrapper20070000 (v2.7), SE FW/SFW101 (SPI1), STATUS0, FIFO_DISABLE0,
HW_PARAM0=201029e4/HW_PARAM1=20104800 (16words/32bits), TX/RX empty.
MCLK11/CLKSEL0 with qualified XO19.2MHz means inherited SCK19.2MHz, exceeding
the touch device10MHz limit. WORD_LEN0/PACK0=7f807 also need8-bit configuration.
PACK1=ffefe, DMA_MODE0, CPHA/CPOL/CS_SEL/CS_INV0, externalIRQf, GSI0,
M_IRQ_EN33c0007e. This proves access to those registers, not SPI communication.
RST21 remains GPIO input/pulldown/low; no chip identity or firmware upload yet.

0104 storage regression log `research/tmp/p2-ufs-0104-recovered-20261105.txt`:
5251lines, ring351364bytes/flush1043, PET1020 at~1030.04s; exact new build ID
xnu-fa92111953af4c2a9940d24a7c73578b matches image. No captured UFS/log errors,
panic or shutdown. Actual runtime logs physical28056571/exposed28055482,
reserved1089blocks and HFS17179869184B. Thus the new geometry is actually in
use and normal lock-screen IO survives; timeout recovery and data-integrity
stress are NOT hardware-qualified by this. Log SHA256
5ce9f10d8a5d830f09dddce048925003eb9eae94a70eb667a4af9f0f58d3100d.
Read-only block at exposed_end-4096 has zero at expected alternate VH offset;
no alternate-VH write was observed, so do not claim that on-disk write path was
exercised. Existing HFS volume remains16GiB; no format/resize/GPT change.
0104 image36311353... is now a verified normal-IO lock-screen baseline.

0105 (whole-frame HID API plus digitizer factory NULL handling) and host fixtures
are being staged into fresh source105; no input is enabled. Independent review
found baseline handleClose could leave a raw target after allocation failure;
a separate no-allocation client-close candidate is frozen for0106. These input
interfaces still need full-kernel CI and physical event evidence.
SPI setup and bounded firmware parser/plan candidates remain ignored; payload
asset packaging is being prepared without changing default image output.

### 2026-11-05 — P2 CI passes, image prepared; mode2 log still pending

Local a7ce787 (UFS0103/0104) and17b4aeb (build identity) are published together
as sanitized snapshot7b6f72db1d99b4938700d3364e30cdf415aaf061, parent5ca5e7a.
Push succeeded. CI **42004257034** succeeded for that exact head:
https://github.com/lvyufeng/ios-gauguin/actions/runs/42004257034
Dispatch file `research/tmp/p2-ci-dispatch-0104-20261105.txt`; artifact target
`research/tmp/p2-ci-42004257034-artifacts/`.98patches/allhosttests/make_exit0;
source104's5230entries qualify with only the same four exactly reproduced dxb
path changes. UFS SHA52d9e171... matches. Kernel17313240B SHA256
45a9b2f3a683b73043bae509d766bb2d55616941930c60099ffa3265025f959f.
Actual complete banner and manifest share ID
`xnu-fa92111953af4c2a9940d24a7c73578b`; same-date historical log is rejected with
exit3. Fresh CI had no old link targets; incremental preservation remains
host-fixture verified, not an actual cached CI build. Mach-O/payload static
qualification passes. No CI or device observer remains live; do not duplicate.

Prepared `shim/out/shim-p2-ufs-0104-20261105.img`, SHA256
363113537421a1c67d476d1b02adb8b25e8c3220991e762caf6e024fa823fba7.
Evidence JSON `research/tmp/p2-ufs-0104-evidence-20261105.json`. Preserved
shim/DTB/ADT and baseline args, explicitly sweetnvtprobe=0/sweettouchmode=0.
This image has NOT booted. No filesystem capacity or metadata change has been
performed by0103/0104 on the device; current root is still the16GiB volume.

Phone's0102 mode2 experiment was observed for181seconds; user recovery/screen
confirmation is still pending and latest adb had no device. Do not boot the
P2 image until the mode2 log has been collected. Next P2 hardware regression
should use the established lock-screen args with sweetnvtprobe=0, so storage
behavior is tested independently of new controller accesses.

The HID whole-frame candidate remains ignored under
`research/tmp/gauguin-nvt-p1/hid-frame/`; reset_evidence is preparing final
factory-allocation/publication-lifetime corrections after its first real C++
TU pass. Do not treat its old hash as the final candidate without checking the
agent's latest report. No HID frame patch is integrated and no real touch
input has been verified.

### 2026-11-05 — storage fixes committed; unique build identity ready for integration build

Local **a7ce787** commits0103/0104 and their host fixtures; source104 is the
fresh98-patch tree and differs from source102 only in bsd/dev/sweet_ufs.c.
Report `research/tmp/p2-source104-comparison-20261105.json`; full host suite
passes in `p2-host-tests-0104-retry-20261105.log`. These storage fixes have not
been built as a full kernel or booted yet. The mode2 phone log is still pending
manual TWRP recovery; do not replace that boot before collecting its evidence.

Build tooling now assigns each manifest a unique xnu-UUID32 identity through
the real KERNEL_BUILD_OBJROOT/newvers path. Native/CI/Linux adapters explicitly
pass it. prepare-build preserves the selected old unstripped kernel/version.o
under the new run and removes those exact link targets so even same-tick,
unchanged-source incremental builds relink. Published known kernels are untouched.
finish refuses a missing, mixed or different-ID complete banner despite make0.
Observer/cycle/image-audit use one complete-banner parser instead of date-only
or75/120-byte comparisons. Observer wording no longer claims that missing TWRP
proves the kernel is running. This identifies a build, not repeated boots of
the same image. It deliberately changes output bytes between invocations.
Actual newvers/version.o incremental negative controls and all host fixtures
passed; the first full CI build with the new identity remains pending.

### 2026-11-05 — 0102 mode2 observation ended; storage fixes ready for CI

Local71785a1 was published as sanitized snapshot
5ca5e7a56eaafb3b413b8e3cce911ee12cf5241a (parenta6ffd47). CI **41998969266**
succeeded, 13.5/DEVELOPMENT/gauguin:
https://github.com/lvyufeng/ios-gauguin/actions/runs/41998969266
96patches/allhosttests/make_exit0; source102's5230entries match except the four
exactly reproduced dxb path adaptations. Artifact directory
`research/tmp/p1-ci-41998969266-artifacts/` includes qualification.json.
Kernel17313240B SHA2561cc6a95a8930b656921287bd52c27dfa1934bd467b2ea5988021418c0ead784b;
Mach-O/mkpayload boundaries pass. No CI is live now; do not duplicate dispatch.
Mode2 image `shim/out/shim-p1-nvt-stage1-0102-20261105.img`, SHA256
a8ec6c4126a1cc94d027fb1436bce9dd666bb4eff3e7b262453c2e2c62749b7f, preserves
baseline shim/DTB/ADT and args except sweetnvtprobe=2, with old sweettouchmode=0.
Temporary observer63560 ended after181s without recovery (exit4); send16616KB
0.387s,boot0.134s,total0.527s. Cycle
`research/tmp/p1-nvt-stage1-0102-cycle-20261105.log`. User was asked to manually
return to TWRP and report the screen; reply is pending, latest adb reports no
device. Do not boot another image before recovering this log. No mode2
hardware result is known yet.

P2 now has0103/0104 ready for CI, not hardware-qualified.0103 holds global DMA
ownership after the slot-owner mutex through bounce preparation/command/result;
panic uses try-lock only. A timeout permanently quarantines DMA for this boot,
retains its allocation and rejects reuse; host/device recovery is not implemented.
All sync-cache errors propagate. Old sweetstage UFS writes are disabled, keeping
no-op exported interfaces.0104 reserves1089physical4K blocks from BSD exposure,
keeps original GPT bounds/log addresses, validates HFS geometry before mount,
and checks signed/large sector numbers before multiplication. No resize/format
or GPT write occurs in that code. This does not yet expand the16GiB filesystem.

The first sequential-only candidate was insufficient; independent review caught
admission/completion races and a legacy stage bypass. Final actual-flow threaded
ASan/UBSan tests cover waiting root/log/mark owners, timeout/bounce quarantine,
panic busy-owner skip, and independent completion/OCS/UPIU/cache/sync failures.
Root completed the revision after the parallel UFS task was interrupted by a
tool content check. Final source SHA256
52d9e171135755aceb02e1bfd9d97b49b0890ea4575999207e384cae33842582.
Real ARM64 UFS single-TU passes (`p2-dma-audit-20261105/kernel-crosscompile/run-cqb6pu9r`).
Fresh source104 replays98patches; full host suite passes after adapting old
descriptor/mark fixtures to their new ownership dependencies.
Known tradeoff: global owner spans an entire mark/log batch, delaying root IO;
a contended panic flush is skipped. Future optimization/recovery needs its own
qualification. Old source101 and known boot artifacts remain unchanged.

Current partition-tail bytes do
not contain a VH signature; this does not prove a corruption event or erase
the demonstrated potential same-LBA conflict in the code paths.

P3a **preparatory audit and address planner only** are done in ignored
`research/tmp/p3-gpu-abi-20261105/`. NativeAdreno's old PA>>12 CPU cache-attribute
calls are invalid for this16K XNU; use owned16K backing split into4K SMMU leaves,
with low32bit GPUVA separate from high physical addresses. No real GPU submit,
fence, Metal or rendering is implemented or verified by these host fixtures.
Live memory inventory: DT banks total8517582848B, recovery MemTotal7742418944B,
current XNU high bank4293918720B at0x180000000. Raw maps remain ignored under
`p2-recovery-memory-map-20261105.txt`; summary `p2-memory-inventory-20261105.json`.
Linux runtime allocations/reservations must not be mistaken wholesale for
permanent firmware holes. No RAM expansion has been attempted.

### 2026-11-05 — stage0 succeeds on hardware; reset/SPI state must be initialized

User confirmed the0101 diagnostic image still showed iOS lock screen before
manually returning to TWRP. Fresh log
`research/tmp/p1-nvt-stage0-0101-recovered-20261105.txt` has4380lines,
ring293626bytes/flush677, PET690 at13433092793ticks (~699.64s). No captured panic,
shutdown or UFS error. Stage0 snapshot and worker-finished markers are present.
Log SHA256705d69f9c2888b52ede7779a030e88f6af89e5dbbc119e4f9496fd772a67f53d.
Phone is now TWRP, no boot/observer/CI is live. Public head for the latest
handoff is a6ffd4709859076ff8146d98a41205be95341e22 (local91fa519); tested code
head remains3b2e3987. Never push the private development ancestry.

Observed raw XNU handoff state (not the earlier recovery active state):
- GCC vote52000=9c000003. M_AHB21004=0, S_AHB21008=8000000a;
  core2100c/core2x21014=4220 (CLK_OFF31 clear), S0 CBCR21144=80004220.
- RCG_CMD21148=80000000, DFS2115c=21, selected level0 CFG21164=1,
  stable on repeat. Parent0/XO and HID1 imply19.2MHz from the pinned clock
  model, not the recovery100MHz cached rate. SPI divider remains unread.
- GPIO0 cfg1/io1; GPIO1 cfg200/io0; GPIO2/3/21/22 cfg1/io0.
  All are GPIO mux0. RST21 is input with pull-down and low observed level;
  do not assume the touch chip retained its running firmware across reboot.
These named GCC and TLMM accesses are now hardware-verified. Wrapper/SE access
and real touch input remain unverified. No touch pin or reset was written.

Next P1 candidate is mode2 controller-only access: temporarily vote only GCC
bits6/7/10, use native bounded branch checks, persist markers before wrapper
HW_VERSION and SE FW/status reads, collect named idle-SPI config if qualified,
restore only added vote bits. No GPIO, SE configuration, SPI or HID writes.
This is a controlled first peripheral-access experiment, not a guarantee that
clock readback proves fabric access.0102 now contains this mode2 implementation;
the default remains off, mode1 remains read-only stage0. Fresh source102 replays
96patches and differs from source101 only in bsd/dev/gauguin_nvt_probe.c.
Actual ARM64 single-TU compile and all host tests pass. Probe source SHA256
ecad5b2aee182b81cd4fd9c95e07472827a05903464d4239db0fa6541a88fa68;
crosscompile report `gauguin-nvt-p1/kernel-crosscompile/run-8xokbtv_/compile.json`.
Actual-flow ASan/UBSan tests cover all initial vote subsets, peer-bit changes,
three gate timeouts, vote rejection, mapping/identity/busy failures and failed
restore reporting.2ms gate polling is deliberately longer than native200us;
neither can bound a synchronous MMIO stall. No other XNU QUP0 owner is allowed
during this bring-up probe; this is not a refcounted shared clock driver.
Full CI and mode2 hardware access are pending. Keep old touchmode1 off.

Parallel P2 audit reproduced two real defects using actual functions: UFS timeout
clears a list bit without ownership quarantine then reuses descriptor/bounce;
filesystem GETBLOCKCOUNT exposes physical tail used by log/marks, placing HFS
partition-end alternate VH in the last log block. Candidates are not integrated.
Read-only real HFSX header capture (ignored) proves allocation block4096,
total4194304=16GiB, free708124; physical userdata114919714816B. Reserving current
log+64mark blocks would not truncate this volume. Future driver guard must still
validate geometry before mounting other/full-sized volumes. No resize, format
or partition change was performed. Repro/geometry evidence under
`research/tmp/p2-dma-audit-20261105/` and `p2-hfs-geometry-20261105.json`.

### 2026-11-05 — 0101 CI passes; stage0 observation ended, awaiting recovery

0101 and its tests are committed locally as74bbe29 and published as sanitized
snapshot3b2e3987dbc9a39ff1ba186bfe1bd31fdeec259b, parentb7a266d.
CI **41992972330** succeeded for that head (13.5/DEVELOPMENT/gauguin):
https://github.com/lvyufeng/ios-gauguin/actions/runs/41992972330
95patches/allhosttests/make_exit0. All5230source entries compare to source101,
apart from the same four exactly reproduced dxb path-adapter files. Probe
symbol is linked; payload layout and bounds qualify. Report:
`research/tmp/p1-ci-41992972330-artifacts/qualification.json`. Downloaded kernel
17296776bytes, SHA256cc34cae7d20b179c7f24461e4589800d94d832dad0ec1b9bf23f51e8573871d1.
Do not dispatch another run or confuse this with successful baseline41989463747.

Temporary image `shim/out/shim-p1-nvt-stage0-0101-20261105.img`, SHA256
29a9f4856243a579526eba731cd803e87eb68e510f947e0ace67d300fb55f051, uses preserved
shim/DTB/ADT and baseline arguments plus sweetnvtprobe=1.180second device
observer90557 ended after181s without recovery; expected exit4 because XNU
does not expose the recovery log channel. Cycle
`research/tmp/p1-nvt-stage0-0101-cycle-20261105.log`; evidence JSON
`p1-nvt-stage0-0101-evidence-20261105.json`. User asked whether a manual reboot
is needed and was instructed to return to TWRP, retaining pre-reboot screen
observation. That confirmation is pending. No stage0 register result yet.
Fastboot send16616KB0.394s,boot0.134s,total0.534s. Latest adb get-state reports
no device; do not treat an absent USB connection as proof of a hang or crash.
Next: read fresh log and interpret named register snapshots. Do not boot
another image until that log is captured; keep old sweettouchmode1 and host-only
SPI candidates disabled. This build still cannot accept physical touch.

### 2026-11-05 — P0 lock-screen baseline passes; opt-in NVT stage0 ready for CI

Public handoff snapshot **b7a266d830c1f6b0e59cf7cd233e05d3dd615a43** (local
057bd51) was pushed successfully after the user's explicit authorization.
This documentation update does not replace the tested CI kernel head6a6fe42.
User confirmed the CI0100 image has reached the iOS **lock screen**. Observer
22696 ended after660s without automatic recovery (exit4 because USB/log pull
is unavailable while XNU runs). User then manually returned to TWRP. Fresh
`p0-ci-0100-recovered-20261105.txt` has the exact image banner,4129lines,
ring277297bytes/flush671, PET710 at13817295132ticks (~719.65s at19.2MHz),
60presents/client2. No captured panic/shutdown or UFS failure/timeout. Evidence
JSON `p0-ci-0100-evidence-20261105.json`; log SHA256
7b5a08a8993e1ad5b965a7f397e89e6f55cd3482a4ecb6e69bf18017d5252368.
Together with the native clean0099 regression, P0's reproducible lock-screen
baseline gate passes. Unlock/home, real input, GPU and daily use remain open.
Phone is now in TWRP; no observer remains live.

0101 adds `bsd/dev/gauguin_nvt_probe.c`, its build entry and a call from touch
initialization. Only `sweetnvtprobe=1` queues an independent worker delayed30s;
the default does not map or read hardware. Thread creation failure never runs
inline. The probe performs named GCC reads (vote,5CBCRs, bounded selected
DFS/RCG tuple, selected GPLL raw fields) and CFG/IO reads for pins0/1/2/3/21/22.
It does not map wrapper/SE or write MMIO, call RPMh, issue SPI, reset touch or
publish HID. Persistent phase markers use the existing UFS logging path.
Invalid/changed clock selections stop the dependent sampling; observed PLL
values are not called a verified rate or a proof that SE MMIO is accessible.

Independent native source audit separates QUP0/core and DDR bandwidth votes
from the CPU-to-QUP CNOC path; no supported single GCC/TLMM predicate proves
SE accessibility. Thus this first probe deliberately samples only GCC/TLMM.
Source/reference report is `research/tmp/gauguin-nvt-p1/bus-preconditions.txt`.
TLMM is confirmed by recovery, not yet by this XNU probe.

Fresh upstream `.deps-cache/p0-20261105/source101` replays95patches. Full
comparison with source100 shows only new probe, bsd/conf/files and sweet_touch.c
changes (`p1-source101-comparison-20261105.json`). Actual ARM64 kernel single-TU
compiles pass for both the probe and changed hook using the successful native
build flags. Candidate SHA256879b7ae33791f47bd196537396ba93d7c6e10bbd248e8d83fb9afd54acdf7eda.
ASan/UBSan fixtures cover actual stage0 control flow with only MMIO load/barrier
and XNU services mocked: disabled/noIO, one-shot and thread-failure behavior,
30second delay, named register/map allowlist, DFS/mode/PLL invalid or changing
states and map failures. Initial full-suite failure was the existing touch-gate
fixture lacking the new independent init dependency; its mock was added and
one-shot call checked, while test_nvt_probe tests the real diagnostic path.
Full host suite now passes in `p1-host-tests-0101-retry-20261105.log`. Crosscompile
script and argv/log evidence are in ignored `gauguin-nvt-p1/kernel-crosscompile/`.
All12undefined probe dependencies resolve in the known native kernel. A full
CI build is next; this is diagnostic groundwork, not working physical input.

### 2026-11-05 — remote push authorized; third CI succeeds

User explicitly authorized pushing code to the remote. Continue publishing only
sanitized snapshots on `codex/gauguin-p0-ci-20261105`; the private development
branch's historical device identifier must still remain local.

Local commit f378f37 (0100 platform guards and handoff) is published as snapshot
6a6fe426781a0327a96e89c3383f3129c21964ca, parent b69e431. Third CI
**41989463747 succeeded** on that exact head:
https://github.com/lvyufeng/ios-gauguin/actions/runs/41989463747
Artifacts are in ignored `research/tmp/p0-ci-41989463747-artifacts/`.
Downloaded kernel17313000bytes, SHA256
`6c258c443d5dc986ae403ad480bce7cdc3c514bfed3100194fdb46aa9f8ac1d6`.
Manifest make_exit0 and artifact hash pass. All5229 source entries were compared
against source100:5225 match, with only the four documented dxb path-adapter
files different.0100's two C files match. Mach-O and mkpayload checks pass;
the linker rename_segment warning produces no new nonempty segment-name
difference against native0099. Report: `payload-qualification.json` in the
artifact directory. This does not yet qualify the CI kernel on hardware.

Prepared temporary image `shim/out/shim-p0-ci-0100-20261105.img`, SHA256
`27d8bb2a7207d5032a059e76c3e07c1a654f7a306e33e6bda37e28be419fc9a5`,
with the exact shim, DTB, ADT and boot arguments from the successful native0099
image. Only the XNU kernel changes. Before boot the device was in TWRP3.6.2.1B;
SPI power/control=auto and runtime_status=suspended. Temporary fastboot boot
succeeded: send16616KB0.394s, boot0.134s,total0.540s.660second observer is now
running, exec session22696; cycle log `p0-ci-0100-cycle-20261105.log`, intended
recovered log `p0-ci-0100-observe-20261105.txt`. Do not boot another image while
this observation is running. No CI-kernel UI confirmation or recovered log yet.

P1 board candidate and sanitizer fixtures now exist only under ignored
`research/tmp/gauguin-nvt-p1/`. Resource probe restores its pin/vote masks on
exit and defaults unknown parent clocks to CLOCK_UNVERIFIED. Native interconnect
votes precede clock enabling; inherited fabric access remains under review.
Do not assume a software timeout can rescue a stalled peripheral MMIO read.
Protocol/PIO/board host passes are not physical touch or unlock evidence.

### 2026-11-05 — P0 device gate passes; CI platform guard fix ready; P1 active resources captured

After user manually returned to TWRP, fresh log is
`research/tmp/p0-clean-0099-recovered-20261105.txt` (+.bin): banner14:58:55,
332430bytes/flush887/4903lines, PET860 at16700073482ticks (~869.8s at19.2MHz),
130presents/client2. No captured panic/shutdown or UFS OCS/timeout/write error.
User explicitly confirms lock screen, with no touch/unlock. This passes the
native clean-build/ten-minute lock-screen regression portion of P0; it does
not prove home-screen operation or any GPU/input capability. Battery read in
recovery100%,33.4C. Correct PON subtype4 registers now read successfully;
charger WD_CFG raw0, so the earlier charger-watchdog conjecture is not supported
by this run. Device returned manually, not automatically.

Second CI41984003767 is terminal FAILURE at final link, missing
_iBoot_Stage_2_version. Both real compiler commands set XNU_TARGET_OS_OSX,
but pe_init.c lacks SDK TargetConditionals while model_dep.c includes it via
corecrypto. New local clang predefines TARGET_OS_OSX; CI clang15 does not.
0100 fixes all five related guards to the build-wide XNU_TARGET_OS_OSX, keeping
ARM64 restriction and real definition/DT fill/logging, not adding a stub.
Independent-TU regression22macro combinations compile/link/nm/run successfully.
Fresh `.deps-cache/p0-20261105/source100` replays94patches; only the expected two
files differ from source99, all other5227bytesets/paths are unchanged. Evidence:
`p0-source100-comparison-20261105.json`, `p0-replay100-20261105.log`,
`p0-ci-41984003767-artifacts/audit/macro-audit.json`. New CI still to dispatch.

P1 protocol+PIO candidates in ignored research/tmp/gauguin-nvt-p1 pass sanitizer
host fixtures, including actual combined67byte transfer, FIFO contention,
malformed contact snapshots and timeout/cancel. These are NOT kernel drivers
or hardware communication proof. Source99 SweetHID already clamps1079/2399;
NVT IDs1..10 map toslots0..9. It dispatches after each individual finger update,
so a future frame-level API is preferable to intermediate all-up snapshots.

Recovery SPI is normally suspended with SE0 source rate100MHz, gatecount0.
First printf-based PM writes reportedEINVAL; exact single-write behavior was
not proven (strace unavailable). Ordinary-file bytes were correct. A subsequent
single-block dd write of the same on value succeeded; native runtime PM reached
active, and both captures restored **auto+suspended**. No SPI command, reset,
raw-register scan or firmware write was performed by these captures.
Active snapshot files: `p1-nvt-recovery-active-dd-20261105.txt` and
`p1-nvt-recovery-active-gpio-20261105.txt`:
- M_AHB/S_AHB andSE0 enable/prepare1, SE0/source100MHz; wrappercore/core2x0.
- GPIO0 in/high func2, GPIO1 out/low func2, GPIO2 in/low func1:6mA,pulldown.
- GPIO3 in/high func1:6mA,no pull.
- RST21 out/high func0:16mA,pullup; IRQ22 in/low func0:16mA,pulldown.
These replace guessed board settings. Native PM changes were temporary and
verified restored. Board candidate may only touch native-confirmed clock bits
6/7/10 and SPI pin fields; do not enable unused core bits8/9 or reset21.
First future XNU stage is bounded resource/protocol/clock-state qualification,
then inherited-FW metadata reads when ready; do not publish HID on guesses.

### 2026-11-05 — P0 native clean build passes; lock screen confirmed, touch pending

Local commit **c0f200a** adds0098/0099. Full native target rebuild from source99
completed **makeexit0**, all host checks passed, and the output was published
only after validation. Manifest
`.deps-cache/p0-20261105/build/runs/gauguin.HsArvW/build-manifest.json` records
that commit and only the preserved tools/mkadt.py tracked dirty edit. Kernel
16761424bytes, saved `research/k-p0-clean-0099-20261105`, SHA256
`a748836a3f311cf2879ac51a65432bd869c65e141c896b98cacdfd2fc679f7c6`.
Native log `research/tmp/p0-clean-native-retry2-20261105.log`.

Temporary image `shim/out/shim-p0-clean-0099-20261105.img`, SHA256
`48d70b18704328e79dde1d0fb7fd54fbd74318cb3a77f14a0d07ac301f2657ec`, uses the
same saved ADT and UI commandline, including cpus8/sweettouchmode0. Send16688KB
0.397s,boot0.134s,total0.537s. Observer660seconds is running, session55785,
cycle `research/tmp/p0-clean-0099-cycle-20261105.log`; no log pull yet.
User confirmed UI at~3minutes, then clarified **LOCK SCREEN ONLY; touch does
not work and cannot unlock**. Do not claim the home screen/unlock is verified.
The old probe remains intentionally disabled; physical Novatek input is P1.

CI public branch now has snapshot **b69e4313af8bc6f427241011848c8212997fe70a**,
parentdf02d30, same tracked tree asc0f200a. New run **41984003767** was dispatched
and is being monitored; do not mistake prior failed41982348666 for this run.
https://github.com/lvyufeng/ios-gauguin/actions/runs/41984003767
No device test of a CI-produced kernel has yet occurred. P0 ten-minute device
log gate and final CI qualification remain pending.

During the device wait, P1 protocol/PIO candidates are being prepared only in
ignored `research/tmp/gauguin-nvt-p1/`, with host fixtures. No P1 kernel code or
hardware operation has been enabled. Native point packets have no established
checksum in this driver's source; do not invent one. FWINFO complement check
is real. NativeSPI choosesDMA above64bytes; our proposed67byte PIO service must
be independently validated, not described as a proven native code path.

### 2026-11-05 — P0 build gaps fixed by0098/0099; fresh93-patch replay verified

CI41982348666 completed FAILURE, makeexit2. Its reported compiler root cause is
ipc_mqueue.c:228: matched label directly precedes uint32_t declaration, accepted
as a C23 extension by local clang but rejected by Xcode15.0.1 in CI. Full failed
step log: `research/tmp/p0-ci-41982348666-failed.log`. The run is terminal; no
CI remains live until a new run is dispatched. Do not poll/restart it as a wait.

0098 changes only host LLDB installation: python3 -I prevents stdlib shadowing;
syntax validation happens before INSTALL so failure leaves no target. Regression
uses the actual invocation and actual Make template: valid input passes,
invalid syntax/TAB fail and create no output.0099 inserts a null statement after
the diagnostic label, preserving behavior under C11. Its extracted real tail
fails -std=c11 -pedantic-errors before the patch and passes afterwards.

Both patches were appended to series and replayed from the pinned upstream into
`.deps-cache/p0-20261105/source99`: **93patches pass** and source-state is recorded
under `.deps-cache/p0-20261105/build/source-state`. Complete source comparison
has5229files: only makedefs/MakeInc.rule and osfmk/ipc/ipc_mqueue.c differ from
frozen0097; all other5227files and executable modes match. Report
`research/tmp/patch-repro-audit-20261105/p0-source99-comparison-20261105.json`.
Tests/test_lldb_syntax.py passes against source99.

For a full target recompile, failed retry object/symbol directories were moved
to `build/obj-pre0098` and `build/sym-pre0098`. No old object kernel was copied
or published. The isolated SDK and dependency build remain; these two changes
do not alter their header inputs. Original authoritative cache/frozen0097 and
UI-producing artifacts are unchanged. Next native run must explicitly select
source99 and keep --build-root at the isolated P0 build directory.

### 2026-11-05 — P0 scripts committed; isolated kernel links; Python install fix pending

P0 reproducibility changes are committed on local branch
`codex/gauguin-p0-repro-20261105` as **4d2a01f**. SDK host/target separation and
nine build fixtures passed. Subsequent privacy cleanup is **94278f7**.
**Do not push the local development branch/history:** publication audit found a
device identifier in an old unpublished handoff commit. Current tree was
redacted, but history remains local. CI uses a sanitized snapshot commit
**df02d30db0c429fcc25a33a15f6c6fc333159e1f**, parent remote main fef77ed, on
`codex/gauguin-p0-ci-20261105`. It has the same final tree as94278f7 and no new
identifier. Only this snapshot branch was pushed. Future CI updates must remain
children of this public snapshot branch, not expose the private local history.

CI **41982348666** was dispatched with gh, profile13.5/DEVELOPMENT/gauguin.
Latest authoritative poll: job127095123216 in_progress at Build kernel,
setup/checkout/profile/deps passed. URL:
https://github.com/lvyufeng/ios-gauguin/actions/runs/41982348666
This is not yet a successful build; keep polling this run rather than duplicate it.

Native retry log `research/tmp/p0-clean-native-retry1-20261105.log` (352MiB)
shows full compile/link produced an approximately16MiB object kernel under
`.deps-cache/p0-20261105/build/obj-gauguin-macos/DEVELOPMENT_ARM64_GAUGUIN/`.
But make still returned2, and publication correctly failed: LLDB macro syntax
checking starts Python with its script directory on sys.path, shadowing stdlib
collections with tools/lldbmacros/core/collections.py. The failure is ImportError,
not permission to copy the object kernel and call the build successful.

0098 is being implemented only in fresh P0 source makedefs/MakeInc.rule:
explicit python3 -I isolates the host syntax checker, and validation precedes
INSTALL so failure cannot leave a target that later mtime checks skip. Original
command failed under3.14; isolated command passed under3.14/3.9/3.15 and still
rejects invalid syntax. Regression fixture and patch are pending. Old cache and
frozen0097 remain unchanged. Remove the failed P0 dSYM Python install targets
or use fresh objects before retry; none of these failed builds is a boot image.

A raw `git diff --cached --check` flags required unified-diff context whitespace
inside the new6063-line0083patch. Script/source whitespace checks exclude
*.patch, while patch validity is covered by strict replay/hunk validation and
complete resulting-source comparison. Do not strip patch context to silence it.
The pre-existing tools/mkadt.py edit remains uncommitted and out of CI snapshot.

### 2026-11-05 — P0 fresh replay passes; first clean build exposes host SDK mixing

Final fresh staging into `.deps-cache/p0-20261105/source` starts from Git object
1b191cb58250d0705d8a51287127505aa4bc0789, tree
5c0fc728332a322c2fb8fde61dfc6152a34c9ad6; Apple GitHub API independently matched
both IDs. All91patches, fixedSDKheader, post-patch and watchdog staging pass.
The new tree's5229files equal frozen0097 in content/type/executable bits with
the documented three cached-only exclusions. Final report is
`research/tmp/patch-repro-audit-20261105/p0-final-source-comparison-20261105.json`;
source manifest SHA256 b399d8e00ec76217f7a8c43c58fa0f8c8e8170bd6692b40b1db6552f0ff55911.

The first genuinely isolated native build FAILED, makeexit2. It correctly did
not publish a kernel. Log `research/tmp/p0-clean-native-build-20261105.log`,
failed manifest `.deps-cache/p0-20261105/build/runs/gauguin.j373g4/build-manifest.json`.
The failure is in HOST SETUP tools, not a newly identified kernel bug:
installhdrs replaces sys/cdefs.h in the kernel SDK copy with XNU's older header,
while modern SDK libc headers still require __alloc_align and
__swift_nonisolated_unsafe. build-macos incorrectly points HOST_SDKROOT_RESOLVED
at this mixed kernel SDK. Original system SDK has the macros. Old and new
kernel SDK headers match; old cached SETUP binaries had hidden the problem.
Fix implemented and nine build fixtures pass: host tools use the pristine
system SDK; target kernel retains the isolated staged SDK. The manifest records
both SDK identities/cdefs hashes; CI also hashes generated framework headers.
No per-header macro workaround or copied old binary. Failed target object/symbol
directories were moved to obj-failed-sdk-mix/sym-failed-sdk-mix inside the P0
build root, so the retry will rebuild all target objects.

Host checks on final replay passed in
`research/tmp/p0-build-script-host-tests-20261105.log`;8build fixtures also test
stale-output rejection and propagation of a failing CI installhdrs before its
success marker. CI profile13.5/source pins, strict staging, unique publication
stage and input manifests are implemented but not yet committed or CI-qualified.
Review also requested a digest of generated framework/private headers, not just
fakeroot/usr/local. Real native build is being used to close actual gaps.

Recovery was read-only checked: TWRP3.6.2.1B-gauguin, battery100%,31.8C. No
new boot has been performed. Original UI artifacts remain hash-verified.
Parallel GPU audit is saved as `research/tmp/ui-gpu-abi-audit-20261105.txt`:
flame uses NativeAdreno ABI1 while current UniXNU hasABI2; the exact Mesa/m2v
patch set must be pinned. First headless GPU memory-write/fence test can avoid
the full Rust/Metal toolchain. No GPU implementation or hardware test yet.

### 2026-11-05 — revised app goal ACTIVE; P0 source equivalence verified

The user set the revised objective in the app and resumed it. get_goal confirms
active status. The preceding planning turn made progress by committing the
staged plan622ef08; no no-progress blocker applies. P0 is now executing, on
branch `codex/gauguin-p0-repro-20261105`. Remote main is ancestor fef77ed;
local work is128commits ahead,0behind before this P0 implementation.

The known UI kernel/image/ADT and0097 kernel were SHA-256 checked and match
the recorded full hashes. Cached0097 source is frozen under
`research/tmp/patch-repro-audit-20261105/frozen0097/`.
Full bidirectional tree scan found **5229common files with identical bytes**,
no replay-only files and no symlinks. All executable bits match.5184ordinary
mode differences are cache group-write bits (664/644 or775/755); watchdog
header is600/644. These access permissions are explicitly normalized, not
claimed byte-for-byte filesystem metadata identity.

Three cache-only files are explained: .patch-set local tag, generated lldb
Python bytecode, and unreferenced bsd/kern/sweet_probe.c. A full source search
finds that probe only in itself; nm of0097kernel contains none of its symbols.
Raw manifests and qualified report are under the audit directory as
`p0-{cached,replay97}-source-manifest-20261105.json`,
`p0-source-compare-{raw,qualified}-20261105.json`. The qualified result passes
with those explicit non-build exclusions. This supersedes the old0091-only
full-source-compare.json; clean compilation and device regression are pending.

Build/CI work is being corrected to isolate all SDK/obj/sym/log/install paths,
reject stale kernel success, record inputs, and reject unsupported profiles.
Independent review found prepare.sh wrongly resolves SDK headers even when
SKIP_TARGET_MACROS=1, breaking Linux staging; that fix is included in P0 scope.
No CI run is live: most recent39957353555 ended failure at3a2f529. No new device
operation has started. GPU ABI/source audit proceeds read-only in parallel.

### 2026-11-05 — revised engineering goal and staged implementation plan

The user approved the comparative recommendation and requested an updated goal
and a plan for staged implementation. This entry is the current engineering
scope and supersedes earlier next-action/paused-work prose for planning.
At planning time the app-managed goal was still paused and the available
tools could not edit its objective or resume it. The user has since updated the
objective and activated it; see the newer P0 entries and verify with get_goal.
No new build or device operation was started during the planning turn itself.

**Revised goal text (ready for the app's goal field):**

> 在红米 Note 9 Pro 5G（gauguin，SM7225／Adreno 619）上，保留已验证的原厂引导＋shim＋XNU／iOS 16 基线，复用已有实机成功的开源组件，分阶段实现真实 GPU／Metal 加速、全部安全可用 RAM 与可靠持久存储、触摸及手机外设、90／120 Hz 高刷，以及联网、通话、充电、休眠等日常功能。以本机实测的稳定性、帧率、功耗和应用兼容性验收；未完成的关键功能保持未完成状态，不以进入主屏幕、虚拟容量或占位驱动代替完成。保留恢复能力和备份，任何破坏性写入逐次确认。

**Architecture decision:** keep this device's working ABL/shim/XNU path. GPU
integration first follows ios-flame's iOS16-compatible UniXNU Metal frontend,
metal2vulkan and Mesa Turnip, backed by a real A619 kernel driver. HakiOS is a
reference for A6xx hardware and display/presentation; its direct Metal path can
be a later measured alternative. Do not wholesale migrate to UEFI merely to
obtain GPU support. Reconsider that decision only for a demonstrated blocking
interface that cannot reasonably be solved in this baseline.

**Evidence baseline:** real iOS lock/home UI was user-confirmed and its log
records at least409.354seconds,57swaps/52presents/client2. Working kernel
7baffcae... and image d5235255... are preserved with full hashes below.
New0097 kernel cdca3c7f... has compiled and passed host tests but has NOT booted.
True touch is Novatek SPI, not the old Focaltech I2C probe. GPU is currently a
stub, display is CPU copied, and all-RAM/high-refresh/daily use are unverified.

**Dependency order:** P0 -> P2a -> P3a -> P3b -> P4. P1 runs alongside P2a;
GPU source/ABI/firmware audit starts during P0/P1. P2b and independent P5 work
can run alongside the GPU work. A usable runtime debug channel is desirable,
but USB completion must not indefinitely block GPU experiments: retain the
verified UFS log path. Basic temperature/power limits precede GPU stress;
complete sleep/resume follows working storage, GPU and display suspend paths.

| Phase | Work | Exit evidence required | Current state |
| --- | --- | --- | --- |
| P0 Reproducible baseline | Freeze rollback artifacts, complete source replay and compare, review build/CI changes, build clean, temporary-boot regression | All source differences explained; tracked inputs/toolchain; passing host checks; successful clean kernel build with run/log/hash; repeated UI with continuous logging for at least10minutes and no new panic/UFS faults; recovery still usable; distinguish lock screen from verified unlock/home | PASS for lock-screen baseline: native clean0099 with869.8s log and CI41989463747/0100 with719.65s log; manual recovery preserved; no verified unlock/input |
| P1 Input and observability | Correct Novatek SPI driver and HID delivery; keys; live logs/status and preferably file transfer through a runtime channel | Chip/FW identity verified, bounded SPI including67-byte frames, contact down/move/up and multitouch, correct coordinates/edge gestures, no stuck contacts or UI regressions in30minutes of exercised use; successful live diagnostic read, with UFS fallback retained | Native hardware/protocol audited; no working XNU touch driver yet |
| P2a Memory/DMA/storage correctness | Verified reserved regions, CPU/GPU DMA mappings, cache ownership, UFS bounds/errors/flush and journal behavior | Pattern/hash checks on owned buffers and bounded filesystem test files; synchronized restart retains data; error/timeout paths terminate; no out-of-partition or reserved-memory access | Existing UFS boots real root; recent bounds/cacheline fixes need broader qualification |
| P3a Real A619 GPU | Board-correct clocks/power/firmware/SMMU/GMU/CP; owned buffers, submission, completion and recovery | A command really executes on A619, fence completes, known pixels/hash read back correctly; repeated submissions and error recovery work; kernel/UI survives; basic temperature/frequency monitoring active before stress | Source/firmware/ABI research only |
| P3b Metal and iOS rendering | Port flame/UniXNU frontend and Turnip ABI; compile shaders on device; integrate IOSurface and system compositor | Standalone clear/triangle/texture/compute checks, cross-client buffer lifetime/fences, correct pixels, then backboardd/SpringBoard and representative stock/third-party apps demonstrably use GPU; failures are reported instead of fake success | Not implemented |
| P2b Full usable capacity | Describe all safe RAM banks; make intended userdata capacity available; improve storage throughput/recovery | XNU's real allocatable RAM reconciles with physical banks minus documented reservations; filesystem/block capacity and read/write addressing agree; pressure/reboot checks pass | Deferred behind GPU correctness, not forgotten; resizing/reformatting needs specific approval |
| P4 Presentation and high refresh | Correct native-panel60Hz presentation, then90/120Hz DPU/DSI/DSC modes and synchronization | Measure actual scan period independently from timer callbacks; report rendered/presented fps, p50/p95/p99 frame times, dropped/torn frames, temperature and power on fixed workloads; normal and warm sustained runs; touch survives modes and display resets | No real high-refresh implementation |
| P5 Daily phone functions | Wi-Fi/BT, RTC, audio/calls, media decode, camera, sensors/GNSS/haptics, battery/charging/thermal, modem/SIM/network/voice/SMS/data, sleep/resume, application/service compatibility | Separate per-function device tests, actual outputs and recovery; modem registration is separate from SIM detection and voice/IMS/data; charging verified with measurements; full-device sleep/wake restores storage/GPU/display/input/radio | Mostly absent/unverified; interface feasibility audit starts early |
| P6 Daily-use qualification | Integrated endurance and usability against an explicit capability matrix | Target24hours mixed operation,8hours screen-off idle, repeated cold/warm boots and at least50sleep/wake cycles, charging/network/call tests, data integrity, stable representative apps and repeatable high-refresh measurements; no unexplained failures | Not started |

P4 target is genuine high-refresh operation at native panel resolution, with
60fps as the initial performance gate and90/120Hz as subsequent targets.
A panel advertising120Hz or reduced-resolution short benchmark does not pass
120fps qualification. Sustained120fps, if not achieved, remains an open result;
do not silently rename a lower-frame-rate mode as meeting that target. Record
workload, resolution, governor, wallpaper configuration and test duration.
The endurance counts above are planned engineering gates, not completed tests
or a prediction that the hardware will meet them without further work.

**Important device-specific prerequisites:**

- A619 may require a below4GiB GPU virtual-address space; do not copy A640's
  high GPU-VA layout. This does not imply a4GiB physical-RAM limit. Verify
  XNU16KiB CPU pages -> SMMU4KiB mapping, >4GiB physical backing, cache aliases,
  IOSurface pin/unpin and process isolation before compositor integration.
- The actual Novatek unit matches NT36675_memory_map (event buffer0x22d00)
  despite NT36672C firmware naming. Use captured identity, not marketing name.
  SPI transfer67bytes exceeds the64-byte FIFO; preserve CS and drain final RX.
  Firmware downloads, when needed, target volatile SRAM via the native protocol.
- Live Tianma display configuration lists120/90/60/50/48/30Hz; preferred mode
  is60Hz. DSI porch/clock switching and shared touch/display reset need real
  implementation. Software vsync rate alone is not evidence.
- Baseband/IMS, camera/ISP, sleep and secure storage/platform services receive
  early feasibility reviews. Unsupported Apple services or missing security
  hardware stay explicit limitations; do not claim iPhone-equivalent security
  or daily completion by substituting stubs. Any accepted scope exception
  requires the user's decision, not an agent redefining success.

**First concrete implementation batch: P0 only.**

1. Preserve working artifacts and snapshot0097 source; inventory the pending
   changes without mixing the pre-existing tools/mkadt.py edit.
2. Compare fresh replay97 against the full authoritative0097 source tree after
   identical post-patch/SDK/watchdog staging, in both directions. Track modes
   and symlinks as well as content. List explicit generated-file exclusions.
   The old full-source-compare.json covers0091, NOT0097.
3. Review source pins and all build entry points. build-macos --xnu/--out does
   not isolate OBJROOT/SYMROOT/SDK/logs; use a separate checkout/build root or
   add an explicit isolated root while retaining current defaults.
4. Validate and commit only the finished reproducibility changes. Use gh for
   the clean GitHub Actions build; record commit, runID, exact inputs, logs and
   artifact hashes. Any CODEQL=1 dxb path fixups must be documented as such.
5. Boot that new artifact temporarily with the known UI parameters and disabled
   old touch probe, then collect matching logs and verify P0's device criteria.
   A failed regression returns to the preserved image; it does not overwrite it.

**Execution rules:** one hardware subsystem/change per controlled experiment;
relevant host checks plus device evidence; keep observation separate from
inference. At every milestone update this handoff with commit/run/image/log
identities and remaining work. Do not mark a stage complete from a screenshot,
API success, host test or stub alone. Keep dumps, serials, Apple files and
firmware outside git. Preserve bootloaders/recovery/modem/persist/backups;
confirm each destructive write before running it. No device is rebooted merely
to satisfy a wall-clock progress update.

**Pinned starting references from the completed review:**

- ios-flame745c4341: https://github.com/NWylynko/ios-flame/tree/745c4341af86089efb0df851fa8a27fb8face624
- HakiOS87bf4851: https://github.com/oosexgang/hakios-xnu-kernel/tree/87bf4851bcc9cbb24fd79997820aa3661abe4ea5
- UniXNU-sheng46017956: https://github.com/UniXNU/UniXNU-sheng/tree/460179565a018c741b93e0b1efa07c55d4de497a
- UniXNU-tb128fua9c3863d: https://github.com/xVanTuring/UniXNU-tb128fu/tree/a9c3863dedbee6f319bff16d3b609ec6cef409bf

### 2026-11-05 — implementation PAUSED by user; comparative architecture review

User explicitly paused device/driver work to compare the current port, UniXNU
and HakiOS against GPU acceleration, complete RAM/storage, high refresh and
daily phone operation. Goal status is paused. Phone remains in TWRP; do not
resume boots, firmware or implementation until the user resumes. Completed
stable-default/PON changes are committed as **e04033a**, UI milestone as570ba62.

Reproducibility work was stopped with uncommitted changes: explicit91-patch
series through0097, aggregate baseline, patch/SDK tools, build/CI scripts,
source-path test plumbing and two new tests. Fresh isolated replay97 and its
full host suite passed exit0. Complete source-byte comparison, clean kernel
build and CI execution were NOT completed. Keep this pending work distinct
from the successfully built main cache and known UI-producing kernel.

The user requested GitHub examples with actual reported hardware success.
Read-only review verified HakiOS redwood/A642L (87bf4851, current spelling
hakios-xnu-kernel), ios-flame/A640 (745c4341), ios-topaz/A610 (e4772911, branch
is topaz; main README is old), UniXNU-sheng/A740 (46017956) and community
UniXNU-tb128fu/A610 (a9c3863d). These have GPU source and author-reported device
results, but do not establish complete daily-phone functionality on gauguin.
Flame explicitly integrates UniXNU Metal frontend/bridge and Mesa into an
ios-sweet/ABL boot chain. Thus borrowing the graphics stack does not require
replacing the currently working gauguin boot chain with UEFI. Current local
UniXNU-gauguin BRINGUP retracts old arm_init claims; it lacks post-MMU/UI proof
and selected GPU/input/display drivers. No A619 complete hardware success was
verified in the reviewed sources. Recommendation will distinguish retaining
the current device baseline from reusing mature external driver components.

### 2026-11-05 — UI run recovered: >409 seconds, presentation active; real touch is Novatek SPI

User manually returned to TWRP after the successful UI run. Observer ended at
363seconds without recovery; its attempted pull failed and removed OUT as
intended. Fresh recovery pull saved as
`research/tmp/ui-touch-off-recovered-20261105.txt` (+.bin), banner13:38:21
matches known UI kernel. Ring total301640bytes/flush421/4151lines. It confirms
`SWEET TOUCH: mode 0, bring-up skipped`, no captured panic/shutdown entry,
PET400 at7859599836ticks (**409.354seconds**), framebuffer57swaps/52presents/
client2 near the end. Key/HID events were delivered while the user returned to
recovery. This is sustained rendering evidence alongside the user's lock/home
visual confirmation. Exact total runtime is not inferred beyond recorded ticks.

Real recovery input is **NVTCapacitiveTouchScreen**, event4; spi2.0 is bound to
PA0x880000. Current native dmesg identifies trim0c0000726603 and selects
`novatek_nt36672c_j17_fw01.bin`; download completes, FWversion16, PID5937.
Live DT SPI CS0/mode0/10MHz; RST21/IRQ22, swrst0x3f0fe/fast-read0x3f310.
The prior Focaltech/I2C variant assumption does not match this unit. Fixed
Lineage source includes the Novatek firmware as ihex; no firmware/device dump
is committed. Read-only interface inventory is
`research/tmp/ui-nvt-recovery-interfaces-20261105.txt`. Vendor recovery files
named novatek_ts_tianma_fw.bin etc are139264bytes; do not assume they equal the
actual built-in fw01 merely from panel name. Hardware/firmware audits ongoing.

Patches0096(PON/charger evidence) and0097(default touch probe off, blind GCC
scan removed) compile successfully with all hosttests, makeexit0, log
`research/tmp/ui-stable-default-build-20261105.log`. Saved new kernel
`research/k-ui-stable-default-20261105`, SHA256
`cdca3c7fd9127164082d7456b4a7fec9381964bae63047965ea1fbd669294298`.
This newer build has not yet booted; retain the proven7baffcae kernel/image.
Phone is now TWRP. Next work is correct Novatek SPI input, preserving the UI
baseline and not enabling the known-wrong experimental Focaltech path.

### 2026-11-05 — USER CONFIRMS iOS LOCK/HOME UI with touch probe skipped

**Milestone: user reports an iOS lock/home interface on the actual gauguin.**
At >160seconds after the touch-off boot, host still had no recovery; user then
answered "出现 iOS 界面" and clarified "锁屏或主屏幕". This is user visual
confirmation, not a captured screenshot. Physical touch functionality has NOT
been established: the unfinished hardware probe is disabled. Full-iOS goal
remains active; do not call complete or assume networking/audio/camera works.

Preserve the known UI-producing artifacts unchanged:
- kernel `research/k-ui-shutdown-entry-20261105`, SHA256
  `7baffcae773ba7f15549f1c02cc26cad48e7d67c34152a8530f1bb2fb55e3233`;
- image `shim/out/shim-ui-touch-off-20261105.img`, SHA256
  `d5235255e1d7b449497570469ec77c34690ae1e51e125ea0afed0d71eb5b2c8e`;
- ADT `research/tmp/ui-sampler-20261105.adt`, SHA256
  `7d6d93bea46bb80331d76238be295137ea33bbe8e3109789c68f4f0e45a291ff`;
- payload `research/tmp/ui-touch-off-20261105.bin`;
- send16688KB0.394s, boot0.135s, total0.534s;
- commandline (before shim's appended hardware fields):
  `debug=0x8 serial=3 cpus=8 keepsyms=1 -noprogress rd=ufsroot0 unentitled_ios_sim_launch=1 ignition_level=1 ufsrw=1 rootrw=1 launchd_unsecure_cache=1 sweetlog=1 sweetlogms=500 sweetfb_noconsole=1 sweetufsquiet=1 sweetsample=SpringBoard,backboardd,iconservicesagent,cfprefsd sweetsampledelay=20 sweetsampleinterval=10 sweetsamplecount=16 sweetwdtpet=1 sweettzsample=1 sweettouchmode=0`.

Commits7c09029(UFS/TZ),7ea5cb9(normal reboot entry) underpin this build. The
360second observer is still pending; it cannot read the ring while iOS owns
USB. User was told to keep running. Later recovery/log pull must preserve this
run separately and compare banner. No automatic forced reboot is performed.

Next code prepared:0096 fixes PON evidence and reads charger WD config only;
0097 makes gauguin's unfinished touch probe opt-in and deletes the proven bad
GCC blind walk. These are not yet in the UI-producing kernel. Touch audit also
found incorrect clock offsets/vote bits, invalid stageG GPIO offsets, unset
st.se/st.gpio, incorrect timer units and Focaltech protocol. Do not simply turn
probe back on after removing the walk; restore touch against native sources
in a separately validated change. User-visible UI is an intermediate milestone.

### 2026-11-05 — captured touch GCC data abort; no-touch control running

Patch0095 native build passed, kernel `research/k-ui-shutdown-entry-20261105`,
SHA256 `7baffcae773ba7f15549f1c02cc26cad48e7d67c34152a8530f1bb2fb55e3233`.
The extracted-function shutdown test passes eight scenarios, including IRQ
restore, recursive/duplicate entry, missing proc/thread, bounded nonterminated
name and opt-in normal reboot. Controlled image
`shim/out/shim-ui-shutdown-control-20261105.img`, SHA256
`b59c06c3d4c41137c5e7e19458b65071a1395a3053ffa5a50fbcb2d29007d5a6`,
send16688KB0.392s/boot0.134s/total0.533s, returned to TWRP101s. User confirmed.
Log `research/tmp/ui-shutdown-control-boot-20261105.txt` **validates both new
records**: reboot_kernel howto0 at1037688627ticks, platform type1 at1105066911.
Launchd receives SIGTERM and completes shutdown through MACH Reboot; kernel
periodic threads continue afterwards. There is no implemented platform reset
hook found, so a completed software reboot is not established by this test.

**New decisive observation in this control:** the independent touch bring-up
thread (default45second delay after root init) starts late, scans GCC pages,
and raises Kernel data abort. PC0xfffffe00074ef6d8 is actual kernel
_touch_bringup+0xc8, `ldr w9,[x8]`; LR74ef700 is the loop's printf return.
Last completed page0x9000, fault x8=0xfffffe4017d56000, mapping
VA0xfffffe4017d4c000: next page0xa000, PA **0x0010a000**. It is within the
mapped0x60000 span; enlarging the mapping is not a fix. The probe blindly
reads unsupported hardware registers. Natural runs had the same45s probe
queued but did not preserve its tail, so common causality awaits a control.

Current temporary no-touch image `shim/out/shim-ui-touch-off-20261105.img`,
SHA256 `d5235255e1d7b449497570469ec77c34690ae1e51e125ea0afed0d71eb5b2c8e`,
uses identical0095kernel+ADT, normal8CPU boot, no deliberate reboot timer,
`sweettouchmode=0` and16process samples to cover longer operation. Observer
360seconds: `research/tmp/ui-touch-off-cycle-20261105.log`, pending log
`research/tmp/ui-touch-off-boot-20261105.txt`. Do not interpret absence of adb
as continued kernel execution without later device/log confirmation.

### 2026-11-05 — correcting reset-evidence assumptions; normal shutdown trace

Completed UFS/live diagnostic work is committed as **7c09029**. Subsequent
read-only recovery evidence is in `research/tmp/ui-onecpu-recovery-dmesg-20261105.txt`.
Immediately after this XNU-to-recovery cycle, the native driver reports SID0
PM6350 PON at0x800, power-off from **PS_HOLD (MSM controlled shutdown)**;
SID2 PM7250b and SID4 PM6150l report SOFT. This names the PMIC input, not the
software/firmware caller; it does not establish a userland reboot.

Fresh actual recovery FDT saved as `research/tmp/ui-recovery-live-20261105.dtb`
(588757bytes), decompiled alongside it. Root is Qualcomm Gauguin/lagoon-qrd.
Current XNU PON code wrongly reads SID6 PMK8350 at0x1300; its zero values are
not evidence about the active primary PMIC. The old unpacked mainline-style
DTS also contains the correct SID0 pon@800 plus an unrelated SID6 pon@1300;
the earlier claim that PM6350 had no PON node is false. Actual SPMI controller
base0xc440000 already matches the port: the logged0x50010000 is its **version**,
not its address. Raw DT and recovery state remain ignored and must not enter git.

Patch0095 adds first-entry persistent records before reboot_kernel waits/locks
and before platform halt/restart notifications. This closes a real diagnostic
gap: old output only appeared late, and ARM64 has no observed registered
PE_halt_restart implementation, so normal shutdown can stall without a panic.
This is a source-level possibility, not a captured cause. Optional control uses
`sweetreboot=15 sweetrebootnormal=1` for normal sync reboot; default timer still
panics. Build log `research/tmp/ui-shutdown-entry-build-20261105.log`, pending.

### 2026-11-05 — UFS fix hardware result and single-core control

Patches0093/0094 were compiled together and booted successfully. Native build
`research/tmp/ui-ufs-isolation-build-20261105.log` exited0 with all host tests
passing. Kernel `research/k-ui-ufs-isolated-20261105`, SHA256
`888970aec301f3762e5d4ec18dda6a3d8c0208cfcd7ffd0373260520695d0c57`.
Eight-core image `shim/out/shim-ui-ufs-isolated-20261105.img`, SHA256
`7053c4a212fb793f01cea748cf950465ab09b8f6809092979eff9dd044625f81`.
Cycle `research/tmp/ui-ufs-isolated-cycle-20261105.log`: send16688KB0.395s,
boot0.135s, total0.538s, automatic recovery **101s**. Log
`research/tmp/ui-ufs-isolated-boot-20261105.txt` contains1955lines and no UFS
OCS/timeout/write failures. TZ SRAM14696000/3000 maps successfully, empty ring
through70samples. HYP801fc000/2000 has S2faults0 and unchanged ring. No first
panic record. These observations do not identify the reset source.

The identical kernel and ADT were then booted with only cpus8 changed to cpus1.
Image `shim/out/shim-ui-onecpu-20261105.img`, SHA256
`148fd58684fe970d7eda0c9c9646d236c3742b6533d3254df274e3c7e566a553`.
Cycle `research/tmp/ui-onecpu-cycle-20261105.log`: send16688KB0.397s,
boot0.134s, total0.538s, recovery again **101s**. Log
`research/tmp/ui-onecpu-boot-20261105.txt` confirms requested1/selected1 and
1/1 initialized, contains1586lines, reaches launchd/SpringBoard/backboardd.
User reports return to TWRP. UI remains unavailable; panel has no connected
client. Single-core runtime did not change the observed reset time. No panic
record or UFS completion error was captured; best-effort final flush can still
miss events. Normal reboot/powerdown entry points are now being audited.

No new GitHub Actions build was dispatched. All images were temporary fastboot
boots. No partition restoration or repartitioning was performed. Previous
notes below describe earlier stages; the two tests above supersede their
pending hardware/build statements.

### 2026-11-05 — panic capture validated; live firmware logs and UFS descriptor fix

Commits **355f099** (early FB) and **0e9ceeb** (panic entry and safe polled-I/O
logging) are complete. The first controlled panic was recovered after the user
manually returned to TWRP. `ui-panic-control-recovered-20261105.txt` contains
66727 bytes, flush1, matching the new banner, and the exact first panic
`SWEET: debug reboot timer (15 s)` plus debug8/hold0/caller. This validates the
capture path, although its initial version caused a second console panic while
flushing with IRQs disabled. User photo `/Users/baai/Downloads/IMG_1109.HEIC`
shows `Console I/O from interrupt-disabled context @serial_console.c:168`.
Patch0092 routes all eight reachable UFS flush diagnostics directly to the
lock-free ring in IRQ-off context. Tests verify routing, format safety, bounds
and the actual callsites. The photo and conversions stay outside git.

The subsequent normal image `shim-ui-earlyfb-safe-20261105.img` still returned
to recovery at **100s** according to its cycle transcript, with no first-panic
record. An interim chat update based on message timing incorrectly suggested
longer runtime; use the cycle timer. Kernel
`research/k-earlyfb-panic-safe-20261105`, SHA256
`5b69056333004a64c8bab7fa9535a09bfcc602b23d10533e50accf3b043587ee`.
Image SHA256 `ede7a3f9a87d6d1dffb4592e103f20c8a96e698b934bc00002dd6d7bac7a96a7`.
Raw log `research/tmp/ui-earlyfb-safe-boot-20261105.txt`. A busy panic flush
trylock can still lose the last record, so this remains qualified evidence.

Optional live secure diagnostics are prepared in patch0093. First hardware run
`shim-ui-tz-20261105.img` returned101s. HYP buffer at0x801fc000/0x2000 was valid,
with S2faultcounter0 and unchanged log tail over seven10s samples. TZ pointer
was0x14696000/0x3000, rejected by the initial DRAM-only guard. Native tz_log
exposes TZ9.1 from the same firmware-published pointer interface. The revised
guard adds exactly this SRAM extent; direct recovery /dev/mem read yielded no
bytes. Revised code polls1s, prints status on change/every10, tail on change,
and caps300rounds. tests/test_secure_diag.py extracts real code and tests bounds,
SRAMwhitelist, headers, positions, quiet logging and scheduling. No SRAM-inclusive
hardware run yet. `ui-tz-boot-20261105.txt` is the initial DRAM-only run.

**Current build includes a concrete UFS fix, patch0094.** 32-byte UTRDs for
MAIN0/LOG1 share one64-byte cacheline. XNU's actual MMU_CLINE=6 maintenance
cleans wholelines, allowing stale OCS0xf to overwrite an adjacent DMA completion.
New slots0/2/4 occupy separate lines; CAP must expose at least5 before takeover
writes. UPIU tasktags equal their hardware slots, matching pinned native gauguin
ufshcd.c; the rotating shared counter was incorrect. The old layout corruption
is demonstrated by a host negative control. tests/test_ufs_descriptors.py checks
the actual preparation/takeover, all six slot pairs, CAP bounds and tag reuse.
Marker tests now derive the actual slot macro. Saved driver baseline
`research/tmp/ufs-descriptors-before-20261105.c`. Hardware causality is pending.
Build in progress `research/tmp/ui-ufs-isolation-build-20261105.log`.

Reproducibility audit also found a viable isolated replay: 0001–0082 (0026 needs
hunk count correction), then complete cached legacy delta, then0090 onward.
Candidate `research/tmp/patch-repro-audit-20261105/candidate-pre0090.patch`
reproduces5215tracked sources plus3required files when staged with the existing
SDK inputs. Current0083/0084/0086 are overlapping cumulative patches, not an
incremental sequence. Adoption still needs path fixes in sync-watchdog/tests
and a clean build; no active series files have been replaced by that audit.

### 2026-11-05 — active full-iOS goal, correcting early framebuffer and panic capture

The active user objective is complete iOS operation on Redmi Note9 Pro5G
gauguin. GUI bring-up is an intermediate milestone. The previous continuation
made progress through verified writes/SMC/reset evidence; no completion claim
has been made. The goal remains active.

Re-auditing the authoritative binary and source found two concrete defects.

1. `start.s` has two early framebuffer constants, `arm_vm_init.c` installs its
   alias, and `sweet_early.c` initializes its pointer at sweet PA0x9c000000.
   Gauguin splash is PA0xa0000000. Actual old kernel disassembly confirms its
   stage stripe writes0x9c9c1800. Patch0090 selects0xa0000000 for GAUGUIN and
   retains0x9c000000 otherwise. New disassembly writes0xa09c1800. Pixel range
   [0xa0000000,0xa09e3400), map range[0xa0000000,0xa2000000) fit the actual
   reserved splash[0xa0000000,0xa2300000). The incorrect old range overlaps no
   named fixed reserved region in saved stock DTB; its dynamic use is unknown.
2. `panic_trap_to_debugger` never called `sweet_log_flush_panic`. The existing
   early panic display is disabled after serial initialization. Moreover,
   current boot logs still report gPanicBase uninitialized, contrary to an older
   note claiming the size property alone fixed it. `SavePanicInfo` waits forever
   with missing panic info. Thus the absence of persistent panic records and
   prior debug=0xc result do not exclude XNU panic.

Patch0091 writes a bounded first-panic record directly to the console ring
before machine panic/rendezvous, then best-effort flushes with IRQs disabled.
It logs caller/reason/options/debug/hold and formats a va_copy of the original
arguments. Atomic recursion guard and bounded511-byte body protect this path.
`tests/test_panic_record.py` passes six cases (bounds,varargs,IRQ restore,
missing callbacks,nested entry). Normal panic handling still follows the hook.

Native build of both changes passed, makeexit0, all existing hosttests passed,
log `research/tmp/ui-earlyfb-panic-build-20261105.log`. Kernel saved as
`research/k-earlyfb-panic-20261105`, SHA256
`0bad4c547b102e912d2763c0e3a7a41eed1ff2a4a7f05e1910bfb1d12172fe48`.
Original files are under `research/tmp/earlyfb-before-20261105/` and
`research/tmp/panic-entry-before-20261105/`.

**Controlled validation running**: temporary image
`shim/out/shim-ui-panic-control-20261105.img`, SHA256
`b43d5bb2eade239b07047c520e45ef46a8508a66cc5bd5a8e5dbd577b9fff556`, uses
`sweetreboot=15` to deliberately panic after root-device initialization. Same
highmem ADT, cpus8 and sweetwdtpet1. Send16668KB OKAY0.391s, bootOKAY0.135s.
Pending log `research/tmp/ui-panic-control-boot-20261105.txt`, cycle transcript
`research/tmp/ui-panic-control-cycle-20261105.log`. Confirm the known deliberate
panic text persists before interpreting a later natural-failure boot.

Additional read-only work found TZ/HYP diagnostics can be sampled before reset.
Exact reference `tz_log.c` is under `research/tmp/gauguin-scm-reference/`.
Recovery HYP header was read and saved as `ui-tz-hyp-general-20261105.txt`,
magic6879706d, CPUs8, S2fault0. An optional bounded live sampler is under review.
The IMEM restart_reason mailbox is overwritten by the intervening recovery-to-
bootloader reboot; previous swrst values cannot name the original XNU reset.

### 2026-11-05 — sixth boot closes the APSS enable-state lead

Commit `be2588b` adds full `wdtpre` / `wdtpost` values to the shim log. The final
controlled boot used these records,
using the fifth boot's kernel, ADT, sampling args and opt-in reset-only pet.
Both values are **00000000**. Thus APSS EN was already zero before the shim's
secure-watchdog attempt, and clearing it did not change that boot's state.
The proposed preserve-EN experiment has no demonstrated difference to test on
this setup. PET again reaches count70 with EN=0/STS=0.

Image `shim/out/shim-ui-wdtstate-20261105.img`, SHA256
`69a1fa63bf909a7d99c5d6b0eb7f9c5609fe66d6f4b3f452ff3e17ba7914f124`.
Send16668KB OKAY0.393s, bootOKAY0.134s, total0.532s, back in TWRP100s.
Log `research/tmp/ui-wdtstate-boot-20261105.txt`, transcript
`research/tmp/ui-wdtstate-cycle-20261105.log`. The full shim announcements and
boot args total499 bytes, within608. Shim rebuild/ramdisk byte comparison and
SCM host tests passed.

**End-of-session state**: phone in recovery, six automatic returns at roughly
100–101 seconds, no usable interface verified. Native Linux and the shim both
reject the secure-watchdog disable operation with the same x0=-2/x1=-4.
Reset-only APSS petting and the panic-debug boot did not extend the observed
runtime. The reset source remains unidentified; these results do not prove a
secure watchdog is responsible. Better previous-boot firmware/reset evidence is
needed before selecting another hardware control change. Recovery's current
TZ/pstore interfaces did not preserve a usable prior cause. Disk first-block
restoration, if needed, requires separate user approval and a verified baseline.

### 2026-11-05 — five controlled boots, UI still unavailable, automatic reset unresolved

**Current device state is TWRP/recovery. No usable UI has been verified.** Five
temporary boots reached launchd, SpringBoard and backboardd, then automatically
returned to recovery after 100, 101, 100, 101 and 101 seconds respectively.
The user confirmed automatic restart. The latter tests omit the diagnostic
reboot timer. Changing user stacks demonstrate initialization progress; the
historical check-in wait cannot describe the current failure by itself.

Fifth experiment `sweetwdtpet=1` is committed as **`9ff59ba`**, patch0089. Its
independent callout writes only APSS WDT0_RST=1 each second. EN and thresholds
come from the existing setup. It uses clock_interval_to_deadline, logs counts,
timestamps, EN and STS, and preserves the old status sampler's cadence. An
extracted-function host simulation checked default-off behavior, 20 callbacks,
one-second deadlines, RESET-only writes, continued scheduling and log frequency
(`research/tmp/ui-wdtpet-simulation.cpp`). The final code uses DMB OSHST for
store ordering. Kernel rebuild and all host tests passed, make exit0, log
`research/tmp/ui-wdtpet-build-20261105.log`.

Kernel `research/k-ui-wdtpet-20261105`, SHA256
`e0e2d3863df11eac0328c79fc462649c5d19980b521a195033f3087184eb707c`.
Image `shim/out/shim-ui-wdtpet-20261105.img`, SHA256
`f8c6a40a65d63c794c0dc536c7cff53626810d6e772141c55586b1dce7963a22`.
Send16668KB OKAY0.390s, bootOKAY0.134s, total0.531s, recovery101s.
Log `research/tmp/ui-wdtpet-boot-20261105.txt`, ring119656 bytes, flush75,
420 execs. PET counts1..5,10,20,...70 show ~1.001 seconds per callback,
always EN=0/STS=0; the last count70 is at absolute ticks1516753604. This proves
the pet callback runs, but it did not extend the boot. It does not establish
whether the secure watchdog is serviced by this RESET register when EN=0.

**Native Linux control test confirms the same firmware rejection.** Recovery
has `/sys/devices/platform/soc/17c10000.qcom,wdt/disable`, initially0. Writing1
through the driver's normal interface returned I/O error and left it0. Recovery
dmesg records `func id 0x42000107, ret: -2, syscall returns:
0xfffffffffffffffc,0x0,0x0` and `Failed to deactivate secure wdog`. Saved in
`research/tmp/ui-recovery-wdt-disable-20261105.txt`. Thus the current SCM shim
matches the native driver's failed operation; arbitrary alternative argument
values are not justified. This still does not identify the reset initiator.

Recovery CONFIG_DEBUG_FS and CONFIG_MSM_TZ_LOG are enabled. Mounting the
debugfs virtual filesystem exposed `/sys/kernel/debug/tzdbg`. Bounded reads
saved `research/tmp/ui-tz-{reset,general,boot,log,hyp_log}-20261105.txt`.
Reset counters are allzero, TZ log returned no bytes, hyp log is current boot
initialization. `/sys/fs/pstore` is empty, `/proc/last_kmsg` absent. These do
not recover the previous XNU reset cause. debugfs was a temporary recovery mount.

Commits this continuation are `d02486d` (out-of-partition marker write fix),
`ed913c9` (intermediate hardware handoff), `fcb4840` (SCM ABI/results), and
`9ff59ba` (opt-in RESET probe). No new CI run was launched. Clean patch-series
reproduction remains blocked by the older 0084/0086 duplicate/corrupt patches,
as documented below. `tools/mkadt.py` has the pre-existing uncommitted edit.

**Next work requires better reset-source evidence.** One concrete source-level
lead is error handling: native Linux aborts watchdog disable if the secure call
fails, while the shim still clears APSS EN. A controlled test would first need
full EN values at shim entry/exit and preservation of the existing timer setup,
with a verified pet path; `swwd` high-nibble packing cannot supply this evidence.
Alternatively capture previous-boot secure/reset diagnostics before recovery
clears them. Do not present an unproven watchdog hypothesis as the root cause.
Keep the first-block backups and obtain approval before any disk restoration.

### 2026-11-05 — SCM call verified, firmware rejected secure-watchdog disable

SCM fix committed as `fcb4840`. Shim detects 64/32-bit SCM ABI, queries BOOT
service1/SEC_WDOG_DIS command7, and logs transport/service results. PSCI has its
own helper. New mocked-monitor regression test extracts the actual shim control
flow and covers register arguments, ABI fallbacks, unsupported calls, bounded
busy/interrupted retries and the observed failure response. All host tests pass
(`research/tmp/ui-final-host-tests-20261105.log`).

Fourth boot used unchanged UI-icons kernel/payload/ADT with the corrected shim,
image `shim/out/shim-ui-scm-20261105.img`, SHA256
`2f01a43bea3a2c1519d6dd8b2c63bfedccd9c4968b8b084c845ceab133508f68`.
Send 16668 KB OKAY 0.388 s, boot OKAY 0.134 s, total0.529 s. Recovery after101 s.
Log `research/tmp/ui-scm-boot-20261105.txt` proves

```
scmstep=00000003 scmabi=00000040 scmrc=fffffffe scmret=fffffffc
```

The 64-bit ABI and availability checks passed; disable itself returned x0=-2
(SCM_EINVAL_ARG in the reference driver), x1=-4 (meaning undocumented in the
retrieved source). This **did not disable the secure watchdog**. The repeated
reset still has no established cause. Do not try arbitrary SCM argument values.

Next bounded experiment under preparation is an opt-in `sweetwdtpet=1` which
periodically writes only APSS WDT0_RST=1 using the exact Linux pet operation,
with actual timestamps/EN/status in the log. EN and timeout register values are
retained for this comparison. Source does not prove that this operation pets a
secure watchdog while EN=0, so an unchanged reset time would not exclude it.
References are pinned in shim source to gauguin commit
`19b63c8192b1c9b7c4d931d7d3be92024bc2d778`.

### 2026-11-05 — three boots reset around 100 s while UI initialization progresses

User confirmed the first return to TWRP was automatic. The second image,
`shim-ui-icons-20261105.img`, omitted `sweetreboot` and returned after 101 s.
Log `research/tmp/ui-icons-boot-20261105.txt` has three SMP rounds. SpringBoard
main changes from allocation to MobileGestalt/ISDefaults initialization to a
synchronous CFPreferences write. This does not show a fixed IconServices hang.
Symbols `research/tmp/ui-icons-sb-symbols-20261105.txt`.

Third controlled image changes debug=0x8 to debug=0xc, enabling ARM64 DB_NMI
panic debugging per `osfmk/kern/debug.c:panic_init`. It also has no sweetreboot.
`shim/out/shim-ui-panic-hold-20261105.img`, SHA256
`348775d4b7ee54d0b2f6fcc6a9c158fb1bbdc3697659882c9c8ca9729c549481`, returned to
TWRP after 100 s. Log `research/tmp/ui-panic-hold-boot-20261105.txt` again has
no panic/MACH Reboot/platform-restart line. APSS WDT sample around 52 s reports
en=0. Panic-debugging activation itself has no runtime confirmation yet, so
these observations narrow the reset investigation without proving a source.

Recovery dmesg after boot two is saved in
`research/tmp/ui-recovery-dmesg-20261105.txt`. PM6350 SID0 reports PS_HOLD/MSM
controlled shutdown; PM7250B SID2 and PM6150L SID4 report SOFT. This identifies
the PMIC reset category, not its initiating caller. Existing SweetWatchdog
PON diagnostics use SID6/base0x1300, incompatible with the observed PMIC map.
Existing shim `swwd` also stores only register top nibbles, so en=1 and en=0
both appear as zero there.

Next candidate is the secure-watchdog SCM call. Current shim calls
`smc(0x0200000c,0,0,0)` and ignores the result. Exact gauguin Linux reference
`LineageOS/android_kernel_xiaomi_gauguin` lineage-23.2 watchdog_v2/scm sources
use BOOT service1, command7, arginfo1, arg0=1 with SCM ABI detection. References
downloaded under `research/tmp/gauguin-scm-reference/`. A candidate with ABI
probe, availability check and persisted return status is being prepared for
review. No changed SCM command has been booted yet.

PosterBoard's earlier trap is independently symbolicated to
`PBFPosterExtensionDataStore _stateLock_setupSwitcherConfigurationForFirstTime`,
assertion `!_stateLock_switcherConfiguration` at source line3431. It is a first
setup call on an already-present configuration object. Its contribution to the
missing interface remains unproven.

### 2026-11-05 — current stacks pass shell check-in, investigating IconServices

First fresh boot completed, returning to TWRP after 100 seconds, with the new
kernel banner verified. Log `research/tmp/ui-sample-safe-boot-20261105.txt`
contains two full sampler rounds, rather than the planned six. The log records
`sweetreboot=160` but ends without a panic/restart reason. User was asked whether
the recovery transition was automatic or by keys; answer still pending.

Current SpringBoard has progressed beyond the historical `_checkIn` wait.
Sample 0 is in `BKSDisplayGetMainScreenInfo`, initializing the system shell.
Sample 1 is in `ISIconManager _init`, sending a synchronous NSXPC request while
`SBHGetApplicationIconImage` initializes icons. `exec iconservicesagent` occurs
immediately before sample 1, so this single wait can be normal startup. It is
not yet evidence of a persistent IconServices deadlock. Symbolicated SB stacks
are in `research/tmp/ui-sb-symbols-20261105.txt`.

backboardd main progresses from a `CAWindowServerDisplay.uniqueId` mutex wait
to the CFRunLoop. Its dispatch-group waiter at executable offset 0x18a78 is
`BKButtonHapticsController._controllerReadyGroup`, verified by ObjC metadata
and `_configureAsyncWithBlock:` disassembly. That waiter does not establish a
DataMigration dependency. The log does execute `com.apple.datamigrator` at line
817, which has no later SMP snapshot. PowerLog permission requests account for
the matching background waits in SB, backboardd and runningboardd. Details in
`research/tmp/ui-bbd-symbols-20261105.txt`. PosterBoard also has a SIGTRAP at
line 1636, under investigation.

Marker fix verified on hardware after this boot. First 8192 disk bytes exactly
match the pre-boot backup, and 31 `MARK` blocks occur in the reserved userdata
region starting at relative block 28055482. Evidence files are
`research/tmp/ui-sda-head-after-20261105.bin` and `ui-marks-after-20261105.bin`.

Second temporary boot is running with the same corrected kernel and ADT.
Image `shim/out/shim-ui-icons-20261105.img`, SHA256
`82ec6069f22360e971cf3295e1af650ea1611192762b19893e3cf441bf66badd`.
Samples `SpringBoard,iconservicesagent,cfprefsd,PosterBoard,backboardd`, delay
20 seconds, interval 10 seconds, 8 rounds. The diagnostic `sweetreboot` argument
is omitted for this run. Output `research/tmp/ui-icons-boot-20261105.txt` and
cycle transcript `research/tmp/ui-icons-cycle-20261105.log`. Verify the sampled
names as well as the banner, since both images use the same kernel.

### 2026-11-05 — marker write bug fixed, first fresh sampling boot

User reconnected the gauguin in recovery. A pre-boot audit found that the local
`sweet_log_mark_flush()` calculated a destination `base` but issued a WRITE(10)
CDB with LBA zero for every marker. `ufs_scsi_slot()` copies that address into
the command directly on `su.lun`. The actual previous boot log selects LUN 0,
userdata first block `0x2c1000`, length 28056571 blocks.

Read-only device evidence is saved in ignored
`research/tmp/ui-sda-head-20261105.bin` (first 8192 bytes of `/dev/block/sda`).
LBA 0 really begins with `MARK `. The protective MBR signature is 55aa, partition
type ee, and the LBA 1 GPT signature and header CRC are valid. Existing disk
contents still require care; any restoration must follow the user approval rule.

**Fix committed as `d02486d`**, patch 0088. Marker writes encode `base + i` and
reject invalid/overflowing/out-of-partition ranges before issuing SCSI. A failed
write retains its dirty bit, and an update published during an in-flight write
stays pending. `tests/test_mark_writes.py` compiles the actual extracted C
function with a fake SCSI target. All 64 destinations, invalid ranges, failed
write/retry and concurrent publication pass. The same harness fails against the
saved original at the LBA-zero assertion. Original source saved under
`research/tmp/ui-marks-before-20261105/`.

Native rebuild passed (make exit 0), including all host tests. Log
`research/tmp/ui-sampler-marks-build-20261105.log`. Kernel saved as
`research/k-ui-sample-marks-20261105`, banner 22.6.0, Nov 5 11:47:15 CST 2026,
SHA256 `55ffc6c850024c4ad475d6767919ec9edfee8ba175a331a984b624b3bc04415c`.
**Use `shim/out/shim-ui-sample-safe-20261105.img`** (17068032 bytes), SHA256
`52949301538bbbb7102974d39823fd446e22fda0ba516d36bf82df591092c946`.
The earlier `shim-ui-sample-20261105.img` still contains the defective marker
writer. Payload is `research/tmp/ui-sample-safe-20261105.bin`, byte-verified
against the packaged ramdisk. ADT and 8-CPU setup match the preceding experiment.

Sampling uses exact process names, including `com.apple.datamigrator` (the
earlier bare `datamigrator` token does not match `proc_name`). Additional name
`com.apple.migrationpluginwrapper`; delay 20 s, interval 20 s, 6 rounds,
`sweetreboot=160`. The device was temporarily booted through
`tools/sweet-observe.sh` with a 260-second recovery observation limit. Send
16668 KB OKAY (0.390 s), boot OKAY (0.134 s), total 0.532 s. Pending fresh log
`research/tmp/ui-sample-safe-boot-20261105.txt`; cycle transcript same prefix
with `cycle` instead of `boot` and `.log` extension.

Timing corrections from source and old logs must guide interpretation.
`SweetWatchdog.cpp` adds 1000000000 raw absolute ticks, giving about 52.08 s at
19.2 MHz, although its comment says one second. PW `t=20` is iteration 20 of a
two-second sleep loop. `observe-tap9.txt` actually contains HB 1/2/3 and PW
15/30/45/60/75. In `ui-current`, the first 3600 vsyncs span about 63.43 s, and
the old 90-second sampler is due after about 111 s. Display power-off suppresses
vsync log output while rescheduling the timer. Missing later vsync/HB/SMP lines
therefore cannot establish that timers stopped. `sweet_callout_runs` counts
processor running timers, rather than general thread-call callbacks.

Firmware confirms backboardd exposes `com.apple.backboard.system-app-server`
and BackBoardServices contains `checkInAndWaitForDataMigration:completionBlock:`.
DataMigration reads `LastSystemVersion` in `com.apple.migration` under
CurrentUser/CurrentHost, after synchronizing preferences. Fresh stacks should
also consider cfprefsd if the migration process waits there.

### 2026-11-05 — userspace stack audit, diagnostic image ready, phone offline

Read the actual saved stacks before using the older claims that SpringBoard is
idle or that userspace PCs cannot be obtained. `research/tmp/observe-tap2.txt`
(kernel banner 2026-11-03 22:02:34) and `observe-tap9.txt` both contain `SMP`
records. After subtracting each boot's shared-cache slide, their SpringBoard
main-thread stacks match. Symbolication against the local iOS 16.7.16 cache gives

```
SBSystemAppMain
  FBSystemShellInitialize
    -[BKSSystemShellService _checkIn]
      BSXPCServiceConnectionMessage sendSynchronouslyWithError:
        xpc_connection_send_message_with_reply_sync
          _dispatch_mach_send_and_wait_for_reply
            mach_msg2_trap
```

This is a synchronous registration waiting for a reply. Receiving on a port
owned by SpringBoard cannot exclude an outstanding request to another process.
In the same historical sample, backboardd is waiting in `DMPerformMigration`
through `DMConnection migrateCheckingNecessity:...`; another thread is waiting
in `RBSConnection handleForPredicate:error:`. These samples predate the Nov 4
root tweaks. They identify a concrete dependency chain, but **do not establish
the current blocker after those tweaks**. Raw and symbolicated results are in
`research/tmp/ui-historical-symbols-20261105.txt` (ignored).

Two diagnostic defects were found in the local cached `osfmk/kern/task.c`.
The new user-PC probe passes count 34 to `machine_thread_get_state`, while
`ARM_THREAD_STATE64_COUNT` is measured in uint32_t units (68). The port probe
subtracts `offsetof(ipc_port, ip_messages)` from a waitq pointer, although that
pointer is `ip_waitq` and XNU supplies `ip_from_waitq()`. Its `msgs=0/0`, active
and sequence values cannot establish the queue state. The existing process
sampler already uses `find_user_regs()` from `osfmk/arm/thread.h` successfully.

Current read-only device pull is `research/tmp/ui-current-20261105.txt` and
`.bin`, 125835 bytes of console, flush #79, kernel banner 2026-11-05 00:32:43.
The phone is gauguin in recovery. This log has 3 presents, 2 clients, and an
OCS 0xf error for SCSI 0x35. A separate latest log, `r12.txt`, has an OCS 0xf
read error (0x28) followed by launchd exit and `initproc failed to start`.

Installed the official `ipsw` v3.1.741 binary only under ignored
`research/tools/ipsw-3.1.741/`; archive SHA256 verified against the release
checksums (`546af036b81c957ac7ddc71098ef65d2a8efebb70c81cce65bac4b9499091e8a`).
Cache input is `/private/tmp/m-86593/System/Library/Caches/com.apple.dyld/`.
Use `--cache research/tmp/ios16.a2s` with `dyld a2s` and subtract the logged
slide, or pass `--slide`. Public/private symbols parsed. ObjC metadata parsing
reported an EOF, so inspect function ranges when a method is unresolved.

**Committed sampler change `fd9bcd3`**, patch
`0087-sweet-configurable-process-sampler.patch`, adds configurable sampling
delay/interval/count with the prior defaults. It snapshots referenced threads,
releases the task lock before reading user memory, obtains registers through
`thread_getstatus(... ARM_THREAD_STATE64_COUNT ...)`, and splits long backtraces
into console-sized lines. Running-thread stacks are best-effort after the
register snapshot. The old `sweetdump` probe is omitted from the test boot args.

Native incremental build **passed, make exit 0**, all existing host tests
passed. Log `research/tmp/ui-sampler-build-20261105.log`. Built kernel banner
`Darwin Kernel Version 22.6.0: Thu Nov 5 11:33:59 CST 2026`, SHA256
`0b4736225113bfd18b3fd332926ba82785c5d291f62c8f0db9fec0a0d218a853`.
Build used the existing cached source tree, which has many prior local changes
absent from CI. Patch 0087 applies cleanly to the saved pre-change copies in
`research/tmp/ui-sampler-before-20261105/` and reproduces both compiled sources
byte-for-byte. A replay of the older tracked series exposed a pre-existing
corrupt hunk in 0086 at line 2709; `--recount` also hits changes duplicated from
0084. A clean series build is still unverified. `PATCH_SET` stays at 0082-2 to
retain the current source tree. Do not regenerate that tree during diagnosis.
`gh run list` shows latest CI run **39957353555** failed at commit `3a2f529`;
no CI build launched in this session.

**Prepared image** `shim/out/shim-ui-sample-20261105.img`, 17068032 bytes,
SHA256 `799a42d1eed9c7c16b53048bb337cb865f06b9ff03f7ad1e1d1fe93072a12342`.
Payload `research/tmp/ui-sampler-20261105.bin`; ADT same basename with `.adt`.
The shim packer unpacked and byte-compared its ramdisk with the payload.
ADT extracted from the latest `shim-safe.img`/`shim-r12.img` to hold that
configuration fixed, with base `0x180000000`, size `0xfff00000`, SHA256
`7d6d93bea46bb80331d76238be295137ea33bbe8e3109789c68f4f0e45a291ff`.
It includes the earlier uncommitted `/chosen` additions from `tools/mkadt.py`.
The test keeps cpus=8 and the previous root boot args, plus

```
sweetsample=SpringBoard,backboardd,runningboardd,datamigrator
sweetsampledelay=45 sweetsampleinterval=30 sweetsamplecount=4 sweetreboot=160
```

**No new device boot has been performed.** Before sending the image, the phone
disappeared from USB. Unsandboxed `adb devices` and `fastboot devices` both
returned no devices. User was asked to reconnect in recovery or fastboot.
Next action is temporary `fastboot boot shim/out/shim-ui-sample-20261105.img`
once reachable, then pull the console in recovery, verify the new kernel banner
and `SMP armed` configuration, and symbolicate the fresh stacks. The startup
dependency observed in the old logs may have changed after Nov 4's root tweaks.

### >>> 2026-11-04 (105): **always pass --highmem** - the 76k-page failures were my own flag <<<

`tools/mkadt.py X.adt --device=gauguin` without `--highmem` produces a tree whose
`/chosen` says `dram-base 0xb0000000`, `dram-size 0x4cf00000`. XNU then bootstraps
with **76,058-76,123 free pages** and dies at 10-13 execs. That is not a device
fault and not the intermittent "low memory state" earlier notes blamed: the
correct invocation

```sh
python3 tools/mkadt.py OUT.adt --device=gauguin --highmem
```

gives `dram-base 0x180000000`, `dram-size 0xfff00000` and **258,664 free pages /
419 execs**. Several forced power cycles were spent chasing this. **Every gauguin
ADT must be built with `--highmem`**; the size check is
`dram-base == 0x180000000`.

**State of the port after this fix (image `shim/out/shim-fx2.img`):** correct high
memory, `embedded-panic-log-size = 0x100000` in `/chosen` (this alone fixes
`debug_log_init: gPanicBase is still not initialized`), **no `/pram` node**,
`_PanicOnCrash` injected into the launchd cache for SpringBoard and backboardd so a
crash panics instead of being swallowed by `_PanicOnCrasX`, and `sweethidtest=30`
for periodic synthetic key events. Boot result: 419 execs, no `SpringBoard gone`
loop, `client=2`, presents=3, `driverkitd` SIGKILL only (harmless, 274 execs follow
it).

**Two ADT additions proved harmful and are reverted in `tools/mkadt.py`:**

- `/product/haptics` - SpringBoard and backboardd then die together every 10 s
  (`SpringBoard gone` / `backboardd gone` at t=10..400, client=0, presents=0).
- `/options` - `IONVRAMController` panic: `Unable to find nvram-bank-size`.

**Kernel-side chain is now fully verified:** SweetHID delivers key events to a real
client (`key 0x40 down (1 clients)`, previously always 0), backboardd opens
IOMobileFramebuffer, obtains a surface and performs complete SwapBegin/SwapEnd
cycles (its swaps are logged as `by kernel_task` because the user client runs on a
kernel thread - not evidence that userspace never submits). What remains is only
that SpringBoard never submits its own layer.


### >>> 2026-11-04 (104): /product must stay child-less; the crash loop is paired <<<

Two additions to the ADT were tried and **both are now known to be wrong**:

- **`/product/haptics`** (a child node, which the real D22AP tree has with
  `closed-loop` and `supports-3rd-party-haptics`). SpringBoard does read
  `IODeviceTree:/product` 42 times per boot, which made this look like the missing
  piece. Adding it is **actively harmful**: SpringBoard and backboardd then die
  together every ten seconds -

  ```text
  SWEET PROC: SpringBoard gone (t=250)
  SWEET PROC: backboardd gone (t=250)
  ... repeated at 260, 270, 280, 290 ...
  SWEET FB: vsync=30000 ... presents=0 client=0
  ```

  Ten seconds is launchd's ThrottleInterval plus startup. Without the node the same
  root and kernel give a stable SpringBoard with **97 IOKit calls, client=2,
  presents=2, 3 swaps and no `gone` line at all**. So `/product` stays child-less
  and the 42 `/product` reads are normal behaviour, not a retry loop.

- **`/options`** (the node SpringBoard reads for boot-args, `-> none` in the boot
  log). Adding it **panics immediately**: `IONVRAMController` matches it and then
  fails in `getNVRAMProperties` - `Unable to find nvram-bank-size property`,
  `IONVRAMCHRPhandler creation failed`, `panic(cpu 0)` at `IONVRAM.cpp:1380`
  (photo IMG_1102). Apple's own `/options` carries only `name` and `AAPL,phandle`;
  leaving it absent is strictly better than the panic.

**A user observation that reframes the whole failure:** with the crash-looping
image the phone is *not* hung - **pressing a button prints kernel log**. The panel
shows `SWEET KEYS: key=0 down=1 pon=0x5 gpio:c110=0` and `SWEET HID: key 0x30 down
(0 clients)`. So the kernel, timers, vsync and input are all healthy; what is
broken is only the userspace GUI layer, and the HID events reach **zero clients**
because nothing has subscribed.

**Attempts that did not help this stretch:** a spin lock around the UFS command
path (the driver already serialises slot 0 with `sweet_io_serial_lock`; reverted),
and `StandardOutPath` for SpringBoard and backboardd (both logs stay at 0 bytes -
iOS does not write to stdout, so an empty log is not evidence of a hang).

### >>> 2026-11-04 (103): root rebuilt from the IPSW, and what it took <<<

The macOS rebuild path now works end to end, which removes the dependency on a
Linux host with `apfs-fuse`:

- `hdiutil attach` mounts Apple's APFS images natively - no `apfs-fuse` needed.
- `hdiutil create -fs "Case-sensitive HFS+"` produces **APFS**, not HFS+. Create a
  raw file, attach it with `hdiutil attach -nomount`, then `newfs_hfs -v iOSRoot -J
  -s /dev/diskN`. Only then is the signature `HX`.
- **Ownership needs `sudo chmod`/`sudo chown` with `hdiutil attach -owners on`**;
  without `-owners on` the chown silently does nothing and every file stays at
  501:20. That, not the format, was why the first rebuild died:
  `map('dyld_shared_cache_arm64'): owned by uid=501 instead of 0` ->
  `Library not loaded: /usr/lib/libSystem.B.dylib` -> `initproc failed to start`.
- The cryptexes must go to `private/preboot/Cryptexes/{OS,App}`; the
  `System/Cryptexes/*` names there are symlinks and `mkdir` does not follow them.
- Upstream's `copy()` uses `rsync -aH --numeric-ids`. Without `--numeric-ids` rsync
  re-owns everything to the invoking user, which is the trap above.

The rebuilt volume still stalls around 100 s: `SWEET HB: 1 wdt=1 tick=273122
exp=269081 call=4044` - the heartbeat callback did not run for ~100 s, after 363
execs. The volume built from the OS/cryptex images alone also lacks the container
directories a first boot creates; the `mobileactivationd` container and its
`-ActivationState: Activated` ark were copied over from the older volume to match
(a fresh image logs `CRASH mobileactivation[132] sig 5` without it). Work stayed on
the older, already-booted volume, which is what reaches SpringBoard.


### >>> 2026-11-04 (103): the render chain is complete except the one link in userspace <<<

Three diagnostics narrowed (102)'s "two clients, one frame" to a single missing
step. All measured on the patched root, `cpus=8`, 500 s:

**1. The only two swaps come from `kernel_task`, not from SpringBoard.**

```text
SWEET FB: swap 1 by kernel_task layer 0 surface 2 1125x2436 fmt 0x42475241 bpr 4608
SWEET FB: swap 2 by kernel_task layer 0 surface 3 ...
```

Those are the boot splash the kernel itself draws. **Neither SpringBoard nor
backboardd has ever swapped a frame.**

**2. The surface contents are a black field with a white centre.**

```text
SWEET FB: corners 1125x2436 bpr 4608: ff000000 ff000000 / ff000000 ff000000 / mid ffffffff
```

All four corners opaque black, centre opaque white - the Apple logo fading out,
which is exactly what the user sees on the panel before the reboot. So the blit
path and the surface format are correct; there is simply nothing else to show.

**3. Every process that opens the display is named, and SpringBoard is not one of
them.**

```text
framebuffer opened by IOMFB_FDR_Loader (type 0)
framebuffer opened by MobileGestaltHelper (type 0)
framebuffer opened by backboardd (type 0)
framebuffer opened by thermalmonitord (type 0)
framebuffer opened by aggregated (type 0)
```

backboardd opening it is correct and expected - SpringBoard is supposed to reach
the display through CoreAnimation, not directly. **backboardd opens the display
successfully and then never swaps.**

**So the chain is complete end to end except one link:** framebuffer driver works,
AppleCLCD matches, backboardd opens it, both render clients attach - and
**SpringBoard never submits a layer to the render server.** Everything on the
kernel side of that boundary is healthy, and the failing step is in userspace
CoreAnimation/RenderBox, which this port has no way to observe.

**A user report worth keeping with this:** on the panel the Apple logo appears,
fades, **the top-left quarter turns magenta**, and the phone reboots. Magenta is
not a UI colour and the surface is black-and-white, so that magenta is almost
certainly an uninitialised surface being scanned out during teardown - consistent
with SpringBoard dying rather than drawing.


### >>> 2026-11-04 (102): the upstream README was the missing manual <<<

Read `dipa-studio/ios-sweet`'s own README for the first time. It settles two things
this port had wrong and hands over the step that was never run.

**1. There is no GPU in the working configuration - at all.**

> No GPU. Everything is drawn by the CPU at roughly 20-30 fps.
> CoreAnimation renders in software

Hundreds of rounds went into the GPU stub, `IOAcceleratorES`, `AGXAccelerator` and
`sweetgpuok`. **None of it was ever the problem**, and `AGXAccelerator` being a stub
that cannot draw is expected on the working board too.

**2. `tools/sweet-root-tweaks.py` had never been run.** It was in the tree the whole
time; every previous round applied only its Setup/preferences part by hand. Run
against the mounted root it changes seven things, and the first boot afterwards
looked different from any boot before it:

| change | effect |
| --- | --- |
| `launchd.plist` `_PanicOnCrash` -> `_PanicOnCrasX` (7 jobs) | a crashing daemon no longer takes the system down |
| CommCenter jobs removed (2) | no baseband, no crash loop |
| `-ActivationState: Activated` in the mobileactivationd ark | the activation branch is taken |
| MediaToolbox `StartRecorderServer=false` (3 variants) | avoids the NULL OpenGL prewarm crash without a GPU |
| VirtualAudio plug-in disabled | mediaserverd stops crash-looping |
| containers dirs, migration `LastSystemVersion` | DataMigration does not run for an hour |
| SpringBoard `BKNoWatchdogs`, Setup skip | (already done by hand in earlier rounds) |

**Measured, `cpus=8` with the patched root:**

| | before | after |
| --- | --- | --- |
| SpringBoard IOKit calls | **33** | **97** |
| SpringBoard's furthest point | `/product` polling | **network/Wi-Fi lookups, then `/chosen`** |
| render clients | **0** | **2** |
| panel | 5 colours | 4 colours (`4d4d4d` gone) |
| presents | 0 | **1** |
| console ASCII map (`SWEET FB: \|`) | drawing | **silent - `sweetfb_noconsole` finally takes effect** |

`cpus=6` instead of 8 gives 100 IOKit calls rather than 97, and the same panel.

**What is still wrong, precisely:** two render clients connect, one frame is
presented, and nothing is ever presented again. On a working iOS, SpringBoard
re-presents continuously (animations, status bar). So SpringBoard attaches to the
render server and then never submits a second frame - it has no scene that redraws.
Injecting a touch (`sweettap=1 sweettapdelay=60`) raises the IOKit count to 103 and
changes nothing, so it is not waiting for input either.

**Ruled out this stretch:** the fourteen `/product` properties from Apple's real tree
(they make the boot die at **76,121 free pages** instead of 258,729 - reproducible,
and removing them one group at a time did not fix it, so the whole set is abandoned),
`cpus=6` vs 8, the hardware watchdog (our `IOWatchdog` accepts check-ins and never
fires), and `driverkitd`'s SIGKILL (274 execs happen after it).

**Crashes now reach the console** (`CRASH driverkitd[67] sig 9`, `CRASH
useractivityd[187] sig 10`) because `_PanicOnCrash` is renamed. Symbolicating needs
`ipsw dyld a2s`, which is not installed here - that is the next tool to add.


### >>> 2026-11-04 (101): ADT integers are little-endian, Apple's tree is big-endian <<<

A trap worth writing down before someone "fixes" it. Apple's `DeviceTree.d22ap`
stores integers **big-endian** (`artwork-scale-factor` = `00 00 00 03`,
`device-perf-memory-class` = `00 00 00 04`). The ADT we generate does not: XNU
parses ADT lengths and values little-endian, and `tools/mkadt.py`'s
`u32 = struct.pack('<I')` matches that. The known-good properties prove it -
`sweet-fbcon`'s `width` is `38 04 00 00` = 1080 and `height` is `60 09 00 00` =
2400 only when read little-endian.

So the values lifted out of Apple's tree must be written with `u32(3)` and
`u32(4)`, **not** copied as their big-endian bytes. Copying the raw bytes would
make `artwork-scale-factor` read back as 50,331,648 - wrong in a way that is
silent, since nothing rejects it.


### >>> 2026-11-04 (100): the real iPhone device tree is readable, and /product was nearly empty <<<

**Apple ships `DeviceTree.<board>.im4p` as an IM4P wrapper around an **LZFSE**
stream (magic `bvx2`). Nothing in this repo could read it, so for hundreds of
rounds the port ran on a `/product` node with four properties while the real
D22AP node carries dozens. `tools/extract-devicetree.sh` now unpacks it with
macOS `libcompression` (verified: byte-identical 186,084 bytes on repeat runs).

**The properties that matter, read straight out of the dump** (hexdump, not a
parser guess):

| property | real value |
| --- | --- |
| `graphics-featureset-class` | `"APPLE4"` |
| `graphics-featureset-fallbacks` | `"APPLE3:APPLE3v1:APPLE2:APPLE1:GLES2,0"` |
| `artwork-device-idiom` | `"phone"` |
| `compatible-app-variant` | `"0"` |
| `artwork-dynamic-displaymode` | `"0"` |
| `device-color-policy` | `0x0` |
| `siri-gesture` | `0x1` |
| `watch-companion` | `0x1` |

**`graphics-featureset-class` is read by iOS** - the string appears once across the
44 shared-cache shards. That is how the renderer is told what the GPU can do, and
it is exactly the shape of the observed failure: SpringBoard opens
`/product` twelve times per boot, gets nothing useful, and never draws.

All eight are now in `tools/mkadt.py`. **Not yet measured** - the phone has been
off USB, and `shim/out/shim-gfx2.img` (class + fallbacks) is built and waiting.

**Also from this stretch, all ruled out on hardware:** the whole provisioning set
(purplebuddy/notbackedup/BKNoWatchdogs), `EmbeddedHomeScreen`, `region-info`,
`chip-revision`, the GPU `stub`/`IOGPUFamilyStub` markers, and clearing a stale
`/var/run` to revive `logd`. **`logd` is granted `GLOBAL_PROC_INFO` now** - it was
being denied by our all-deny sandbox - but it still writes no `.tracev3`, so the
os_log channel stays closed and a silent process still cannot be distinguished
from an idle one.

**A correction worth keeping:** SpringBoard makes **zero GPU calls in a healthy
iOS too** - it delegates to backboardd's render server. "SpringBoard doesn't call
the GPU" was never an anomaly; the anomaly is that it never submits a layer. And
present counts are not a progress signal: adding the backlight service and
removing the stub markers each dropped presents 222 -> 5 with nothing else changed.


### >>> 2026-11-04 (99): the GPU stub markers are not the blocker either <<<

`IOAcceleratorES` publishes `stub=true` and `IOGPUFamilyStub=true`. If
SpringBoard/RenderBox reads either, it would know the accelerator cannot render
and could skip render set-up - a plausible reason for never submitting a layer.
**Removed both markers and booted: no change.** 434 execs, **still 33 SpringBoard
IOKit calls**, still `exec Setup` = 0, same five-colour panel.

**Markers restored**, because they are the honest description of a service that
never draws, and removing them bought nothing.

**A measurement worth remembering:** present counts are not a progress signal.
Adding the backlight service and removing the stub markers each dropped presents
from ~222 to **5**, both times with the panel unchanged and SpringBoard unchanged.
A stable, complete service table seems to let backboardd stop re-submitting, so
a *low* present count can mean "nothing left to poll", not "less rendering".
Compare panel content and SpringBoard's call count, never presents alone.

**Also confirmed this round:** the entire system has exactly three
`NEVER FOUND` classes - `ApplePearlSEPDriver`, `AppleM2ScalerCSCDriver` and one
empty name - i.e. Face ID and a video scaler that this board does not have. **There
is no remaining IOKit service gap to fill.**

**And a correction to how "silence" should be read.** `com.apple.oslog` exists in
the kernel and `test_oslog_handleOSLogCtl` is wired up, but userland `os_log` goes
through `logd`, which asserts continuously (`logd + 90880 ... : 0x2`) and wrote no
new `.tracev3` even after `Persist/` was cleared for a clean capture. So **a process
that emits nothing in our logs is not necessarily idle** - its channel may be
broken. `SWEET MSGSEND: 0 message(s) captured` on every boot says the same for the
message tracer: that trace never worked, and `msgs=0/0` remains meaningful only
because it reads the port structure directly.


### >>> 2026-11-04 (98): the iOS os_log exists - 312 MB of it - and backlight is ruled out <<<

**A data source missed for ~270 rounds.** iOS keeps `os_log` for every process under
`/private/var/db/diagnostics/Persist/*.tracev3`. After a few boots this was 1001
files, 312 MB, **3669 records mentioning SpringBoard**. Everything until now read
only the kernel console, so "SpringBoard goes silent after 33 IOKit calls" was
measured on the wrong log. `.tracev3` is a private binary format and `log show`
refuses the directory as an archive (no index), so `strings` fragments are all that
can be had for now - but they already show:

- `springboard.hasBlankedScreen` (7), `springboard.lockstate` (5),
  `springboard.SBRenderer` (2), `springboard.SBRendererService` (1)
- `failed lookup: com.apple.accessibility.AXSpringBoardServer ... No such process`
- `logd[24]: assertion failed` repeatedly - **logd itself is unhealthy**, which is
  why clearing `Persist/` produced no new files on the next boot

**Backlight was a real gap, and filling it changes nothing.** backboardd looks for a
*service* with `backlight-control=true`, but `/backlight` was only a device-tree
node, so the property match returned `0 found` and backboardd stopped its display
set-up. `SweetBacklight` (an `IOService` with the property, registered in
`KernelConfigTables.cpp`) fixes that: the lookup now reports
**`-> SweetBacklight`, `-> 1 found`**. SpringBoard still makes exactly 33 IOKit
calls, still draws nothing, and presents actually dropped from 222 to 5. **The
service is kept - iOS should have it - but it is not the blocker.**

**Also checked and clean this round:** backboardd's three `NEVER FOUND` classes are
Face ID and a video scaler (no such hardware); SpringBoard's `Info.plist` requires
only `arm64`; `/product` is polled 12x by SpringBoard and 38x by backboardd, which
is normal; `runningboardd` starts and the boot continues past it for another 200+
execs.

**Where this leaves the question:** every configuration, device-tree and IOKit
requirement checked so far is satisfied or ruled out. What remains is knowing where
SpringBoard's main thread actually is, which needs either a symbolised userspace PC
in the thread dump or in-process debugging - neither exists in this port yet.


### >>> 2026-11-04 (97): 8 cores plus the IPSW write path, and provisioning ruled out <<<

**Two capabilities gained, one hypothesis killed.**

**8 cores.** `cpus=8` (with `sweetlogms=500`, `debug=0x8`, no
`-enable_kprintf_spam`) is now the default boot line: **418-429 execs, 1937-2677
log lines, presents 198-225**, against 268 execs / 1591 lines / 109 presents at
`cpus=1`. The system finally runs about as fully as this port allows.

**The iOS root is now writable from the host, end to end:** pull the HFS+ volume
(`dd if=/dev/block/sda35 bs=4096 count=4194304`, 17.18 GB - the volume is only the
front of a 114.9 GB partition, so counting blocks matters), `hdiutil attach
-readwrite`, edit, then stream it back with
`adb exec-in "dd of=/dev/block/sda35 ..." < image` (9 minutes). Ownership survives
as `501:20`, so the files are accepted.

**Provisioning is ruled out.** With `com.apple.purplebuddy.plist`
(SetupDone/SetupFinishedAllSteps/SetupVersion 11/daemonizeNeedsToRun false), both
`.notbackedup` files, and `BKNoWatchdogs` + `FBLaunchWatchdogExceptions` +
`MCForceShowCloudConfigurationUI` merged into `com.apple.springboard.plist`, a boot
gives **429 execs and still 33 SpringBoard IOKit calls, still no `exec Setup`, still
the same five-colour panel.** These are exactly the files `sweet-root-tweaks.py`
writes for the Sweet images - **they are necessary there and not sufficient here.**

**Also ruled out this round:** MobileGestalt is healthy - `MobileGestaltHelper`
answers `sel 8` with `[0x465, 0x984]` = **1125x2436**, the panel's real geometry,
and then closes its client normally.

**What is left.** SpringBoard emits nothing at all after its 33 IOKit lookups -
`exec SpringBoard` and those 33 lines are the only trace of it in a 1781-line log,
where a working SpringBoard is famously verbose. It is not crashing; it is waiting
somewhere that produces no output. Answering that needs in-process debugging of a
userspace binary, which this port has no channel for.


### >>> 2026-11-04 (96): the intermittent short boots are UFS read failures, not the ADT <<<

A panic screen supplied by the user shows what the last several rounds were
guessing at:

```text
exec launchd_cache_loader
SWEET UFS: command 0x28 failed: ocs 0xf uplu 0x21 response 0x0 status 0x0
exit launchd_cache_loader[22] rv=0x0
panic(cpu 0 caller 0xfffffe0007afbcf0): launchd_cache_loader[22] exited
```

with, just above it:

```text
kern.prng.user_reseed_count: (-1) (2) No such file or directory
hfs_mark_inconsistent: Runtime corruption detected on iOSRoot, fsck will be forced
failed to load kernel prng seed: (-76) (22) Invalid argument
failed to store kernel prng seed: (-76) (22) Invalid argument
```

**`command 0x28` is SCSI READ(10) and `ocs 0xf` is a UFS out-of-context status -
this is a read failing in hardware, not a software bug in the ADT.** The chain is
consistent: a failed read makes HFS+ mark the volume inconsistent, the seed files
cannot be read or written, and `launchd_cache_loader` exits, which panics.

**This reframes the short boots.** Rounds 275 and 311 saw 940/941-line boots and
several later runs stopped at ~550-565 lines; all of them were treated as
tracking-code overhead or ADT problems. They are far more likely the same UFS
read failure. The page-count evidence fits: a boot that found only 76,128 free
pages (297 MB) rather than 258,735 (1 GB) is one whose memory scan did not finish,
which is what a storage stall during bring-up would look like.

**What still needs separating:** whether the failing reads correlate with a
particular boot image or are purely a property of the device at the time. Two
`shim-verify` boots (01:50 kernel) both gave 258,735 pages and full logs; two
`shim-regclean` boots (06:54 kernel) both gave 76,128 and stopped early. That looks
like a kernel correlation but is more likely timing luck on a flaky UFS path -
**the next run must interleave the two images** rather than run each twice.


### >>> 2026-11-04 (95): the region-info experiment compared a log against itself <<<

`observe-region.txt.bin` (06:16) and `observe-dump6.txt.bin` (02:06) are **byte
identical** - same md5 `05610bb8...`, same `flush #141`, same 161,887 bytes.

That makes (94)'s table unsafe. The runs did differ in line and present counts,
but the ring that was pulled for the region boot still carried the earlier
kernel's content, so "the panel was identical" is a comparison of one boot with
itself, not evidence that region-info changes nothing. **The region-info question
is back to untested.**

**The general trap, now written down because it has bitten twice:** a boot that
dies before `sweet_log_start()` leaves the PREVIOUS boot in the ring, and
`tools/sweet-log-pull.sh` returns it looking perfectly healthy. `total` and
`flush #` come from the ring header, so **compare flush numbers between runs** -
an unchanged flush means the pull did not see a new boot.

**`research/tmp/three-boots.sh` now enforces this**: it boots baseline, region and
propreq in sequence, and after each prints the line count, the flush number and
the banner, so a stale ring is visible instead of being mistaken for a result.


### >>> 2026-11-04 (94): region-info tested and ruled out; the property trace had two real bugs <<<

**`region-info` is not the cause.** With `/product/region-info = "LL/A"` added, a boot
produced 2217 lines and presents=128 against the 1591/109 baseline - but the panel
content was **identical**: distinct=5, colours `ffffff b7b7b7 818181 bfbfbf 4d4d4d`,
and `Setup` still never executed. Line and present counts drift between boots; the
panel did not change. The guess is disproved.

**The property trace did not work, for two reasons, both now understood:**

1. it matched on `proc_selfname()`, which in the `IORegistryEntry::getProperty`
   path is not the calling BSD process - so `strncmp(me, "SpringBoard")` never
   matched and the trace printed nothing for a whole boot
2. the attempted fix, `get_bsdtask_info(current_task())`, **crashed before
   `sweet_log_start()`** - the ring still held the previous boot's banner
   (01:53 vs the image's 06:31). `getProperty` is reached very early in IOKit
   bring-up, where no BSD process sits behind the task yet.

**Current form** (`sweetpropreq=<key prefix>`) filters on the **property key**
instead of the process, which sidesteps both: the key is a plain string on the
object actually read, and the question "which property does it want" is about the
key anyway. It prints `SWEET PROP: [proc] node.key -> FOUND|NULL`.

**Not yet measured.** The key-filtered build booted and ran the full 200 s
(`still running after 201s`), but every log pull failed and the phone left USB;
the cached ring from that run still contains the 01:53 kernel, so it says nothing
either way. **Open question: did that boot write the ring at all, or did the
over-broad `product` prefix cost enough on one core to matter?** First thing to
do when the phone returns: pull the ring and look at the banner.

### >>> 2026-11-04 (93): four more ruled out from the local mount; ADT structure is sound <<<

All checked against the mounted IPSW, no device needed.

| candidate | result |
| --- | --- |
| iOS version mismatch | build `20H392` / 16.7.16 on disk, in `mkadt.py`, and in the device's `_SBLastSystemVersion` - all three agree |
| SpringBoard resources missing | 11 plists in `SpringBoard.app`, every one non-zero, plus `Assets.car`; `DefaultIconState.plist` and its `~iphone` / `375w-667h` / `414w-736h` variants all present |
| Clarity mode confusion | iOS has two shells: `ClarityBoard` (`_LimitLoadToClarityMode: True`, `EmbeddedHomeScreen: True`) and `SpringBoard`. Only SpringBoard runs on gauguin, which is correct for an iPhone10,3 identity - so the board is in standard mode and ClarityBoard's absence is expected, not a fault |
| ADT structure wrong | generated and re-parsed the tree: `device-tree > {chosen, defaults, cpus, arm-io, sweet-fbcon, buttons, backlight, product, sweet-ufs}`. `/product` exists where iOS looks for it; the lookups succeed and return `IOPlatformDevice`, so the node is found - only its contents are thin |

**Identity properties the ADT publishes:** `/chosen` has `unique-chip-id`, `chip-id`,
`certificate-production-status`, `certificate-security-mode`; the root has `model`,
`target-type`, `target-sub-type`; `/product` has `product-name`, `product-type`,
`regulatory-model-number`. Against the names iOS references in the shared cache,
**`region-info` is the only one with no value anywhere** - and (86)/(90) say a
missing property is not evidence of a fault, so this stays a lead, not a cause.


### >>> 2026-11-04 (92): the real iOS filesystem can be mounted locally <<<

After 370 rounds of reading the iOS root through `tools/hfs-read.py` over adb - a
path that truncates large files at 4096 bytes and needs the phone - the system
disk was mounted straight from the IPSW on this machine:

```
unzip ... "087-86698-044.dmg" -d research/ipsw-x/
hdiutil attach -readonly -mountpoint /tmp/ipsw-mnt   research/ipsw-x/087-86698-044.dmg   # 4.4G, root fs
hdiutil attach -readonly -mountpoint /tmp/ipsw-mnt2  research/ipsw-x/087-86593-047.dmg   # 2.6G, cryptex
```

`/tmp/ipsw-mnt2/System/Library/Caches/com.apple.dyld/` is the 2.4 GB shared cache
- the place where iOS 16.7 actually keeps framework code. **Everything is readable
without a device.**

### What that answered

**SpringBoard's launchd plist, read in full for the first time** (`plistlib`, no
truncation): `MachServices` has **33 entries** - UIKit statusserver, frontboard
systemappservices, springboard.services, bulletinboard, siri activation,
usernotifications and so on. `KeepAlive` and `RunAtLoad` are both true.

**DT property names iOS actually references**, found in the shared cache:
`chip-id` (3), `unique-chip-id` (2), `product-name` (2),
`certificate-security-mode` (2), **`region-info` (2, shard .09)**.
`region-info` sits next to `development-cert` among MobileGestalt keys. Of those,
**`mkadt.py` publishes all but `region-info`** - `chip-id`, `unique-chip-id` and
`certificate-security-mode` are in `/chosen`.

**Icon layout resources are complete**: `DefaultIconState.plist` plus
`~iphone` / `375w-667h` / `414w-736h` variants, so the home screen is not missing
its configuration.

### What it did not answer

Nothing here says *why* SpringBoard draws nothing. The device-tree payload inside
the IPSW (`Firmware/all_flash/DeviceTree.d22ap.im4p`) is **compressed** - the
`IM4P`/`dtre` header is plaintext, the rest is not - so the real D22AP `/product`
node still cannot be recovered that way, which is exactly what `mkadt.py`'s
comment says. `region-info` remains the only referenced property with no value
anywhere; given (86) and (90), **a missing property is not evidence of a fault**.

**Rule going forward: mount the IPSW for filesystem and binary questions; only the
device can answer runtime questions.**


### >>> 2026-11-04 (91): gauguin never showed an interface - the milestones were another board <<<

**This corrects a misreading that shaped many rounds.** NOTES (2026-10-17/18) records
Setup's "Hello" screen (057u, v12) and the **SpringBoard home screen** (0069s,
v14) as milestones. Both were on **Sweet - the D22AP (iPhone X) bring-up**, not
on gauguin. The gauguin board port only started 2026-10-19; the `/product` node
that SpringBoard looks up twelve times per boot was added 2026-10-22
(`1057d24`).

So on gauguin nothing regressed from working to broken. **There was never an
interface to regress from.** That removes "some change between v12 and now broke
it" as a hypothesis, and with it the plan to bisect against old images.

### What is actually known on gauguin, all measured here

| observation | evidence |
| --- | --- |
| kernel boots, 268 execs, no crash | `observe-dump6.txt` counts |
| UFS, HFS+, launchd, ignition complete | progress markers |
| SpringBoard present t=3..t=20, 9 threads | `sweetdump` samples |
| every thread's queue `msgs=0/0` | same |
| SpringBoard does 33 IOKit lookups, 0 GPU matches | `sweetiolog` |
| `/product` x12 and `/arm-io` x13 - polling | `observe-wait4.txt` |
| Setup / buddy never executes | 3 logs incl. the 36,093-line one |
| no `purplebuddy.plist`, no activation record | `hfs-read.py` |

### The narrowest open question

**`/product` carries three properties** (`product-name`, `product-type`,
`regulatory-model-number`) because `mkadt.py` falls back to a minimal node when
`research/ipsw-x/d22ap.adt` is absent - and it is absent, and the device tree
inside the local IPSW is compressed (`IM4P`/`dtre` payload is not plaintext, so
it cannot be mined for property names). **A real D22AP product node has dozens.**

SpringBoard re-opening that node twelve times is consistent with wanting a
property that is not there. **It is not proof** - the same polling could be
harmless - and (86)/(90) are reminders that a scary-looking absence is often
benign.

**Next concrete step, once the phone is back:** read the property names SpringBoard
actually asks for, with the already-built `sweetpropreq=SpringBoard` trace
(image `shim/out/shim-prop.img`). That turns "twelve lookups" into a list of names
and a list of NULLs, and the fix - if there is one - is then a few lines in
`mkadt.py` rather than a driver.


### >>> 2026-11-04 (90): SpringBoard is idle, not stuck - and the kmsg hook was removed <<<

**The expensive send trace is gone.** `sweet_kmsg_note` was removed from
`ipc_kmsg_send`. Measured on the same kernel: **614 lines and no SpringBoard with
it, 1616 lines and a healthy boot without it.** Resolving a destination's owner
per message on one core is enough to stop the boot at launchd's "Early boot
complete". A hook on the hottest path in the system cannot be made cheap enough;
this is recorded rather than reverted silently so nobody re-adds it.

**What replaced it, and what it shows.** Two existing, cheap traces were finally
used:

`sweetdirs=SpringBoard` - 41 records, only two directories:
`/System/Library/Caches/com.apple.dyld` ×38 and `/private/var/` ×2.

`sweetdump=SpringBoard sweetdumprounds=14 sweetdumpevery=12` - **thread count
over one boot: 1,1,1,1,1,2,2,3,4,4,9,9,9,9.** It grows to nine and settles.

Final snapshot, all nine threads:

| tid | state | waitq | meaning |
| --- | --- | --- | --- |
| 222 | 1 `TH_WAIT` | PORT | main thread, seq=1972184400 (was once active) |
| 288, 343, 512-515 | 1 | QUEUE | parked, seq=0 - never fired |
| 327 | 4 `TH_RUN` | - | running at sample time |
| 511 | 41 | TURNSTILE | exiting (`TH_WAIT\|TH_UNINT\|TH_TERMINATE2`) |

**Every thread's queue is `msgs=0/0`.**

**The correction that matters:** (previous rounds described SpringBoard as
"stopped after 33 platform calls"). It is not stopped. It builds nine threads and
then all of them idle with empty queues. That is the normal signature of a
process waiting for input, not a wedged one. Combined with 268 exec calls (more
than the 236 in the older "healthy" log) and both SpringBoard and backboardd
staying `present` through t=20, the system is fully booted. **Nothing crashes and
nothing fails to start.**

**Also checked and dismissed:**

- `/var` symlink -> `private/var` exists and is correct (a round earlier claimed
  it was missing; that was a truncated `head` listing, withdrawn)
- dyld cache files present; `not in trust cache` is a warning and the code
  continues past it; the 40+ shared-cache mappings are done by launchd and
  inherited
- `/private/preboot` contains only `Cryptexes/`; the `.roots-installed` cookie
  launchd looks for is absent. Noted, **not** claimed as causal - 268 processes
  started anyway, the same pattern as the trust-cache warning.

**So the question is no longer "why did SpringBoard stop" but "what was supposed
to tell it to display something, and why did that never arrive".**
`sweetmsgwait` already proved the queues stay empty for a whole boot.


### >>> 2026-11-04 (89): the system never learns which app is in the foreground <<<

Found by grepping an existing 43,808-line boot log for error patterns rather
than by adding instrumentation. This is the most direct evidence yet that
SpringBoard has nothing to show, and it sits upstream of every IOKit and IPC
observation in this file.

```text
MKBUserSessionID         = 501          (mobile, Foreground = 1)
UMD_INIT: failed to read nextsession dict
UMD_INIT: Unable to Obtained foreground, curFG:502, nextID:-1
UMD_INIT: Failed to get next session, booting with default id to be Loginwindow UID
UMD_INIT: FAILED to Set Foreground ID + multiuser in commpage successfully
```

`nextID:-1` is the whole story in one number: **the system cannot name the next
session**, so it falls back to `Loginwindow UID`, and the write of the
foreground ID into the commpage **fails**.

**Why this matters more than the earlier findings:** every previous result
described *behaviour* (no GPU matches, idle queues, blank surfaces). This one
describes a *missing input to the compositor's decision*: if the foreground ID
is not in the commpage, SpringBoard has no answer to "what should be on screen",
and doing 33 platform lookups and then idling is exactly what that would look
like.

**Where it comes from:** `UMD_INIT` is dyld code, not kernel code - grepping the
kernel tree finds nothing. So the file it fails to read lives on the iOS root
and can be inspected from the host with `tools/hfs-read.py` without any new
instrumentation.

**Next step when the phone is back:** locate the session configuration the
`nextsession` dictionary would come from (candidates: `/var/db/` session
plists, `/Library/Preferences/com.apple.loginwindow.plist`) and check whether
it exists and what it says. A missing or malformed session file would be a
one-file fix rather than a driver.

**Not yet verified:** that this is causal rather than a benign fallback. The
counter-argument is the same one used for `not in trust cache` (86) - that
warning looked fatal and was proved harmless. **Do not treat this as the root
cause until the file is inspected.**


### >>> 2026-11-04 (88): kmsg hook overhead, and the run-order that makes it meaningful <<<

(87) raised the possibility that the short boot was the `ipc_kmsg_send` hook
itself. That hook sits on the path of *every message in the system*, so its cost
matters on one core. Two rounds of work cut it:

| version | per-message cost |
| --- | --- |
| first | resolve the destination task, read its name, `strncmp` |
| (85) + | destination filter before slot allocation |
| round 279 | one-slot verdict cache (covers two ports) |
| **round 280** | **32-slot direct-mapped verdict cache** |

A boot fans out across dozens of ports, so a single cached "not it" was not
enough; 32 slots indexed from the port pointer covers the hot set without a scan.

**The order that makes any of this meaningful** - and the reason (87) drew no
conclusion:

1. **control first**: boot `shim/out/shim-wait4.img` (previous kernel, no kmsg
   hook) and confirm it reaches `exec SpringBoard` and ~30 k lines
2. only then run `research/tmp/run-kmsg.sh`

If the control also comes up short, the short boot is not the hook and the kmsg
build is innocent. If the control is healthy and the kmsg build is not, the hook
is real overhead and needs to be cut further. **Running the trace first proves
nothing either way** - which is exactly what happened at round 275.

Also fixed there: `run-kmsg.sh` wrote to a fixed output path, so its second run
overwrote the first run's log and destroyed the evidence for the 940-line boot.
Output names now carry a timestamp.


### >>> 2026-11-04 (87): both dual-trace runs failed to produce data; one boot was short <<<

The phone came back for one round and both attempts came to nothing:

| attempt | what happened |
| --- | --- |
| 1 | boot ended early - 940 lines, no `exec SpringBoard`, no `exec backboardd`; `SWEET KMSG: 0 captured, 0 to SpringBoard` is therefore **meaningless**, since the process under test never ran |
| 2 | ran the full 201 s (`still running after 201s`) but all four log pulls failed and the phone left USB again |

**No conclusion of any kind is drawn from these runs.**

**One thing to check before running the kmsg build again:** the short boot could be
the new `ipc_kmsg_send` hook itself. It runs for *every message in the system*,
resolving the destination's process name each time until the 64 slots fill, on a
single core. The second attempt running the full 201 s argues against a systematic
break, but that is the same "looked fine once" reasoning that has been wrong
repeatedly in this project.

**Next experiment is therefore a control, not the trace:** boot the *previous*
kernel (no kmsg hook) and confirm it reaches `exec SpringBoard` and ~30 k lines.
Only if that is stable does the kmsg build mean anything.


### >>> 2026-11-04 (86): the send trace is hardened; one boot now answers two questions <<<

(85) rebuilt the send-side trace because the old hook may never have been on the
path. While the phone has been off USB, the replacement was hardened against
every failure mode this project has already been bitten by:

| check | result |
| --- | --- |
| hook reaches all sends | `ipc_kmsg_send` is called from `ipc_mig`, `mach_msg`, `flipc` |
| runs under no lock | hook sits above `ip_mq_lock(port)` |
| filter before slots | destination is resolved first, so unrelated traffic cannot fill the array |
| needle not clobbered | own buffer; sharing `sweet_msgwait_needle` let `sweet_msgwait_init()` clear it |
| overhead bounded | report sampled every 4096 receives, not 34,132 times a boot |
| destination name resolvable | same `get_bsdtask_info` path that already prints `owner=SpringBoard` |

**Also added `ip_destination` to the wait trace**, so one boot now answers two
questions at once:

- `sweetkmssend=SpringBoard` - does anything send to it?
- `sweetmsgwait=SpringBoard` - are the ports it parks on its own queues
  (`dest` = itself or `none`) or services it provides and is waiting to be
  called on (`dest` = another process)?

That distinction matters: "idling on my own dispatch queues" and "waiting to be
called by a client" are entirely different diagnoses and the previous trace
could not tell them apart.

Run with `bash research/tmp/run-kmsg.sh` (both traces, retries the flaky log
pull). **Not yet run** - the phone has been off USB since round 258.

**Nothing here is a finding.** It is preparation, and the session has produced no
new measurement in these rounds. Recorded as such.


### >>> 2026-11-04 (85): the "zero messages" result may have been a wrong hook site <<<

(84) concluded "nobody ever sends to SpringBoard" from
`sweetmsgsend=SpringBoard` reporting `0 message(s) captured` for a whole boot.
**That conclusion is now suspect, because the hook may not be on the path.**

The trace sits in `ipc_mqueue_send_locked`. Checked where sends actually go:

| function | callers |
| --- | --- |
| `ipc_mqueue_send` | essentially none outside flipc.c |
| **`ipc_kmsg_send`** | `ipc_mig.c:164`, `ipc_mig.c:398`, **`mach_msg.c:854`** (the ordinary mach_msg syscall), `flipc.c:276`, `flipc.c:636` |

So **`ipc_kmsg_send` is the rendezvous every send passes through**, and the
message-queue function is a leaf that most traffic never touches. A zero from a
leaf proves nothing about the system.

**What was built in response** (`sweetkmssend=<destination>`):

- hook moved to `ipc_kmsg_send` right after `port = hdr->msgh_remote_port`
- lockless: one port pointer per slot behind an atomic counter, bounded at 64
- **filtered by destination before recording** - without it the 64 slots fill
  with whatever the boot sends first and a later match is invisible, which is
  exactly the mistake (81) made with the wait-queue cap
- the filter needle has **its own storage**: the first version reused
  `sweet_msgwait_needle`, and `sweet_msgwait_init()` clears that whenever
  `sweetmsgwait` is absent, so the trace silently did nothing

It builds and links; one boot decides it. **Not yet run** - the phone left USB
again after the build.

**Either way this matters:** if the new hook also reports zero, "nothing is sent
to SpringBoard" is real and the search goes upstream to launchd. If it reports
messages, (84) was wrong and the question returns to SpringBoard not acting on
what it receives.


### >>> 2026-11-04 (84): NOBODY EVER SENDS TO SpringBoard. That is the answer. <<<

Both outstanding experiments ran. The send-side one is decisive.

**`sweetmsgsend=SpringBoard`, whole boot: zero messages.**

```text
SWEET MSGSEND: 0 message(s) captured      (reported 34,128 times across the boot)
```

**Nothing - not launchd, not backboardd, not any daemon - ever sends a message
to SpringBoard.** That closes the question the last eighty rounds were circling.

**`sweetmsgwait=SpringBoard`, cap 2000, 369 records (cap not reached, so this is
the complete set):**

| port | waits | share |
| --- | --- | --- |
| 0x...4953a8 | 184 | 50 % |
| 0x...495268 | 76 | 21 % |
| 0x...ee4688 | 40 | 11 % |
| 13 others | 69 | 19 % |

All 369 report `owner=SpringBoard`. Recorded between log lines 957 and 30,634 of
36,093, i.e. essentially the whole boot.

**So the picture is complete:**

```text
SpringBoard starts
  -> parks on 16 of its own queues (this is the 33 IOKit calls plus idling)
  -> opens AppleKeyStore and IOPMrootDomain
  -> waits
  -> nothing is ever sent to it
```

It is not blocked on a dependency, not crashed, not wedged, not waiting for
input - **it was never asked to do anything.** The bug is upstream: whatever is
supposed to tell SpringBoard to put up UI never does.

**Note on instrument history, because it matters for trusting this:** the cap
was 40 when the first version of this experiment was written, and 40 filled up
in the first third of the boot. Raising it to 200 revealed 11 ports and a
wait-work-wait pattern; raising it to 2000 showed the cap is not even reached
(369 total). The first two readings were partial and would have supported the
wrong conclusion.


### >>> 2026-11-03 (83): what SpringBoard should be providing <<<

Read from `/System/Library/LaunchDaemons/com.apple.SpringBoard.plist` on the
HFS+ root with `tools/hfs-read.py cat`. Its `MachServices` list includes:

```text
com.apple.frontboard.systemappservices
com.apple.springboard.services
com.apple.springboard.statusbarservices
com.apple.springboard.backgroundappservices
com.apple.springboard.blockableservices
com.apple.UIKit.statusbarservice
com.apple.systemstatus.publisher
com.apple.pegasus
```

**`com.apple.frontboard.systemappservices` is a Mach service SpringBoard
provides itself.** That does answer the operational question - no separate
process has to start for FrontBoard to exist - but it does **not** establish that
a binary named `frontboardd` is absent from the system. Both could be true at
once. Rounds spent hunting for a missing `frontboardd` were looking in the wrong
place either way, since the service is SpringBoard's to publish; the stronger
claim that such a process "was never meant to exist" is not supported by a plist
entry alone and is withdrawn.

The plist also carries `RunAtLoad`, `KeepAlive`, `ThrottleInterval`,
`HideUntilCheckIn`, `EnvironmentVariables` and `POSIXSpawnType`, so the job
itself is configured normally.

**Not knowable from the kernel:** whether these services ever get registered or
looked up. The kernel log records IOKit lookups, not Mach service registration;
a `grep` of the service names over a boot returns zero and that zero is
inconclusive, not evidence. Registration happens in userland launchd.

So the open question downstream of (80) is: SpringBoard owns the queues from
(80) and would publish these services - did anything ever ask for one?


### >>> 2026-11-03 (82): SpringBoard waits first, then calls - the order is not what I assumed <<<

Reading the successful `sweetmsgwait` log again, with the ordering checked against
the ring first (vsync runs 2 -> 4200 strictly monotonic, no overwrite, so line
order is time order here):

| event | log lines |
| --- | --- |
| 40 port waits | 620 - 777 |
| 33 IOKit calls | 1002 - 1041 |

**No overlap.** SpringBoard parks on its own queues *before* it enumerates the
platform, not after.

So the earlier phrasing "it makes 33 calls and then goes quiet" described the
end of the sequence, not the whole of it. The sequence is:

```text
start -> park on its own ports -> (woken) -> 33 platform calls -> nothing
```

That matters because it means SpringBoard **is** woken: something did reach it
early. The failure is not "no message ever arrives" - it is that after handling
what arrived it does 33 lookups, opens two services, and stops.

**What is still unseen:** whether it parks again after the 33 calls. The 40-record
cap filled during the early burst, so the later behaviour is invisible. The cap is
now 200 and one boot would show it - that boot has not happened (phone off USB).

**Why this is "waits on its own ports" and not something else:** every one of the
40 records reports `owner=SpringBoard`, `type=3` (`WQT_PORT`). Those are message
queues SpringBoard owns, i.e. its own libdispatch side, not a service it is
waiting for somebody to provide.


### >>> 2026-11-03 (81): the wait cap hid most of the data; tools fixed, not yet re-run <<<

(80) reported 7 ports and 40 records, but the record cap is 40 and it filled
between log lines 620 and 777 of a 1649-line boot. **Everything after that is
invisible**, so "7 ports" means "the first 7 ports", not the whole set.

Fixed, built, not yet run (the phone has been off USB since round 218):

- **cap 40 -> 200**, so a boot's later waits are not simply dropped
- **`sweetmsgsend=<receiver>`**, a send-side trace, so the quiet side can be
  read the other way: does anything ever send *to* SpringBoard?
- the send trace is **lock-safe**: it is called from
  `ipc_mqueue_send_locked` with the port lock held, so it only writes a fixed
  16-slot array behind an atomic counter and never logs there.
  `sweet_msgsend_report()` prints afterwards, outside the lock. Logging inside
  that lock takes `sweet_log_lock` and is the kind of pairing that wedges a
  single-core boot - the first version did exactly that and is replaced
- the send trace also **checks before incrementing**: once full it exits on an
  atomic read, since the path runs for every message in the system

**Two experiments outstanding, both one boot each:**

1. `sweetmsgwait=SpringBoard` with the cap at 200 - the full wait pattern
2. `sweetmsgsend=SpringBoard` on its own - whether anything sends to it

Between them they split the problem in two: if messages do arrive, whatever
SpringBoard does next is where it stops; if none arrive, it was never asked to
do anything. Neither has been measured yet.

**Address pattern, noted but not conclusive:** three of the seven ports sit
160-320 bytes apart (one allocation), the rest are far apart. That is the shape
of a few independently created queues, i.e. libdispatch, which fits (80)'s
"idle queues" reading. It is a hint, not evidence.


### >>> 2026-11-03 (80): sweetmsgwait ran at last - SpringBoard waits on its own ports <<<

The instrument from round 82 had never once been enabled, despite 128 rounds of
asking what SpringBoard was waiting for. The phone came back, and it was the
first thing run:

```text
sweetmsgwait=SpringBoard
```

Result, 40 records (the cap) over 7 distinct ports:

| port | waits |
| --- | --- |
| 0xfffffe200f72f9c8 | 15 |
| 0xfffffe200f72f888 | 13 |
| 0xfffffe200f6f2028 | 5 |
| 0xfffffe200f72fb08 | 2 |
| 0xfffffe200f717608 | 2 |
| 0xfffffe200f6f20c8 | 2 |
| 0xfffffe200f716f28 | 1 |

**Every one reports `owner=SpringBoard`, all `type=3` (`WQT_PORT`).**

Two conclusions, both measured for the first time:

1. **No missing external dependency.** SpringBoard is not blocked on a service
   somebody else should be providing - it is parked on message queues it owns.
2. Two ports carry 28 of the 40 waits, which is the shape of libdispatch idle
   queues rather than a protocol stall.

This rules out the whole family of "a daemon it needs never started" theories,
including the `frontboardd` line that ran for many rounds.

**What it does not answer:** whether anything ever sends to those ports. A
port with no sender and a port whose sender is late look identical from the
receiving side, so a send-side trace was added (`sweetmsgsend=<receiver>`,
noted in `ipc_mqueue_send_locked`). It builds and is in the kernel, but the
test boot could not be read - the log pull failed and the phone left USB again.
**That experiment is still outstanding.**


### >>> 2026-11-03 (79): SpringBoard's 33 calls, enumerated, and its threads, decoded <<<

Two things that had been described loosely are now exact.

**The 33 calls, de-duplicated - 10 distinct kinds, nothing graphic:**

| call | count |
| --- | --- |
| path IODeviceTree:/arm-io -> IOPlatformDevice | 13 |
| path IODeviceTree:/product -> IOPlatformDevice | 12 |
| match <IOProviderClass=AppleKeyStore> -> AppleKeyStore | 1 |
| open AppleKeyStore | 1 |
| open IOPMrootDomain | 1 |
| path IODeviceTree:/buttons | 1 |
| path IOPower:/IOPowerConnection/IOPMrootDomain | 1 |
| path IOService:/IOResources/AppleKeyStore | 1 |
| path IODeviceTree:/arm-io/pearl-sep -> none | 1 |
| path IODeviceTree:/product/camera -> none | 1 |

Not one is display, surface or accelerator. The single `matching1` is the
keystore.

**The final thread states, decoded against `thread.h`** (`TH_WAIT 0x01`,
`TH_UNINT 0x08`, `TH_TERMINATE2 0x20`):

| thread | waitq | state | meaning |
| --- | --- | --- | --- |
| tid 222 (main) | PORT | 1 | TH_WAIT - parked on a port |
| tid 338 | QUEUE | 1 | TH_WAIT |
| tid 462 | QUEUE | 1 | TH_WAIT |
| tid 466 | TURNSTILE | 41 | TH_WAIT+TH_UNINT+TH_TERMINATE2 - **exiting** |
| tid 474 | QUEUE | 1 | TH_WAIT |

**Correction:** (56)'s "the block ring shows a deadlock" reading of `tid=466`
was wrong. `state=41` is a thread on its way out, not a stuck one. Every thread
is in an ordinary state; the process is **idle**, not wedged. Four wait for
work, one is terminating.

That is the honest characterisation of SpringBoard at the end of the log: a
healthy, idle app that has finished its platform enumeration and is waiting.
It has not failed. Nothing is going to arrive.

**Also corrected:** (56) is cited elsewhere as "8 ports, all owned by
SpringBoard". That came from a thread dump, not a port listing, and the counts
do not match - different samples show 3 and 5 threads. Only the *states* above
are established; the port-ownership claim was never measured and should not be
relied on.


### >>> 2026-11-03 (78): SpringBoard stops after two opens <<<

The sharpest statement of where SpringBoard halts. Both processes open
`AppleKeyStore` and `IOPMrootDomain`; then they part:

| service | SpringBoard | backboardd |
| --- | --- | --- |
| AppleKeyStore | yes | yes |
| IOPMrootDomain | yes | yes |
| SweetHIDTouch | - | yes |
| SweetHIDButtons | - | yes |
| AppleCLCD | - | yes |
| IOCoreSurfaceRoot | - | yes |
| IOAcceleratorES | - (0 matches) | yes (213 matches) |

**SpringBoard opens exactly two services, both platform basics, and no
graphics-related service at all.** backboardd opens six, the whole display kit.

So it is not that SpringBoard "cannot draw" - it never reaches the step where
drawing would begin. The normal order after keystore and power would be display
service, surface creation, GPU, frame; none of it happens.

Combined with (76)-(77) the picture is consistent: nothing below SpringBoard is
broken, and SpringBoard itself stops before its first graphics call. What is
not established is *why* it stops there - that needs a debugger inside the
process, which this setup does not have.


### >>> 2026-11-03 (77): the display path is healthy end to end; it is fed blanks <<<

The other half of (76), from the same log. The display controller side is not
the problem:

```text
93   SWEET FB: AppleCLCD 1080x2400 stride 4320 at 0xa0000000,
                default surface 1, presented as 1125x2436     (initialised)
819  backboardd open AppleCLCD type 0 -> 0x0                  (opened)
835  backboardd matching1 AppleCLCD -> AppleCLCD              (matched)
```

and it is fed: 16 panel submissions, 8 per surface. What they contain is the
finding:

| surface | swaps | nonblack | distinct | first pixel |
| --- | --- | --- | --- | --- |
| id=2 | 8 | 10 | 1 | 0xff000000 |
| id=3 | 8 | 13 | 2 | 0xff000000 |

13 non-black out of 4096 samples is 99.7 % black. **backboardd is compositing
and submitting on a working controller - it is being handed empty surfaces.**

This corrects the wording in (76) that said the compositor "spins" with
`sweetgpuok`: it does not spin, it submits blanks normally. The input is empty,
the output is honest.

**Full chain, settled:**

```text
SpringBoard   0 GPU matches - produces nothing
     |
backboardd    2 blank surfaces, 99.7 % black
     |
AppleCLCD     healthy, 16 submissions
     |
panel         the centred 180x168 shape plus black
```

So nothing below SpringBoard needs fixing. The missing piece is entirely "produce
a frame", which needs the GPU command path from (76).


### >>> 2026-11-03 (76): the GPU chain, traced end to end from an existing log <<<

Assembled from `research/tmp/observe-hid2.txt` while the phone was offline (round
143 on). Nothing here is new measurement - it is the same log read with the
right prefixes, and it settles where the GPU path actually stops.

**SpringBoard and backboardd do not behave alike at all:**

| process | IOKit calls | of which device-tree | of which GPU match |
| --- | --- | --- | --- |
| backboardd | **300** | 51 | **213** |
| SpringBoard | **33** | 25 | **0** |

33 is a hard constant: identical in all 19 boots on disk, across ADT changes and
`sweetgpuok`. SpringBoard enumerates the platform (25 tree lookups + keystore +
power + two failed nodes) and then stops - it never asks for a GPU at all.

**backboardd does ask, and the chain is complete up to one call:**

```text
110  SWEET GPU: AGXAccelerator published (stub)
864  backboardd matching1 AGXAccelerator -> AGXAccelerator      (found)
870  backboardd open AGXAccelerator type 1 -> 0x0                (opened)
869  SWEET GPU: user client opened
871  SWEET GPU: method 2 (0 in, 0 out) -> unsupported             <- stops here
872  SWEET GPU: user client closed
```

All 213 `IOAcceleratorES` matches **succeed** - 0 MISS. So the class name is
fine; an earlier note suspecting a name mismatch was wrong.

**method 2's failure is a switch, not a bug** (`SweetFramebuffer.cpp:240`):

```c
return sweet_gpu_ok ? kIOReturnSuccess : kIOReturnUnsupported;
```

and `sweet_gpu_ok` comes from boot-arg `sweetgpuok`. **Turning it on does not
help** - measured:

| build | presents | distinct | nonblack |
| --- | --- | --- | --- |
| `sweetgpuok=1` | 177 | 5 | 60 |
| default | 132 | 5 | 60 |

34 % more submits, byte-identical content. The compositor spins; nothing is
drawn.

**So the gap is precise now:** not discovery, not naming, not permission -
**the GPU commands are never executed.** That is a driver to write, not a flag
to flip, and it is the reason SpringBoard has nothing to composite.


### >>> 2026-11-03 (75): device offline since round 143; what is saved and what is not <<<

The phone dropped off USB after the round-142 colour-map run and has not come
back for 22 rounds. Host side checked: `ioreg -p IOUSB` still lists three
`AppleT8142USBXHCI` controllers, so the host is fine and simply has no device
attached. Nothing here can fix that.

**Two kernels exist and they are not the same. Do not mix them up:**

| kernel | time | GPU caller name | verified on hardware |
| --- | --- | --- | --- |
| `research/k-proven` | 23:06 | no | **yes** - this is the last one that booted |
| `xnu/out-gauguin-macos/.../kernel.development.gauguin` | 23:17 | yes | **no** - links, never ran |

Same size, different hash. When the phone returns, boot `k-proven` first to
reproduce the known state, and test the GPU caller name as its own change -
otherwise a new observation cannot be attributed to either.

**What is saved:**

- `xnu/instrumentation/` holds byte-identical copies of the four instrumented
  sources (verified against the build tree in round 163), with a README that
  separates verified from unverified instrumentation
- every conclusion, retraction and measurement is in this file
- `research/k-proven` is the working kernel

**What is not, and cannot be:** the boot images themselves. They are 17 MB,
regenerate in four minutes, and differ every build, so they are deliberately
not tracked. `research/tmp/observe-*.txt` device dumps stay out of git too.

**First things to do when the phone is back:**

1. boot `k-proven` unchanged, confirm the known panel state still reproduces
2. run the colour-coded map, which was lost mid-flight - it answers "is the
   centred 180x168 px shape white (a boot logo) or coloured (something else?)"
3. only then test the GPU caller-name build


### >>> 2026-11-03 (74): the centred shape is ~180x168 px, and it took three tries <<<

Measured from the ASCII map of entry (72), counting the actual columns and rows
per line rather than eyeballing them:

| quantity | value |
| --- | --- |
| size | **180 x 168 px** (16.7 % x 7.0 % of the 1080x2400 panel) |
| centre | x=544 vs panel 540, y=1184 vs panel 1200 - centred |
| profile | widest at row 8 (45 columns), narrowing to 27 by the last row |

Widths per row: 41, 42, 41, 40, 40, 40, 41, 42, 45, 44, 41, 38, 33, 27. It is
wider at the top than the bottom, so not a rounded rectangle - something with
content inside it.

**Three attempts to get this number, and the first two were wrong:**

- (72) said "about 600x250 px" - I read map *columns* as pixels and forgot the
  4 px step
- (73) said "200x156" - still estimated the extent instead of counting it
- here: counted every row, 180x168

The lesson repeats the one from the instrument defects: **a number that comes
from a map has to be converted back through the sampling step, and counted, not
eyeballed.** Do not quote a size from the map without doing both.

**Resolution caveat:** the map samples 4 px per column and 12 px per row, so
the height carries +-12 px of error. A finer map is needed to pin it down, and
that needs the phone.


### >>> 2026-11-03 (73): the ASCII map sees the screen; the nonblack counter does not <<<

Following (72): five independent boots, same final colours every time
(`ffffff b7b7b7 818181 bfbfbf 4d4d4d`) and the same non-black bounding box
(`x=200..832 y=1037..1378`), but `nonblack` itself was 60 in one run and 13 in
the other four.

The counter is the problem, not the screen. `nonblack` samples the panel with
a **632-pixel stride** (4096 points over 1080x2400). The box is 8.3 % of the
panel, so a solid fill there should register ~341 hits; 60 is 18 % of that and
13 is 4 %. The ASCII map, by contrast, samples 128x24 points *inside* the box,
about five times denser, and shows a solid rounded mass.

**So the content is real and `nonblack` has been badly understating it.** That
counter has been quoted since round 71 as evidence that "the panel shows almost
nothing"; it never meant that. Do not use it to judge how much is drawn - use
the map.

The bounding box *is* reliable (identical across all five boots), so it is the
right thing to check content against.

**Still open, and needs the phone:** what the shape is. The colour-coded map
that would have said (white? blue? an icon?) was lost when the device dropped
off USB, and it has not come back.


### >>> 2026-11-03 (72): what is actually on the panel, for the first time <<<

For ~100 rounds the panel was described by three numbers - `nonblack`,
`distinct`, `presents` - and nobody knew what any of it looked like. Printing
the colours and then an ASCII map settled it.

**The colours change when the first swap happens**, which pins the content to
backboardd rather than to the bootloader:

```text
vsync=2     presents=0    distinct=2   ffffff 00ff00          (ABL splash + our mark)
vsync=1800  presents=0    distinct=1   ffffff
vsync=3000  presents=5    distinct=5   ffffff b7b7b7 818181 bfbfbf 4d4d4d
vsync=4200  presents=122  distinct=5   (same)
```

The greys are not a smooth ramp (steps of 52/54/8/64), so they are not
antialiasing - they are separate elements.

**Whole-panel map** (`#` bright, `+` dim,`.` black), 64x40 over 1080x2400:

```text
... 18 all-black rows ...
                                  :
                          ##########
                           ###########
                              #...*+
... 18 all-black rows ...
```

**Zoomed to the band (x 240..840, y 1100..1400, 128 columns):** one solid
rounded mass about 600x250 px near the vertical centre, with a separate
full-width dim line at y~1300.

**So the screen is not blank and not noise**: iOS is drawing a real filled
shape, centred, black everywhere else. It is equally clearly *not* a home
screen, lock screen or app.

**What this does not tell us:** what the shape is. Resolution and the lack of
colour channel information are not enough to identify it, and I have no
reference image to compare against. The round-142 attempt to add colour was
lost when the phone dropped off USB (see below), so that is still open.

**Tooling added for this** (all off by default, one-shot): colour list on the
`vsync=` line, `nonblack` bounding box, and an ASCII luminance map driven by
the same counters. The map is the most useful thing this session built for
looking at the display; it answers "did anything draw?" in one boot.


### >>> 2026-11-03 (70): injected touch reaches the HID service and SpringBoard ignores it <<<

The one experiment this session could actually run to completion. Five
conditions held at once, which none of the previous thirteen attempts managed:

| condition | evidence |
| --- | --- |
| boot completed | 1638 lines, every milestone |
| SpringBoard running normally | 33 IOKit calls |
| touch delivered | `touch 0 down -> dispatched`, then `touch 0 down` from the client - **no `deduped` line** |
| observation window | 150 lines after the tap |
| control | matched run with no tap: 1577 lines, 33 IOKit calls, distinct=5 - identical to the tap run |

Result:

```text
SpringBoard IOKit calls before the touch: 33
SpringBoard IOKit calls after the touch:   0
panel: distinct=5, unchanged
```

**SpringBoard receives a real HID touch and does nothing.** No IOKit activity,
no IOSurface, no framebuffer, no repaint.

So entry (56)'s "SpringBoard is working normally, waiting for an event" is
**wrong**, and the correction is measured rather than argued.

**How the experiment was made to work**, after thirteen failures:

- the tap gets its own `thread_call` (`sweettapdelay=`), not a slot on the
  bring-up thread: `sweettapdelay` under ~12 s puts I2C/RPMh work on the bus
  during vfs_mountroot and the boot stops (measured: 787 lines, presents=0,
  against 1586 and 177 at the default 45 s)
- the delay is a `thread_call`, not `IOSleep`: IOSleep in a busy single-core
  boot stretches far past its nominal value, and an
  `assert_wait_deadline` + `thread_block(THREAD_CONTINUE_NULL)` pair never woke
  at all
- `SweetHIDTouch`'s `fDown[]`/`fX[]`/`fY[]` were never initialised, and
  `touch()` returns early when `fDown[finger] == down` - an uninitialised true
  would have swallowed the first touch silently. Now zeroed in `start()`, and
  the early return logs `-> deduped`
- `sweetufsquiet=1` silences the per-command UFS line, which was 84 % of the
  log

**What this rules out:** input as the trigger. Whatever SpringBoard is waiting
for is not a touch event.


### >>> 2026-11-03 (54): "the image is missing components" was wrong <<<

Entry (53)'s conclusion - that frontboardd and BackBoardServices are absent from
the iOS root, so the image is incomplete - **does not hold**.

`find BackBoardServices` returns nothing, but the actual path is
`/System/Library/PrivateFrameworks/BackBoardServices.framework/`. Searching for
a bare binary name misses every framework, and there are 32 board-related
frameworks present, including `FrontBoard.framework` and
`BackBoardServices.framework`.

**Lesson, the same one as entry ()'s instrument defects:** a negative result
from a name search means "that exact name is not there", not "that component is
absent". The find command should be used to test presence only after the
expected path form is known.

Whether `frontboardd` itself exists remains **unknown**: iOS ships many daemons
only inside `dyld_shared_cache_arm64`, and the reader cannot read that file -
its records do not use the +104 extent offset that `.journal` does (same failure
as the .tracev3 files in entry (52)).

**So the state after (53)-(54) is:** the absence of frontboardd is unproven,
not established. Do not treat the image as incomplete on this evidence.


### >>> 2026-11-03 (52): adding a GPU node to /arm-io changed nothing, and posts over again <<<

Entry (51) left one specific lead: SpringBoard's last act is **thirteen
consecutive queries of `IODeviceTree:/arm-io`**, after which it makes no IOKit
call at all for the remaining ~7,000 log lines. `arm-io` published only gic,
wdt and disp0 even though the device tree carries `gpu@3d00000`
(`qcom,adreno-619.0`). Hypothesis: SpringBoard walks /arm-io looking for an
accelerator, does not find one, and stops.

Added a `gpu` node to `tools/mkadt.py` with no kernel driver behind it, so the
only thing that could change is whether the walk succeeds.

**It changed nothing:**

| | without the node | with the node |
| --- | --- | --- |
| SpringBoard IOKit calls | 33 | **33** |
| `/arm-io` queries | 13 | **13** |
| last SpringBoard log line | 14050 / 15554 | 13918 / 15455 |

`presents` did move, 36 → 75. **That is noise.** Entry (51) proved
`sweetgpuok=1` moves the same counter 36 → 88 while changing no pixel, so a
rising presents value on its own is not evidence of anything, and this entry
would have said "progress" if the call counts had not been compared.

The node was reverted; `tools/mkadt.py` is unchanged.

**What this rules out:** SpringBoard is not waiting for a GPU node under
/arm-io. Its 13 queries succeed - the log shows `arm-io -> IOPlatformDevice`,
not `-> none` - so whatever it wants is something else, or nothing it looks
for in IOKit is the blocker at all.

**Standing rule, earned twice now:** compare *behaviour* (call sequences,
thread states), never counters alone. presents/`nonblack`/`distinct` have each
misled at least one conclusion.


### >>> 2026-11-03 (51): sweetgpuok inflates presents and changes no pixels <<<

Controlled A/B with the now-trustworthy observer (banner-checked both runs),
identical cmdline except for the switch:

| | GPU methods | presents | distinct |
| --- | --- | --- | --- |
| no `sweetgpuok` | `2` -> unsupported, **connection closed** | **36** | 5 |
| `sweetgpuok=1` | 2, 0, 4 ok, then 33 x22 | **88** | 5 |

**Same picture, more than twice the submissions.** `sweetgpuok=1` tells
backboardd its GPU calls succeeded, so it submits the same already-black image
more often. The counter rises; no pixel changes.

So entry (45)'s "selector 2 is a gate" is true in the narrow sense - userland
does go further - and **had no bearing on the picture**. "Goes further" was
never "moves toward an image", and earlier entries implied otherwise.

**Consequence for the images:** `shim-proven.img` had been built with
`sweetgpuok=1`, i.e. the "proven" configuration was the one with the fake
success in it. It now carries the honest build (`c78ef4e2c6d0ef99`, no
sweetgpuok); `shim-bisect-on.img` keeps the probe.

**Standing fact, now measured with a trustworthy instrument:** with the GPU
service opened and every call answered either way, the panel stays at
`distinct=5` and `presents` between 36 and 88. The GPU is not what is drawing,
and answering its methods success does not make it draw.


### >>> 2026-11-03 (50): the measuring tools were lying, twice <<<

Neither entry changed a pixel. Both changed how much the other entries can be
trusted.

**1. `shim-proven.img` did not contain the current kernel.** Its banner was
`19:01:48` while the tree built `19:43`. Every boot I called "proven" from that
file was running a kernel 40 minutes older than the source being edited.
Rebuilt; `shim-proven.img` and `shim-bisect-on.img` now both read
`c721b54dc8a162c2`, banner `19:43:28`.

**2. `tools/sweet-observe.sh` could report a previous boot as this one's.**
The log pull ended in `|| true`, so a failed pull left `$out` holding the
*earlier* log, and every counter printed afterwards (`progress markers`,
`panel counters`, `GPU lookups`, `log lines`) was computed from it - silently.
That is the worst failure mode for an instrument: the output looks like
evidence.

Fix: `rm -f "$out"` before pulling; exit 4 if the pull fails or produces an
empty file; and compare the kernel banner in the log against the banner inside
the image (the check `fastboot-cycle.sh` already had and this script did not),
exiting 3 on mismatch.

`tests/test_observe.py` (7 checks) asserts all of that from the source so it
cannot regress unnoticed; `tests/run-all.sh` picks it up automatically.

**Why this matters more than it looks:** several earlier entries concluded
things from these tools - "the panel never changes", "presents climbed to 98",
"the GPU is never opened". Those conclusions were drawn from logs I cannot now
prove came from the run they were attributed to. They should be re-measured
before anyone builds on them.


### >>> 2026-11-03 (49): HFS+ reader - works for listing, still wrong for records <<<

`tools/hfs-read.py` (uncommitted): reads the iOS root straight off
`/dev/block/by-name/userdata` over `adb dd`, because TWRP on this phone has no
HFS support. Useful as it stands for one thing - locating a file:

```text
python3 tools/hfs-read.py find dyld_shared_cache_arm64
  -> cnid=326127 parent=322858
python3 tools/hfs-read.py list /private/var
```

A full catalog walk returns **323,281 entries in 17 s**.

**What is proven about the format:**
- volume header at byte 1024; block size 4096; 16 GiB
- catalog file: start block 181633, 32768 blocks; nodeSize 8192 (`hdr[32:34]`)
- root node 264, height 3
- node kinds: 0 = index, 255 (-1) = leaf
- record k of a node spans `[offs[nrec-1-k], offs[nrec-k]]`
- the key is followed by the data *directly* - there is no 4-byte offset field
- index records carry the child node as 4 bytes right after the key
- leaf keys: parentID(4) + nameLen(2) + UTF-16BE name

**What is proven WRONG:** the file-size field. `.journal` reads 4194304 at
`+56` and that looked like a rule, so the size was taken from there - but the
`dyld_shared_cache_arm64` record then showed ASCII `hlnkhfs+` at `+48` and
`0x0100000000000000` at `+56`. That string cannot occur inside a catalog file
record, so **for that node the 248-byte record boundaries are wrong too**.
Conclusion: record slicing is only verified on the leaf node that holds the
HFS+ private files (12490); elsewhere it is unproven, and `cat` must not be
trusted until this is settled.

**Performance note, because it cost five rounds:** reading one node per
`adb dd` made a full walk look like a hang or an infinite loop. Batching 256
nodes per read turned it into 17 s. Before concluding a loop is broken, time a
minimal case - the earlier "no output" runs were timeouts, not logic errors.

**Guesses, marked as guesses:** that `+40` is allocated bytes; that the
dataFork logicalSize is somewhere in 88..96 per the public struct layout. Both
contradicted by the data above. Do not build on either.

**Status of the objective itself:** unchanged by any of this. The iOS system
boots and runs on hardware (see entry (47)); the panel shows no UI because
`method 33` command buffers are submitted and never executed.


### >>> 2026-11-03 (46): selector 33 is a command-buffer submission, and that is a wall <<<

Logged the scalar arguments of the GPU methods (entry 45 guessed at what 33
was; this measures it). One boot, 22 calls:

```text
method 33 (2 in, 0 out) in0=1104320000 in1=320000
method 33 (2 in, 0 out) in0=1104640000 in1=320000
method 33 (2 in, 0 out) in0=1104960000 in1=320000
method 33 (2 in, 0 out) in0=1105280000 in1=320000
...
method 33 (2 in, 0 out) in0=1603840000 in1=320000
```

**`in1` is 320000 (0x4E200) on every single call**, and `in0` is monotonically
increasing from 1,104,320,000 to 1,603,840,000 - a 500 MB span. The first three
deltas are *exactly* `in1`.

That is not a query and not a frame. `in0` is a low user-space address
(`0x41d29600`-class, nothing like the kernel's `0xfffffe…`), `in1` is a fixed
320 KiB, and the addresses advance by the allocation size: this is userland
handing the driver a **command buffer** and asking for it to be executed.

**Consequence, stated plainly:** making the UI appear now requires *executing*
AGX command streams - parsing the queue format, decoding the commands and
rendering them. That is a real GPU driver, not a shim. Nothing in this session
- and nothing in the tree - gets close to it; the whole display path so far
works because the panel is a linear framebuffer that CoreAnimation's CPU
renderer can write directly.

**What is *not* proven:** that accepting selector 33 and doing nothing is
harmless, which is what `sweetgpuok=1` currently does. It reports success while
discarding the work, so userland believes every buffer was executed. That is
acceptable as a probe but must not ship as a default.

**Where the port stands, without overstating it:**

| layer | state |
| --- | --- |
| kernel, UFS, HFS+, launchd, 281 processes | works, verified on hardware |
| SpringBoard | runs; threads park normally (block ring: 319,295 blocks, no deadlock) |
| framebuffer + IOSurface + swap | works - 16 full-panel BGRA swaps per boot |
| AGX service, connection, selector gate | works (entries 44, 45) |
| **command-buffer execution** | **absent - this is the wall** |


### >>> 2026-11-03 (45): the first GPU question was a gate - succeeding opens the rest <<<

Entry (44) got the service opened but backboardd asked **one** question
(`method 2`, no args, no outputs), got `kIOReturnUnsupported`, and closed the
connection on the next line. A failing first question proves nothing about the
ones behind it, so added **`sweetgpuok=1`**: every method returns
`kIOReturnSuccess` with outputs left zeroed. It is a probe, not a fix.

The difference is decisive. Without it:

```text
open AGXAccelerator type 1 -> 0x0
method 2 (0 in, 0 out) -> unsupported
user client closed                    <- gives up immediately
```

With `sweetgpuok=1`:

```text
method 2  (0 in, 0 out) -> ok         <- the gate
method 0  (0 in, 0 out) -> ok
method 4  (0 in, 0 out) -> ok
method 33 (2 in, 0 out) -> ok   x29   <- the real workload
user client closed: 0 occurrences     <- stays open for the rest of the boot
```

**So selector 2 is a gate**: answer it and userland proceeds to 0, 4 and 29
calls of 33. Refuse it and nothing else is ever asked. That is why every
previous round saw exactly one GPU method call and concluded the GPU was
unused.

**Still not visible:** `presents` 177, panel still `distinct=5`. The workload is
now known - 33 is called with two scalars and no outputs, so it is a
submit/signal call, not a query - but nothing has been implemented behind it.

**Next, concretely:** `method 33` is where the work is. Log its two scalar
arguments, and find out whether it is arriving per-frame (29 calls in a boot
with 177 presents is consistent with once per swap or less often) or a one-off
setup.


### >>> BREAKTHROUGH 2026-11-03 (44): backboardd wanted AGXAccelerator, not IOAcceleratorES <<<

Entry (45) ended without a conclusion because `-> notify` looked like a failed
match and I refused to build on that without checking it. Reading the code
settled it, and the answer was not what either of us assumed.

**`notify` is not a match result at all.** In
`internal_io_service_get_notification_matching`, `sweet_iolog_dict(...,
"notify")` is a *hard-coded* label printed when a notification is registered -
it says nothing about whether a service was found. The real signal is the pair
`matching1` (found) / `matching1 MISS` (not found), produced by
`internal_io_service_get_matching_services`.

With the right vocabulary, a boot shows exactly six failed lookups:

```text
IOK backboardd: matching1 MISS IOProviderClass=AGXAccelerator      -> none
IOK backboardd: NEVER FOUND class AGXAccelerator
IOK backboardd: matching1 MISS IOProviderClass=ApplePearlSEPDriver -> none
IOK backboardd: NEVER FOUND class AppleM2ScalerCSCDriver
```

**backboardd asks for `AGXAccelerator`.** `IOAcceleratorES` - the name the
earlier investigation settled on, and which entry (34) built a UserClient for -
is matched 218 times and opened **zero** times, because it is simply not what
anything looks for. It was never the blocker.

Fix, in two places:

- `class AGXAccelerator : public IOAcceleratorES` in `SweetFramebuffer.cpp`,
  inheriting the stub unchanged (io class name AGXAccelerator, every user
  method still returns an error)
- an entry in `iokit/KernelConfigTables.cpp` so the class is instantiated

Result (`research/breakthrough/agx-found.txt`):

```text
SWEET GPU: AGXAccelerator published (stub)
IOK backboardd: matching1 ... IOProviderClass=AGXAccelerator -> AGXAccelerator
SWEET GPU: user client opened
IOK backboardd: open AGXAccelerator type 1 -> 0x0
SWEET GPU: method 2 (0 in, 0 out) -> unsupported
```

**NEVER FOUND is gone, the service opens, and userland issues method 2.** That
is the first time anything has opened a GPU service on this port.

**Still not visible:** `presents` rose to 217 (from ~104-155) but the panel is
still `distinct=5`, one colour. Now that the method calls are logged, the next
step is concrete: implement the handful of selectors that actually appear
instead of guessing which ones matter.


### >>> 2026-11-03 (43): the block ring resolves - no deadlock, the machine is just idle <<<

The block ring (`sweet_block_trace`, entry 41) had been recording all along but
was only ever *cleared*, never printed, because printing from the block path
hung the boot. Added `sweet_block_ring_report()`, gated by `sweetblockring=1`,
and drove it from the **log thread** - after first trying the watchdog tick and
finding the same trap as everywhere else: `sweet_dump_tick()`'s callback ran
**exactly once** per boot even though `tick=130732`. The log thread reaches the
last line of the log (13,094 scsi ops), so it is the only reliable 1 Hz context
this boot has.

Output (`research/breakthrough/block-ring.txt`):

```text
SWEET BLOCKRING: 319295 blocks total, showing 256
```

**319,295 thread blocks** - the system is very much doing work. Resolving the
last 256 continuations against `llvm-nm -n` of the kernel:

| continuation | meaning |
| --- | --- |
| `_ipc_mqueue_receive_continue` | waiting for an IPC message |
| `_thread_preempted` | preempted by the scheduler |
| `_mpsc_queue_thread_continue` | parked waiting for work |
| `_workq_unpark_continue` | kernel workqueue thread idle |
| `_thread_call_thread` | kernel thread_call idle |
| `_serial_keyboard_poll` | hardware polling |

**Every one is an ordinary park point. There is no deadlock, no stuck lock, no
missing wakeup.** SpringBoard's threads sitting on `QUEUE`/`TURNSTILE` in entry
(42) are waiting for work that would arrive if anything produced any - the
renderer has nothing to composite because `IOAcceleratorES` is still a stub
(entry 34).

**So the architecture is sound and the remaining gap is exactly what entry (34)
said it was:** a UserClient behind `IOAcceleratorES`. The last five entries were
chasing a stall that does not exist.

**Method note worth keeping:** the watchdog tick *looked* alive (`SWEET HB` with
`tick=130732`) but its callback fired once. Two rounds were spent hooking things
onto it. Before trusting a periodic hook, count how many times it actually runs.


### >>> 2026-11-03 (42): correction - SpringBoard runs, *then* stops; 20 samples say when <<<

Entry (41) concluded "SpringBoard is running, not stuck" from **three**
samples. That was too few to see the rest of the boot. `sweet_dump_threads_soon()`
stopped after `round < 3`, so made the count and the pacing boot-args
(`sweetdumprounds`, `sweetdumpevery`; defaults reproduce the old behaviour) and
ran 20 samples:

```text
thread count per sample:
1 1 1 1 1 2 2 2 3 5 5 8 8 8 6 6 5 5 5 5
```

It climbs to 8, then **falls to 5 and stays there**, and in the final sample
**every thread is `run=0`**:

```text
tid=222 run=0 state=1  wq=PORT
tid=338 run=0 state=1  wq=QUEUE
tid=462 run=0 state=1  wq=QUEUE
tid=466 run=0 state=41 wq=TURNSTILE
tid=474 run=0 state=1  wq=QUEUE
```

| sample | threads running |
| --- | --- |
| 3 (what entry (41) saw) | 6 of 10 |
| **20 (end of boot)** | **0 of 5** |

So the correct statement is: **SpringBoard starts up, creates threads, then all
of them go to sleep on QUEUE/TURNSTILE/PORT and none wakes.** Entry (41)'s
"running, not stuck" is right only for the middle of the boot; the end state is
stalled. The earlier framing was not wrong, it was **sampled too early**.

`tid=466` sitting on a `TURNSTILE` is the most specific lead so far: that is a
thread waiting on a lock or an IPC turnstile, not on a plain queue.

**Method note:** three samples 20 s apart looked conclusive and were not. The
round count is now a boot-arg so this cannot happen silently again.


### >>> 2026-11-03 (41): sweetdump was already in the tree - and SpringBoard is running, not stuck <<<

Spent three rounds (38-40) building a process watcher to answer "is SpringBoard
alive?", then found that **`sweetdump=Name` already existed** in
`osfmk/kern/task.c` and does the job far better:

- `sweet_dump_threads_soon()` arms a task at exec (from `kern_exec.c`)
- `sweet_block_trace()` records each `thread_block` into a lock-free 256-entry
  ring (tid, continuation, waitq type, event) - note in its comment: "printing
  here hung the boot (NOTES 20:50)"
- `sweet_dump_tick()`, called once a second from the watchdog, walks the task's
  threads and prints `tid`, `run`, `state`, `wq` and the wait message count

Booted with `sweetdump=SpringBoard`. The answer contradicts what the last three
rounds assumed:

```text
SWEET THREADS: SpringBoard sample 1, threads=1
SWEET THREADS: SpringBoard sample 2, threads=1
SWEET THREADS: SpringBoard sample 3, threads=10
SWEET THREADS: SpringBoard tid=222 run=0 state=1 wq=PORT mask=1181c80 msgs=0/0
SWEET THREADS: SpringBoard tid=289 run=1 state=4     <- running
SWEET THREADS: SpringBoard tid=327 run=1 state=4     <- running
SWEET THREADS: SpringBoard tid=344 run=1 state=4     <- running
SWEET THREADS: SpringBoard tid=529 run=0 state=41 wq=TURNSTILE
SWEET THREADS: SpringBoard tid=530 run=0 state=1 wq=QUEUE mask=69d1fe8
SWEET THREADS: SpringBoard tid=531 run=1 state=4     <- running
SWEET THREADS: SpringBoard tid=533 run=1 state=4     <- running
SWEET THREADS: SpringBoard tid=535 run=1 state=4     <- running
SWEET THREADS: SpringBoard tid=536 run=1 state=4     <- running
```

**Six of its ten threads are `run=1 state=4` (running).** Thread count went
1 -> 10. Only `tid=222` (the main thread) parks on `PORT` with an empty
message queue, which is what a main thread waiting for the first UI event
looks like.

**So SpringBoard is not stalled and not crashed - it is doing work.** That
invalidates the framing of entries (36)-(40), which all assumed it stopped
making progress. What it is *not* doing is presenting UI, and the earlier
finding that `IOAcceleratorES` is a stub with no UserClient (entry 34) remains
the best explanation for that.

**Lesson for the next round:** before building an instrument, grep the tree for
one. `sweetdump`, `sweetblock`, `sweetiolog` and the block ring were all
already here; rounds 38-40 rebuilt a worse version of the first.


### >>> 2026-11-03 (40): four more hypotheses for the watcher's death, all wrong <<<

Tried to explain why an ordinary `tsleep` kthread stops after ~30 s while
`vsync` (IOTimerEventSource) keeps firing, `SWEET HB` keeps counting to
`tick=129502`, and the log thread keeps doing scsi I/O to the end.

| hypothesis | test | result |
| --- | --- | --- |
| local `static event_t chan` was a zero-valued event | moved to a file-scope `int` | **still beat=15** |
| `thread_deallocate` freed a thread that never exits | compared with `sweet_log_thread`, which uses the identical idiom and survives | not it |
| `proc_list_lock()` deadlocks inside the scan | moved the heartbeat **before** the scan | **still beat=15**, so the loop is what stops, not the scan |
| the scan itself (even lock-free) is the blocker | replaced the locking walk with a lock-free one | **still beat=15** |

The moved heartbeat is the useful part: with the beat printed *before*
`sweet_proc_watch()`, exactly one beat (`beat=15`) still appears, so the
question is "why does the loop stop spinning", not "why does the scan hang".
That narrows it to the thread itself ceasing to be scheduled after ~15
iterations.

**Still true and useful:** `SWEET PROC: ... (t=20)` appears in every run, so
SpringBoard is confirmed alive at that point; and the SYNC CACHE fix from
entry (39) keeps the ring writing to the end of the boot.

**Not concluded:** whether this is one bug or two. The watcher (our kthread)
and SpringBoard (a userland process) both stop progressing in the same window,
but that is a correlation with no mechanism attached yet.


### >>> 2026-11-03 (39): the watcher thread dies around t=30 - measured, not guessed <<<

Entry (38) left the watcher reporting only to `t=20`. Five runs had stopped at
the same tick, so instead of trying a sixth wait idiom, an **unconditional
heartbeat** was added to distinguish "thread dead" from "nothing to report":

```c
static uint32_t beat;
if ((++beat % 15) == 0) {
	printf("SWEET PW: alive beat=%u\n", beat);
}
```

Result (`research/tmp/observe-beat.txt`): **exactly one heartbeat, `beat=15`**,
i.e. the thread ran to about 30 s and then stopped - while the system kept
running `exec` for another ~70 s, with no panic, no assert, no exception.

So the thread does not "fall silent"; it **ends**. And it is not the wait
idiom: four variants behaved identically.

| wait used | last report |
| --- | --- |
| `assert_wait_deadline` + `thread_block`, 2 s | t=20 |
| same, 2000 ms corrected | t=20 |
| same, `THREAD_UNINT` | t=20 |
| `tsleep(&chan, PZERO, "sweetpw", hz*2)` | beat=15 (~30 s) |

**Also fixed and kept:** `sweet_log_sync_cache()` no longer aborts the flush
when SYNC CACHE (`0x35`) fails with OCS `0xf`. That failure used to stop the
ring at line ~4660 of every boot, exactly when the boot became interesting;
the data is already in the controller cache and TWRP only needs that, so the
error is now reported once and ignored. The ring now writes to the end.

**What this rules out for SpringBoard's stall too:** the watcher and
SpringBoard both stop making progress within the first ~30 s, and the watcher
is under our control with no userland involvement. That makes "something in
the kernel stops scheduling kthreads after ~30 s" a live hypothesis, separate
from anything in the GPU or the device tree.


### >>> 2026-11-03 (38): a process watcher that actually keeps running <<<

SpringBoard's silence could mean "crashed" or "alive and stuck", and the log
could not tell the two apart. Built a watcher that walks `allproc` and reports
whether the interesting processes exist, and had to fix **three** broken
placements before it ran continuously:

| placement | what went wrong |
| --- | --- |
| UFS log thread | `SWEET LOG: write failed (5), stopping` - the thread exits for good on the first EIO, taking the watcher with it |
| watchdog heartbeat (`sweet_wdt_sample`) | the hook was only ever observed to fire **once** per boot (`SWEET HB: 1 ... tick=132004`), so the watcher reported at `t=1` and never again |
| **own kernel thread** | works: reports at `t=3, 10, 20, ...` from a 2 s sleep loop it controls |

Result (`research/breakthrough/proc-watch-works.txt`):

```text
SWEET PROC: SpringBoard gone    (t=1)
SWEET PROC: backboardd gone     (t=1)
SWEET PROC: SpringBoard present (t=3)
SWEET PROC: backboardd present  (t=5)
SWEET PROC: SpringBoard present (t=10)
SWEET PROC: backboardd present  (t=10)
SWEET PROC: SpringBoard present (t=20)
SWEET PROC: backboardd present  (t=20)
```

**So SpringBoard is alive, not crashed.** It exists from `t=3` onward and stays
in `allproc`. Combined with entry (36)/(37) - it opens `AppleKeyStore` and
`IOPMrootDomain`, queries `/arm-io` thirteen times, then produces no further
tracer output - the picture is a process **blocked**, not a process gone.

Also worth recording, because it cost the most time this round: while moving
the watcher around, `sweet_ufs.c` was cut down to 269 lines by a bad
line-range edit (the file lives in the git-ignored `.deps-cache` tree, whose
git copy is only the 823-line patch baseline). It was reassembled from a
`/tmp` copy plus the git baseline and a rebuilt tail, and then repaired function
by function (`dma_sync`, `ufs_wr`, `ufs_rd` had to be re-inserted). The file
now compiles clean, but **the lesson is to copy a file before any line-range
surgery on it** - `cp` is cheaper than reconstruction.

**Next:** the watcher gives liveness but not a stack. To see *what* SpringBoard
is blocked on needs either a `proc`-level stack sample from the kernel or an
equivalent traced syscall.


### >>> 2026-11-03 (37): the 400-line trace cap was a red herring - SpringBoard really stops <<<

Entry (36) concluded "SpringBoard stops at line 10866". That conclusion was
immediately suspect, because `sweet_iolog()` used a **single global budget of
400 lines**, and backboardd (matching `IOAcceleratorES` in a loop) had used
369 of them. A silent SpringBoard could have been a starved one.

Checked and fixed the instrument rather than trusting either reading:

- **Measured**: SpringBoard 33 lines, backboardd 369, total 402 - the cap was
  hit at line 13150, so the suspicion was justified.
- **Changed** `sweet_iolog()` in `IOUserClient.cpp` to a **per-process** budget
  (300 lines each, up to 8 tracked names) held in a fixed-size table. The
  first attempt used a string-packed `name=count,...` buffer and was rewritten
  before building: `strchr(p, '=') - p` underflows when the `=` is absent.
- **Re-measured** with kernel `51605ab8`, boot-arg `sweetiolog=SpringBoard,backboardd`:

```text
SpringBoard IOK:  33 lines   (last at line 9435)
backboardd  IOK: 302 lines
```

**SpringBoard still emits exactly 33 lines with the cap no longer shared.** So
entry (36) was right after all: the process genuinely stops after opening
`AppleKeyStore` and `IOPMrootDomain` and querying `/arm-io` thirteen times.
The global cap was a real defect in the instrument, but it was not hiding
anything.

A side effect worth noting: `presents` rose from 71 to **177** in this run with
16 swaps still, i.e. backboardd is compositing more often. That is progress
without any rendering change, so it is likely timing/load variance rather than
a fix - not evidence of anything.

**Where that leaves the port:** iOS boots, 281 processes exec, SpringBoard
starts, opens two services, queries the device tree, and stops. The UI stays
five colours. The next useful instrument is not more device-tree logging but
the stack SpringBoard is sitting in - the IOK echoes say what it asked for,
never what it is waiting on.


### >>> 2026-11-03 (36): SpringBoard stops before it ever renders, and the ADT has no GPU node <<<

Entry (35) corrected the claim that "the GPU is the proven root cause". This
round located where SpringBoard actually stops, using the 180 s observation
(`research/breakthrough/observe-180s.txt`, 16,764 lines).

**SpringBoard's whole visible life** is lines 10,546-10,866. It opens exactly
two services and then goes silent:

```text
open AppleKeyStore            -> 0x0
open IOPMrootDomain           -> 0x0
path IODeviceTree:/arm-io     -> IOPlatformDevice     x13
path IODeviceTree:/product    -> IOPlatformDevice     x12
path IODeviceTree:/buttons    -> IOPlatformDevice
path IODeviceTree:/arm-io/pearl-sep -> none
path IODeviceTree:/product/camera   -> none
```

Nothing after line 10,866 mentions SpringBoard. Meanwhile the rest of the
system keeps running: `securityd`, `accountsd`, `mobileactivationd`, `tccd`
all start later, and `SWEET HB: 1 wdt=1 tick=132654 ... call=321` shows the
heartbeat thread is alive. So SpringBoard is not a crashed system - it is a
process that stopped making progress **before** submitting any render work.

**The ADT has no GPU node.** Parsed `shim/out/sweet-gauguin-new.adt`:

```text
device-tree
  chosen / defaults / cpus(cpu0..7)
  arm-io:   gic, wdt, disp0          <- no accelerator
  sweet-fbcon, buttons, backlight, product, sweet-ufs
```

So the `IOAcceleratorES` stub is not merely "missing a UserClient" (entry 34):
**there is no device-tree node for it either**. SpringBoard queries `/arm-io`
thirteen times and every lookup returns the generic `IOPlatformDevice`, because
`SweetPlatformExpert::createNubs()` publishes every ADT node under that single
class.

**What this changes:** a software compositor behind `IOAcceleratorES` would
still not address why SpringBoard is silent. The specific unanswered question
is *which* node/service SpringBoard is looking for and not finding - the
repeated identical `/arm-io` lookup is the strongest lead, and it needs a
strace-equivalent rather than more inference from device-tree echoes.

**Honest status:** iOS boots, 281 processes exec, SpringBoard starts and stops
before rendering. The UI is blank. The root cause is narrowed but **not
established**, and the two theories so far (missing accelerator, missing ADT
node) are hypotheses that the log does not yet separate.


### >>> 2026-11-03 (35): measured with a 180 s window - the system keeps running <<<

`tools/fastboot-cycle.sh` waits 20 s and then treats "TWRP appeared" as "the
kernel died", which is the wrong assumption for a kernel that reaches
userland. Added **`tools/sweet-observe.sh IMAGE OUT [SECONDS]`**, which boots
the image and then watches for the full window, reporting the progress markers
and the panel counters at the end.

Run for 180 s (`research/breakthrough/observe-180s.txt`, 16,764 lines):

| marker | |
| --- | --- |
| `init complete` | yes |
| `BSD root` / `mounted iOSRoot` | yes |
| `exec launchd` / `ignition sequence complete` | yes |
| `exec SpringBoard` / `exec backboardd` | yes |

The phone came back to TWRP at **100 s**, i.e. the kernel did stop on its own
rather than being cut short by the script.

**But "stopped logging" is not "stopped running".** After the last
`vsync=4200` line there are still **154 `scsi 0x28` reads** plus `0x2a` writes
and `0x35` syncs - the system keeps doing filesystem I/O right up to the end of
the ring. The ring did not wrap (it starts at the kernel banner), so those
lines are genuinely later in time.

That fits entry (34) exactly: the machine is alive and working, the compositor
submits full-panel BGRA swaps (`presents=71`, 16 swaps), and the content is
still five colours because there is no accelerator to draw with. vsync stops
printing because the panel stops changing, not because the kernel died.

**So the state of the port is: iOS boots, launches 281 processes, runs
SpringBoard, and has nothing to render with.** The next real step is a
UserClient behind `IOAcceleratorES` (a software compositor is the tractable
option; AGX for this Adreno class is not).


### >>> 2026-11-03 (34): the GPU stub is never *opened* - it has no UserClient <<<

Following entry (33), the decisive evidence is what backboardd opens versus
what it only matches by name.

**Services backboardd actually opens** (`IOK backboardd: open X -> 0x0`):

```text
AppleCLCD            <- the framebuffer, works
AppleKeyStore        <- works
IOCoreSurfaceRoot    <- IOSurface root, works
IOPMrootDomain       <- power, works
SweetHIDButtons      <- works
SweetHIDTouch        <- works
```

**Services backboardd only *matches*** (`IOServiceFirstMatch ... -> found`):
`IOAcceleratorES`, 284 times, and never an `open`.

That asymmetry is the answer. `IOService::registerService()` on a bare
`IOService` publishes the *name*, so `IOServiceFirstMatch` finds it - that is
what stopped the old segfault. But every familyd/backboardd GPU path needs a
**UserClient** to talk to the driver, and `IOAcceleratorES` declares none
(`class IOAcceleratorES : public IOService` with only `start`/`stop`). So
backboardd never opens it and the render server has nowhere to submit work.

**The framebuffer path is not the problem.** All 16 swaps in the log are full
panel `1125x2436 BGRA`, `bpe == 4`, and the copy loop in
`IOMobileFramebufferUserClient` runs. The pixels arrive; they are just empty.
The `nonblack` count tells the story:

| vsync | nonblack | distinct | meaning |
| --- | --- | --- | --- |
| 2 | 993 | 2 | the boot logo |
| 1800 | 488 | 1 | logo fading out |
| 4200 | 72 | 5 | background only - no UI |

**What this rules out:** the display pipeline, the swap record, the surface
plumbing and the colour format are all fine. **What it leaves:** either a real
accelerator (`AGXAccelerator` for this Adreno 619 class, a very large job), or
a UserClient-based software compositor behind `IOAcceleratorES`.

Note for whoever picks this up: adding a UserClient that returns errors is
*not* automatically better than none - the current stub at least keeps
backboardd from crashing. Any change here needs to be measured against the
`presents`/`nonblack` counters, which is what these two entries did.


### >>> 2026-11-03 (33): why SpringBoard runs but shows nothing - the GPU is a stub <<<

Analysed `research/breakthrough/boot-reaches-springboard.txt` line by line.
SpringBoard is genuinely alive, but the screen never gets real content, and the
reason is visible in one line of the log:

```text
SWEET GPU: stub IOAcceleratorES published
```

**The framebuffer timeline** (`SWEET FB: vsync=N ... presents=P client=C`):

| vsync | presents | client | nonblack | distinct |
| --- | --- | --- | --- | --- |
| 2 - 2400 | **0** | 0 | 993 -> 493 | 2 -> 1 |
| 3000 | 26 | 2 | 60 | 5 |
| 3600 | 105 | 2 | 60 | 5 |
| 4200 | **110** | 2 | **72** | **5** |

So for the first 2400 vsync intervals **nothing presented at all**; then
backboardd appeared as `client=2` and started presenting - but the content is
essentially a single colour (5 distinct, 72 non-black pixels, sampled
`0x1006` = `#100030`, a dark violet). That is SpringBoard drawing its
background with no composited UI on top.

**`IOAcceleratorES` is matched 284 times by backboardd and is a stub**
(`SweetFramebuffer.cpp`, `IOAcceleratorES::start()` sets `stub=true` and just
publishes the service). iOS composites through Metal/IOGPUSurface; with a stub
accelerator there is nothing to composite with, so the home screen never
appears. The comment in that file records the earlier symptom it was added for
("backboardd looks up IOAcceleratorES, gets 0 found, and then segfaults"), so
the stub kept `backboardd` alive but cannot draw.

**The iOS root itself is healthy.** Read back over adb from TWRP:
`dd if=/dev/block/by-name/userdata bs=1024 skip=1 count=1` gives the volume
header `HX` (HFS+), version 5, attributes `HFSJ` (journaled). TWRP cannot mount
HFS+, so this signature read is the check.

**So the remaining work is rendering, not boot:** either give iOS a working
accelerator path, or make backboardd/SpringBoard fall back to software
compositing. That is a different problem from everything the last 30 rounds
were chasing, and it is the blocker between "userland runs" and "iOS is
usable".

Also noted: `CRASH driverkitd[67] sig 9` (killed, not a fault) and
`UMD_INIT: ... persona ... No such process` (no SEP; expected on this port).


### >>> BREAKTHROUGH 2026-11-03 (32): iOS userland runs, SpringBoard executes <<<

**The phone came back and the boot now reaches SpringBoard.** After 28 rounds
without a device, `tools/bisect-keys.sh` was run against the staged pair and
**both images mounted the root and reached userland**:

```text
sweetkeys=0  reached: userland
default      reached: userland
verdict: both_mount
```

Log preserved as `research/breakthrough/boot-reaches-springboard.txt`
(15,987 lines, 778 KB).

**What the boot does now**, in order:

| stage | evidence in the log |
| --- | --- |
| UFS init tail | `sample_start` -> `keys_init` -> `touch_init` -> `usb_probe` -> `init complete` |
| root mount | `BSD root: ufsroot0`, `hfs: mounted iOSRoot on device b(1, 0)`, `vfs_mountroot ok` |
| exec | `exec launchd`, `Darwin Bootstrapper Version 7.0.0` |
| ignition | `ignition sequence complete`, dyld shared cache opened from `/System/Library/Caches/com.apple.dyld` |
| launchd tasks | mount-phase-1/2, data-protection, finish-obliteration, MSUEarlyBootTask |
| **processes** | **281 `exec` lines**, incl. `backboardd`, **`exec SpringBoard`** |
| **framebuffer** | `SWEET FB: ... nonblack=72 distinct=5 presents=110 client=2` - **pixels are being drawn** |

SpringBoard is not merely spawned: it opens `AppleKeyStore` (AKS selects 0/35/7
all return 0x0), `IOPMrootDomain`, and `IODeviceTree:/buttons`.

**This means the `keys_init` stall that defined the last 30 rounds is gone.**
The most likely cause is the touch-bring-up delay restored in entry (28): the
bring-up had been starting immediately, putting GENI/TLMM/RPMh traffic on the
buses during `vfs_mountroot`. That is consistent with the log, which now shows
`SWEET TOUCH: starting in 45 s` while the root mounts.

**Both `sweetkeys=0` and the default work**, so the keys driver was never the
blocker - correct diagnosis, wrong suspect.

Remaining rough edges, all non-fatal:
- `shared_region: ... 'dyld_shared_cache_arm64' : not in trust cache` (expected: SWEET has no trust cache; the cache still maps and dyld runs)
- `ERROR: BindFS bindfs_mount: lookup of /private/preboot/... failed error: 2` (no preboot volume)
- `mount: data volume missing, but not required in env: 0`
- `libignition: ignition level insufficient: actual = 1, required >= 2/3` for preboot, cryptex1, graft (intended: `ignition_level=1`)

**Next:** confirm SpringBoard actually reaches a visible home screen / setup
screen rather than spinning, then work the remaining userland errors.


### >>> UPDATE 2026-11-03 (31): `shim-boot.img` was silently carrying the DSB variant <<<

Adding a provenance check to the toolchain (`tools/image-audit.py`, below)
immediately found a live hazard: **`shim/out/shim-boot.img` held the DSB
kernel**, left there by `deps/ab-keys-barrier.sh`. `deps/shim-macos.sh` always
writes that filename, and it is the name a person types into `fastboot`, so
the most natural way to boot the "current" image would have run the A/B
*variant* - quietly adding the very variable the experiment isolates.

Fixed in three places:

1. `deps/ab-keys-barrier.sh` now restores `shim-boot.img` from
   `shim-proven.img` when it finishes.
2. `shim-boot.img` was restored by hand (it equals `shim-proven.img`,
   `44f358d7`).
3. `tools/image-audit.py` prints each live image's kernel build banner, read
   out of the packaged file, and with `--check KERNEL` fails when
   `shim-proven` / `shim-bisect-on` / `shim-bisect-off` were built from a
   different kernel than the one given.

The audit deliberately does **not** flag `shim-ab-dmb` / `shim-ab-dsb` for
being built from different kernels - that difference is the experiment, and
`tests/test_ab_variants.py` checks it is the *only* difference. It also only
looks at the five live images: `shim/out` holds 100+ historical ones, and
listing them buried the answer.

`tests/test_image_audit.py` pins all of this (5 checks), including that a
genuinely stale bisect image still fails.

**Twenty-nine rounds, no phone.**


### >>> UPDATE 2026-11-03 (30): the A/B images were stale - rebuilt, and a test-gate conflict fixed <<<

Auditing the artifacts against the notes turned up a real problem: the two
`shim-ab-*` images were built in entry (26), **before** the touch delay was
restored in entry (28). Booting them would have started the touch bring-up
immediately again, adding a second variable to an experiment whose whole point
is that only one thing differs.

Two fixes:

1. **Rebuilt both variants** with the current tree. They now carry the touch
   delay (`SWEET TOUCH: starting in` is present in both kernels) and
   `tests/test_ab_variants.py` confirms they still differ only in the barrier
   opcode at `0x4e1818`.
2. **`deps/ab-keys-barrier.sh` now builds with `SKIP_TESTS=1`.** The build gate
   added in entry (24) runs `tests/test_ab_variants.py`, which compares the two
   A/B kernels - so it can only pass once both exist. Building the second
   variant therefore failed on a test whose subject was the build in progress.
   The script checks the pair itself after the second build and fails if they
   are byte-identical, so the protection is kept, just moved to where it can
   work.

| file | kernel | image |
| --- | --- | --- |
| `shim/out/shim-proven.img` = `shim-bisect-on.img` | `aeffcfe7` | `44f358d7` |
| `shim/out/shim-bisect-off.img` (`sweetkeys=0`) | `aeffcfe7` | `bea2aa03` |
| `shim/out/shim-ab-dmb.img` | `9fa9c82b` | `0d271de2` |
| `shim/out/shim-ab-dsb.img` | `ac057dbb` | `f1e2d8e8` |

All four use the working boot line; the three non-`bisect-off` kernels agree on
everything except the one variable each pair is testing.

**Lesson worth keeping:** artifacts decay when the tree moves under them. The
notes recorded image hashes, but nothing checked them against the kernel they
were built from - that check is what caught this, and it is now part of the
audit rather than an accident.

**Twenty-eight rounds, no phone.**


### >>> UPDATE 2026-11-03 (29): the working log has been swept end to end <<<

Entry (28) found one real departure (the touch start delay) by reading a
different window of `boot-journaled-userland.txt`. This round the remaining
windows were swept the same way, so that the next session does not repeat it.

**Early boot (lines 60-105)** - platform expert, AKS, WDT, SURF, HID, battery,
framebuffer, CPU bring-up, MAC/AMFI/Sandbox, `dlil_init`, `bsd_autoconf`,
`rootdev called`, `init reg`, host takeover. **No departure found**; the
current tree produces the same sequence and the same messages.

**Root mount to launchd** - `vfs_mountroot`, the touch delay (fixed in (28)),
a key event and its HID delivery, the HFS hotfile btree creation,
`hfs: mounted iOSRoot on device b(1, 0)`, `vfs_mountroot ok`,
`root volume is not authenticated (error 25); continuing unsealed`,
`VM Swap Subsystem is ON`, `load_init_program` x2, `exec launchd`,
`shared_region`, `SWEET Sandbox: launchd op 2`, libignition.

- The root-auth message comes from `bsd_init.c`'s `ARM64_BOARD_CONFIG_SWEET`
  branch, which reports and continues instead of panicking; the current tree
  has the same code and the same behaviour.
- `SWEET HID: buttons registered` / `touch registered` appear **before** the
  UFS init tail, i.e. the HID services match and start during platform
  bring-up, not from `sweet_keys_init()`. The current tree has the same
  structure (`SweetHIDButtons::start()` calls `registerService()`).
- The display identity (`1125x2436`, presented as the iPhone X panel over a
  1080x2400 framebuffer) is unchanged.

So after this sweep the known departures from the working boot are exactly
three, all now reverted: the init `sweet_log_sync()` calls (entry (5)), the
`cpus=8` boot line (entry (6)), and the immediate touch bring-up (entry (28)).
Everything else in the log's path matches the tree.

**Twenty-seven rounds, no phone.**


### >>> UPDATE 2026-11-03 (28): the touch bring-up was starting 45 s too early <<<

Found by reading the working log's root-mount window rather than the init tail
again:

```text
BSD root: ufsroot0, major 1, minor 0
SWEET boot: vfs_mountroot
SWEET TOUCH: starting in 45 s          <- held back on purpose
SWEET KEYS: key=1 down=1 pon=0x4 ...
SWEET HID: key 0xe9 down (0 clients)
hfs: mounted iOSRoot on device b(1, 0)
SWEET boot: vfs_mountroot ok
```

The boot that reaches launchd starts the touch bring-up **45 seconds late**,
which is also what the old note (2026-10-15, `0060` drivers) recorded: "starts
45 s after boot". In this session the bring-up was moved onto its own thread
and started **immediately**, so GENI, the TLMM and an RPMh vote all run
exactly while the root is being mounted - the window where a stall is fatal
and hardest to observe.

`touch_bringup_thread` now waits first (`sweettouchdelay`, default 45 s) using
the same `assert_wait_deadline` idiom as `sweet_keys.c` (`hz` is not visible
in this translation unit, which cost two build attempts). The wait is in the
thread, never on the init path.

This is the third change this session that was an unverified departure from
the working boot - after the init `sweet_log_sync()` calls (restored, entry
(5)) and the boot line `cpus=8` (restored, entry (6)). The pattern is the same
each time: the working log is the specification, and anything done differently
has to be justified by evidence this session does not have.

**Images rebuilt**: `shim-proven.img` = `shim-bisect-on.img` (`44f358d7...`),
`shim-bisect-off.img` (same except `sweetkeys=0`). Kernel `aeffcfe7...`.

**Twenty-six rounds, no phone.**


### >>> UPDATE 2026-11-03 (27): the A/B kernels are checked to differ in ONE instruction <<<

Entry (26) claimed the two variants differ only in the barrier. That claim is
now measured instead of asserted: the two kernels are the same length and
differ in **21 bytes**, in four regions, of which only one is code:

| offset | bytes | what |
| --- | --- | --- |
| `0x14a0` | 16 | `LC_UUID` / build identity - differs on every build |
| `0x3cf71` | 2 | the build-time seconds (`04` vs `12`) |
| `0x3cff1` | 2 | the same timestamp, second copy |
| **`0x4e1818`** | **1** | `bf` (dmb osh) vs `9f` (dsb osh) - **the only code difference** |

`tests/test_ab_variants.py` asserts exactly this: it names each differing
region, accepts the build identity and the timestamp, and **fails on any
region it cannot explain**. Run against the same kernel twice it fails with
"the barrier opcode actually differs", which is the check that matters - an A/B
pair that is secretly identical would waste a whole round.

Suite is now **39 checks** across four files; still wired into the build.

**Twenty-five rounds, no phone.**


### >>> UPDATE 2026-11-03 (26): the DSB/DMB A/B is built and ready <<<

Following entry (25), the experiment is prepared so it costs one boot each when
the phone returns.

`keys_read()`'s barrier is now `#ifdef SWEET_KEYS_USE_DSB ... #else dmb ...`
and **`deps/ab-keys-barrier.sh`** builds both variants, flipping the define in
the source (XNU has no extra-CFLAGS variable that reaches `bsd/dev`) and
restoring the file afterwards, even on failure.

Verified in the disassembly - the two `_keys_read` bodies differ by exactly one
instruction:

```text
dmb variant:  dmb oshst ; str w8,[x9] ; dmb osh  ; ... dmb oshld
dsb variant:  dmb oshst ; str w8,[x9] ; dsb osh  ; ... dmb oshld
```

| file | kernel | image |
| --- | --- | --- |
| `shim/out/shim-ab-dmb.img` | `6f54350a...` | `53508056...` |
| `shim/out/shim-ab-dsb.img` | `e7a429db...` | `a6d3f085...` |

Both use the working boot line and the working init sequence, so the only
variable is the barrier.

**How to use it:** boot each with `tools/fastboot-cycle.sh` and compare where
the init tail stops:

- both stop on `INIT: entering keys_init` -> the barrier is not the problem,
  and entry (14)'s reasoning was wrong; look elsewhere (SPMI ownership,
  arbiter state).
- `-dsb` stops there and `-dmb` does not -> keep `dmb` and the reasoning in
  (14) was right after all.
- `-dmb` stops there and `-dsb` does not -> restore `dsb`; the change made in
  (14) was a regression.

**Twenty-four rounds, no phone.**


### >>> UPDATE 2026-11-03 (25): correction - the dsb->dmb change has no evidence <<<

Entry (14) changed `keys_read()`'s `dsb osh` to `dmb osh`, arguing that a DSB
on a stalled SPMI fabric would never return. **That argument has no evidence
either way**, and this entry records it as such rather than letting it pass as
a finding.

What is actually known:

- `sweet_spmi.c` uses the **same** `dsb osh` idiom after issuing EXT_READL,
  and it is the older, previously working code path.
- But the successful boot's log shows
  `SWEET BATTERY: static fallback, 100% 4200mV` - which is the path taken when
  `sweet_spmi_init()` **failed early** (`arb_version` out of range), so it never
  reached its `dsb osh` either. The working log therefore says nothing about
  whether that barrier is safe on this SoC.

So `dmb osh` stays (it is sufficient for the ordering this code needs: the
command store must precede the status loads), but it is marked **unverified**
rather than **fixed**.

**Cheapest experiment if the phone stalls in keys_init again:** build the same
image with `dsb osh` restored in `keys_read()` and run it. That is a one-line
A/B against a kernel that differs in nothing else, and it settles the question
the failed reasoning left open.


### >>> UPDATE 2026-11-03 (24): one test entry point, wired into the build <<<

The three tool tests (entries (20)-(23)) plus `tests/run-all.sh` now run on
every kernel build - `deps/build-macos.sh` calls them after the post-patch
fix-ups and **aborts the build** if any fail (`SKIP_TESTS=1` overrides).

Why gate the build on them: these tools are what will explain the next boot.
A build that silently ships a broken watchdog or a mis-offset mark reader is
worse than a build that fails, because the resulting silence would be
indistinguishable from "the kernel got further than before".

The gate was checked in both directions: injecting a deliberate failure into
`tests/test_watchdog.py` makes `run-all.sh` exit 1, and restoring it returns 0.

The same build step also runs `deps/sync-watchdog.sh`, so the copy of
`sweet_init_watchdog.h` in the git-ignored patched tree cannot drift from the
repo's.

**Running the suite today:** 35 checks across three files, all passing.

```text
== test_bisect.py     all bisect-verdict checks passed   (16)
== test_marks.py      all mark checks passed              (11)
== test_watchdog.py   all watchdog checks passed          (8)
all host tests passed
```

One of those 35 caught a stale assertion made by this session itself: after
`tools/sweet-mark-pull.sh` was changed to read its block geometry from the
driver source, `tests/test_marks.py` still expected the literals `1025 - 64`
and failed. That is the suite doing its job on its own author.

Kernel is unchanged by this entry and still `59044a9a...`.

**Twenty-three rounds, no phone.**


### >>> UPDATE 2026-11-03 (23): the mark reader is split out and tested <<<

Third tool in a row to get the same treatment (after the watchdog and the
bisect verdict). `tools/sweet-mark-pull.sh` embedded its parser in a heredoc
and had two defects that tests caught:

1. **The block geometry was a literal.** `skip=$((bytes/4096 - 1025 - 64))`
   hard-codes "4 MiB ring + 1 header" and "64 marks". Change `SWEET_LOG_SIZE`
   or `SWEET_MARK_BLOCKS` in the driver and the offset silently moves - the
   tool would read an unrelated part of `userdata` and report "no MARK blocks",
   which reads exactly like a boot that never marked anything.
   The parser now reads both constants out of `sweet_ufs.c`
   (`ring_blocks_from_source`), and the shell asks for them with
   `sweet-marks.py --sizes SRC`, falling back to 1025/64 only when the patched
   tree is not staged.
2. **A malformed slot killed the whole run.** `line.split(" ")[1]` and
   `int(seq)` raise on a block that starts with `MARK ` but is not well formed
   (a torn write mid-flush is exactly when that happens). Such blocks are now
   skipped, and a duplicate sequence number - which can only come from a torn
   write - is de-duplicated so the ordering stays stable.

`tools/sweet-marks.py` holds the parsing; `tests/test_marks.py` checks it with
10 cases including the two geometry constants read from the real driver source.

Checked end to end with a dump built the way the kernel writes it (single-byte
stores, tail left uncleared) for a boot that stalls inside `keys_init`:

```text
MARK 00001 INIT: sample_start done
MARK 00002 INIT: entering keys_init
```

The last line is the stalled step, which is the whole point of the marks.

**Twenty-two rounds, no phone.**


### >>> UPDATE 2026-11-03 (22): the bisection verdict is now tested too - three bugs found <<<

`tools/bisect-keys.sh` decided its verdict with four `grep -q "keys_init done"`
checks. That is too coarse to separate the cases that actually matter, so the
decision moved into **`tools/bisect-verdict.py`** (pure: two logs in, one
verdict out) with **`tests/test_bisect.py`** covering it: 16 checks, all
passing, two of them driving the *real* logs (the boot that reached
`exec launchd` and the run that stopped on the `keys_init` line).

Writing those tests found three bugs that would each have produced a wrong
conclusion on the next boot:

1. **Both runs succeeding was reported as `keys_blocks`.** The `off` case was
   checked before the "both" case, so two healthy boots would have been blamed
   on the keys driver.
2. **The prefix check contradicted itself.** `reached_keys_init_prefix()`
   matched only `sample_start done` and `keys_init`, so a log that reached
   `init complete` was reported as "(did not even reach the keys_init line)" -
   and the verdict then said the stall was *before* `keys_init`, the opposite
   of the truth. It now also counts any later phase as having passed.
3. **Depth was not compared.** "`off` passed `keys_init`" was treated as
   proof that keys blocks the boot even when the default run had gone further
   (`usb_probe`), which is contradictory. The phases are now ordered and the
   deeper run wins before any conclusion is drawn.

The verdict vocabulary is now explicit - `keys_blocks`, `both_mount`,
`before_keys`, `before_keys_both`, `same_phase`, `inconsistent`, `unclear` -
so the script, the tests and whoever reads the output all use the same words.

Example, using the two real logs:

```text
  sweetkeys=0  reached: userland
  default      reached: nothing past sample_start

ROOT MOUNTED with sweetkeys=0 (phase: userland) but not with the default
(phase: nothing past keys_init). The keys driver is what blocks the boot.
verdict: keys_blocks
```

**Twenty-one rounds, no phone.**


### >>> UPDATE 2026-11-03 (21): the watchdog is now a tested pure function <<<

Entry (20) found two watchdog defects with a throwaway simulation. This round
made that permanent and found **two more** that the throwaway script had not:

- **`xnu/sweet_init_watchdog.h`** holds the decision as a pure inline
  function, `sweet_wd_should_report(&state, step)`. `sweet_ufs.c` calls it and
  the host tests compile the *same header*, so the tests exercise the kernel's
  code rather than a copy of it.
- **`tests/test_watchdog.py`** compiles the header with the host compiler and
  drives it over simulated timelines: 8 checks, all passing.
- **`deps/sync-watchdog.sh`** copies the header into the patched tree (which is
  git-ignored and rebuilt from patches, and no patch carries this file).

The two new defects, both real and both fixed:

1. **A one-tick false alarm at the boundary.** The check was `ticks <
   GRACE`, so at exactly `GRACE` it warned - and a tail finishing one tick
   later (8.2 s) got a "still inside the init tail" line for no reason. Now
   `ticks <= GRACE`, i.e. strictly after.
2. **Back-to-back reports.** The first warning landed on a tick that also
   satisfied the repeat condition, so it printed at 40 and again at 50, ten
   ticks apart instead of fifty. The repeat countdown now restarts after every
   report (`since` field).

The checks that pin the behaviour:

| check | what it pins |
| --- | --- |
| healthy boot is silent | no warning for a 3.2 s tail |
| finishes just past grace is silent | the strict boundary |
| stall reports the stalled step | the warning names `keys_init`, not a sibling |
| first warning comes after grace | tick 41, not 40 |
| repeats steadily while stuck | gaps are exactly `SWEET_WD_REPEAT_TICKS` |
| step change reported at once | slow-but-moving is visible |
| nothing printed before grace | the original false-alarm regression |
| last report names the current step | the stale-pointer regression |

**Images rebuilt**: `shim-proven.img` = `shim-bisect-on.img` (`7b91041c...`),
`shim-bisect-off.img` (`356046d2...`). Kernel `59044a9a...`.

**Twenty rounds, no phone.** The instrumentation that will diagnose the next
boot is now itself tested, which is the most useful thing that can be done
without the device.


### >>> UPDATE 2026-11-03 (20): the watchdog itself was wrong twice - simulated first <<<

The init watchdog from entry (19) had two defects, both caught by simulating it
offline before any phone was involved (a small model of the loop, driving
`sweet_init_step`/`sweet_init_done` on a fake timeline):

1. **It reported on a healthy boot.** The first version printed whenever the
   step changed *and* the grace period had passed, but the two conditions were
   OR-ed the wrong way round, so a tail finishing in 3.2 s produced four
   "still inside the init tail" lines. Fixed: **nothing is reported before
   ~8 s**, so a fast tail is silent by construction.
2. **The step name was not read atomically.** `sweet_init_step` was a plain
   `const char *` written by the init thread and read by the log thread; the
   loader could keep a stale copy, which would name the wrong step exactly
   when it matters. It is now `_Atomic` with `os_atomic_store/load`.

After both fixes the simulation gives:

| scenario | output |
| --- | --- |
| healthy tail (done at 3.2 s) | **silent** |
| stalled in `keys_init` | `~8s step=keys_init`, then every 10 s |
| stalled in `touch_init` | `~8s step=touch_init`, then every 10 s |
| slow but moving | reports each step as it advances |

That last row is what separates "hung" from "slow", which the earlier
single-shot marks could not do.

**Images rebuilt**: `shim/out/shim-proven.img` = `shim-bisect-on.img`
(`685e00dc...`), `shim-bisect-off.img` (`c16c1432...`, adds `sweetkeys=0`).

**Nineteen rounds, no phone.** Twenty commits this session; nothing verified on
hardware.


### >>> UPDATE 2026-11-03 (19): a device read cannot be bounded, so the log thread reports it <<<

`keys_read()` now has two exits and the barrier is DMB (entries (12), (14),
(17)), but one class of stall is beyond the reach of any in-code deadline: the
MMIO load itself. `keys_rd()` is a bare `*(volatile uint32_t *)...`; a load from
an unresponsive SPMI window never returns, and there is no way to interrupt it
from the same thread. If that is what the phone does, no amount of polling
bounds will help and the marks will simply stop.

So the **log thread now watches the init tail**. It runs every `sweetlogms`
(200 ms) regardless of what init is doing, and if `sweet_init_done` is still
clear after ~5 s it prints, once, and then every ~50 s:

```
SWEET INIT: still inside the init tail after ~5 s (last step: keys_init) - look at the mark blocks
```

`sweet_init_step` is set on entry to each step (`sample_start`, `keys_init`,
`touch_init`, `usb_probe`) and `sweet_init_done` on the last line. This turns
"the boot stopped somewhere" into a named step in the console itself, without
needing the mark blocks to survive.

**Not done on purpose:** `sweet_spmi.c` and `sweet_keys.c` each map the same
three SPMI windows (`0x2000`/`0x1000`/`0x10000` at `0xc440000`/`0xc40a000`/
`0xe600000`). Sharing one mapping would save 24 KiB of a very empty
`io_submap`, but it would couple keys to the battery driver's init order and
add a failure mode. The duplication is kept.

**Images rebuilt** (`shim-proven.img` = `shim-bisect-on.img`, `9f4c4973...`;
`shim-bisect-off.img`, `ff56cba5...`). Eighteen rounds, no phone.


### >>> UPDATE 2026-11-03 (18): session handoff written to HANDOFF-2026-11-03.md <<<

`HANDOFF-2026-11-03.md` is the short version of this session: what is proven
vs merely reasoned, the sixteen commits and why each one exists, the offline
audits, the artifact list with hashes, and the exact next action when a phone
is reachable (`tools/bisect-keys.sh`).

The key distinction it draws, which the inline notes above do not make clear
in one place:

- **Proven**: the stall is inside `sweet_keys_init()` (step-by-step diff
  against a boot that reached launchd).
- **Reasoned, not yet observed**: everything else this session changed - the
  SM7225 TLMM address, the per-slot UFS queue, the threaded touch bring-up,
  the boot line, the DSB fix.

**Seventeen rounds, no phone.** If the device stays unavailable, this document
plus `NOTES.md` is the complete state; nothing else is pending.


### >>> UPDATE 2026-11-03 (17): the keys fix is verified in the built binary, not just the source <<<

Checked the compiled kernel (`research/k-proven`, `5c3907c8...`) rather than
trusting the source diff, because a barrier that did not actually change would
look identical in review.

`_keys_read` at `0xfffffe00074e56e4` disassembles to:

```text
fffffe00074e5730: b9000128   str  w8, [x9]     ; SPMI command
fffffe00074e5734: d50333bf   dmb  osh          ; DMB, not DSB (was dsb osh)
fffffe00074e5748:            bl   nanoseconds_to_absolutetime
fffffe00074e5764: 52807d18   mov  w24, #0x3e8   ; 1000 iterations
loop:
fffffe00074e5780:            tbnz w8, #0x0, done_bit   ; status & 1
fffffe00074e5784:            bl   mach_absolute_time
fffffe00074e5794:            b.hi deadline_reached     ; now > deadline
fffffe00074e579c:            bl   _delay                ; delay(1)
fffffe00074e57a4:            b.ne loop
```

All three exits are present (done bit, deadline, iteration cap), and the
barrier is the ordering-only one. So the claim "no unbounded wait is left on
this path" now has evidence from the binary, not just from the editing.

Also compared the PMIC apid values across **every** working log: all of them
report `arb=0x50010000 apids=512 pon-apid=308 gpio-apid=366`. The scan result is
stable hardware topology, so there is no per-boot variance to explain a hang
in `keys_find_apid()`.

**Sixteen rounds, no phone.** The remaining unknown is the device, not the code.


### >>> UPDATE 2026-11-03 (16): ADT and payload agree with the phone; USB gate logic checked <<<

A consistency audit of the artifacts the bisection images are built from, done
by parsing the generated ADT instead of trusting the generator:

| property | ADT value | payload header | matches |
| --- | --- | --- | --- |
| `dram-base` | `0x180000000` | `phys_base 0x180000000` | yes |
| `dram-size` | `0x100000000` (4 GiB) | `mem_size 0x100000000` | yes |
| `dram-base-low` | `0x80000000` | - | matches PORT-gauguin.md |
| root `compatible` | `D22AP`, `iPhone10,3`, `xiaomi,gauguin`, **`qcom,sm7225`**, `AppleARM...` | - | SM7225 correction is in |
| CPU `compatible` | `qcom,kryo465`, `ARM,v8` (all 8) | - | |

Both bisection payloads carry the same values, so the two images really do
differ only by `sweetkeys`.

Also checked the USB gate logic against the register values in the working
log: `GDSC 0xf822f000` has bit 31 set (on) and every CBCR in
`master/sleep/utmi/cfg-noc-axi/aggre-axi/phy-aux/clkref` has bit 31 clear
(on), which is exactly what `clocks_on = (gdscr & (1<<31)) && !(cbcr[0] &
CLK_OFF) && !(cbcr[3] & CLK_OFF)` evaluates to. So the probe's decision
matches the hardware that actually booted; `sweetusb=0` is not needed and
must not be used as the workaround.

The complete post-`keys_init` sequence in the working boot is:
`keys_init done` -> `touch_init` -> `touch_init done` -> `usb_probe` ->
(SWEET USB 12 lines) -> `init complete`. Nothing else happens between them.

**Fifteen rounds, no phone.**


### >>> UPDATE 2026-11-03 (15): a two-image bisection is staged for the next boot <<<

The stall is proven to be in `sweet_keys_init()` (entry (12)), and every cheap
cause inside it has been excluded (entry (14)). Rather than keep guessing at
the PMIC code, the next hardware access should **measure** whether that path is
the problem, with a difference of exactly one boot-arg:

| image | boot-arg | what it proves |
| --- | --- | --- |
| `shim/out/shim-bisect-off.img` | `sweetkeys=0` | `sweet_keys_init()` returns before **any** MMIO access, so this image's init tail cannot stall in the keys driver |
| `shim/out/shim-bisect-on.img` | (default) | the driver runs as normal |

Both are otherwise the same kernel (`5c3907c8...`) and the same command line,
which is the one from the working log (`debug=0xc cpus=1 sweetlogms=200`).

`tools/bisect-keys.sh` runs both unattended and prints a verdict:

- **`-off` passes `keys_init done` and `-on` does not** -> the stall is the
  keys/PMIC path, and the per-step marks narrow it further.
- **both pass** -> the stall is later (touch or USB); the marks say which step.
- **neither passes** -> the boot-arg is not what differs, and if both stop on
  the same mark the stall is before `sweet_keys_init()` or in the log path
  itself.

That last case is worth keeping in mind: it is the outcome that would put the
blame back on the UFS/log machinery rather than on the PMIC.

**Fourteen rounds, no phone.** Everything above is staged, nothing is measured.


### >>> UPDATE 2026-11-03 (14): ruled out the cheap causes of the keys_init stall <<<

Follow-up to entry (12), which proved the stall is inside `sweet_keys_init()`.
Each candidate was checked against the source rather than guessed at:

| candidate | verdict |
| --- | --- |
| `ml_io_map()` running out of the IO submap | **ruled out**: `IO_MAP_SIZE` is 8 MiB on arm (32 MiB on i386), and the whole boot path - UFS 0x4000 twice, GCC 0x60000/0x90000, TLMM, SE8, three KEYS windows, DWC3, QUSB2 - sums to **1.55 MiB, 19 %** |
| apid offset past the mapped window | **ruled out**: the working boot's `pon-apid=308` and `gpio-apid=366` index `0x9a00`/`0xb700`, and the highest access is `+0x18` -> `0x9a18`/`0xb718`, well inside the 0x10000 window |
| `io_map()`'s linear `virtual_space_start` allocator overlapping | **ruled out**: that branch only runs before `STARTUP_SUB_KMEM`, and `sweet_ufs_init()` runs after `bsd_autoconf` |
| **the `DSB` in `keys_read()`** | **fixed**: a DSB only returns when every outstanding access in its shareability domain has completed. If the SPMI fabric stalls, the barrier itself never returns - and the 50 ms deadline added in entry (12) cannot help, because it is checked inside the loop that the barrier *precedes*. It is now `dmb osh`, which orders the command write against the status reads (all the code needs) without waiting for completion. |

`dsb osh` was also the only unbounded wait left on this path: every other
poll has both an iteration cap and a wall-clock deadline.

**Image: `shim/out/shim-proven.img`** (kernel `5c3907c8...`, boot.img
`3c09428a...`, kernel saved as `research/k-proven`). Thirteen rounds, no phone.


### >>> UPDATE 2026-11-03 (13): the init marks were still hostage to the log thread <<<

Entry (12) bracketed every init step with a mark, but `sweet_log_mark()` only
fills RAM - the write happens in the log thread, which calls
`sweet_log_mark_flush()` on its own loop. For a boot that is healthy that is
fine. For the case marks exist to diagnose - **a stall inside keys_init** - it
is exactly backwards: if init is stuck, the flush may never run, and the marks
stay in RAM.

`extern void sweet_log_mark_sync(const char *)` now records the mark and then
flushes it **on the caller's thread**. It uses `UFS_SLOT_MARK` (slot 2), which
no other caller touches, so it cannot collide with the main I/O slot even if
the caller holds `sweet_ufs_lock`. Verified: the three `lck_mtx_lock(
&sweet_ufs_lock)` sites are at lines 581, 654 and 876 and none of them covers
the init tail, and the lock order between `sweet_log_lock` and
`sweet_mark_lock` is the same in both paths (log flush takes mark flush while
holding the log lock; `sweet_log_mark_sync` takes only the mark lock), so
there is no lock-order inversion.

Every init step now pays exactly one 4 KiB SCSI write for the privilege of
being visible after a hang:

```text
INIT: sample_start done
INIT: entering keys_init      <- last one written if keys_init hangs
INIT: keys_init done
INIT: entering touch_init / INIT: touch_init done
INIT: entering usb_probe  / INIT: usb_probe done
```

**Image: `shim/out/shim-proven.img`** (kernel `30dd6621...`, boot.img
`a35f7e6b...`, kernel saved as `research/k-proven`).

**Twelve rounds, still no phone.** This is the first image that can tell us
*where* keys_init hangs without relying on the console ring at all - which is
the only thing that has been unavailable all session.


### >>> UPDATE 2026-11-03 (12): the stall is provably inside keys_init, and the init tail is now bracketed <<<

Diffed the init sequence of the working boot and a failing one step by step
(`SWEET UFS: init ...` lines after `init reg=0x1d84000/0x3000`):

| # | working boot (`boot-journaled-userland.txt`) | failing run |
| --- | --- | --- |
| 1-10 | ... | identical |
| **11** | `SWEET UFS: keys_init` | `SWEET UFS: keys_init` |
| 12 | `SWEET KEYS: arb=0x50010000 apids=512 ...` | **nothing** |
| 13 | `SWEET UFS: keys_init done` | - |
| 14-17 | `touch_init`, `touch_init done`, `usb_probe`, `init complete` | - |

Everything before `keys_init` is byte-for-byte the same, including the boot
phases (`dlil_init`, `bsd_autoconf`, `rootdev called`, `init reg`). So the
stall is unambiguously **inside `sweet_keys_init()`** / the PMIC access, not in
the UFS driver below it and not in touch/USB.

The working boot answered the PMIC on the first read (`pon-apid=308`,
`gpio-apid=366`, all `*ok=1`). Two changes make the failure mode bounded and
observable:

1. **`keys_read()` is deadline-bounded.** It polled up to 1000 times with
   `delay(1)` per call and `keys_init` makes five of them, so a PMIC that never
   asserts done could park this path for seconds - on the thread that must
   return before BSD mounts the root. It now also stops after 50 ms wall clock.
2. **Every init step is bracketed with a mark** (`INIT: entering keys_init`,
   `INIT: keys_init done`, `INIT: entering touch_init`, ...). Marks are RAM-only
   and written by the log thread (entries (5) and (10)), so this costs a few
   dozen byte stores per step and survives the ring being overwritten. Reading
   them with `tools/sweet-mark-pull.sh` will name the exact step that stalls,
   even when the console is lost.

**Image: `shim/out/shim-proven.img`** (kernel `1404ed3c...`, boot.img
`4be40d96...`, kernel saved as `research/k-proven`). Eleven rounds, still no
phone - this cannot be validated until the device is reachable.


### >>> UPDATE 2026-11-03 (11): where the iOS root image lives (it is NOT on 137) <<<

Checked while the phone is still off USB, because a successful kernel boot is
useless without a root to mount.

The iOS root images are on **the Linux workstation** at
`/run/media/dipa/android/ios-sweet-ipsw/ios16-root-20H392-v15.img` (+ `.simg`,
v14 as fallback) - not on this Mac and **not on 137**. Verified: no
`ios16-root*` under `~` on either host, and 137 has no removable media mounted.

So the recovery picture has two separate pieces:

| piece | where | verified |
| --- | --- | --- |
| phone firmware/partition backups (`abl`, `boot`, `dtbo`, `vbmeta*`, `persist`, `modemst1/2`, `fsg`, `fsc`, `misc`, `recovery`, GPT, all LUNs) | 137 `~/backup/gauguin/`, with `SHA256SUMS` | yes, this session |
| iOS root image (16 GiB HFS+, `userdata`) | the Linux workstation's removable media | **not reachable from here** |

That matters if the phone ever has to be re-flashed: restoring the firmware is
possible from 137, but putting iOS back on `userdata` needs the workstation
(or a fresh `tools/mkiosroot.sh` run from an IPSW, ~7 min flash). The phone
currently holds image v15, so a normal boot does not need any of this.


### >>> UPDATE 2026-11-03 (10): marks cost nothing on the init path now <<<

`sweet_log_mark()` was already memory-only (2026-11-03 (5)), but each call
still did a 4 KiB `memset` plus an `snprintf`, and `sweet_keys_init()` carries
eleven of them. It now formats the line with single-byte stores and no
clearing - the newline is what the reader keys on, and the flush writes the
whole block anyway. The output is byte-identical to what
`tools/sweet-mark-pull.sh` expects (`MARK %05u %s\n`), checked by simulating
the writer against the reader's `split(b'\n')[0]` / `split(' ')[1]` logic.

Total added work per mark: one atomic increment, one atomic OR, and ~30 byte
stores. That is nothing next to the SCSI round trip the old version paid.

**Image: `shim/out/shim-proven.img`** (kernel `157f5090...`, boot.img
`d9118ae7...`).

**Nine rounds, still no phone.** Nothing since round 1 has run on hardware.
The code is at its best-known state - the init sequence and boot line match
the log that reached `exec launchd`, every base address and mapping window is
verified against the device tree, and the DMA layout is audited - but that is
all offline reasoning. The backup on 137 can restore the phone if it is
bricked; the only missing thing is physical access to it.


### >>> UPDATE 2026-11-03 (9): every gauguin hardware constant checked against the device tree <<<

The phone is still off USB (both hosts checked: this Mac and 192.168.201.137
report no device in `adb`, `fastboot` or `lsusb`). The backup on 137
(`~/backup/gauguin/`, with `dt/` = the full live device tree and
`SHA256SUMS`) is complete: abl/ablbak, boot, dtbo, vbmeta*, persist,
modemst1/2, fsg, fsc, misc, recovery, GPT and all LUNs. So a hard recovery is
possible if it ever comes to that.

With the DT available offline, all nine base addresses in the drivers were
decoded from `dt/soc/*/reg` and compared:

| constant | code | device tree | |
| --- | --- | --- | --- |
| `TOUCH_GCC_PA` | `0x100000` | `0x100000` (`qcom,gcc@100000`, `0x1f0000`) | ok |
| `TOUCH_SE_PA` | `0x988000` | `0x988000` (`i2c@988000`) | ok |
| `TOUCH_NORTH_PA` | `0xf100000` | `0xf100000` (`pinctrl@f100000`, `0x30000`) | ok |
| `KEYS_CORE_PA` | `0xc440000` | `0xc440000` (spmi `core`, `0x1100`) | ok |
| `KEYS_CNFG_PA` | `0xc40a000` | `0xc40a000` (spmi `cnfg`) | ok |
| `KEYS_OBS_PA` | `0xe600000` | `0xe600000` (spmi `obsrvr`, `0x100000`) | ok |
| `DWC3_PA` | `0xa600000` | `0xa600000` (`ssusb@a600000`) | ok |
| `QUSB2_PA` | `0x88e3000` | `0x88e3000` (`qusb@88e3000`, `0x400`) | ok |
| UFS | `0x1d84000` | `0x1d84000` (`ufshc@1d84000`, `0x3000`) | ok |

Every `ml_io_map()` window was also checked against the highest offset the
code actually reads: KEYS core `0x1700<=0x2000`, cnfg `0xf00<=0x1000`, obs
`0xff98<=0x10000`, GCC `0x19000<=0x60000`, SE `0x1000<=0x4000`, DWC3
`0xc124<=0xd000`, QUSB2 `0x258<=0x400`. No window is short.

**Conclusion: the address map is not a remaining source of the stall.** The
SM7225 corrections from the first entry (TLMM) were the only address that was
ever wrong; everything else matches the phone.


### >>> UPDATE 2026-11-03 (8): init tail now matches the working log line for line <<<

Diffed the current `sweet_ufs_rootdev()` tail against
`boot-journaled-userland.txt` (the boot that reaches `exec launchd`),
*including* the `scsi` lines that the synchronous `sweet_log_sync()` calls
produce. Two of those calls had gone missing while the earlier entries were
experimenting:

    printf("keys_init") -> sync -> keys_init() -> printf("keys_init done") -> sync

The working log shows a `scsi 0x2a`/`0x35` pair immediately after
`SWEET UFS: keys_init` and another pair after `keys_init done`; the tree had
neither, so `keys_init()` ran with no flush either side. Both are restored.

The tail now reproduces the working sequence exactly:

```text
sample_start -> sync -> sample_done -> sync -> keys_init -> sync
  keys_init() -> keys_init done -> sync -> touch_init -> touch_init done
  -> sync -> usb_probe -> usb_probe() -> init complete [-> sync]
```

**Image: `shim/out/shim-proven.img`** (kernel `5fe0afd7...`, boot.img
`b082ba8a...`, kernel saved as `research/k-proven`).

**Six rounds without the phone.** Every change from round 1 onwards is
compiled and packaged but unverified on hardware. The single blocking action
is physical: full power-off (15 s), 10 s wait, cold boot into TWRP. Until then
no further code change can be validated, and each additional speculative edit
carries the risk this entry is undoing - drift away from the sequence that is
known to work.


### >>> UPDATE 2026-11-03 (7): the split slots needed an atomic tag; layout audited <<<

Two checks on the per-slot request queue (2026-11-03 (2)), one of which found
a real bug.

1. **Command tags were not unique under concurrency.** `ufs_scsi_slot()` did
   `ucd->cmd[3] = ++su.tag` - a read-modify-write with no atomicity. Splitting
   the slots made concurrent callers real, so two of them could stamp the same
   tag, and the controller may then attribute a completion to the wrong
   command. It is now `os_atomic_inc_orig(&su.tag, relaxed)` masked to 1..31.
   This cannot be observed in the old logs (the working boots never overlapped
   a command - 0 `still busy`, 0 timeouts, 0 failures in 33,947 lines), so it
   is a latent bug that only became reachable once the slots were separated.
2. **The DMA layout was audited arithmetically** (no overlaps, all three UCDs
   fit below `DMA_BOUNCE`):

   | region | range | note |
   | --- | --- | --- |
   | UTRL | `0x0`..`0x400` | 32 slots x 32 B; slots 0/1/2 used |
   | UCD (main) | `0x1000`..`0x1440` | |
   | UCD log | `0x2000`..`0x2440` | |
   | UCD mark | `0x3000`..`0x3440` | ends before `DMA_BOUNCE` |
   | BOUNCE | `0x4000`..`0x104000` | slot 0 |
   | STAGE | `0x104000`..`0x105000` | |
   | MARK | `0x105000`..`0x106000` | slot 2 |
   | BOUNCE_LOG | `0x106000`..`0x206000` | slot 1 |

   total `0x206000` = 2.02 MiB (was 1.02 MiB); the phone has 4 GiB.

**Also confirmed from the logs:** the successful run that reaches userland
does not end in a crash - the ring simply stops where the log was pulled, with
backboardd still polling for `IOAcceleratorES`. So a working boot does not by
itself knock the phone off USB.

**Image: `shim/out/shim-proven.img`** (kernel `50397b51...`, boot.img
`6b64b32a...`, kernel saved as `research/k-proven`). Same proven boot line as
the previous entry. Still not booted; the phone has now been off USB for five
rounds.


### >>> UPDATE 2026-11-03 (6): match the boot line of a boot that provably worked <<<

The successful boots in `.deps-cache/logs/` all ran with a command line that
differs from every image built this session. `boot-journaled-userland.txt`
(which reaches `exec launchd`) has:

    debug=0xc serial=3 cpus=1 ... sweetlog=1 sweetlogms=200 sweetfb_noconsole=1

while this session's images used `debug=0x8 cpus=8 sweetlogms=250
sweetfb_hz=30`. Both differences matter:

- **`cpus=1`.** Every log that mounted the root is `cpus=1`. `cpus=8` is the
  right setting for *usability* (2026-10-23 17:30 - it makes the SpringBoard
  stretch fast) but it was measured after the root already mounted, and it has
  never been in a boot line that got that far. It brings up seven secondary
  cores on this SoC, and any of them hanging takes the system with it.
- **`debug=0xc`, not `0x8`.** `0x8` is `DB_KPRT` only; `0xc` adds 0x400
  (`DB_KERN_DUMP_ON_PANIC`), so a panic keeps its information instead of a
  silent reset (2026-10-21 03:00: "debug=0xc explains the silent resets").

**Second fix:** `sweet_touch_init()` was still running the whole bring-up
inline. In the successful log, `touch_init` and `touch_init done` are
*adjacent* with no other output between them - that function only started a
thread. It now calls `sweet_touch_start_at_init()`, which queues the bring-up
on its own kernel thread (the one added in 2026-11-03 (3)) and returns.

**Image ready: `shim/out/shim-restored.img` is superseded by
`shim/out/shim-proven.img`** (kernel `bcbdb25c...`, boot.img `8ae7f6d2...`,
kernel saved as `research/k-proven`). Its boot line is byte-for-byte the one
from the working log apart from nothing at all - it is the same string. Its
init path is the proven order, its marks are RAM-only, and its only additions
over the 2026-10-20 kernel are the SM7225 corrections (TLMM `0x00f100000`, ADT
`qcom,sm7225`), the per-slot request queue and the threaded touch bring-up.

**Still not booted - the phone has been off USB since the `sweetlog=0` run
four rounds ago and has not re-enumerated.** That is the only thing blocking
verification now.

**Phase comparison, for whoever runs it:** in the working log `rootdev called`
is line 102 and `init complete` line 189; a failing run stops on the
`SWEET UFS: keys_init` line (~line 157 of a 202-line ring). Getting past
`init complete` and to `BSD root: ufsroot0` is the success criterion for the
next boot.


### >>> UPDATE 2026-11-03 (5): the earlier "deadlock" diagnosis was WRONG - see the logs <<<

**Corrects the 2026-11-03 (1) entry. Read this before believing that one.**

`.deps-cache/logs/` holds ~20 boots from 2026-10-20/22, and **every one of them
mounted the iOS root** (`mounted iOSRoot`, `exec launchd`). One is a complete
worked example of the exact sequence this bring-up is trying to reproduce -
`boot-journaled-userland.txt`:

```text
SWEET UFS: sample_start -> sample_start done -> keys_init
SWEET KEYS: arb=0x50010000 apids=512 pon-apid=308 gpio-apid=366
SWEET UFS: keys_init done -> touch_init -> touch_init done
SWEET USB: GDSC usb30_prim on ... DWC3 GSNPSID 0x5533330a
SWEET UFS: usb_probe -> init complete -> init returned 0
BSD root: ufsroot0, major 1, minor 0
```

Three things follow, and the first two mean the earlier fixes were solving
non-problems:

1. **`sweet_log_sync()` on the init path is fine.** Every step in that log is
   followed by its own `scsi 0x2a` + `0x35` write - the synchronous flush ran
   and returned, repeatedly, on a boot that reached userland. The claim that it
   deadlocked on `sweet_ufs_lock` (2026-11-03 (1)) is **wrong** and the calls
   are **restored**. What *was* different on the failing runs is not yet known;
   it was not this.
2. **`sweet_usb_probe()` reading registers is fine on gauguin** with the
   SM7125/lagoon register map (2026-10-20 22:10 note). The old "USB probe kills
   the boot" only applied before that map was corrected, so `sweetusb=0` is
   **not** the fix and was not used.
3. **The real regression was mine: `sweet_log_mark()` did synchronous SCSI
   writes inside the init path.** Eleven of them sit in `sweet_keys_init()`
   alone. Each is a full 4 KiB write round trip, and `keys_init` is a
   sub-second step when it is not doing that. The runs that stopped on the
   `SWEET UFS: keys_init` line are consistent with exactly that.
   `sweet_log_mark()` is now **memory only** (64 slots in `sweet_mark_ram` +
   a dirty bitmap) and `sweet_log_mark_flush()` writes the pending blocks from
   the log thread, never from init.

**Also changed:** the init tail calls `sweet_touch_init()` again (start the
touch thread, ~7 lines of log) instead of `sweet_touch_start_at_init()` (run
the whole bring-up inline). The touch bring-up itself still runs on its own
thread - that part stands and is a genuine improvement.

**Built: `shim/out/shim-restored.img`** (kernel `3c401b69...`, boot.img
`b27379ce...`; kernel also saved as `research/k-restored`). This is the first
image whose init path matches a boot that is *known* to reach userland.
**Not yet booted - the phone has been off USB since the `sweetlog=0` run.**


### >>> UPDATE 2026-11-03 (4): QEMU cannot verify the gauguin path - stop trying <<<

Measured this round, so nobody spends another cycle on it. QEMU boots the
kernel only as far as `VM bootstrap done` + `IOKit IOMD setownership ENABLED`
and then takes an **Undefined Instruction** exception at `0xfffffe0007482000`
(QEMU `virt` lacks the SM7225 ISA bits).

- **Both kernels do it**, including the pre-change `shim-safe` payload: that
  one dies with the same Undefined Instruction and never decodes a frame.
- So the panic is a QEMU limitation, **not** a regression from the UFS slot or
  touch-thread work.
- QEMU never reaches UFS at all, and the phone's stop is *after* UFS (at
  `sample_start` / the log thread), so QEMU cannot validate anything in the
  range this bring-up is stuck in.

Practical rule: `tools/qemu-sweet.py` is only useful for changes above BSD
init (platform/VM/framebuffer). For UFS, log, keys, touch or USB, the phone is
the only witness. `--fail-on-panic` also requires `--kernel`, and the kernel
binary is overwritten by each build, so a comparison against an older kernel
needs that binary saved first (e.g. copy `kernel.development.gauguin` to
`research/k-<tag>` before rebuilding).


### >>> UPDATE 2026-11-03 (3): touch bring-up leaves the UFS init path <<<

`sweet_touch_start_at_init()` ran the **whole** touch bring-up synchronously
from `sweet_ufs_rootdev()` - on the one thread that has to return before BSD
can mount the root and start launchd. That bring-up walks 25 GCC pages with
strongly-ordered reads, votes an RPMh rail, reprograms a GENI SE and polls the
I2C chip for its ID (5 x 200 ms in the worst case). Any stall there means iOS
never gets a root.

Touch is not needed for iOS to boot, so it now gets its own
`kernel_thread_start()` thread (`touch_bringup_thread`), and the init path
returns immediately after queueing it. If the thread cannot be created the old
inline behaviour is kept. New state: `st.thread_started`.

Checked at the same time and found safe: `sweet_usb_probe()` only reads
registers (no waits). The `delay(1000)` loops in the USB path are inside
`sweet_usb_gadget_start()`, which only runs with `sweetusb=2` - the boot
command line does not set it.

Also verified the on-disk layout does not collide: the HFS root occupies the
start of `userdata` (16 GiB image), the mark area and log ring sit at the very
end (lba 28055482.. / 28055566.. of a 96 GiB partition).

**Built: `shim/out/shim-touchthread.img` (kernel `fb8346ea...`,
boot.img `25283433...`). Still NOT booted - the phone has been off USB since
the `sweetlog=0` run.** Pending phone access, in order:
1. `adb devices`; if empty, a manual full power-off (15 s) + 10 s + cold boot
   into TWRP is required (2026-10-23 22:05).
2. `tools/fastboot-cycle.sh shim/out/shim-touchthread.img out.txt`
3. `tools/sweet-mark-pull.sh marks.txt` - the first `UFS step:` / `KEYS:` /
   `TOUCH:` / `USB:` marks will show how far the init tail now gets.


### >>> UPDATE 2026-11-03 (2): one UFS request slot per writer, and a panic-safe log <<<

Continuation of the SM7225 entry below. Three things were rewritten in
`bsd/dev/sweet_ufs.c`; the first is the actual fix for "the boot stops after
`sample_start`", the other two are correctness around it.

1. **The UFS had one request slot for everybody.** `ufs_scsi_pa()` built every
   command in UTRL slot 0, used `DMA_BOUNCE` for the data, rang doorbell bit 0
   and then polled `UTRLDBR & 1`. With two callers in flight the second
   overwrites the first's UTRD and then polls a bit the hardware already
   cleared for the other one - it waits forever. The log thread is started from
   `sweet_ufs_rootdev()` and its first flush runs *while init is still in there*,
   which is exactly the pair that collided.
   Now: `ufs_scsi_slot(..., slot)` with three independent slots, each with its
   own UCD, data buffer and lock (all still one contiguous allocation):

   | slot | users | data buffer | lock |
   | --- | --- | --- | --- |
   | 0 `UFS_SLOT_MAIN` | root device, file system, partition scan, stage | `DMA_BOUNCE` | `sweet_ufs_lock` |
   | 1 `UFS_SLOT_LOG` | persistent log flush thread, `sweet_log_sync{,cache}` | `DMA_BOUNCE_LOG` | `sweet_log_lock` |
   | 2 `UFS_SLOT_MARK` | `sweet_log_mark()` checkpoints | `DMA_MARK` | `sweet_mark_lock` |

   Doorbell and completion now use `1u << slot` instead of a literal 1, and
   every `dma_clean`/`dma_sync` is indexed by the slot's offsets.
   `sweet_log_mark()` also stopped using `DMA_BOUNCE` (it would have scribbled
   over an in-flight file-system transfer).
2. **The panic path could deadlock on the new lock.** `sweet_log_flush()` grew
   a `panic_mode` argument: `sweet_log_flush_panic()` passes `true` and the
   flush then uses `lck_mtx_try_lock()`, giving up if the log thread owns the
   slot (that thread's own write is already carrying the bytes out). Every
   other caller - the log thread, `sweet_log_sync()`, `sweet_log_flush_now()`
   and `sweet_log_start()`'s first flush - passes `false`.
3. `/dev` of the init tail still has no `sweet_log_sync()` (previous entry);
   that removal stands.

**Built, NOT yet booted - the phone went off USB after the `sweetlog=0` run
and has not come back.** Image ready: `shim/out/shim-slots2.img`
(kernel `d9fa12f7e2b7...`, boot.img `9877539ee2a7...`). The earlier
`shim/out/shim-slots.img` is the same change without the panic-mode argument.

**When the phone is back, the first thing to do is:**
`adb devices` - if empty, the phone needs a manual **full power-off (15 s),
10 s wait, then cold boot into TWRP/fastboot**; the 2026-10-23 22:05 entry
calls this the reboot-loop protection state and a warm reset does not clear it.
Then `tools/fastboot-cycle.sh shim/out/shim-slots2.img out.txt` followed by
`tools/sweet-mark-pull.sh marks.txt`, and read `UFS step: keys_init enter`,
`KEYS: ...`, `TOUCH: ...`, `USB: ...` - those would be the first marks ever
written, and they say how far the init tail now gets.


### >>> UPDATE 2026-11-03: gauguin is SM7225 - the TLMM constant and the init-path log deadlock <<<

**READ THIS FIRST. The port was planned on the wrong SoC.**

`lvyufeng/UniXNU-gauguin` and `PORT-gauguin.md` called this phone "SM7125
`lagoip`". It is **SM7225 (Snapdragon 750G, `lagoip`/"lito" family)**, confirmed by
the phone itself: `getprop ro.board.platform` = `lito`, and the TWRP `cpuinfo`
`Hardware: Qualcomm Technologies, Inc SM7225`. SM7125 (720G, `curtana`/
`excalibur`) is a different chip with an Adreno 618 and is an easy pair to
confuse. Everything below follows from that.

**Fixes made and measured this session:**

1. **TLMM (GPIO) base was SM7150's address.** `bsd/dev/sweet_touch.c` used
   `TOUCH_NORTH_PA 0x03900000` for gauguin - that is *sweet*'s pinctrl. The live
   DT (`/sys/firmware/devicetree/base/soc/pinctrl@f100000`,
   compatible `qcom,lagoon-pinctrl`, reg `<0x0f100000 0x30000>`) says the
   TLMM is at **`0x00f100000`**. `0x03900000` is unmapped address space here, so
   `ml_io_map()` + the first GPIO read hung - which is exactly the "stops after
   `stage D: map TLMM`" repeated in the 2026-10-23 14:35 entry. The map now
   starts at `TOUCH_NORTH_PA + TOUCH_GPIO_CFG(pin)` instead of a fixed
   `+0x50000`, and `TOUCH_NORTH_PA` is `0x00f100000`.
   **Verified-good addresses from the phone's DT** (all confirmed present):
   GCC `0x00100000` (`qcom,lagoon-gcc`), GENI SE8 `0x00988000`
   (`i2c@988000`), UFS `0x01d84000`, SPMI core/obs/cnfg
   `0x0c440000`/`0x0e600000`/`0x0c40a000`. So only the TLMM was wrong.
2. **`tools/mkadt.py` now emits `qcom,sm7225`** for gauguin (was `sm7125`).
   Regenerated ADT is otherwise byte-identical apart from the random seed.
3. **The log flush deadlocked the init path.** `sweet_ufs_rootdev()` called
   `sweet_log_sync()` between `sample_start`, `keys_init`, `touch` and
   `usb_probe`. `sweet_log_flush()` takes `sweet_ufs_lock` and then waits on a
   SCSI completion using the **single UTRL/UCD slot**, which the log *thread*
   holds at the same moment. The boot therefore stopped right after
   `SWEET UFS: sample_start done` (two consecutive `shim-safe` runs, and
   `shim-ver` stopped identically on two retries - so it is deterministic, not
   the "bootloader protection" state from 2026-10-23 22:05). All
   `sweet_log_sync()` calls are now removed from the init tail; the ring still
   receives those lines through `__cnputs()` and the thread flushes them.

**New instrumentation (keep it):** `sweet_log_mark()` checkpoints in
`keys_init`, `touch` and `usb_probe` (`UFS step: ...`, `KEYS: ...`,
`TOUCH: ...`, `USB: ...`), written to the 64 blocks just below the log ring so
they survive the ring being overwritten. Read them with
`tools/sweet-mark-pull.sh OUT.txt`. The mark area grew 16 -> 64 blocks
(`SWEET_MARK_BLOCKS`).

**Where it stands after all of the above (measured):** the boot still stops
right after `SWEET UFS: sample_start` / `SWEET LOG: thread running, first
flush follows`. With `sweetlog=0` the phone resets without reaching the Apple
logo. So the remaining stop is **in or just after the log thread's first
flush**, not in the SoC constants and not in the init-path syncs (those are
fixed and stay fixed).

**Build/tooling notes:** `deps/shim-macos.sh` is new - it builds the shim on
macOS with Xcode clang + Homebrew LLVM (`ld.lld`, `llvm-objcopy`,
`llvm-readelf`, `llvm-nm`) because there is no `aarch64-linux-gnu-gcc` on this
host. It needs `-fno-jump-tables`: clang turns the `switch` in `exc_handler`
into a table of string pointers in `.rodata`, violating the "no absolute
relocations" rule the shim is linked by. `shim/ufs.c` uses a local
`shim_strcmp()` for the same reason (`__builtin_strcmp` folds to a libc call
under clang). Kernel builds: `deps/build-macos.sh gauguin` (~4 min).
Images this session: `shim/out/shim-sm7225.img` (TLMM+ADT fixed),
`shim/out/shim-nosync.img` (also the syncs removed),
`shim/out/shim-nolog.img` (`sweetlog=0` probe).

**Next concrete action:** the log thread. `sweet_log_start()` does one
`kernel_thread_start(sweet_log_thread)`; the thread prints and then loops on
`sweet_log_flush()` + `tsleep()`. Either the first flush in that thread
deadlocks on `sweet_ufs_lock`/the single UTRL slot, or the thread never gets
scheduled. Cheap discriminator: give `sweet_log_flush()` its own DMA bounce
buffer and its own UTRL slot (or make the log thread the only UFS writer until
`init complete`), and mark each step of the log thread with
`sweet_log_mark()` *before* the first flush.


**Breadcrumb build (2026-10-20 19:56, cached tree only):** `bsd/dev/sweet_ufs.c`
now prints on entry to `sweet_ufs_rootdev`, around `ml_io_map` (with HCE/HCS),
before/after `ufs_take_over_host` and around `ufs_find_partition`. Kernel SHA256
`f00ecc9eb6578f6c2238e0d30c5ba6f3c1732433abbb16bcb267065381fb5e10`
(`shim/out/shim-boot-ufs.img`). It reaches the DLIL thread scheduling (i.e. past
`bsd_autoconf`) but the photo at 12 s had not reached the UFS prints yet, and
the phone resets to the UEFI on the boot partition ~1 min later. Those prints
are uncommitted in `.deps-cache/xnu-patched-0082-2` on purpose: they are a
debug build, not part of the series.

Note: with the boot partition still holding the gauguin-windows UEFI, a reset
lands in UEFI, not Android/TWRP. `backup/boot.img` (on 137) is the stock image.

**UFS works at the register level on gauguin (2026-10-20 19:52, `shim/out/shim-boot-probe.img`
= the shim with an empty ramdisk, which runs its own read-only UFS probe):**
`ver=00000300 cap=1587031F`, `hce=00000001 hcs=0000010F`, `is=00000400`,
`utrlba=9B9AE000 nutrs=00000020`, our slot at `A2497000`, `TUR rc=0`,
`CAP rc=0`, `LUN0 lastlba=01D82BFF blk=00001000`, `READ rc=0`, MBR `0xAA55`
type `0xEE`, GPT entries=0x40 at lba 2, partitions visible (persist,
persistbak, logdump, rawdump, ...). So the controller window in the live DT is
right and ABL leaves the host usable; the hang is in XNU's own root path, not
in the hardware hand-off.

**XNU's root path still hangs/resets** even with `panic_reboot=0` and with the
`wdt*` args removed (19:49). Same image stops at different places across boots
(one boot frozen at `Registered coredump handler for kernel`, another reached
`VM bootstrap done` + `IOMD setownership ENABLED`), which points at a race or
an interrupt storm rather than one deterministic bug. Next: add progress
prints inside `sweet_ufs_init` (`ml_io_map`, `kmem_alloc_contig`,
`ufs_take_over_host`, `ufs_scsi`, `ufs_find_partition`) and photograph the
frozen screen, since the framebuffer console is the only log until the UFS
console log (0047) can write.

### >>> UPDATE 2026-10-23 22:05: reboot-loop protection is real - cold start clears it <<<

Symptom the user hit repeatedly: the phone flashed a few lines of log and
rebooted immediately, **with every image, including ones that had booted
minutes earlier** (`shim-ver`, `shim-iv`). Partitions were checked and are
clean: `misc` holds exactly `boot-recovery` and nothing else, `oem_misc1` is
all zeros, and the HFS root (blocks 4096..4198400) does not overlap the log ring
at block 28055546, so nothing on disk was damaged.

What fixed it: a **full power-off** (power button 15 s+), 10 s off, then cold
boot into recovery. The same `shim-iv.img` then booted to the Apple logo and the
progress bar again.

**So: several abnormal reboots in a row put the bootloader into a protection
state, and a warm restart does not leave it. When the same image suddenly stops
booting, stop bisecting - power the phone fully off first, wait, cold boot, and
only then judge the image.**

Also learned the hard way in the same window: a `for (;;)` polling loop placed
in the UFS init path keeps the UFS thread from ever returning, iOS cannot read
its root, and the phone reboots. Any long-running driver loop needs a thread of
its own - never the initialisation path.

### >>> UPDATE 2026-10-23 21:45: THE TOUCH CHIP ANSWERS <<<

The panel verdict (a green quarter of the screen) says the whole chain works:

    RPMh vote for ldoa6 .............. ok   (rail == 0)
    TLMM window mapped ............... ok   (gpio != 0)
    Focaltech chip id 0xA3/0x9F ...... ANSWERS   (0x56 0x62)

So the touch hardware is live: rail, pinmux window and I2C all behave. The
remaining work is turning reports into HID events, not fixing the hardware.

**How this was finally observed, after six boots of log archaeology:** the ring
is overwritten by userland output faster than it can be read back, and three
consecutive runs "stopped" at three different places purely because that is
where the last flushed line happened to be. The fix is not a better log - it is
to **answer on the panel**: `sweet_fb_mark()` paints a quarter of the screen
with the verdict (red = rail failed, blue = no TLMM, yellow = chip silent,
green = chip answered), and the user reads it off the phone. Use that for every
bring-up result from now on; it has never lied, while the log has repeatedly.

Ported from `oosexgang/hackios-xnu-kernel` to get here: its bring-up order
(RPMh vote -> reset GPIO -> poll chip id 5x200 ms expecting 0x56 0x62) and its
insight that this kernel has no clock/pin/regulator framework, so a driver does
all of it by hand in the vendor's order. Our RPMh and GENI code was already
close; the missing piece was the chip handshake and, above all, the order.

### >>> UPDATE 2026-10-23 17:30: the display is fine - `cpus=1` was the bottleneck <<<

Measured the thing that was actually unknown, with a real microsecond interval:

    SWEET FB: vsync interval 17404 us over 600 frames

**17.4 ms per vsync = 57 Hz, rock steady.** The display path is healthy. Every
earlier theory about the framebuffer being the slow part (full-panel copies,
pixel compare, timer programming) is therefore wrong for the *observed* speed.

Then the decisive experiment: the cmdline had carried **`cpus=1`** all along.
Booting with **`cpus=8`** makes the Apple progress bar *dramatically* faster -
the user's words, and the boots that used to take over an hour now get through
the same stretch quickly. iOS userland (backboardd/SpringBoard) is heavily
multithreaded and simply cannot make progress on one core.

**`cpus=8` is the correct configuration for any usability test from now on.**

State after the fast stretch: the progress bar slows again and the home screen
does not appear, but the sampler shows SpringBoard and backboardd alive (292
`SMP` lines), so they start and then wait. The sampler now prints each thread's
kernel `state` (`SMP name tN st <state> pc ...`) so the next run distinguishes
blocked-on-a-service from spinning without needing user-address symbols - the
dyld shared cache is split and no `ipsw` binary is available offline, so
symbolicating user PCs is not currently a cheap path.

### >>> UPDATE 2026-10-23 16:45: reads through the panel mapping cost as much as writes <<<

Tried to make the framebuffer cheaper by comparing each destination pixel with
the source and writing only the changed span. **It made the boot slower.**
The panel is mapped `kIOMapWriteCombineCache`, so a *read* of the panel costs
about what a write does; scanning 2.6M pixels to save a few thousand stores is a
straight loss. Reverted to `memcpy` over the rectangle the swap record already
carries.

What the log actually says (user ran one boot for over an hour):

    vsync=252600  dirty=1  presents=32090  client=2

- userland *is* submitting frames constantly (179 samples dirty=1, 94 dirty=0),
- `presents` grows 100 per 600 vsyncs, i.e. the flush divider works,
- and 252600 vsyncs at 16.667 ms each is ~70 min, which matches the hour the
  user spent watching the progress bar.

So the frames are being produced; something per-vsync is simply slow. `implied_hz`
in the old log (200442) is the number of *counter ticks per vsync-ish unit*, not
a display rate - the log line needs a real microsecond interval instead, which is
now instrumented as `SWEET FB: vsync interval %llu us over %llu frames`.

**Not yet measured:** the actual wall-clock cost of one vsync callback. That is
the next number to read, and it decides whether the time goes into `memcpy`, the
`IOMallocData`/`IOFreeData` pair each flush, or the timer itself.

### >>> UPDATE 2026-10-23 16:05: the wall is NOT touch - the control without it stalls too <<<

Compared upstream `dipa-studio/ios-sweet` (81 patches, SpringBoard home screen
reached, touch working on sweet/SM7150). Three differences worth copying:

1. **Where touch starts.** Upstream calls `sweet_touch_init()` at the end of the
   UFS init path (the UFS driver's own context), not from a display driver.
2. **How it gets power.** `sweet_rpmh_vreg_enable("ldoc11", 3200)` - an RPMh
   vote, not a PMIC write. On gauguin the same call takes `ldoa6`.
3. **Its GCC offsets are IDENTICAL to ours** (`0x5200c`, `0x18148`), and they
   work there. So our offsets are not wrong; reading zero means the context is
   wrong, not the address.

Then the measurement that matters: touch moved to the UFS context, and the boot
stopped right after `sample_start done` - 172 lines, not even `keys_init`.
**A control build with no touch call at all stalls in exactly the same place.**
So the touch driver is not what is blocking; the UFS init tail is.

Suspects in that tail, in order: `keys_init()` (reads SPMI/PMIC), then
`sweet_log_sync()` calls (each waits on the log thread that is itself expected to
flush), then `usb_probe()`. Next control: drop `keys_init()` and see whether
`usb_probe` / `init complete` are reached.

Also fixed on the way (kept, they are independent improvements):
- `touch_wait()` is now a bounded spin on `mach_absolute_time` - every blocking
  form was proven never to return (NOTES 22:38).
- Panel painting is opt-in (`sweetfb_mark=0`), 320x96 when on - full-panel
  uncached fills were the earlier "hangs".

### >>> UPDATE 2026-10-23 15:35: "hangs" were uncached full-panel painting <<<

The user watching the panel supplied the missing datapoint: **the Apple progress
bar keeps moving, just extremely slowly.** Nothing was hanging.

Cause: `sweet_fb_mark()` filled the whole 1080x2400 panel with `volatile`
stores through a `VM_WIMG_IO` (uncached, strongly ordered) mapping - about
2.6 million uncached writes per call, and the probe calls it once per stage.
That is minutes per colour, which is why:

- a colour appeared, then "nothing" for a long time (the next fill was running),
- the ring had no new lines (the boot had not reached the log thread yet),
- `mode=3`, which does no touch work at all, still looked wedged (the red fill
  before it was the cost).

**Rules from now on:**

1. Never paint the panel pixel-by-pixel on the boot path.
2. Painting is opt-in: boot-arg `sweetfb_mark=0` disables it entirely, the
   block is 320x96 when enabled, and `sweetmarkhold` adds a human-readable
   pause on top (default off).
3. A slow boot is not a hung boot - check the progress bar before concluding
   anything, and prefer log evidence over timing.

Still standing from earlier: the touch probe's own reads are fine (GCC maps and
reads `0xd010003d`); the TLMM step is where the probe stops, and the clock
offsets read back zero, so the clock step has never actually run.

### >>> UPDATE 2026-10-23 15:00: clock offsets are wrong; panics leave no trace <<<

Fresh log (banner 14:49:19 matches the image). Two hard facts:

1. **The clock step reads the wrong registers.** `gcc vote=0 rcg=0 cfg=0 dfs=0` -
   all zero. The GCC window itself is fine (control register reads
   `0xd010003d`), so `TOUCH_GCC_VOTE` / `TOUCH_RCG` are not the APCS branch
   offsets. The "turn the clock on first" attempt therefore did nothing.
   A one-shot scan of the GCC aperture is now in the code to find the real
   offsets instead of guessing again.

2. **With the (ineffective) clock step in between, the TLMM mapping no longer
   blocks**: `stage D: map TLMM (one page)` is followed by vsync 3000, UFS I/O
   and the heartbeat, so the kernel keeps running. But the phone then shows a
   **black screen with white English text - a panic page** - and nothing in the
   ring explains it, because panics are written to `gPanicBase`, which is a
   different buffer from the ring.

   Fixed in response: `paniclog_flush()` in `osfmk/arm/model_dep.c` now mirrors
   the panic text into the ring (`===== PANIC =====` ... `===== END PANIC =====`),
   so the next panic is readable from TWRP. **Do not spend another cycle without
   this** - the panic page is the only thing telling us what broke.

Method note - colour legend is now in the code as `RGB(r,g,b)` comments; the
earlier hand-written names were wrong (see 14:45 exchange with the user). Panel
order for the current build: cyan (map GCC) -> magenta (read GCC) -> azure
(clock on) -> spring (map TLMM) -> blue (map SE) -> green (done).

### >>> UPDATE 2026-10-23 14:35: touch bring-up stops at the TLMM mapping <<<

Panel markers plus a fresh log (banner 14:31:06 matches the image, so this is a
real measurement) place the stall exactly:

| stage | result |
| --- | --- |
| `AppleCLCD::start` completes | panel turns green |
| marker -> bring-up entered | panel turns blue |
| A: `ml_io_map(0x00100000, 0x60000)` (GCC) | `0xfffffe100033c000` |
| B: read GCC control register | `0xd010003d` - sane |
| C: `ml_io_map(0x03900000, 0x5b000)` (TLMM) | **stalls; nothing after this line** |

So MMIO mapping and register reads work in this port; the single failing step is
the **TLMM (GPIO) window**. Everything after it - rail vote, reset, I2C, probe -
has never run yet.

Next control (already built as `shim-b1.img`): map only the one page that holds
GPIO21/22 (`0x03950000`, `0x1000`) instead of the 0x5b000 window. If the page
works, the problem is with the large/cross-page mapping; if it stalls too, the
TLMM aperture itself is the problem.

Tooling that made this measurable, keep using it: `sweet_fb_mark(colour)` paints
the whole panel, `AppleCLCD::mark` holds each colour for a visible moment, and
`sweet_touch.c` paints a colour before/after each stage. The panel is the primary
witness; the log is corroboration (and only when the banner matches the image).

### >>> UPDATE 2026-10-23 14:40: THE "HANG" VERDICT WAS WRONG - the kernel runs fine <<<

Built a panel marker instead of relying on the log: `AppleCLCD::start` paints the
whole panel a colour once the framebuffer is registered (`sweet_fb_mark`).

**Observed on the phone (user watching the screen):**

    screen turns fully GREEN   <- AppleCLCD::start finished, framebuffer is up
    brief scroll of text
    Apple logo takes over      <- iOS userland grabbed the display

So the kernel boots, the display driver initialises, and userland comes up. It was
**never hanging**. `fastboot-cycle.sh`'s `no recovery after 172s` verdict is a
false negative: it waits for the device to drop off USB and come back into
recovery, and it reads the persistent ring - and the ring stops being refreshed
after boot (the 14:00 contradiction), so a perfectly healthy boot reports as a
hang and the run is abandoned.

**Retracted** - every "context X wedges the boot" conclusion from 12:20, 12:50 and
14:00. The exec hook, the workloop timer callback and `AppleCLCD::start` are all
usable; the experiments were reading a stale log and a recovery that does not
always happen.

**What is still true:** a kernel thread parked on a deadline is still never woken
(that one was measured directly, with the system demonstrably continuing) - so the
driver must not sleep. Everything else needs re-testing with the panel as the
witness.

**New rule: on the panel, green = framebuffer driver up. Apple logo = userland.**
That pair is the verdict from now on; the log is a supplement, not the judge.

### >>> UPDATE 2026-10-23 14:00: every start point loses the boot, and one run is unexplained <<<

Tried the remaining plausible start contexts for the touch probe:

| start point | variant | outcome |
| --- | --- | --- |
| `AppleCLCD::start` (driver start) | full read-only probe | **no log at all** |
| `AppleCLCD::start` | `mode=0` (hook runs, prints, returns) | no boot back |
| top of `bsd_init` | full read-only probe | no log written |
| top of `bsd_init` | `mode=0` | no boot back |
| exec hook | anything | no boot back (NOTES 12:50) |
| workloop timer callback | atomic increment only | no boot back (NOTES 12:20) |

**But there is a contradiction that must be resolved before reading anything into
the above:** the 13:44:33 build (AppleCLCD hook, `mode=0`) later showed a *complete*
boot in the persistent ring - 643 execs, "SYSTEM/LOGGER PIPE FOREIGNIP" traffic -
with `SWEET TOUCH: start_at_init, mode=0` in it. In other words that build **did
boot**, even though the cycle around it reported a stale log and looked like a hang.
Also: that run's `start_at_init` printed *before* the kernel banner, and none of
the later runs wrote the ring at all, so a boot can complete (or progress) without
the persistence path running.

So the working assumptions from 12:20/12:50 - "new code in context X wedges the
boot" - are **not established**; what is established is that the cycle's
`no recovery after 172s` is not a reliable verdict, because the ring is sometimes
not written even by a boot that got as far as 643 execs.

**Next thing to build, before any more driver work:** a verdict that does not
depend on the ring. The devices have to tell us they are alive - e.g. the USB
gadget enumerating (host sees a device) or the framebuffer's vsync counter being
visible some other way. Until then every "hang" here may be a log artefact.

### >>> UPDATE 2026-10-23 12:50: running ANY code in the exec hook loses the boot <<<

Four controls, each with a fresh log verified against the image banner:

| hook does | outcome |
| --- | --- |
| nothing (hook compiled out, `sweetdohook` absent) | boots, 94 execs |
| `printf` + 2 s wait + bring-up, from a workloop timer | timer fires; wait never returns; **system keeps running** |
| synchronous read-only MMIO probe (map GCC/TLMM/SE, read 3 regs) | boot stalls at 17 execs, **not even the first printf appears** |
| `sweettouchmode=0`: enter, print, return - no hardware at all | boot stalls |
| `sweettouchmode=2`: enter, print, return - literally nothing else | boot stalls |

That last row is the whole finding: **a single `printf` on the first call into
`sweet_touch_init()` from the exec hook wedges the boot.** Not the touch hardware,
not the timer, not the wait - the *act of running new code at that point*.

Placement facts checked: the hook sits after `proc_unlock(p)` and before the
`done:` label of the exec path, and the pre-existing per-exec `printf("exec %s")`
in the same block is harmless, so it is not a lock or a printf-in-lock issue.

Honest status of this hypothesis: it is not explained yet. What it does tell us is
that this hook is the wrong place to start a driver, and each experiment there
costs a manual power cycle.

**Change made in response:** `kern_exec.c` now requires `sweetdohook=1` before it
touches any of this, so a normal boot can never be lost to the hook again. The
touch path itself is left as the synchronous read-only probe, ready to be started
from somewhere better (candidates: the framebuffer's `AppleCLCD` workloop at
init time, or `bsd_init` before userland - both are contexts where a driver is
normally started).

### >>> UPDATE 2026-10-23 12:20: the workloop timer callback is the suspect, not the touch hardware <<<

Ran three variants, each verified fresh against the image banner:

| variant | what the timer callback does | outcome |
| --- | --- | --- |
| `shim-r84.img` (12:10:46) | `printf` + 2 s wait + bring-up | timer fires, **wait never returns**, system keeps running (94 execs) |
| `shim-nw.img` / `shim-nw2.img` (12:12:56) | `printf` + bring-up with **no wait** | timer never even prints; log ends at 89 execs, mid-UFS-read |
| `shim-na.img` (12:14) | `printf` only, **no hardware access at all** | boot does not come back to recovery |

The last row is the important one: a callback that only prints wedges the boot.
That kills the "touch hardware is the culprit" theory and points at the callback
**context**.

`IOTimerEventSource::timeout()` runs the action while holding the workloop gate:

    wl->closeGate();
    ... me->invokeAction(doit, me, me->owner, me->workLoop); ...
    wl->openGate();

and `printf` goes through `bsd_log_lock()` (`osfmk/kern/printf.c`). So the
candidate failure is a lock-order / self-deadlock inside the gated callback.
Next build makes the callback do **nothing but an atomic increment** - no print, no
lock, no hardware - which cleanly separates "callback context is unusable" from
"printing inside the gate is unusable".

Note on reading logs: `IOLog` does *not* reach the persistent ring (it goes to the
serial console), so a callback traced with `IOLog` looks silent even when it ran.
Use `printf` for anything that must appear in a pulled log.

### >>> UPDATE 2026-10-23 12:12: tree restored, and the log audit settled what is real <<<

**Log audit (important).** I listed every image and every pulled log by the
`Darwin Kernel Version` stamp inside it. Result: *every* log matches its image
except the 11:43 batch, which was the stale-ring artefact already described. So
the conclusions from the 22:47-23:47 runs (wl3, tc, np, m0, ks, tw2, as) are
**real** - those logs genuinely came from the kernel that was flashed.

**Tree restored.** `xnu/patches/0084-sweet-exec-probe.patch` now applies cleanly
to the 0082-2 baseline; the residue that 0084 did not carry (the GAUGUIN build
templates in `bsd/conf/Makefile.template`, `libkern/conf/Makefile.template`,
`makedefs/MakeInc.def`, plus the `sweet_sample.c` / `IORPC.h` guards) was
re-applied by hand. The tree builds and boots again: 94 execs, 7886 log lines,
no STALE.

**The touch state, now trustworthy.** With the exec hook armed at 20 execs:

    SWEET TOUCH: starting after 20 execs
    SWEET TOUCH: starting in 3 s
    SWEET TOUCH: armed workloop timer for 3 s
    SWEET TOUCH: timer fired, running bring-up        <- timer fires
    SWEET TOUCH: timed-wait experiment, 2 s
    SWEET TOUCH: wait ms=2000 deadline=907626179 now=869226180
    SWEET TOUCH: armed abortsafe, blocking            <- and then it stops

The thread is parked in the wait and never returns, **but the system keeps
running** (94 execs, the rest of the log is normal). So the hang is not caused by
the wait itself - it is caused by whatever the *bring-up* does when it finally
runs, and the wait is only the thing that delays it.

That is the experiment to run next: **remove the wait from the bring-up** and
let the bring-up run immediately in the timer callback. If the phone wedges, the
bring-up is the killer and we bisect inside it; if it survives, the bring-up is
fine and the wait is the only broken thing - and then the driver must be written
to never sleep at all.

### >>> UPDATE 2026-10-23 11:50: WHOOPS - the log puller was lying, and the tree got reset <<<

Two mistakes worth recording, both mine:

1. **I reset the patched tree to the bare upstream commit** (`git checkout -- .`)
   while trying to "revert to a known-good touch version", which threw away the
   working tree of 0084 and friends. `deps/apply-patches.sh` could not restage it
   (`refusing to overwrite sweet_libpthread` - those dirs are tracked in the
   committed tree), so the tree now holds the **baseline** patch set only: touch
   is called from `sweet_ufs.c`, `kern_exec.c` has no hook, `files.arm64` has no
   `SweetTouchTimer`. It builds and boots.
2. **`sweet-log-pull.sh` reads a persistent ring in `userdata`, not this boot's
   console.** When a boot dies before `sweet_log_start()` runs, the puller happily
   returns the *previous* boot's log. That is why several "identical" runs came
   back byte-identical (`1670d2a5...`) with the banner of an older kernel - and
   why the last three cycles showed the 11:36 kernel while flashing an 11:43 one.

**Rule to keep: always check the `Darwin Kernel Version` timestamp in the pulled
log against the image's own banner before believing any result.** The image's banner
can be read directly:

    python3 - <<'PY'
    d=open('shim/out/X.img','rb').read(); i=d.find(b'Darwin Kernel Version')
    print(d[i+22:i+95].decode('utf8','replace'))
    PY

What is actually established today, after removing the runs that were really
reading a stale log:

* workloop timer callback **does fire** (observed in a run whose log *was* fresh);
* timed waits (`assert_wait_deadline`, `delay`, `THREAD_ABORTSAFE`, workloop,
  `thread_call`) **do not wake** a kernel thread created after userland is up;
* `thread_call` in `sweet_touch.c` and driving hardware from the vsync/timer
  callback both produced boots that never came back to recovery.

### >>> UPDATE 2026-10-23 11:40: phased (no-sleep) bring-up still wedges the boot <<<

Rewrote the driver to never sleep: `touch_step()` is called from the repeating
100 ms `IOTimerEventSource`, advances a phase counter and does one bounded chunk
(map MMIO / clocks / reset + rail vote / probe / one report read). All `touch_wait`
calls became "advance N/100 ticks from now".

Result: **the boot wedges again** (Apple logo, no `recovery`, no capture file).

So the hang is **not** caused by sleeping - it is caused by touching the touch
hardware from that context at all. Combined with 11:30 (thread_call wedged the boot
even with the bring-up never reached) this points at the **MMIO/GPIO/SE access
itself** being the killer when it runs after userland is up, i.e. probably a
register access that never completes (GENI SE or TLMM) with no timeout in the exec
path.

Action taken afterwards: revert to the last version that boots and stop calling
hardware from the timer until this is understood.

### >>> UPDATE 2026-10-23 11:34: the workloop timer DOES fire - but the wait after it still does not wake <<<

Ran the bring-up from the workloop timer callback with a 2 s timed wait as its
first statement (and tried `THREAD_ABORTSAFE`, the one argument by which
userland's working `mach_wait_until` differs from our failing `THREAD_UNINT`):

    SWEET TOUCH: armed workloop timer for 2 s
    SWEET TOUCH: timer fired, running bring-up        <- THE TIMER FIRES
    SWEET TOUCH: timed-wait experiment, 2 s
    SWEET TOUCH: wait ms=2000 deadline=982381670 now=943981671
    SWEET TOUCH: armed abortsafe, blocking
    (nothing - 1,700 more lines of log)

Two separate conclusions:

1. **The workloop timer works.** It fires, from a thread started in the exec path,
   ~2 s after arming. The earlier "never fires" runs (NOTES 23:20) must therefore
   have failed for a different reason - most likely the bring-up they ran hung or
   died before the next flush, and the console is unreliable (NOTES 23:26). **A
   workloop timer callback is a usable, live kernel context.**
2. **The timed wait still never wakes**, even from that live context, and
   `THREAD_ABORTSAFE` does not change it. So the defect is not about *where* the
   wait happens, and not about the interruptible flag - it is in the deadline
   expiry path for kernel threads generally.

Next, and it is now a much narrower question: what does `thread_block` return, and
does the thread ever come back at all? Instrument `thread_block`'s return in
`sweet_touch.c` and, more usefully, print `current_thread()->wait_timer_armed` and
the timer list state from a *second* timer callback while the first thread is
parked. That distinguishes "timer was never armed" from "timer fired but the wakeup
was lost".

Also worth testing now that timers are known to work: **poll instead of sleep.**
Let the workloop timer fire every 100 ms and do one bounded step of the bring-up
per callback, keeping all state in globals - no waiting at all. That fits the
proven-good mechanism and avoids the broken one entirely.

### >>> UPDATE 2026-10-23 11:30: SOLVED - thread_call in sweet_touch.c breaks the boot <<<

Bisected properly. Same kernel, same everything else; the ONLY change was
reverting `bsd/dev/sweet_touch.c` from the `thread_call` version back to the
workloop-timer version:

| kernel | execs | outcome |
| --- | --- | --- |
| current source (thread_call) | 4 | **hung on the Apple logo**, needed a power cycle |
| current source, touch code reverted | **90** | boots, "armed workloop timer for 2 s" |

So the regression is the **`thread_call` use inside `sweet_touch.c`**
(`thread_call_allocate` + `thread_call_enter_delayed` from a kernel thread started
in the exec path), not the touch driver as a whole and not the earlier
`sweettouch=0` kill switch (that test was invalid - the kill switch itself was only
reached *after* the thread started, so the thread_call had already been armed...
and in fact the hang reproduced with `sweettouch=0` for a different reason: the
same kernel still contained the thread_call API path linked in).

Important lesson recorded: a boot that hangs on the Apple logo is **invisible to
adb** (no recovery, no shell) - only a 15 s power cycle gets it back, and the
device must then be steered manually into TWRP. Every kernel experiment therefore
has to be assumed to cost one manual recovery.

Current state of the tree: touch back to the **workloop-timer** version, which
boots. `sweet_touch_timer_arm()` still never fires (NOTES 23:20), so touch is
still not bringing up - but the boot is healthy again, which is the platform to
continue on.

### >>> UPDATE 2026-10-22 23:50: the new kernel hangs with touch DISABLED - it is not touch <<<

After the thread_call run stalled at `exec seputil` twice in a row, ran two
controls:

| image | touch | outcome |
| --- | --- | --- |
| `/tmp/m0` (current source, `sweettouchmode=0`, inline, threshold 6) | never reached | 4 execs, stall at `exec seputil` |
| `/tmp/np` (same, probe removed from exec) | never reached | 4 execs, same stall |
| `/tmp/recheck` (`shim-wl3.img`, built 23:18) | reaches "armed workloop timer" | **92 execs, boot completes** |
| `/tmp/ks` (current source, `sweettouch=0` kill switch, touch never runs) | disabled | **hung - device off USB, needed power cycle** |

So the regression is **in the current kernel, not in the touch code path at all** -
with touch disabled entirely it still wedges. The last image that boots is the one
built at 23:18 (`shim-wl3.img`); everything after it (thread_call, thread removal,
exec-hook edits) does not.

It stalls right after `exec seputil`, the first program that talks to our IOKit
services (SEP), so the suspicious area is what our own kernel changes do in that
window - candidates, all added long ago but only exercised when a userland program
exists: the `IOUserClient` matching/gating hooks, the `IPC mqueue` hooks, and
`task.c`'s block-trace ring (called from `thread_block`).

Next: bisect by disabling our own hooks in that window one at a time, starting
with `sweet_block_trace` in `thread_block` - it is in the hottest path in the
kernel and is the cheapest thing to rule out (`sweetlog=1` runs it; a boot with
`sweetlog=0` that gets through would point straight at it).

### >>> UPDATE 2026-10-22 23:38: thread_call version built and flashed, but the boot window got thin <<<

Replaced the `IOWorkLoop` timer with `thread_call_allocate` +
`thread_call_enter_delayed` (scheduler-owned call threads, created before
userland, not parked in the timed wait that never wakes). Also removed the
`vsyncFired` -> touch call that hung the phone, keeping only
`sweet_log_flush_now()` every 30 frames, so the console no longer depends on the
`tsleep`-driven flush thread.

Three runs, none of which reached the touch start:

| run | `sweettouchafter` | outcome |
| --- | --- | --- |
| `/tmp/tc` | 40 | 25 execs, vsync 1800 - threshold never reached |
| `/tmp/tc2` | 12 | boot stalled at 2,506 lines (10 execs) |
| `/tmp/tc3` | 6 | boot stalled at 1,833 lines (4 execs) |

The last two are the **intermittent early-UFS stall** already recorded (4-6k
lines, "no recovery after 172 s", same image boots fine another time), not a new
failure - but it makes short-window experiments expensive.

Next run should keep `sweettouchafter=6` (touch starts early, no dependence on a
long boot) and simply be retried until the boot gets through. The thing to look
for is `SWEET TOUCH: thread call ran` - that single line decides whether
`thread_call` is the working wakeup path.

### >>> UPDATE 2026-10-22 23:30: running the bring-up inside vsyncFired HANGS the phone <<<

Tried the last obvious shortcut: call `touch_bringup()` synchronously from
`AppleCLCD::vsyncFired` (delay measured in frames, 2 s = 120 frames).

Result: **the phone disappeared from USB entirely** - no TWRP, no fastboot, no
capture file at all; it needed a 15 s power+vol-up press. Recovery confirmed by
the user, device back in TWRP.

So `vsyncFired` is **not** a safe context for driver bring-up: it runs as an
`IOTimerEventSource` callback (interrupt/timer context, and it takes
`IOLockLock(fb->fLock)` immediately after), so any blocking bus access or
`ml_io_map` from there wedges the machine. The same applies to polling the touch
IC from it.

**Boundaries established today, all measured on the phone:**

| context | timed waits wake? | usable for touch bring-up? |
| --- | --- | --- |
| kernel thread started at boot | no (30 s wait never returns) | no |
| kernel thread started at Nth userland exec | no (2 s never returns) | no |
| `IOWorkLoop` timer (own loop) | no (2 s never fires) | no |
| `vsyncFired` (framebuffer timer) | callback *does* run | **no - hangs the phone** |

That leaves one sound path: **a thread that is already sleeping successfully**.
Userland proves timed sleeps work (backboardd lives in `mach_wait_until`), so the
touch work should run from **a real BSD kernel_proc-style thread created with
`kernel_thread_start` *after* `bsd_init` has fully started** - i.e. the same
mechanism the log thread uses, which does flush at least once. Alternatively give
the touch bring-up a **deferred-call** (`thread_call_allocate`) which runs on a
timer-call thread that is created by the scheduler itself rather than by us.

Next concrete step: use `thread_call_allocate` + `thread_call_enter_delayed` for
the initial delay, and run the touch poll loop from the *same* thread call
re-arming itself. That is the standard, context-safe way to do this in XNU and it
does not add a thread of our own.

### >>> UPDATE 2026-10-22 23:26: the vsync callback DOES call touch - the console is what is lying <<<

Checked the built image rather than the source: `AppleCLCD::vsyncFired` contains
`bl sweet_touch_tick` (`+80 -> 0xfffffe00074e5720`), and `sweet_touch_tick`'s
disassembly does exactly the guard we wrote (`cbz` on the static `kicked`). So the
call *is* wired up and *is* linked.

It still prints nothing. The reason is in the log path itself:
`sweet_log_start()` runs a **`tsleep()`-driven** flush loop
(`bsd/dev/sweet_ufs.c:1120`). `tsleep` parks a thread on a timed wait - **the same
mechanism that never wakes in this port**. So `printf` output is only readable
when a flush happens to be batching it, and a callback that runs between flushes
looks silent even though it ran.

Practical consequences, and they matter for reading every earlier result:

* absence of a log line is **not** evidence that code did not run - only that no
  flush followed it;
* the "-186 lines of log after the touch thread blocked" observations remain
  valid (that output *was* flushed), but "no `sleep`/`tick` marker" is weak;
* to observe kernel activity reliably, something must **flush on demand** rather
  than on a `tsleep` tick - e.g. have the vsync callback call `sweet_log_flush()`
  directly, which runs in a context we have proven executes (it prints its own
  `SWEET FB: vsync=` lines from that same batched buffer).

Next concrete step: call `sweet_log_flush()` from inside the vsync callback right
after `sweet_touch_tick()`, and drop the touch thread's dependence on *any*
timed wait (have `sweet_touch_tick` run the bring-up synchronously on the first
frame past the delay). That gives an observable, self-flushing kernel context.

### >>> UPDATE 2026-10-22 23:20: IOWorkLoop has the SAME defect - it is the same thread mechanism <<<

Rewrote the gate as `IOTimerEventSource` on an `IOWorkLoop`
(`iokit/Kernel/arm/SweetTouchTimer.cpp`, C-callable `sweet_touch_timer_arm()`,
`files.arm64` updated). Three runs:

| attempt | output |
| --- | --- |
| workloop timer, timer not retained | "armed workloop timer for 2 s", never fires |
| + `retain()` on workloop and timer | "armed workloop timer for 2 s", never fires |

and in the same runs the log continues ~1,300 lines (~40 s) with a 2 s timer.

Why: `IOWorkLoop::init()` creates its worker with **`kernel_thread_start`**
(`iokit/Kernel/IOWorkLoop.cpp:180`) and parks it with
`thread_block_parameter` - **exactly the mechanism that never wakes here**. So a
fresh `IOWorkLoop` is no better than a bare kernel thread; the framebuffer's timer
works only because backboardd/AppleCLCD attach during boot and something else
keeps that loop spinning.

This is the real shape of the remaining bug: **timer-driven wakeups for threads
created after userland is up do not happen in this port**, regardless of whether
the thread is hand-made or an `IOWorkLoop` worker.

Options, in order of cost:
1. **Run the touch poll inside an existing, already-spinning loop.** backboardd
   proves userland sleeps work (`mach_wait_until`); the framebuffer's own vsync
   timer already fires reliably *and* runs in kernel - so the cheapest place to
   poll the touch IC is **from `AppleCLCD::vsyncFired`** (or a second timer
   attached to the *framebuffer's* existing, working `fWorkLoop`). That needs no
   new thread and no new timer plumbing.
2. Fix the kernel wakeup path itself (larger, and it currently has no minimal
   repro that fails - our probe thread *did* wake).

Given backboardd presents at 60 Hz on the framebuffer's timer, option 1 is the
pragmatic route and costs one call from a callback that is already proven to run.

### >>> UPDATE 2026-10-22 23:11: the touch thread blocks correctly and is simply never woken <<<

Made `touch_wait()` report every stage:

    SWEET TOUCH: wait ms=2000 deadline=990761535 now=952361536
    SWEET TOUCH: armed, blocking

and then **nothing** - the log continues for 1,365 more lines, past `vsync=2400`
(~40 s of real time), with a 2 s deadline. So this is now fully pinned down:

* `assert_wait_deadline` **accepts** (returns THREAD_WAITING - the "refused"
  branch did not fire);
* `thread_block` **blocks** (the thread does not run past that line);
* the 2 s deadline **never expires for this thread**.

Three variants tried in this same thread, all ending at "armed, blocking":
event as `static int`, event as `static char`, and the probe's exact idiom. So it
is not the event address and not the idiom.

Contrast with the same boot: `sweet_wait_probe_start()`'s thread - started from
the same call site, immediately after - does wake after its 1 s deadline. The
difference left is that the probe thread **calls `thread_terminate_self()` right
after waking** and lives for one wait, while the touch thread is long-lived.

Best hypothesis to test next: the touch thread is not actually a **free-running
kernel thread** by the time it blocks - `kernel_thread_start` threads are expected
to call `thread_terminate_self()` (or be joined); every other kernel thread in
this tree that sleeps does so inside a workloop. A cleaner fix than fighting the
scheduler is to **move touch onto an IOWorkLoop** (which is how the framebuffer
already does its 60 Hz timer successfully - `AppleCLCD`'s `IOTimerEventSource`
fires reliably). That would give touch both a working timer and a correct
thread lifetime.

### >>> UPDATE 2026-10-22 23:05: 23:00 retracted - the timebase is fine (1.06x, not 1.25x) <<<

Measured it instead of deducing it: the vsync report now prints the implied
timebase frequency, computed from the tick delta between two 600-frame reports and
the programmed 16,667 us period.

    vsync=600  implied_hz=20373769
    vsync=1200 implied_hz=20373649
    vsync=1800 implied_hz=20307935

If the counter ran at 24 MHz while the kernel scaled with 19.2 MHz, this number
would read **24,000,000**. It reads **20.37 million**, i.e. the timer fires
`20373769/19200000 = 1.061x` later than programmed - a ~6% scheduling/timer
latency, not a 25% clock error.

**So the 23:00 note was wrong** and is retracted: the timebase is not mismatched,
kernel time is not 0.8x wall clock, and the 2 s deadline arithmetic
(38,399,995 ticks = exactly 2 s at 19.2 MHz) is simply correct. The earlier
"vsync 1800 should take 30 s but took 24 s" reasoning was bad arithmetic on my
part: 1800 frames at 16,667 us is 30 s of *programmed* time, and a 6% lateness
cannot turn that into 24 s.

What survives, and is still the useful result:

* the wakeup mechanism **works** (both the probe thread and an inline 1 s wait in
  the touch thread woke);
* the touch thread's *own* `touch_wait(ms)` has not yet been shown to return -
  every run so far ended before its next line, and each run's boot window is only
  ~150 s while the touch path has several waits stacked (3 s, 10 ms, 2 ms, 300 ms);
* so the remaining touch question is simply **whether it completes inside the
  window**, which the next run answers by printing on every step.

Rule to keep: measure a frequency before building a story on it.

### >>> UPDATE 2026-10-22 23:00: FOUND THE REAL BUG - the timebase is 24 MHz, not 19.2 MHz <<<

Put a probe thread next to the touch thread (identical
`assert_wait_deadline`+`thread_block`), then tried the same code inline inside the
touch thread. Same boot, three results:

    SWEET WAITPROBE: thread running, blocking for 1 s
    SWEET TOUCH: probe-style wait 1 s
    SWEET WAITPROBE: woke (wresult=0)          <- probe wakes
    SWEET TOUCH: probe-style wait woke         <- inline block in touch wakes
    SWEET TOUCH: wait ms=2000 deadline=904629001 now=866229006

So the mechanism works - and the deadline arithmetic is **correct**:

    deadline - now = 38,399,995 ticks / 2 s = 19,200,000 Hz   (matches the ADT)

Which finally explains everything: `clock_interval_to_deadline` converts using the
**declared 19.2 MHz** timebase, and `deadline` is therefore 2 s in *declared*
units. But the hardware counter runs at **24 MHz**, so the kernel believes far
less time has passed than really has, and a wait that should end in 2 s is
scheduled ~2.5 "kernel-seconds" away - longer than any boot window.

Independent confirmation from the frame timer: vsync is programmed for **16,667 us**
(`SWEET_FB_VSYNC_US`) and the log reaches `vsync=1800`. At the declared 19.2 MHz
that is 30 s of kernel time; measured against the real 24 MHz counter those same
1800 frames take `1800*16667*19.2/24 = 24.0 s`. **Everything in the kernel runs a
consistent 0.8x of wall-clock time** - i.e. all kernel timeouts are 1.25x longer
than intended.

That is one-line fix territory: the SM7125 XO is **19.2 MHz** as declared, so the
question is whether our platform expert is programming the architected timer with
the wrong divider, or the ADT value never reaches
`gPEClockFrequencyInfo.timebase_frequency_hz`. Check what the kernel prints/believes
for the timebase, then compare against `mach_absolute_time()` deltas measured
against the framebuffer's own 60 Hz cadence (a clock we control).

Practical consequence for touch: with the real timebase known, the touch delay
can simply be set in **real** seconds (currently it is inflated 1.25x, which is
not why it never woke - it never woke because 45 s of kernel time > boot window;
45 * 1.25 = 56 s of wall clock, still inside 150 s, so the 45 s gate alone did not
explain it -- the inner `touch_wait` calls each inflating 1.25x on top of a
*never-bounded* loop is what kept it out of the window).

### >>> UPDATE 2026-10-22 22:52: moving the start later does not help - the wakeup gap is general <<<

Moved `sweet_touch_init()` out of `sweet_ufs.c` (boot-time) into the exec hook,
so the touch thread starts once userland is established:

* `sweettouchafter=N` (default 20) - start on the Nth exec, not the first;
* default touch delay lowered 45 s -> 3 s (userland is up by then).

Two runs:

| when started | result |
| --- | --- |
| on **1st exec** (launchd, UFS still busy) | "starting in 3 s", boot **stalled at 3,427 lines** |
| on **40th exec** (userland established) | "starting after 40 execs", "starting in 3 s", **`slept` never appears**, 123 execs, vsync 1800 (~30 s) elapsed |

So the touch thread's *timed* wait does not resume **even with userland fully
running**, while userland's own sleeps (backboardd in `mach_wait_until`) work
fine. That narrows it decisively: the gap is not "too early in boot" and not
specific to the touch driver - it is **kernel-thread timed waits in this port**,
i.e. the deadline path of `assert_wait_deadline` for a `kernel_thread_start`
thread never re-runs it.

That is one concrete kernel bug left between us and working touch, and it is now
well characterized:
* thread creation: fine (start markers appear);
* thread scheduling: fine (it runs until the wait);
* timer: fine (vsync advances throughout);
* **timer -> thread wakeup for kernel threads: broken.**

Next, minimal reproduction with nothing else in the picture: a kernel thread
started from the exec hook that does `assert_wait_deadline(&chan, THREAD_UNINT,
now + 1 s)` and prints before/after. If it also never wakes, the defect is in
`waitq_assert_wait64_locked`'s deadline arming and the fix is localized.

### >>> UPDATE 2026-10-22 22:47: neither sleep nor spin works for the touch thread <<<

Three attempts to get the touch thread past its start-up delay, all measured on
the phone:

| attempt | result |
| --- | --- |
| `assert_wait_deadline` + `thread_block` (original) | "starting in 30 s", then **nothing** for 50 s of log |
| `delay()` in 50 ms slices | "thread running, entering wait", then **nothing** for 30 s |
| busy-wait on `mach_absolute_time()` | boot **wedges at 596 lines** (spin starves UFS on 1 CPU) |

Proof the thread itself is fine: the added `printf("SWEET TOUCH: thread
running, entering wait")` **does** appear, so `kernel_thread_start` works and the
thread runs up to the wait. What never happens is the **wakeup**.

`delay()` is not an alternative - `_clock_delay_until_deadline()` uses
`assert_wait_deadline(event=clock_delay_until)` + `thread_block()` as well, so it
inherits the same problem. The busy-wait proves the *timer* itself runs (the
framebuffer vsync keeps counting during those same seconds), so what is missing
is specifically the **timer-triggered thread wakeup** for a kernel thread that
was started at this point in boot.

That is a scheduler/timer-integration gap in this port, not a touch bug - and it
is worth fixing on its own, because any kernel thread that sleeps at start-up
hits it. The next probe should be a minimal one: a kernel thread started from the
same place that does `assert_wait_deadline(..., deadline = now + 1 s)` and prints
before/after, so the failure is reproduced with nothing else involved.

Untried escape hatch if that turns out to be expensive: **start the touch thread
later**, from the first userland process context (e.g. on the first `exec` of a
known daemon), where sleeps are known to work - backboardd's own
`mach_wait_until` sleeps fine (NOTES 22:00), which proves the mechanism works
once userland is running.

### >>> UPDATE 2026-10-22 22:38: FOUND IT - the touch thread's sleep never wakes <<<

Added one line after the gate:

    touch_wait(delay_s * 1000u);
    printf("SWEET TOUCH: slept %u s, continuing\n", delay_s);

Run with `sweettouchdelay=30`, captured window reaching **vsync 3000 (~50 s)**:

    SWEET TOUCH: starting in 30 s
    (nothing - no "slept")

So the touch thread **enters `touch_wait()` and never comes back**, even though the
deadline is 30 s and the log continues for ~50 s. That is the actual touch
blocker, and it explains every earlier observation (45 s message, then silence).
It also means the driver was never broken: it never got past its own sleep.

`touch_wait()` is:

    clock_interval_to_deadline(ms, NSEC_PER_MSEC, &deadline);
    assert_wait_deadline(&touch_sleep_chan, THREAD_UNINT, deadline);
    thread_block(THREAD_CONTINUE_NULL);

Two candidate causes, and the next run distinguishes them:
* `assert_wait_deadline` + `thread_block` does not arm the timer the way the code
  expects (the deadline is silently dropped);
* the thread is created before the timer subsystem is usable at that point in
  boot, so the wakeup is never delivered.

Either way the fix is the same and is small: sleep on a **timer that is known to
work in this tree** (`delay()`/`clock_delay_until()` - the spin/yield path, no
blocking) or re-create the thread after userland is up. The `sweettouchdelay`
value is not the problem.

Note: two runs also stalled inside UFS reads (4-6k lines) with *this* image while
the previous image booted fine twice, so the stall is intermittent and not tied
to the touch change.

### >>> UPDATE 2026-10-22 22:30: touch already exists - it is delayed 45 s and never gets there <<<

Important discovery while starting the touch milestone: **a real touch driver is
already in the tree and already initialised.**

* `bsd/dev/sweet_touch.c` - FIFO I2C touch bring-up on QUPv3 GENI. For gauguin:
  **SE8 @ 0x988000, TLMM reset gpio21 / irq gpio22 (falling), Focaltech @ 0x38,
  rail PM6350 LDO6A ("ldoa6", 1.8 V)**, no board enable. (For sweet: SE7, GT9896.)
  It does clock voting, GPIO, RPMh rail voting, then probes the IC - and feeds
  `sweet_hid_touch()`.
* `iokit/Kernel/arm/hid/SweetHID.cpp` - `SweetHIDButtons` and `SweetHIDTouch`
  (`kHIDPage_Digitizer`/`kHIDUsage_Dig_TouchScreen`), both registered, with
  `DisplayIntegrated` and 68x151 mm surface properties. The touch service is
  wired to `sweet_hid_touch()`, which `sweet_touch.c` calls on real reports.
* `sweet_ufs.c:836` calls `sweet_touch_init()` - so the driver does start.

**The blocker is the start-up delay**: `touch_thread` waits
`sweettouchdelay` seconds (default **45**), then does the risky part, so that a
hung bus does not take the GUI down with it. Every serial log so far ends
*before* that deadline (the ~110 s reset lands first), so the driver prints
"starting in 45 s" and nothing else - which is exactly what the logs show.

Tried to shorten it (`sweettouchdelay=5`), but that boot stalled much earlier,
in UFS reads (one line of touch output, 6,533 lines total), so the result is
inconclusive; the next run has to start from a clean TWRP boot.

So touch is **not** a from-scratch driver task: it is a matter of getting the
existing one past its 45 s gate inside the boot window, and then reading its
probe output (`SE8 fw`, `probe xfer`, `probe info`) to see whether the IC answers.

### >>> UPDATE 2026-10-22 22:27: SpringBoard is a healthy multi-threaded app whose MAIN thread is parked <<<

Thread snapshot at exec of the *next* process (i.e. SpringBoard fully started),
9 threads:

| tid | run | state | waitq | notes |
| --- | --- | --- | --- | --- |
| **220** | 0 | 1 | **PORT** | **main thread, parked** (unchanged across 3 samples) |
| 287, 325, 481, 491 | 1 | 4 | - | running/on-CPU work-queue threads |
| 353, 482 | 0 | 0x41 | TURNSTILE | blocked on locks |
| 483, 492 | 0 | 1 | QUEUE | blocked on queues |

Main thread mask `0x1181180` decodes to **WAITQ | TH_UNINT | TH_RUN | TH_IDLE |
AS_ARITHM** - and `TH_UNINT` is the important one: the main thread's
`receive` is **uninterruptible**, so it will sit on that port for as long as
nobody sends to it. It is *not* spinning, not retrying, and not going to time out.

This is the normal shape of a UIKit app that has finished launching and is
waiting for its **event loop** to be fed. So the display-side story is now
complete and consistent end to end:

* our framebuffer presents (180 frames, 5 colours, 0 backboardd crashes);
* the bundle is intact; the start-up directory scan is a burst, not a loop;
* 8 worker threads are alive and doing work;
* **the main thread simply has nothing to draw and no events to process.**

So the remaining gap is not inside SpringBoard - it is whatever is supposed to
**send it events** (a scene/session from the UI host, or the touch path feeding
the event queue). That reframes the remaining work: the next real milestone is
**touch**, not more display probing - a touch that reaches SpringBoard wakes tid
220 and the pipeline above is already proven ready to present it.

### >>> UPDATE 2026-10-22 22:24b: the bundle is COMPLETE - the scan is start-up, not a missing file <<<

Checked the bundle on the root image before assuming a missing resource:

    77 entries, including Info.plist, SpringBoard (Mach-O 64-bit executable),
    Assets.car, _CodeSignature, all the *lproj and the Default*State plists.

So **nothing is missing from the bundle** and the earlier "it cannot find
something in its own directory" reading is too strong. The timeline shows the 40
`SWEET DIR` reads clustered between lines 8,213 and 15,174 of a 23,831-line log -
i.e. a **burst during start-up**, not an endless loop spread over the whole boot.
The 92 `getdirentries64` in the histogram are the same burst counted.

Meanwhile the display is healthy in this run: `presents=180`, 5 colours,
backboardd not crashing. The 8 crashes in the log are **CommCenter (3) and
driverkitd (3)**, unrelated to the display, and **SpringBoard itself never
crashed**.

Revised picture: SpringBoard enumerates its own bundle once at start-up (normal
behaviour for an app resolving its resources), then goes quiet and sleeps in
`mach_wait_until`. **That is not a stall - it may simply be idle**, waiting for a
task/session that nothing in this environment ever delivers.

Which means the next question is not "what file is missing" but **"what is
SpringBoard supposed to be displaying, and who tells it to"** - i.e. whether the
XPC/lockdown-side service that hands SpringBoard its scene is running at all.
That is a userland-services question, and `sweetdump` on SpringBoard's *threads*
(after the burst) is a better instrument than more syscall head-counting.

### >>> UPDATE 2026-10-22 22:24: the scanned directory is SpringBoard/System/Library/CoreServices/SpringBoard.app <<<

    SWEET DIR: live path = /System/Library/CoreServices/SpringBoard.app

SpringBoard enumerates **its own bundle directory** over and over (40+ times,
always fd 3). fd 3 is **inherited** from launchd, not opened by SpringBoard, which
is why the fd->path table said "?" until the dump resolved it live.

Notable: enumerating its own bundle directory in a loop is what SpringBoard does
when it is looking for a resource **inside the bundle** it cannot find -
`Info.plist` siblings, the scene/artifact cache, or the `Assets.car`/`en.lproj`
entries. Combined with the earlier facts (it sleeps in `mach_wait_until`, does no
UI work, presents nothing of its own) the picture is consistent: **SpringBoard
cannot find something in its own app directory and retries forever**.

Next: list the bundle on the device and compare against what a working iOS 16
install has. The cheap check is whether the directory has entries at all (an
empty/mangled HFS+ directory would produce exactly this loop) and whether
`Assets.car` and `Info.plist` are present and readable.

### >>> UPDATE 2026-10-22 22:16: the directory tracer now takes a safe path to the fd (not yet run) <<<

The first tracer hung two boots in a row. Cause: it **copyin()-ed `uap->path`
again** after `openat_nocancel` had already consumed that user pointer - a second
user access from the syscall return path is exactly the kind of thing that
faults/hangs under this bring-up. Rewritten to resolve the path through the fd
table instead, with no user-memory access at all:

    fp_getfvp(p, fd, &fp, &vp)     -> takes the fd lock itself, do not hold it
    vnode_getwithref(vp)           -> hold a ref while reading the path
    vn_getpath(vp, buf, &pathlen)  -> pathlen is int*, not size_t
    vnode_put(vp); fp_drop(p, fd, fp, 0);   -> fp_drop's 4th arg is `locked`, an int

Builds clean. **Not yet verified on device**: the phone dropped off USB right
after the last flash, so the `SWEET DIR:` lines have not been seen. Next run with
`sweetdirs=SpringBoard` is the decisive one - if it boots, the 40-line cap will
name the directory tree SpringBoard keeps re-reading.

Signature traps hit while writing it (all cost a build each):
`fileproc_guard_t` does not exist in this TU, `vn_getpath`'s length is `int *`,
`fp_drop`'s last parameter is `int locked` (not a pointer).

### >>> UPDATE 2026-10-22 22:06: directory tracer added; first run hung the boot <<<

Added `sweetdirs=<proc>` (in `bsd/vfs/vfs_syscalls.c`): `openat` records
`fd -> path` for the watched process, `getdirentries64` prints the path for its
fd (first 40 lines only). Build clean, but the first boot **did not come back to
TWRP within 172 s** and the phone fell off USB, so there is no data yet and the
device needs a power-cycle.

Two lessons worth keeping:
* the helper block was first inserted **between `int` and the function name**
  (the anchor matched `openat(proc_t p, ...) {`), giving "cannot combine with
  previous 'int' declaration specifier" - when anchoring on a function, anchor on
  the whole `int\nname(` pair or insert after the closing brace;
* `copyinstr` is already declared in this TU; declaring it again locally
  conflicted with the real prototype.

Whether the hang is caused by the tracer or is the usual ~110 s reset landing in
the wrong place is unknown - the next run will say (the tracer prints at most 40
lines, so it should not be able to flood the console).

### >>> UPDATE 2026-10-22 22:03: SpringBoard is *scanning directories* in a loop <<<

Syscall histogram for SpringBoard after the display came up:

| # | syscall | count |
| --- | --- | --- |
| 375 | `kevent_id` | 127 |
| 399 | `close_nocancel` | 96 |
| **344** | **`getdirentries64`** | **92** |
| **346** | **`fstatfs64`** | **92** |
| 368 | `workq_kernreturn` | 72 |
| 478 | `bsdthread_ctl` | 26 |
| 153 | `pread` | 22 |
| 336 | `proc_info` | 15 |
| 374 | `kevent_qos` | 15 |
| **340** | **`lstat64`** | **14** |
| 170 | `csops_audittoken` | 9 |
| 463 | `openat` | 9 |

Compared with the earlier histogram (before the display came up: no
`getdirentries64`/`fstatfs64`/`lstat64` at all), the new profile is unmistakable:
**92 directory enumerations + 92 statfs + 14 lstats**. That is a *filesystem
walk*, not UI work - SpringBoard (or something it drives) is crawling a directory
tree over and over.

Combined with the `mach_wait_until` sleeps from the previous note, the shape is
"scan a directory tree, sleep, scan again" - i.e. **it is polling for files that
never appear**. The prime candidate is a cache/asset directory on the iOS root:
`/System/Library/Caches/`, a font asset dir, or the SpringBoard icon/scene
caches.

Next: find *which* directory. `getdirentries64` takes a file descriptor; logging
the resolved path per fd (a one-shot map built on `openat`) would name the tree
being scanned - cheap and decisive.

### >>> UPDATE 2026-10-22 22:00: SpringBoard is sleeping in mach_wait_until - a timed retry <<<

Block ring at SpringBoard's exec (31,460 blocks total, 256 shown), main thread
tid 217 breaks down as:

| kind | count | meaning |
| --- | --- | --- |
| `cont=fffffe0007315900 wqt=0` | 60 | `_thread_preempted` - **running**, preempted |
| `cont=0 wqt=1 ev=fffffe000731aab8` | 14 | **real wait**, on a port waitq |
| `cont=0 wqt=0` | 4 | other waits |
| `cont=0 wqt=2` | 1 | turnstile (a lock) |

Resolving `ev=fffffe000731aab8` against the unstripped kernel:

    fffffe000731aaa8  _mach_wait_until_continue   (osfmk/kern/clock.c:1511)

so those 14 blocks are `mach_wait_until` - **`usleep`-style timed sleeps**, each
returning `KERN_SUCCESS` and coming straight back. That is a retry loop with a
delay, not a deadlock and not a missing service.

Combined with the pixel evidence (5 colours, presenting at 60 Hz, zero crashes),
the honest reading is: **the display path is up and SpringBoard is alive and
looping on a timer**, presumably waiting for something it polls for (a scene, a
lock state, or a session) that never becomes ready.

Next: the 14 waits are on a **port** waitq, and we now know the dump cannot name
the port (NOTES 18:07). The cheaper question is *what SpringBoard is polling* -
and the most direct evidence left is **its own stdout**, which is quiet after the
`/product` lookups. Capturing its last lines (or the first line after the display
comes up) is the next step, rather than another kernel probe.

### >>> UPDATE 2026-10-22 21:57: `/product` now resolves; SpringBoard's loop changed shape <<<

The ADT had **no `/product` node** (`tools/mkadt.py` only emitted one when a
D22AP device tree was present at `research/ipsw-x/d22ap.adt`, which is not in the
repo), and SpringBoard asked for `IODeviceTree:/product` **12 times a boot**,
getting `-> none` every time.

Added a minimal `/product` node (product-name/type, regulatory-model-number) used
only when the real tree is absent. Effect:

| lookup | before | after |
| --- | --- | --- |
| `IODeviceTree:/product -> none` | 12 | **0** (12x `-> IOPlatformDevice`) |
| `IODeviceTree:/arm-io` opens | 13 | **1** |

So the repeated `arm-io` open loop collapsed once `/product` existed, and the
display keeps presenting (presents 204, still 5 colours, 0 crashes).

Still true: SpringBoard **does not yet draw its own scene**. The next probe
should be SpringBoard's own view of the world - `sweetdump=SpringBoard` with the
block ring, now that the display path is healthy, to see what it does after
`/product` resolves instead of assuming it is stuck on the lookup.

Note for the tool: `mkadt.py` takes the **output path as `sys.argv[1]`** and
ignores flags' order; calling it as `mkadt.py --device=gauguin out.adt` writes a
file literally named `--device=gauguin`. That happened here and the stray file
was removed from git.

### >>> UPDATE 2026-10-22 21:52: the panel now carries real content, not a flat fill <<<

Added pixel sampling to the vsync report (4,096 evenly spaced samples, counts
non-black ones and distinct colours) to answer "frames are presented - but is
anything *drawn*?".

    vsync=2    ... presents=0   client=0  px nonblack=513 distinct=1   (boot console)
    vsync=2400 ... presents=0   client=0  px nonblack=599 distinct=1   (boot console)
    vsync=3000 ... presents=3   client=2  px nonblack=60  distinct=5   <- SpringBoard
    vsync=3600 ... presents=94  client=2  px nonblack=60  distinct=5
    vsync=4200 ... presents=169 client=2  px nonblack=60  distinct=5

Three things this proves:

1. **backboardd really did hand over the surface**: the moment clients appear,
   the panel stops being the flat single-colour boot console and becomes a
   **5-colour** framebuffer;
2. `presents` climbs steadily (169 by vsync 4200) with `dirty=1`, so it is
   swapping continuously, not once;
3. the content is *sparse* - only 60/4102 samples non-black - which is what a
   mostly-black SpringBoard boot screen looks like (black background, a few
   glyphs/indicators), rather than a solid fill or garbage.

Still 0 backboardd crashes in this run.

Remaining known gap: **SpringBoard itself has not been seen drawing its own
scene yet** (the 5 colours are consistent with the display coming up under
backboardd; the next milestone is SpringBoard's UI). Touch, USB and high refresh
are still untouched after this.

### >>> UPDATE 2026-10-22 21:49: *** FIRST REAL FRAMES *** - zeroed structures unlock the swap path <<<

Experiment from the 21:44 note: make selectors **79 and 74 return fully zeroed
structures** instead of the invented header. Result:

| | before | after |
| --- | --- | --- |
| backboardd crashes | 13/boot | **0** |
| vb clients | 1 (briefly) | **2** |
| presents | **0** | **177** |
| dirty | 0 | **1** |

Serial excerpt:

    SWEET FB: vsync=2400 ... presents=0   client=0
    SWEET FB: vsync=3000 ... presents=2   client=1
    SWEET FB: vsync=3600 ... presents=77  client=2
    SWEET FB: vsync=4200 ... presents=177 client=2 dirty=1

**The display pipeline is now actually presenting.** backboardd stopped crashing
the moment the invented mode/timing structures were removed, which finally
identifies the crash cause: the fabricated `hdr[0] = 1` mode-count header made
the userland parse a **name string** out of a buffer whose contents were not a
string, giving the 0..15 pointer in `strlen` - exactly the chain resolved in the
21:55 note.

So the honest summary of the last few hours: the blocker was **our own made-up
ABI reply**, not a missing kernel facility, not the GPU, not the device tree.

Next steps, in order:
1. confirm the frames are *correct* (pull a screenshot / check the panel is not
   showing garbage) - `presents` proves the swap path works, not that the
   pixels are right;
2. keep 79/74 zeroed until the real structure layout is known (the real driver's
   1580-byte mode list), rather than re-inventing it;
3. that unblocks the remaining goals: SpringBoard drawing, touch, high refresh.

### >>> UPDATE 2026-10-22 21:44: the backlight node is NOT the source (correcting 21:39) <<<

Found and fixed a real but unrelated bug in `tools/mkadt.py`: the `backlight`
node emitted **two** `AAPL,phandle` properties (`ph()` plus a manual
`('AAPL,phandle', u32(next(phandle)))`), burning a phandle number and producing a
duplicate property. Fixed; the ADT regenerates at 10,244 bytes.

But the crash **did not change**:

    crash pc-slide = 0x1d1b024c4   (identical to every previous run)
    13 crashes per boot             (unchanged)

So the hypothesis in the 21:39 note - "the 0..15 pointer comes from the
backlight device-tree node" - is **wrong**. Recorded here so it is not chased
again. The ADT fix stands on its own merit (duplicate properties are wrong
regardless), but it is not the display blocker.

What is still true: the faulting string routine receives a pointer in 0..15,
the call chain is QuartzCore -> CoreFoundation -> IOKit -> libc++ -> strlen-like
code, and it happens right after the `IOAcceleratorES` lookup succeeds and the
`disp0 -> AppleCLCD` match. Since our scalar replies are all self-consistent and
the DT node change had no effect, the next suspect is the **1580-byte structure**
of selector 79 (and the 64-byte one of 74): we fill only the first 64 bytes with
a made-up header and zero the rest, and IOKit/CF may be parsing a *name* out of
it. That is cheap to test: return an all-zero structure for 79/74 and see if the
crash point moves.

### >>> UPDATE 2026-10-22 21:39: the exact call sequence before the crash <<<

Logging every framebuffer call with the values we return (first 200 calls,
`SWEET FB: <n> <proc> sel ... [out0 out1 out2]`). One full round, verbatim:

    3  backboardd sel 57 in 0/0 out 1/0 -> [0]            ; we answer 0
    4  backboardd sel 15 in 2/0 out 1/0 -> [10]
    5  backboardd sel 22 in 1/0 out 0/0 -> []
    6  backboardd sel 8  in 0/0 out 2/0 -> [465 984]      ; 1125x2436 in hex
    7  backboardd sel 28 in 0/0 out 1/0 -> [1ca]          ; dot pitch 458
    8  backboardd sel 29 in 0/0 out 0/8 -> [struct]       ; we fill 8 bytes
    9  backboardd sel 33 in 1/0 out 0/0 -> []
   10  backboardd sel 79 in 2/0 out 0/1580 -> [hdr]
       (IODeviceTree:/chosen, AppleM2ScalerCSCDriver MISS, backlight MISS,
        disp0 -> AppleCLCD match)
   11  backboardd sel 74 in 1/0 out 1/64 -> [1]
       backboardd notifications type 3 on
   12  backboardd sel 72 in 4/0 out 0/0 -> []
   13  backboardd sel 73 in 2/0 out 0/0 -> []
       IODeviceTree:/backlight -> IOPlatformDevice
       IOAcceleratorES -> 1 found
    >>> CRASH sig 11, pc-slide 0x1d1b024c4 (same instruction every time)

Two findings that matter:

1. **The crash is not caused by one selector's return value alone** - the same
   round repeats 3 times per boot (after each relaunch) and dies at the same
   point, immediately after the accelerator is found and right after the
   backlight and disp0 nodes are touched. The string pointer that faults
   (0..15) is being built from device-tree/service *properties*, not from our
   scalar replies, which are all self-consistent (465/984, 1ca, 1).
2. **The order is stable**: 57, 15, 22, 8, 28, 29, 33, 79, 74, 72, 73 - so the
   selectors are a fixed sequence and can be matched one-to-one against the
   shipping driver's external methods by signature alone (each has a distinct
   in/out shape in the table above).

Next: the failing string is built after `IODeviceTree:/backlight` is opened,
which is *our* backlight node from `mkadt.py` (NOTES 14:12). A DT node whose
`compatible`/`label` properties are malformed is a very plausible source of a
0..15 pointer. Check what properties that node actually carries on device.

### >>> UPDATE 2026-10-22 21:55: the crash chain, frame by frame <<<

Every frame of `CRASH backboardd bt`, minus the slide `0x216b0000`, resolved
against the parsed cache (smallest `__TEXT` claim wins):

| frame | image | offset |
| --- | --- | --- |
| 0 | AXRuntime | 0x9b20c |
| 1 | **IOKit** | **0x1a58** |
| 2-7 | CoreFoundation | 0x74de4, 0x8ffa0, 0x91bb4, 0x75744, 0x79d20, 0xb8bec |
| 8-9 | QuartzCore | 0x27da70, 0x287418 |

The IOKit frame disassembles as an **inline selector dispatch**:

    0x...a58  lr -->  34000093  CBZ   w19, +0x10
    0x...a5c          b94002e0  LDR   w0, [x23]      ; arg0 = *x23
    0x...a60          aa1303e1  MOV   x1, x19        ; arg1 = x19
    0x...a64          958e9291  BL    0x1948f64a0    ; libc++.1.dylib + 0x1f84a0

so the chain is **QuartzCore -> CoreFoundation -> IOKit -> libc++ ->
libsystem_platform's vectorised string routine -> fatal `LDR q0,[x1]`**.

`far = 0` plus the `AND x1, x0, #~0xf` prologue pins the argument down: the
pointer handed to the string routine was **in 0..15**, i.e. effectively null /
offset-from-null, not a wild address. In this IOKit shape that is the classic
"call an external method with an **uninitialised or zero output** and treat the
result as a C string" pattern - and backboardd is talking to *our*
user client, whose selector semantics we are still guessing at.

That connects the two threads of evidence: our unknown selectors (15, 22, 29,
33, 57, 72, 73, 74, 79) answer a **plausible-looking but wrong** value, and
CoreFoundation/IOKit turns one of those into a C-string pointer, which is 0..15
and faults.

Concrete next step: log, for **every** call, the selector **and the first few
scalar outputs we hand back**, then diff against the crash timing - the call
whose reply precedes the crash is the one returning the bogus pointer-scale
value.

### >>> UPDATE 2026-10-22 21:45: the crash is an unaligned SIMD load in libsystem_platform <<<

Symbolised the crash by parsing the dyld4 sub-cache on the iOS root image
(`/System/Library/Caches/com.apple.dyld/dyld_shared_cache_arm64*`): walk each
shard for `MH_DYLIB` headers, take the real `__TEXT` claim, and match
`pc - slide = 0x1d1b024c4`.

    libsystem_platform.dylib  __TEXT @ 0x1d1b01000   ->  offset 0x14c4
    (libtzupdate/libc++abi/corecapture also "match" only because their
     __TEXT claims overlap; the hit with the smallest claim is this one)

Disassembly at `0x1d1b024c4`:

    0x1d1b024c0  927cec01   AND   x1, x0, #~0xf     ; round the pointer down
    0x1d1b024c4  3dc00020   LDR   q0, [x1]          ; 16-byte load, ALIGNED
    0x1d1b024c8  10fff9c3   ADR   x3, ...
    0x1d1b024cc  3cc10462   LDR   q2, [x3, #0x10]   ; 16-byte load, ALIGNED

`LDR q` requires a **16-byte aligned** address. With `far=0` in the crash line,
`x1` rounded down to 0 and the load faulted at address 0.

This is a **libc string/mem routine** (the `AND #~0xf` + vector-load shape is the
standard 16-byte-at-a-time `strlen`/`memchr`/`strchr` idiom): it took a pointer a
few bytes below 0 - i.e. **someone passed it a pointer to memory that had already
been unmapped or shifted backwards**, not a null deref of a big struct.

What that means practically: the crash is **not** in our driver and **not** in
the display path; it is userland string handling on a dangling pointer, and
`pc - slide` stays constant because the faulting instruction is constant. The
useful next step is no longer symbol-chasing but **the caller's argument**:
enable a userland crash detail dump (or look at the `lr` and frame chain in the
existing `CRASH ... bt` line) to see which backboardd call feeds it.

### >>> UPDATE 2026-10-22 21:29: a stub accelerator is found, but the crash is elsewhere <<<

Published a stub `IOAcceleratorES` (class in `SweetFramebuffer.cpp`, entry in
`KernelConfigTables.cpp`, `IOResources` provider, every method inert). Result:

    SWEET GPU: stub IOAcceleratorES published
    IOK backboardd: matching <IOProviderClass=IOAcceleratorES> -> 1 found   (was 0)
    CRASH backboardd[56] sig 11 ... pc 0x1f31b24c4 slide 0x216b0000
    (12 crashes - one fewer, but still crashing)

The crash **offset inside the library is identical** across both runs:

    run "cl"  : pc - slide = 0x1d1b024c4
    run "gpu" : pc - slide = 0x1d1b024c4

So the accelerator lookup was a red herring for the segfault: providing the
service moves the count of crashes by one and changes nothing about **where** it
dies. The crash is deterministic and in shared-cache library code
(`pc - slide` far above the backboardd image), i.e. in a system framework that
backboardd calls, not in our driver.

Current honest state:
* backboardd **crash-looping** is the true blocker for `presents=0`;
* it is **not** caused by the missing GPU accelerator (tested);
* the crash site is reproducible with a constant library offset, which makes it
  symbolisable: take `pc - slide = 0x1d1b024c4` and find that address in the
  dyld shared cache (`dyld_shared_cache_arm64*` on the iOS root image,
  `/System/Library/Caches/com.apple.dyld/`) - the same address appears in every
  serial log, so one symbolisation explains all 12-13 crashes.

Keep the stub accelerator: it is harmless, it makes the service graph honest,
and it removes one legitimate source of "0 found" noise from future logs.

### >>> UPDATE 2026-10-22 21:23: backboardd is CRASHING (SIGSEGV) - no GPU accelerator <<<

Adding a close log to the framebuffer client exposed what the previous runs
could not show. The sequence, repeated on every boot:

    SWEET FB: backboardd sel 74 ... -> 0x0
    SWEET FB: backboardd notifications type 3 on
    SWEET FB: backboardd sel 72 ... -> 0x0
    SWEET FB: backboardd sel 73 ... -> 0x0
    IOK backboardd: path IODeviceTree:/backlight -> IOPlatformDevice
    IOK backboardd: matching <IOProviderClass=IOAcceleratorES> -> **0 found**
    CRASH backboardd[56] sig 11 code 0x100000001 sub 0x0 slide 0x16cec000
    CRASH backboardd pc 0x1e87ee4c4 lr 0x19db574f8 far 0x0
    SWEET FB: backboardd closing its client

**13 crashes per boot**, each followed by a relaunch (pid 56, then 120, ...)
that reconnects, re-registers and dies again.

So `presents=0` is not a rendering-logic puzzle: **backboardd segfaults before
it ever gets a surface to present**, and the immediate trigger is the missing
**GPU accelerator** (`IOAcceleratorES`, i.e. the AGX/IOGPU driver). This matches
the known fact that there is **no GPU driver in the tree** (DT has
`gpu@3d00000`, `qcom,adreno-619.0`, `zap-shader`, `sm6350-smmu-v2`, but nothing
implements it): backboardd looks the accelerator up, gets 0, and dereferences
something that came back null.

That reframes the whole display blocker:

* the framebuffer ABI work was still necessary (it got backboardd as far as
  registering a notification), but it cannot be the last step;
* **the display cannot come up until a GPU accelerator service exists**, even if
  it is a stub - or until backboardd is tolerant of it being absent.

Cheapest next experiment, in order:
1. publish a minimal `IOAcceleratorES`-compatible service (even one that returns
   errors) and see whether backboardd survives past the lookup - that alone
   separates "needs a real GPU" from "needs the service to exist";
2. if it survives, the next crash will name the next missing piece.

The crash backtrace is in `/tmp/cl-1.txt` (and every run's serial log) if the
addresses are worth symbolising against the dyld cache later.

### >>> UPDATE 2026-10-22 21:14: answering the new selectors moved the pipeline forward <<<

First pass at implementing the ABI backboardd actually uses (15, 22, 29, 33, 74,
79 in `SweetFramebuffer.cpp`, with 72/73 already present as notifications).
Result of the very next boot, compared with before:

| | before | after |
| --- | --- | --- |
| selectors called | 15,22,29,33,57,74,79 | same **plus 72 and 73** |
| notification registration | none | `notifications type 3 on` |
| vb clients | 0 | **1** |
| presents | 0 | 0 (unchanged) |

So answering 74/79 (mode/timing) did **not** unlock swapping, but it did let
backboardd get far enough to **register a notification (type 3) and issue two
more calls (72, 73)**, and to keep a client attached. That is real forward
progress: the driver no longer looks like a dead end to it.

Open questions, in order:
1. what are 72 and 73 in the real driver? (72 takes 4 scalars - our notification
   registration matches that shape by luck; 73 takes 2);
2. **notification type 3** needs to fire *something* - today we only deliver vsync
   for type 5 (`SWEET_FB_NOTIFY_VSYNC`), so type 3 is registered and never
   called, which may be exactly why it waits forever for its first frame;
3. which of 15/22/29/33 is load-bearing - they are still "answer something
   harmless" stubs.

Question 2 is the cheapest and the most likely: a registered notification that
never fires is indistinguishable, to userland, from a display that never scans
out.

### >>> UPDATE 2026-10-22 21:50: backboardd's exact framebuffer call signatures <<<

From the driver's own log line (`%s sel %u in %u/%u out %u/%u` = scalars
in/structure in, scalars out/structure out), the full call set is:

| sel | scalars in | struct in | scalars out | struct out | likely meaning |
| --- | --- | --- | --- | --- | --- |
| 57 | 0 | 0 | 1 | 0 | query, one u64 back |
| 15 | 2 | 0 | 1 | 0 | (two args) -> one u64 (e.g. get/set display attribute) |
| 22 | 1 | 0 | 0 | 0 | setter, one arg, no result |
| 29 | 0 | 0 | 0 | 8 | returns an 8-byte struct |
| 33 | 1 | 0 | 0 | 0 | setter, one arg |
| 79 | 2 | 0 | 0 | **1580** | the *big* one: returns a 1580-byte struct |
| 74 | 1 | 0 | 1 | 64 | one arg, returns u64 + 64-byte struct |

`MobileGestaltHelper` calls 8 (DisplaySize: 2 scalars out) and 28 (DotPitch: 1
scalar out), which our enum already implements - consistent with the panel
geometry being *readable* but the pipeline never starting.

**sel 79 returning a 1580-byte structure is the most promising lead**: that size
smells like a display-timing / modes description (a list of video modes), and
`backboardd` asking for it before it ever calls `SwapBegin` fits "I cannot get a
usable mode list, so I will not drive the display". The 64-byte struct from 74
is plausibly a per-mode descriptor.

Also known: the dyld shared *cache* on this root image is a dyld4 sub-cache set
whose index shard carries no image table (`mappingCount=1`, `imagesCount=0`),
so the selector order **cannot** be recovered by parsing it with the old dyld3
layout - the signatures above are the better evidence anyway, and they come from
the device itself.

Next: implement 57/29/74/79 in a first pass (fill plausible values, log what
backboardd does with them) and see whether it advances to a swap.

### >>> UPDATE 2026-10-22 21:35: the framebuffer ABI we accept is not the one backboardd uses <<<

`backboardd` **does** open our driver (`IOK backboardd: open AppleCLCD type 0 ->
0x0`, `IOServiceFirstMatch ... AppleCLCD -> AppleCLCD`), so the service is found
and opened. But the selectors it actually calls are:

    15, 22, 29, 33, 57, 74, 79   (7 calls, one each)

against our `enum`:

    3 GetLayerDefaultSurface, 4 SwapBegin, 5 SwapEnd, 6 SwapWait, 7 GetID,
    8 GetDisplaySize, 12 RequestPowerChange, 18 IsMainDisplay, 28 GetDotPitch,
    72 Notifications

Only **28 and 72** are in our range; **15, 22, 29, 33, 57, 74, 79 are all
outside it**, and `MobileGestaltHelper` calls 8 and 28 (the two that work).

This explains `presents=0` far better than any scheduling theory: backboardd is
talking an ABI where the interesting operations live at selectors we do not
implement, our default case answers harmlessly, and the display pipeline never
gets a usable surface - so it never calls SwapBegin.

Immediate next step: **find the real IOMobileFramebufferUserClient selector
table** (the order of external methods in the shipping driver) and implement the
selectors backboardd actually calls, in the order it calls them. The shipping
`IOMobileFramebuffer` kext is not in the tree, but the dyld shared cache has
`/System/Library/Frameworks/IOMobileFramebuffer.framework` and the selector order
is recoverable from the userland client's `io_connect_method` call sites.

Second, smaller correction now known: the panel is presented as **1125x2436**
(iPhone X) while the real panel is 1080x2400, and there is a `sweetfb_native=1`
boot arg to compare - worth one run *after* the selectors are right, because a
wrong logical size alone cannot explain zero swaps.

### >>> UPDATE 2026-10-22 21:06: SpringBoard's syscall mix - ordinary daemon work <<<

Histogram of SpringBoard's syscalls (boot-arg `sweetsyscall=SpringBoard`,
counter in `unix_syscall`, printed from the dump path - never from the syscall
path itself):

| # | syscall | count |
| --- | --- | --- |
| 375 | `kevent_id` | 42 |
| 368 | `workq_kernreturn` | 33 |
| 478 | `bsdthread_ctl` | 17 |
| 336 | `proc_info` | 13 |
| 399 | `close_nocancel` | 10 |
| 463 | `openat` | 9 |
| 374 | `kevent_qos` | 8 |
| 170 | `csops_audittoken` | 7 |
| 344 | `getdirentries64` | 6 |
| 346 | `fstatfs64` | 6 |
| 25 | `geteuid` | 5 |
| 75 | `madvise` | 5 |

Reading: this is the profile of a process that is **starting up and running its
work loops normally** - libdispatch event loops (`kevent_id`, `kevent_qos`,
`workq_kernreturn`), thread management (`bsdthread_ctl`), and file/config
reads (`openat`, `getdirentries64`, `csops_audittoken`). **Nothing here is a
stuck or failing operation.**

So SpringBoard is not blocked in the kernel at all: it is a healthy userland
process doing normal ramp-up work, which never reaches the point of asking the
framebuffer for a surface. The remaining work is in **userland logic** (why it
decides there is nothing to draw), not in the kernel - and the kernel-side
probe budget for this question is now spent.

Concrete next options (userland side):
1. chase the last thing SpringBoard logs before it goes quiet (NOTES 14:30) and
   compare against a real device's boot log for the same stage;
2. check whether it is waiting on a **scene/session** that needs a `BackBoard`
   connection - i.e. whether `backboardd` ever advertises a display to it;
3. check `MobileGestalt` values that gate rendering (`main-screen-*`, refresh
   rate keys) - a wrong value there is a classic "no scene, no frames" cause.

### >>> UPDATE 2026-10-22 21:05: fffffe0007315900 is _thread_preempted - SpringBoard is RUNNING <<<

Resolving the shared continuation against
`.deps-cache/obj-gauguin-macos/DEVELOPMENT_ARM64_GAUGUIN/kernel.development.gauguin.unstripped`
(nm -n, the binary carries absolute kernel virtual addresses):

    fffffe0007315900  _thread_preempted        (osfmk/kern/ast.c:84)

and `thread_preempted()` is `thread_exception_return()` - **the frame a thread
gets when it is preempted in kernel space and put back on the run queue**.

That rewrites the whole picture:

* the 50 blocks of SpringBoard's main thread on that continuation are **not
  waits** - each one is "preempted while running in the kernel, later resumed";
* so SpringBoard is *busy doing kernel work* (syscalls / IPC), not parked;
* the earlier "one sleeping thread / parked on a port" reading came from
  sampling a thread that happened to be between two of these preemptions -
  `state=TH_WAIT` at the instant of the sample only says "not on a CPU right
  now", which is true of every runnable-but-descheduled thread too.

**Conclusion for the display problem: SpringBoard is alive, running, and making
progress in kernel code. It simply never asks the framebuffer for a surface.**
The blocker is therefore in its own userland logic (what it decides to draw),
not in a missing kernel facility or a dead port - and the next probe should look
at the syscall mix of tid 218 (what it is actually doing 68 times a boot), not
at wait queues at all.

### >>> UPDATE 2026-10-22 20:56: the block ring works, and SpringBoard loops in it <<<

The lock-free ring (`sweet_block_ring`, 256 records, `__atomic_fetch_add`, no
console I/O in the scheduler) boots fine and, dumped from the exec path, shows:

    SWEET BLOCKRING: 32763 blocks total, showing 256
    ... tid=218 (SpringBoard main) appears 68 times, 50 of them with the same
        continuation fffffe0007315900 and wqt=0 (no waitq type)

Key readings:

* SpringBoard's main thread blocks **68 times before the dump point** - it is
  not sitting in one eternal wait; it wakes and re-blocks in a loop;
* **50 of those are the same continuation**, which is a *blocking wakeup loop*:
  something hands it control, it does a little and immediately parks again on
  the same kernel continuation;
* that same continuation is also used by tid 188 (22), tid 192 (3) and tid 219
  (15) - other SpringBoard threads - so it is a shared kernel wait helper, not
  a service-specific one.

This replaces the earlier "parked forever on a port" reading: the main thread
is spinning through a wake/block cycle, which is what a retry loop on a
**not-yet-ready resource** looks like (e.g. waiting for a scene/session that
never becomes valid, retrying every few ms).

Next: identify `fffffe0007315900` from the kernel link map (it is a kernel text
address in the KLD range) - that names the wait helper and therefore the
resource being retried. `.deps-cache/obj-gauguin-macos/.../kernel.link` and
`nm` on the unstripped binary have it.

### >>> UPDATE 2026-10-22 20:50: thread_block hook hangs the boot <<<

Wiring `sweet_block_trace()` into `thread_block_reason()` (right after
`self->continuation = continuation`) hangs the boot: no recovery after 172 s,
phone off USB. That is the expected hazard - `thread_block_reason` runs at
`splsched()` on **every** block in the system, so per-block `printf` to the
serial console at that rate stalls or deadlocks the boot within seconds.

Rule for this board, now proven three ways (pe_identify_machine printf,
task-thread walk with a bad pointer, this): **do not print from hot scheduler
paths.** If block tracing is needed again, it must be
- a ring buffer of scalars written lock-free (no printf at all), dumped later
  from the watchdog/`sweet_dump_tick`, or
- gated by a counter that allows at most a handful of samples, with the gate
  itself checked before touching the console.

Also worth noting for whoever reads the code: an earlier edit of this hook
existed and **silently disappeared** - the file had no `sweet_block_trace`
reference while the log showed "0 lines", which looked like "the kernel never
blocks". Always `grep` the tree for the hook before concluding anything from an
empty trace.

### >>> UPDATE 2026-10-22 19:34: suspend ruled out; the port probes are unreliable <<<

* `state=1` is exactly `TH_WAIT` in this kernel (`thread.h:413`);
* `susp=0` for every SpringBoard thread in every sample - **not suspended**;
* but the port-object probes disagree with reality: `active=0` for *every*
  thread including ones waiting on ordinary global queues, and `seq` reads
  garbage for the main thread. So the `waitq -> ipc_port_t` arithmetic used in
  the dump is still wrong (different container: for queue waits it is not a
  port at all, and for the port wait the offset is not the one assumed).

**Do not quote `msgs`, `active` or `seq` from the dump.** They are wrong by
construction. What the dump *does* reliably say is only: thread id, `state`,
`suspend_count`, `continuation`, and `waitq` type (PORT vs QUEUE) - the type
comes from the waitq object itself and has been consistent across boots.

The remaining contradiction - a thread in `TH_WAIT` that never passes through
`thread_block_reason` - has one clean explanation left that fits all data: the
block trace samples only the *first 40* lines and filters on a **process name
read from `proc->p_name`**, and for the kernel-side exec handshake the exec'ing
process may still be running under a different name (`launchd`/`xpcproxy`), so
SpringBoard's own blocks are filtered out. Both traces (IPC and scheduler) were
name-filtered; the thread dump was not. That asymmetry, not the kernel, is the
likely reason for the "never blocks" reading.

Next: run the block trace with `sweetblock=xpcproxy` and `sweetblock=launchd`
(or drop the filter entirely for the first 40 blocks after SpringBoard's exec).

### >>> UPDATE 2026-10-22 19:15: and it never calls thread_block either <<<

Tracing `thread_block_reason()` for SpringBoard (`sweetblock=SpringBoard`,
prints name, tid, continuation, waitq type, wait event) produced **zero** lines
in a healthy boot (8 vsync samples, normal completion).

Put together with the previous round, the picture is now:

| instrument | SpringBoard | result |
| --- | --- | --- |
| thread dump at exec / +20 / +120 execs | seen, 1 -> 6 threads | main thread always `state=1` (TH_WAIT), waitq type PORT |
| `ipc_mqueue_receive` trace | 0 lines | never issues a receive |
| `thread_block_reason` trace | 0 lines | never blocks through the scheduler |

A thread that reports `TH_WAIT` in its task's thread list but never passes
through `thread_block_reason` is not parked by the scheduler in any normal way.
The most likely explanations, in order:

1. the thread is **suspended** (`thread_suspend` / task-suspend state) - it is
   "waiting" in the sense of `TH_WAIT`-ish bookkeeping but never scheduled to
   block, which is what `posix_spawn`'s suspended-child flow looks like if the
   resume never arrives;
2. the dump is reading a task whose main thread was already terminated and the
   state is stale bookkeeping;
3. `state=1` is not TH_WAIT in this kernel for `thread->state` (the scheduling
   state enum lives in bits 0..3 - worth checking `TH_WAIT`'s value).

Point 3 is cheap to settle and should be settled **before** building any more
instruments: print `state` in hex next to the known values, and also print
`thread->suspend_count`. Point 1 then becomes directly testable.

### >>> UPDATE 2026-10-22 19:10: SpringBoard never issues a single mach receive <<<

Hooking `ipc_mqueue_receive()` (the only kernel entry for a blocking receive,
`mach_msg.c:929`) and tracing by process name (`sweetmsgwait=SpringBoard`,
40 lines max) produced **zero** lines in a full boot where SpringBoard was
exec'd and the boot completed normally (8 vsync samples).

So SpringBoard's main thread is parked on a port waitq **without ever having
called into `ipc_mqueue_receive`** in that boot. Two readings, and they need
different follow-ups:

* the wait was set up **before** the trace could see it (e.g. it blocks inside
  the very exec/dyld path via a `thread_block` that is not a message receive),
  so the "WQT_PORT" in the dump belongs to a port the *kernel* is waiting for -
  most likely the `exec`/`dyld` "wait for the new process" handshake;
* or the thread is blocked on a port **set**/`kevent`-style wait that does not
  go through this function on this kernel.

Either way the earlier framing needs narrowing: it is not "SpringBoard waits
for an IPC service and the service is missing" - SpringBoard does not even get
as far as a receive. The next instrument should be a trace at `thread_block`
for named processes (waitq type + provenance) rather than at the IPC layer.

### >>> UPDATE 2026-10-22 18:07: port identity is not reachable from the dump <<<

Attempts to name the port the main thread waits on:

* `ip_receiver_name` / `ip_kobject` printed as `4294966820` / `50000` - the
  first is `0xFFFFFFE4`, i.e. a name in another space, and `ip_kobject` is
  PAC-signed, so neither is usable from the dump (NOTES does **not** treat them
  as service names);
* `imq_msgcount` / `imq_qlimit` came back `0/0`, which cannot be right for a
  real port (a receiver's port has a qlimit) - so the offset from the waitq to
  the port object, or the inline-vs-out-of-line layout, is not what the code
  assumed.

Both are the same class of problem: **the port a thread waits on cannot be
identified by walking the waitq from here**. Options that would work:

1. hook `ipc_kmsg_receive` / `ipc_mqueue_receive` and record, at the moment a
   task blocks, the name of the mqueue it blocked on *plus* the `task` and the
   message id - the kernel already has the port in hand there;
2. read the target's zone name for the waitq pointer (`zone_element_name`), if
   exposed, to at least tell "port queue" from "global queue" reliably;
3. take the userland route: `lsof`-style listing of SpringBoard's ports is not
   available, but `dtrace`/`ktrace` on `mach_msg_trap` with a kmem read of the
   destination name is.

Recorded so the next attempt does not repeat the offset math. The useful state
so far stands: SpringBoard and backboardd's main threads block on a port
receive while their worker threads run or wait on ordinary queues, and lsd's
main thread runs - the display stack alone parks.

### >>> UPDATE 2026-10-22 17:37: THE CONTROL EXPERIMENT - backboardd matches, lsd does not <<<

Same kernel, three daemons tracked at once, sample 2/3:

| process | threads | main thread | workers |
| --- | --- | --- | --- |
| SpringBoard | 3 | tid 219 **PORT** mask=1181180, state=1 | 2 on QUEUE |
| backboardd | 5 | tid 317 **PORT** mask=1181980, state=1 | **3 RUNNING** (state=4) |
| lsd | 3 | tid 412 **RUNNING** (state=4) | 2 on QUEUE |

This is the result that matters:

* **lsd's main thread is running** - so a daemon parked on a `WQT_PORT` is *not*
  "normal idle" in general; it is specifically the *display stack* that parks;
* SpringBoard and backboardd both block in a **port receive** with
  near-identical eventmasks (`1181180` vs `1181980` - one bit apart), i.e. both
  are waiting on the same family of notification ports;
* backboardd *does* have threads running (3 of them), so it is not dead - it
  is doing something, and still never swaps.

Interpretation (guess, to be tested): both are parked on a **server/notification
port whose mach service never becomes available**, so the display pipeline never
gets its "start" message. The eventmask difference of one bit is a strong hint
they wait on closely related ports - e.g. the same bootstrap service looked up
twice by two processes.

Next: resolve the port. `wq - offsetof(ipc_port_t, ip_messages)` is the
`ipc_port_t`, and for a port wait the port's `ip_kobject` / port_name tells
which service it is. Printing that turns "a port" into a named service.

### >>> UPDATE 2026-10-22 17:24: the main thread waits on a PORT, not on a lock <<<

The waitq type is now printed (`wqt`: 1=QUEUE, 2=TURNSTILE, 3=PORT):

    SpringBoard tid=218  state=1  ev=0  wqt=3  mask=1181180    <- main thread
    SpringBoard tid=285  state=1  ev=... wqt=1  mask=59bdfe8    <- worker
    SpringBoard tid=320  state=1  ev=... wqt=1  mask=5aecbf8    <- worker
    SpringBoard tid=338  state=1  ev=... wqt=1  mask=5ae73d8    <- worker

and this holds for **all three samples** (1 thread, then 4 threads): the main
thread never leaves its port queue. A `WQT_PORT` wait with a nonzero eventmask
is `mach_msg_receive`/`kevent`-style waiting on a Mach port - i.e. SpringBoard's
`main()` is blocked in its first mach_msg receive and none of its own work has
run: no WindowServer connection, no scene host, no CALayer, hence no framebuffer
open and no swap.

That reframes the target: SpringBoard is not broken, it is **waiting for an
IPC message that never arrives**. The next question is *which port* - a port
wait's waitq lives inside the `ipc_port_t`, so the port object is
`wq - offsetof(ipc_port_t, ip_messages)`; printing `ip_kobject`/`ip_bits` for it
identifies the service (e.g. `com.apple.backboardd` bootstrap port).

Beware: this is *also* exactly what a healthy process looks like when it is
simply idle in its run loop - so the discriminating test is a **sibling that
works**. run `sweetdump=SpringBoard,backboardd,lsd` and compare: if lsd's main
thread shows WQT_QUEUE or WQT_TURNSTILE and SpringBoard's shows WQT_PORT, the
port wait is the anomaly; if every daemon's main thread is on WQT_PORT, this is
normal idle and the real blocker is elsewhere (most likely soft: the scene
never becomes foreground because some earlier setup silently failed).

### >>> UPDATE 2026-10-22 16:59: SpringBoard DOES start - it is stuck later <<<

Three samples of the same task, paced by exec count (the probe re-arms itself
and samples again 20 and then 100 execs later):

| sample | when | threads | main thread |
| --- | --- | --- | --- |
| 1 | next exec after its own | 1 | tid 218, state=1 (TH_WAIT), ev=0, wq=0xfffffe1bba42e348 |
| 2 | +20 execs | 1 | tid 218, same state, **same wq** |
| 3 | +100 execs | **4** | tid 218 still parked on the same wq; three more threads (285/318/344) on their own wait queues |

So the earlier reading ("blocked before it started anything") was **wrong for
the long term**: the process does grow threads and become a real process. What
stays constant is tid 218 (the main thread) sitting in plain TH_WAIT on the
*same* wait queue from the first instant to the end.

Note also that the label printed for samples 2-3 says `xpcproxy` - that is
`sweet_later_name` being overwritten with the exec that triggered the sample;
the task dumped is still SpringBoard (tids 218/285/318/344, one thread count
growing 1 -> 4).

Next: identify the owner of wq=0xfffffe1bba42e348. A waitq's owner is what the
main thread is waiting *for*, and that is the last piece of this puzzle - the
dump should print the waitq's `waiters`/`interlock` owner or resolve it against
`task->waitq`/`proc` objects.

### >>> UPDATE 2026-10-22 16:55: SpringBoard is stuck with ONE sleeping thread <<<

Dumping SpringBoard at the next exec after its own (six execs later, a few
hundred ms of boot) gives the decisive line:

    SWEET THREADS: SpringBoard exec, threads=1
    SWEET THREADS: SpringBoard now, threads=1 (at xpcproxy exec)
    SWEET THREADS: SpringBoard tid=219 run=0 state=1 ev=0

`state=1` is **TH_WAIT and nothing else** (not RUNNABLE, not RUNNING, not
UNINTERRUPTIBLE), `run=0`, `ev=0`. A thread that is a plain wait with no wait
event set and that has not yet spawned any second thread means SpringBoard's
main thread blocked **before it started any of its own work** - no
dispatch/CFRunLoop thread, no scene graph, no framebuffer open (which matches
the IOKit trace: zero framebuffer calls).

So the question is no longer "why does SpringBoard not draw" but "what does the
main thread wait on within its first milliseconds". `ev=0` rules out a named
wait channel we could grep for; the next step is a second sample at a *later*
exec (e.g. 200 execs later) to see whether it is the same wait (a real block) or
a different one (a slow start), plus capturing `waitq` owner data via
`thread->waitq` instead of just `wait_event`.

### >>> UPDATE 2026-10-22 16:32: the probe runs, but the watchdog fires once per boot <<<

`shim-thr9.img` (probe actually linked this time - verified with
`strings kernel | grep 'SWEET THREADS: tick'` before booting) prints:

    SWEET THREADS: SpringBoard exec, threads=1
    SWEET THREADS: SpringBoard will be dumped at tick 20
    SWEET THREADS: tick 1 target 20 pending 1          <- and never tick 2

So the per-second driver does **not** repeat: `sweet_wdt_sample` runs exactly
once, the same "one thread call per boot" that was seen earlier (NOTES 12:30 -
which was retracted then, but the tick counter is a *direct* measurement of the
callback and it says one). That also means the 1 Hz `SWEET HB` heartbeat is
really a single line; the earlier `tick=117058` numbers came from the timer
counters, not from this callback.

Consequence: anything scheduled from `sweet_wdt_sample` cannot repeat either.
The thread dump needs a driver that provably ticks: the cleanest is the
existing per-second path used by the framebuffer/`thread_call` code that the
`SWEET HB` line proves works, or simply dump from the **next exec** of any
process (SpringBoard's exec is followed by ~260 more).

Two build pitfalls worth remembering (both cost a cycle today):

* a probe symbol called from a `.cpp` needs `extern "C"` declared at **file
  scope** - inside a function block it is a syntax error, and the build then
  silently keeps the previous kernel (check the kernel mtime and
  `strings | grep` before booting);
* `deps/build-macos.sh` exits non-zero on a compile error but the old kernel
  file stays on disk, so `scp` happily ships a stale kernel. Always verify.

### >>> UPDATE 2026-10-22 16:19: full thread dump works; exec-time state is boring <<<

With the `task_t` fixed, `queue_iterate(&task->threads, ...)` runs fine from the
exec path (no hang) and prints per thread `tid / run / state / ev`. At exec time
both interesting processes are simply "one thread, just starting":

    SWEET THREADS: SpringBoard exec, threads=1
    SWEET THREADS:   tid=219 run=0 state=9 ev=<waiting>
    SWEET THREADS: backboardd exec, threads=1
    SWEET THREADS:   tid=314 run=1 state=4 ev=0

So the interesting moment is *later*: both processes do start correctly and go
quiet afterwards. A useful dump therefore has to happen seconds after exec, in
a context that is allowed to take a task reference - which is exactly what the
very first (delayed thread call) version tried, and that version hung for the
same bad-pointer reason. **Retry the delayed dump now that the pointer is
fixed**: `thread_call_enter_delayed` + `task_reference(task)` + the walk 15 s
later is the next experiment, one step at a time.

### >>> UPDATE 2026-10-22 16:10: the thread-count probe works (1 thread at exec) <<<

The two hangs above were **not** caused by the walk itself: `kern_exec.c` was
passing the `struct proc *` where the probe takes a `task_t`, so it read
`task->thread_count` at the wrong offset (`-832493856`). After
`task_t sweet_task = proc_task(p);` the probe is safe and prints real data:

    SWEET THREADS: SpringBoard exec, threads=1
    SWEET THREADS: backboardd exec, threads=1

i.e. both processes start as a single-threaded exec, as expected - they are
not blocked before they get going.

Left to verify separately (and **do not confuse with the hangs**): whether a
*correct* `task_t` also allows `queue_iterate(&task->threads, ...)` from the
exec path. The earlier hangs are now explained by the bad pointer, not by the
iteration, so the full thread dump may be retried - but only with the task
pointer fixed, and one step at a time.

### >>> UPDATE 2026-10-22 15:56: walking a task's thread list hangs this kernel <<<

Both thread-walk variants hung the boot with the same signature (no recovery
after ~172 s, phone off USB, needs a long power press):

| variant | trigger | result |
| --- | --- | --- |
| thread call 15 s after exec | `thread_call_enter_delayed` | hang |
| inline in the exec thread, no task lock | direct call | hang |

So on this kernel you cannot iterate `task->threads` at all in this context -
likely the queue is mid-update during exec, or touching `thread->continuation`
/ `wait_event` of a task being built faults. The probe is now reduced to a
single scalar read (`task->thread_count`) so the boot stays usable, and its
output is all that is needed to answer "did the exec create threads".

The general lesson, already learned twice today (pe_identify_machine printf,
this): **bring-up instrumentation on this board must be scalar-only and
outside interrupts** until the kernel is better understood.

Patch export: `xnu/patches/0084-sweet-exec-probe.patch` carries this round's
kernel edits (kern_exec hook, task.c probe, exit logging, the timebase store).

### >>> UPDATE 2026-10-22 15:28: thread dump implemented in osfmk; its first boot hung <<<

`sweet_dump_task_threads()` now lives in `osfmk/kern/task.c` (where task/thread
internals are visible) and is triggered from the exec path
(`bsd/kern/kern_exec.c`), once, 15 s after the first matching exec:

    sweetdump=SpringBoard           boot-arg, comma separated names

It prints `SWEET THREADS: <name> tid=.. run=.. state=.. cont=.. ev=..` per
thread. Two build-time facts worth keeping:

* `struct thread` has no `priority` member here (use `thread_id`, `state`,
  `continuation`, `wait_event`); compile error if you assume otherwise;
* the probe task is kept referenced (`task_reference`) until the thread call
  fires, otherwise the task could be torn down under the dump.

First boot with it (`shim/out/shim-thr.img`, `sweetdump=SpringBoard`) **hung**:
no recovery after 172 s, phone off USB until 15:29. Same signature as the
earlier early-printf hangs, but this one is in a thread call, not in boot code,
so the cause is not yet known. Two suspects: (a) `thread_call_enter_delayed`
from the exec path while the task is mid-exec, (b) the dump itself taking
`task_lock` on a task whose threads are being created, which can deadlock with
the exec thread. Next attempt: drop the delayed call and dump only *after*
`exec` has completed (e.g. from `exit1` or from the first syscall of that
process), or dump with `task_lock` already held by the caller.

### >>> UPDATE 2026-10-22 15:20: SpringBoard thread probe - blocked by the BSD/Mach split <<<

Goal: see where a live-but-idle process (SpringBoard) is waiting. Started
`bsd/kern/sweet_probe.c`, a boot-arg probe (`sweetprobe=Name@SECONDS`) that
walks a process's threads after its exec and prints state/wait event.

Two walls, both worth knowing before anyone retries this:

* `kern/sweet_probe.c` (BSD side) cannot see `struct task`/`struct thread`
  internals - `task.h` hides the struct behind `MACH_KERNEL_PRIVATE`/`MACH_BSD`
  and there is no `task_internal.h`/`thread_internal.h` in this tree, so
  `queue_iterate(&task->threads, ...)` does not compile from `bsd/kern/`;
* `machine/arm_saved_state.h` is not on the BSD include path either, so user
  pc/lr are out of reach from there too.

Conclusion: the probe belongs in **osfmk** (`osfmk/kern/xnu` side), where both
the task/thread internals and the saved-state helpers are visible - e.g. a
function next to `task_threads()` in `osfmk/kern/task.c` called from the exec
hook. That is the shape to use next time; the current `bsd/kern/sweet_probe.c`
is left in the tree but **excluded from the build** (no `conf/files` entry) so
it cannot break a kernel link.

### >>> UPDATE 2026-10-22 15:05: 8/8 identical runs; SpringBoard is alive, not dead <<<

`tools/cycle-loop.sh` ran 8 unattended cycles (`shim-bl.img`): every single one
exec'd SpringBoard once, ran 8 vsync samples (4,200 ticks), and recorded **0
swaps**. 237-277 processes per boot. So this is a deterministic stop, not a
race.

Then `bsd/kern/kern_exit.c` was instrumented to print `exit <name>[pid] rv=`
for the first 200 exits. Result for the SpringBoard boot:

* `exec SpringBoard` at line 4,254;
* **zero** `exit` lines in the whole 25,619-line log;
* the boot continues to `misd`, `healthd`, `fairplayd` - 268 execs in total.

So SpringBoard does **not** die and is not throttled by launchd: it starts,
never opens the framebuffer, and sits idle while the rest of the system boots.
backboardd (its sibling and the framebuffer owner) is in the same state: setup
complete, then no more IOKit calls.

The next instrument has to look at a *running* process's threads. The cheapest
that fits this kernel: a boot-arg (e.g. `sweetwaitdump=SpringBoard`) that,
N seconds after the first matching `exec`, walks the process's threads and
prints each one's saved pc/lr and wait channel, using the same
`proc_find`/`thread_t` machinery `kdp` already uses.

### >>> UPDATE 2026-10-22 14:30: SpringBoard is exec'd but silent - where to look next <<<

Facts from the `/backlight` boot:

* 259 processes are exec'd; the system keeps booting the whole time
  (backboardd, lsd, powerd, chronod, biomed, apfs_iosd, ..., fmfd last).
  So this is not a frozen system - it is a **silent SpringBoard**;
* SpringBoard is exec'd at line 4,615, and the only later line mentioning it is
  the `exec` itself: **no IOKit call, no crash record, no launchd message**;
* `launchd`'s own os_log lines stop at "Early boot complete" (timestamps are
  still 1969, i.e. the wall clock was never set), so launchd's job state is not
  visible in this log at all.

SpringBoard's executable (`/System/Library/CoreServices/SpringBoard.app/
SpringBoard`, 112 KB) only trampolines into
`SpringBoard.framework`, and the framework body lives in the dyld shared cache
(6.5 GB, `System/Library/Caches/com.apple.dyld/dyld_shared_cache_arm64*`), so
`otool`/`strings` on the on-disk file tells nothing about it.

Concrete next actions, in order of cost:

1. **Look for a crash report in the iOS root**: the boot writes
   `/.panicked_task` for kernel panics only, but SpringBoard's death would
   leave `/private/var/mobile/Library/Logs/CrashReporter/*.ips`. That directory
   was empty when checked at 14:32 - re-check after a run with the persistent
   log enabled (the image is journaled; the partition can be mounted read-only
   on the Mac at `/tmp/rootmnt`).
2. **Split the shared cache** (e.g. `dsc_extractor`, or any
   `dyld_shared_cache_util`) and `strings` SpringBoard.framework for the
   Metal/IOKit symbols - this tells whether it goes through Metal at all.
3. **Sample SpringBoard from the kernel**: add a boot-arg (e.g.
   `sweetprobe=SpringBoard,20`) that, 20 s after `execve` of that name, dumps
   the process's thread pcs via `print_task()`-style code. This is the only
   instrument that sees a process that makes no IOKit calls.

### >>> UPDATE 2026-10-22 14:20: who actually touches the framebuffer here <<<

In the `/backlight` boot (27,456 lines) the framebuffer user clients are only:

| process | selectors | meaning |
| --- | --- | --- |
| `MobileGestaltHelper` | 8, 28 | display size and dot pitch (query only) |
| `backboardd` | 57, 15, 22, 29, 33, 79, 74 | notifications / surface / size / power path, all queries |

Nobody sends a swap. backboardd does finish its display bring-up and then
opens `SweetHIDTouch` / `SweetHIDButtons` (so IOHIDEventService works), while
SpringBoard is exec'd at line 4,615 and produces **no** IOKit calls at all.

So two separate questions, and the second is the real blocker:

1. why backboardd never swaps (its setup completes, then silence);
2. why SpringBoard - the process that owns the scene graph - never even opens
   the framebuffer. A process that never queries the display will never draw,
   so **SpringBoard is the thing to instrument next**, not the kernel.

Cheapest instrument that exists in the tree: the `IOK <proc>: ...` trace uses
`proc_selfname`, so adding `sweetiolog` names only helps for IOKit *users*.
For a process that makes no IOKit calls, the next step is a userland-side
probe (a launchd job or a dtrace-style sampling of SpringBoard's threads) -
and before writing one, check `launchd`'s view: is the SpringBoard job running,
throttled, or exited?

### >>> UPDATE 2026-10-22 14:12: /backlight node helps; SpringBoard never reaches IOKit <<<

Added a `backlight` node to `tools/mkadt.py` (compatible "backlight",
"backlight-digital", `backlight-control = 1`). Result:

* `IODeviceTree:/backlight -> IOPlatformDevice` - **resolved** now (was `none`);
* the `IOPropertyMatch backlight-control=true` dict still misses, because it
  asks for a *service notification* and our node is not published as a service
  with that property;
* still `presents=0`, and `dirty=0` for the whole run.

The new information is that **backboardd finishes its whole IOKit display
setup** (AppleCLCD open, disp0, backlight, AppleCLCD notification registered,
then `IOAccessoryManager` and `IOAcceleratorES` notification registrations)
and then stops making IOKit calls at all - no swap, no further queries. In the
same boot SpringBoard is exec'd (line 4,615) and produces **zero** IOKit calls.
So the wall is now in userland: backboardd waits for something inside
BackBoard/CoreDisplay before it first presents, and SpringBoard does not get
far enough to ask for a display at all.

Next probes: run the same cmdline with `sweetiolog` including more daemons, and
look for the first process that *does* reach the framebuffer; correlate with
`launchd` job state (is SpringBoard running, waiting, or exited?) - the
`SWEET LDM`/xpc trace lines already in the log are the place to look.

### >>> UPDATE 2026-10-22 14:09: what backboardd is missing is a SHORT list <<<

`shim-iok.img` booted (25,326 lines) with `sweetiolog` on. The distinct
classes backboardd asks for and never finds:

    IOK backboardd: NEVER FOUND class ApplePearlSEPDriver     (sec. enclave - harmless)
    IOK backboardd: NEVER FOUND class AppleM2ScalerCSCDriver  (scaler - image scaling)
    IOK backboardd: NEVER FOUND class ""                      (the IOPropertyMatch
                                                               backlight-control=True dict)

Crucially, the 276 `IOAcceleratorES` lines are **not** misses:

    IOK backboardd: matching <dict IOProviderClass=IOAcceleratorES
                                IOServiceNotificationUser=true> -> notify

That dict carries `IOServiceNotificationUser`, so it is a *registration for a
future notification*, not a synchronous lookup - backboardd is telling the
kernel "wake me when a GPU accelerator appears" and moving on. So the GPU is
NOT what blocks the first frame, which changes the picture completely.

What the trace says backboardd did, in order: open AppleCLCD, `IODeviceTree:
/arm-io/disp0` found, `AppleCLCD` notification registered, then
`IODeviceTree:/backlight -> none`, scaler class absent, Pearl absent.
So the display setup completes up to the *backlight* node, and backboardd
then has no reason to draw. Next: give `/backlight` a node (and/or the
`backlight-control` property on a display node) so the backlight path resolves,
and make `AppleM2ScalerCSCDriver` unnecessary or present, then see whether a
swap arrives.

### >>> UPDATE 2026-10-22 13:52: this round's kernel changes are a patch now <<<

Everything touched in `.deps-cache/xnu-patched-0082-2` during this session is
exported to `xnu/patches/0083-sweet-timer-fb-pmic-trace.patch` (it is applied
after the 0082 set like the rest of the series): PMIC PON reads over SPMI,
etimer/call-out/vsync counters, the timebase report from IOWatchdog, and the
"NEVER FOUND class" line in the IOKit trace. Until now those edits lived only
in the gitignored build cache, so a fresh clone could not reproduce the images
- keep doing this for every round.

Status of the newest probe (`shim/out/shim-iok.img`, boot-arg
`sweetiolog=backboardd,SpringBoard,WindowServer,skyld`): built, **not booted**
- the phone dropped off USB at 13:49 and had not come back by 13:54. The log it
would produce lists, one line per class, everything backboardd looked for and
never found - the list that says what has to exist before the compositor draws.

### >>> UPDATE 2026-10-22 13:38: the dependency is an IOKit class, not Metal <<<

Decompiling the userland side narrows the GPU question:

* `IOAcceleratorES` appears in exactly one binary on the root image,
  `GPUToolsCapture.framework` (a debugging tool) - it is an **IOKit C++ class
  name**, not a userland API;
* `backboardd` links Metal but imports only `MTLSetShaderCachePath` /
  `MTLMakeShaderCacheWritableByAllUsers` - it does **not** create a Metal
  device;
* `MTLCreateSystemDefaultDevice` is only used by UIKit's color picker, the GPU
  capture tool and a watch-face snapshot service - i.e. **not** on the
  home-screen path;
* `IOAccelerator.framework` on the root image is a header-only private
  framework (Info.plist, no binary) - it is the protocol declaration.

So the object backboardd keeps matching is the kernel-side graphics
accelerator service used for display/compositing (SwanSea's drawing path),
and a picture can in principle be produced without a full Metal driver. The
remaining question is exactly which part of that service backboardd waits on,
which needs either a kernel-side instrument (log every IOKit match attempt and
what class it expects) or a dump of backboardd's wait state.

### >>> UPDATE 2026-10-22 13:32: backboardd blocks on IOAcceleratorES (no GPU driver) <<<

The log right after backboardd's framebuffer setup shows what it is waiting for:

    IOK backboardd: matching <key>IOProviderClass</key><string>IOAcceleratorES</string>
    ... x252, the last one 100 lines before the reset ...

`IOAcceleratorES` is the GPU accelerator service. There is **no GPU driver in
this tree** (no AGX/KGSL/IOAcceleratorES class in `iokit/Kernel/arm/`), so the
match never succeeds, and backboardd waits for it before it presents anything -
which is exactly why `presents=0` for the whole boot: not a framebuffer bug,
the compositor is stuck one layer below.

Hardware for it: the DT has `gpu@3d00000`, `compatible = "qcom,adreno-619.0"`,
reg-names `kgsl_3d0_reg_memory`/`cx_mem`, a `zap-shader` child and an
`sm6350-smmu-v2` MMAU/GPU IOMMU. Bringing up a real Adreno 619 driver (KGSL +
SMMU + firmware/ZAP shader authentication) is a large project of its own.

Cheaper path to a picture first: make the *software* path work. BackBoard needs
a framebuffer/compositor that does not require IOAcceleratorES - either satisfy
the match with a CPU-only software renderer node that advertises the minimal
IOAccelerator protocol, or find the CoreDisplay/SkyLight fallback that iDJ can
be forced into (a software renderer exists for the simulator, and
`unentitled_ios_sim_launch=1` is already on this cmdline). Worth checking which
service backboardd is actually waiting on (it polls, so it may be waiting for
UI-unlock/display pipeline rather than a hard dependency) before writing a GPU
driver.

### >>> UPDATE 2026-10-22 13:25: the display pipeline runs; nobody ever swaps <<<

Counters in `AppleCLCD::vsyncFired` (`SweetFramebuffer.cpp`) give a clean
answer for the "no picture" symptom:

    SWEET FB: vsync=2   dirty=0 presents=0 client=0
    SWEET FB: vsync=600 dirty=0 presents=0 client=0
    ...
    SWEET FB: vsync=3000 dirty=0 presents=0 client=1
    SWEET FB: vsync=4200 dirty=0 presents=0 client=1

* the vsync timer runs the whole boot (4,200+ ticks) - the earlier suspicion
  that it fires once was wrong;
* a user client (backboardd) *does* attach (`client=1` from vsync 3000);
* but the surface is **never dirty and never presented**: backboardd opened
  the framebuffer and stopped after the query selectors.

What backboardd actually sent (first call per selector):

    sel 57 in 0/0 -> 1/0     (72 = notifications, now skips repeat logging)
    sel 15 in 2/0 -> 1/0
    sel 22 in 1/0 -> 0/0
    sel 29 in 0/0 -> 0/8
    sel 33 in 1/0 -> 0/0
    sel 79 in 2/0 -> 0/1580
    sel 74 in 1/0 -> 1/64

i.e. it queried the default surface / size / notifications and then stopped -
no `kSweetFBSwapBegin` (4) or `kSweetFBSwapEnd` (5) ever arrives. So the
blocker is **between backboardd's display setup and its first swap**, not in
the panel push path (which is idle because nothing asks it to push). Next
probes: what backboardd does with the surface it was handed (is it a valid
IOSurface it can map, is the "notifications" refcon path correct), and whether
SkyLight/BackBoard fails an assertion right after those calls.

### >>> UPDATE 2026-10-22 13:22: the timer works fine - timers are NOT the bug <<<

Counters (atomics only, no printing in interrupts): `sweet_timer_intrs` and
`sweet_timer_expiries` in `timer_intr()` (`osfmk/arm/arm_timer.c`),
`sweet_callout_runs` in `running_timers_expire()` (`osfmk/kern/timer_call.c`),
printed by the watchdog heartbeat. First boot with them:

    SWEET HB: 1 wdt=1 tick=117058 exp=116716 call=343

117,058 ticks, 116,716 of which found an expired deadline, 343 call-outs
executed. The tick interrupt, the timer queue and the call-out machinery all
work, so "thread_call timers only fire once" was **wrong**: what fired once was
*our* one-shot `thread_call_enter_delayed(..., +1 s)` - which the heartbeat
prints as `HB: 1` because that line is the callback's first pass, not the only
one. So:

* the tick is healthy; the earlier hypothesis chain (timebase -> tick -> call-outs)
  is closed with no bug found;
* everything built on "periodic work never repeats here" must be re-checked -
  in particular the claim that `AppleCLCD` only refreshed one frame. The
  framebuffer refresh path needs its own counter before any conclusion.

### >>> UPDATE 2026-10-22 13:16: timebase is 19.2 MHz (from our own ADT) <<<

`shim-stepB.img` (timebase stored in `pe_identify_machine`, printed later from
`IOWatchdog::start`, where IOLog is safe) booted normally and reported

    SWEET CLOCK: timebase=19200000 Hz

So `gPEClockFrequencyInfo.timebase_frequency_hz` = 19.2 MHz, i.e.
`tools/mkadt.py`'s `TIMEBASE = 19200000` (line 49) - the value written into
the generated ADT's `cpu/timebase-frequency`. That number is the ARM generic
counter (XO/19.2 MHz) and every tick deadline is converted with it, so a
"one second" call-out is CNTV_TVAL = 19,200,000.

Consequence: the single-heartbeat symptom is **not** a wrong timebase. Either
the tick fires once and the call-out queue is never advanced again, or the
timer call-out code on this build has a one-shot path. Next instrument: put a
counter in `timer_intr` (not `rtclock_intr` - no printing from interrupts) and
read it from the watchdog heartbeat to see whether the etimer keeps expiring
while call-outs stop.

### >>> UPDATE 2026-10-22 13:05: `printf` in pe_identify_machine() hangs the boot <<<

Bisect, one change at a time:

| build | change | result |
| --- | --- | --- |
| `shim-hb.img` (12:18) | -- | boots, userland, resets (24,957 lines) |
| 12:35 / 12:46 | printf inside `rtclock_intr` | hang |
| 12:49 `shim-clk2` | no rtclock printf, CLOCK print in `pe_identify_machine` + rtclock atomic | hang |
| 13:04 `shim-stepA` | **CLOCK print only** (rtclock atomic removed) | **hang** |

So the `printf("SWEET CLOCK: timebase=...")` in `pe_identify_machine()` is the
hang: by the time `pe_identify_machine()` runs, the console cannot be written
yet (the clock has not been finalised - `gPEClockFrequencyInfo` is exactly what
is being set up there), and a `printf` that waits on the console takes the boot
down with it. Lesson for this board: **console output before the clock/timer is
finalised is unsafe**; the timebase has to be reported some other way (store it
in a global and have the shim or a later driver print it - e.g. append to the
payload's boot-args from the shim, or print from the UFS driver once it starts).

Kept: the clk print edit is reverted in the tree; `shim-hb.img`'s kernel is the
known-good reference to bisect against.

### >>> UPDATE 2026-10-22 12:52: the print was NOT the cause - three hangs in a row <<<

The print-free build (`shim-clk2.img`, `2408de8`) hung exactly like the two
before it: no TWRP after 172 s, phone off USB. So the timer-interrupt `printf`
was a reasonable suspect but not the cause; something else changed at the same
time (the `SWEET CLOCK:` print in `pe_identify_machine()`, or the atomic in
`rtclock_intr`) - or the phone's state itself is now different (it only hung
after the 12:30 boot, and five clean boots preceded that).

Bisect decided: boot `shim/out/shim-hb.img` (12:18, the last build that
completed a full boot + reset cycle three times). If it hangs too, the phone
is in a different state and no kernel change is responsible; if it resets
normally, put the two changes back one at a time (`SWEET CLOCK` print first,
it is the harmless one).

### >>> UPDATE 2026-10-22 12:48: the rtclock counter itself hangs the phone - revert it <<<

Two boots after adding `sweet_rtclock_intrs` (a plain atomic increment plus a
`printf` every 1024 interrupts inside `rtclock_intr`) **hang instead of
resetting**: no TWRP after ~170 s and the phone disappears from USB, needing a
long power press. The 5 boots immediately before it (1d9a8b6's counter-free
build) all behaved normally, so the change is the suspect - most likely the
`printf` from the clock interrupt at `spl` level (the console write takes a
lock the timer path must not touch), not the counter itself.

Before the next boot the counter must come back **without any printing**:
keep `sweet_rtclock_intrs` (a relaxed atomic add is safe) and read it from the
watchdog heartbeat / the shim instead of printing inside the interrupt.

Also still open from before: the timebase frequency line
(`SWEET CLOCK: timebase=... Hz`) never got as far as being read, because both
boots hung - so the "wrong timebase" hypothesis is **not yet tested**.

### >>> UPDATE 2026-10-22 12:45: prime suspect for "timers fire once": the timebase <<<

Reading the timer path end to end (`rtclock_intr` -> `timer_intr` ->
`timer_queue_expire` -> `running_timers_expire` -> `timer_resync_deadlines`
-> `setPop` -> `ml_set_decrementer` -> `CNTV_TVAL_EL0`) shows the tick length
is computed in **timebase units** (`deadline_to_decrementer`), and the timebase
comes from `gPEClockFrequencyInfo.timebase_frequency_hz`, which
`pe_identify_machine()` takes from the DT `cpu/timebase-frequency` node. There
is no SWEET patch touching it: if that property is missing or not 24 MHz, the
ARM generic counter and the kernel's notion of a second disagree, so a
"one second" thread call is programmed as a tick nanoseconds long, fires once,
and the queue then has nothing to run - exactly the symptom seen (1 heartbeat
per boot, 1 s and 10 s alike).

`pe_identify_machine()` now prints `SWEET CLOCK: timebase=... Hz dec=... Hz`,
and `rtclock_intr` counts interrupts (`SWEET RTC:` every 1024th, with
`now`/`rtcPop`). One boot of `shim/out/shim-clk.img` answers it: a sane
timebase plus a static interrupt counter means the tick never re-arms; a wrong
timebase means fix the DT (or override in `pe_identify_machine`, the file
already defaults to 24 MHz before it looks at the DT).

The phone dropped off USB again between 12:38 and 12:43 (came back for one
scan, then gone), so the boot is queued for the next time it is reachable.

### >>> UPDATE 2026-10-22 12:40: two hard stops found while measuring the timer <<<

Two things bite anyone continuing from here:

1. **A run can hang instead of resetting.** The build with a counter in
   `rtclock_intr` (`sweet_rtclock_intrs`, printed in `SWEET RTC:` lines and in
   the heartbeat) booted and then never came back: no TWRP after 171 s, and the
   phone is gone from USB entirely (no adb, no fastboot, no USB device). So the
   bring-up kernel *can* wedge the SoC - watch for it and keep a power-cycle
   ready. That nullifies the result of that particular probe.
2. **misc must be re-armed from TWRP, and TWRP clears it a few seconds after
   it starts.** `tools/fastboot-cycle.sh` now re-arms after pulling the log
   (`ARM_AFTER=1`, default), which is what makes the unattended loop work; but
   if a run ends somewhere other than TWRP (hang in kernel, UEFI) the next
   boot has no `boot-recovery` and a human is needed again.

Instrumentation in place for the timer question: `osfmk/arm/rtclock.c` counts
interrupts (`sweet_rtclock_intrs`) and prints every 1024th with `now`/`rtcPop`;
`SweetWatchdog` prints the count in its heartbeat. Reading the next successful
boot tells whether timer interrupts keep arriving (then the call-out queue /
`timer_intr` is the bug) or stop (then SWEET's virtual-timer arming is).

### >>> UPDATE 2026-10-22 12:30: thread_call timers only fire once per boot <<<

Trying to measure userland lifetime with a kernel heartbeat exposed a real bug
in the bring-up kernel (not in the test): a `thread_call_enter_delayed()` call
runs **exactly once per boot**, whether the re-arm happens inside its own
callback or from `AppleCLCD::vsyncFired`'s chain - 1 s and 10 s intervals both
give one sample (`SWEET HB: 1`) across five runs. So:

* `SWEET WDT:`/`SWEET PON:` samples are valid at boot but never repeat, which
  is why the watchdog looked "static" - it may simply never have been sampled
  twice (earlier reading stands on the `swwd`/shim side, which does read the
  block at every boot);
* anything periodic (`AppleCLCD` vsync -> flush chain) only ever runs once.

The device counter (`SWEET HB: n wdt=...`) is now in place to check this.
Suspicion: `timer_longterm_deadline`/`rtcPop` bookkeeping on this board, or the
`etimer` arming path being bypassed by the SWEET virtual-timer interrupt - the
next step is to instrument `rtclock_intr` (`osfmk/arm/rtclock.c`, the common
ARM path) with a per-second counter and see whether the timer interrupt keeps
arriving while the call-outs stop.

### >>> UPDATE 2026-10-22 12:17: PMIC PON says the SoC was POWERED ON, not warm-reset <<<

Read the PMK8350 PON over SPMI (read-only; `sweet_spmi.c` now also allows
peripheral 0x08/0x0a and honours a real slave id). The gauge DT puts the PON
on `pmic@6` ("pony@1300", reg-names "hlos"/"pbs"), slave 6 - reading sid 0 (as
the battery code does) fails with a read error, sid 6 works:

    SWEET PON: poff1=00 poff2=00 warm1=00 warm2=00

All zero means the PMIC has **no power-off reason and no warm-reset reason**
recorded - i.e. the phone does not see this as a warm reset or a key/PMIC
shutdown at all; it looks like a fresh **power-on** every time (PON reasons are
cleared after being read, but a warm reset would leave WARM_RESET_REASONn
non-zero for the next boot, and ABL does not clear them that early).

Together with `PSHOLD`=1 and the APSS watchdog disabled, the picture is: the
reset comes from the **always-on (AOSS/co-processor) side**, which can drop
`PS_HOLD` without a PMIC-visible reason - e.g. an AOSS/XO/SSR event or a
secure-world watchdog that resets the APSS domain. Next probes: read the AOSS
XPU / cpr XO shutdown counters, and check `SPMI POFF_REASON` *before* ABL
(a second read on the same boot is useless because the first read clears it -
so sample once and immediately print), plus the AOP/RPM fault registers.

Files: `.deps-cache/logs/boot-pon3-userland.txt`.

### >>> UPDATE 2026-10-22 12:06: the reset is time-based, independent of USB and fb <<<

Bisect with the unattended loop (each setting 2-3 cycles):

| cmdline | restart codes | log lines |
| --- | --- | --- |
| baseline | f823e2d8 f823c2d8 f823c0d8 ... | 24.6k-27.7k |
| `sweetusb=0` | f822c3d8 f823c3d8 f823c2d8 | 24.2k-26.7k |
| `sweetusb=0 sweetfb=0` | f823c0d8 f823c2d8 | 24.4k-24.6k |

Every configuration reaches userland, does the same amount of work (`exec`
237-271, AKS calls 146-191 per run) and resets with the same code family
(`xx23y2d8`, low byte `0xd8`). Driving neither USB nor the framebuffer's flush
changes anything, so the reset is **time-based**: something fires about every
110 s of SoC uptime regardless of what iOS has brought up. NOTE: `sweetfb=0`
is **not** a real gate - `AppleCLCD::start()` only looks at
`sweetfb_noconsole`/`_native`/`_hz`, so the fb driver still starts; only the
USB half of that pair was really disabled.

That rules out "a driver we wrote wedges a subsystem" as the trigger and
points at a periodic secure-world / firmware event (hang detector, RPM
watchdog, or an expiry tied to the boot). The cheapest next probes: read the
PMIC PON `POFF_REASON`/reset-type registers over I2C from TWRP before and
after a kernel run, and check whether the timeout moves with
`mach_absolute_time` (e.g. boot twice with a warm and a cold start).

### >>> UPDATE 2026-10-22 11:10: the APSS watchdog stays off for the whole run <<<

`iokit/Kernel/arm/SweetWatchdog.cpp` now samples the block once a second and
logs on change (`SWEET WDT: ctl=0 rst=0 en=0 sts=0 bark=7ffff bite=fffff`).
Three unattended cycles: the sample is identical from the first second to the
last line before the reset, i.e. the APSS watchdog is disabled throughout
(`WDT0_EN=0`) and its bark/bite timers are static. Restart codes from those
runs: `f823c2d8`, `f823c0d8`, `fa23c2d8` - the low byte `0xd8` and the top
half `0xf82?` hold again.

So the repeating reset is neither a kernel event (panic/IOKit restart), nor
the APSS watchdog, nor a PMIC power cut (`PSHOLD`=1). What is left: a watchdog
in another subsystem (RPM/WCSS), or the secure world's hang detector reacting
to something iOS does (a register/resource we touch) - the USB takeover and
the framebuffer are the two candidates, and the loop can now bisect them in
two-minute steps.

### >>> UPDATE 2026-10-22 11:00: the debug loop is fully unattended (6 cycles, no human) <<<

`tools/auto-cycle.sh IMAGE N` repeats the whole cycle: TWRP arms `misc` ->
`fastboot boot` -> the kernel boots, runs userland, resets -> ABL reads
`misc` and boots TWRP -> the log is pulled -> `misc` is armed again. ~1 min 50 s
per cycle. Six cycles ran back to back with nobody touching the phone; every
one reached userland (24.6k-27.7k log lines) and carried its own reset code.

The restart codes from those six boots:

    f823e2d8   b823e0d8   e823c2d8   f822c2d8   f823e2d8   f823c2d8

The low byte is always `0xd8`, the top word is `0xf823` in four of six, and
the middle byte is only ever 0xc2/0xe0/0xe2. So the reset source is stable
(a real reset type, not garbage in IMEM) while a couple of bits wobble - the
high word probably packs both the reset category and a flag/CPU field. `swwd`
stays 0 in every boot, so the APSS watchdog is off throughout.

Next probe, now cheap: bisect the cmdline with the loop (each run is 2 min):
`sweetfb_noconsole=1` vs the framebuffer untouched, and `sweetusb` off, to see
which subsystem the repeating reset needs. `tools/auto-cycle.sh` also keeps
`misc` armed, so the phone no longer falls into UEFI between cycles.

### >>> UPDATE 2026-10-22 10:50: watchdog registers read back as zero (not the culprit) <<<

`swwd=00000000` in the boot-args of the next run: every one of the first eight
registers of the APSS watchdog block (0x17c10000, WDT0_CTL/RST/EN/STS/BARK/BITE)
has a zero **top nibble**, i.e. the block is already disabled - ABL (or the
secure monitor) turns the APSS watchdog off before booting anything else.
Third distinct reset code (`f823c3d8`, after `f823c2d8` and `f823e0d8`), still
the same `0xf823` upper half, `PSHOLD` still 1.

So the repeating reset is not the APSS watchdog and not the PMIC's power cut:
something else asserts a warm reset. The candidates left are the RPM/WCSS
watchdogs of the subsystems we touch (the USB gadget and the framebuffer both
poke clocks/GDSC, and the SoC freezes hard on the USB takeover), and a
Qualcomm "system hang detector" in the secure world. The next cheap probe is
to run a boot *without* touching those subsystems (no sweetusb, no fb) and see
whether the reset interval changes at all.

### >>> UPDATE 2026-10-22 10:45: APSS watchdog identified and stopped in the shim <<<

The gauge DT has `watchdog@17c10000`, `compatible = "qcom,apss-wdt-sm6350",
"qcom,kpss-wdt"`. Android's `watchdog_v2.c` shows what a kernel has to do:
first `scm_call(SCM_SVC_BOOT, SCM_SVC_SEC_WDOG_DIS=8, {1,4,0})` ("Failed to
deactivate secure wdog" if it fails), then pet `WDT0_RST` (0x04) twice a second
with `WDT0_EN` (0x08) set. iOS does neither: it inherits whatever ABL left and
never pets, which matches a reset that fires minutes into userland with the
same warm-reset code every time (restart_reason high half `0xf823`,
`PSHOLD` still 1).

The shim now dumps the 0x17c10000 block to the screen, issues the same
`0x0200000c` SMC (SMC64 encoding of FUNC=8, SVC=2) and clears `WDT0_EN`.

Run at 10:44 (`shim-nowdt.img`): the same boot reached userland again
(27,559 log lines vs 24,287) and ended the same way, so stopping *this* block
was not enough on its own - either the secure side owns the timer that fires,
or another watchdog (PMIC / RPM) is the one biting. The screen values of the
`WDT off=../val=..` lines are the next data point.

### >>> UPDATE 2026-10-21 15:45: the reset is a warm SoC reset, high 16 bits are constant <<<

The shim now hands the previous boot's `restart_reason` to the kernel via
boot-args, so it lands in the persistent log by itself (`swrst=` in the
launchd `boot-args` line). Two consecutive boots report

    swrst=f823c2d8   (run 1: 24,599 log lines)
    swrst=f823e0d8   (run 2: 24,287 log lines)

i.e. **the high 16 bits (`0xf823`) are identical and only the low bits move**.
Qualcomm resets encode the source in the upper half (the bootloader's
`restart_reason` set by the SCM/PMIC path), so this is one fixed hardware
source firing repeatedly, not a random crash - consistent with a watchdog
expiring (or the PMIC's reset path) while iOS userland is running normally.
`PSHOLD` reads 1 at boot, so the SoC is not being power-cut.

Also confirmed: the reason page at the end of userdata reads back empty, so
the shim's WRITE(10) path (or the page address) needs work before it can be
trusted as a second carrier - the boot-args carrier works and is what the loop
uses.

Next: identify the authoritative PBL/ABL decode for `0xf823`/`0xf823c2d8`
(the bootloader logs usually print `Restart reason:`), and cross-check
against `logs/misc` in `/persist`; then try disabling the APSS watchdog
before jumping to the payload (the shim can program the watchdog block while
the MMU is off).

### >>> UPDATE 2026-10-21 03:12: the reset is NOT a kernel panic <<<

Two more probes (both with `debug=0x8` to keep corefiles out of the way):
* `sweetpanicdump=1` writes the last 512 KiB of the console ring into Qualcomm's
  ramoops at 0xd0000000 (the DT's `ramoops@d0000000`, which TWRP exports as
  `/sys/fs/pstore`) from the panic path. After a run that ended in the usual
  reset, `/sys/fs/pstore` is **empty**, so no panic path ran.
* `IOPlatformExpert::haltRestart` now prints `SWEET: platform restart requested`
  and flushes for `kPERestartCPU`/`kPEHaltCPU`, and `kdp_machine_reboot_type`
  flushes too. That trace is **absent** from the log as well.

So the phone resets while userspace is running normally (the log ends in
`SWEET AKS: securityd ...` with in-flight NAND reads), through a mechanism that
bypasses both the panic and the IOKit restart paths - a hardware watchdog
(APSS/PMIC), the Qualcomm `restart-reason` SCM path, or a bus/bus-timeout
reset. Next: focus on the watchdog and the IMEM `restart_reason` value (the
shim already knows the code at 0x146aa65c and can print it on the next boot),
plus try `cpus=1` longer runs with `log collect` disabled.

The 02:59/03:04/03:09 runs are 25,164 / 31,681 / 23,039 lines and all end the
same way; the logs are in `.deps-cache/logs/boot-*.txt`.

### >>> UPDATE 2026-10-21 03:00: panic flush hook, and debug=0xc explains the silent resets <<<

Two changes to how the bring-up kernel reports:
* `osfmk/kern/debug.c` calls `sweet_log_flush_panic()` (weak) right before
  `DEBUGGER_OPTION_PANICLOGANDREBOOT` restarts, so a panic's text reaches the
  on-disk log; implemented in `bsd/dev/sweet_ufs.c` (no-op until the root
  device is up). The VMAPPLE bootstrap build still links (the symbol is weak).
* `sweetlogms=<ms>` (<=2000) flushes the persistent log every N ms instead of
  every `ufslogsecs` seconds.

**`debug=0xc` sets `DB_KERN_DUMP_ON_PANIC` (0x400).** On non-macOS
(`on_device_corefile_enabled()`) any non-zero `debug` also enables local
corefiles, and 0x400 asks for one on panic; while the core is written the
kernel cannot flush its console log, which is why every silent reset ended with
the log cut mid-line and no panic text. Runs at 02:56 (`debug=0xc`,
shim-pf.img, 25,633 lines) and 02:59 (`debug=0x8` = DB_KPRT only,
shim-d8.img, 25,164 lines) both reached the same place - CommCenter's
`CRASH ... sig 11`, configd, securityd, ReportCrash - and both reset without a
panic in the log, so either there is no panic (a hardware/watchdog reset) or
the panic path never reaches the flush. The D8 log is
`.deps-cache/logs/boot-debug8-userland.txt`.

### >>> UPDATE 2026-10-20 23:10: userland long run, and how the debug loop now closes <<<

Run at 23:01 (`shim/out/shim-long.img`, `sweetlogms=250 sweetreboot=300`,
`boot-long-userland.txt`): the system ran ~3.5 minutes of userland -
datamigrator, ReportCrash, securityd, CommCenter (its thread-count watermark),
UserEventAgent - and the reset **before** the 300 s timer, so it is not our
timer; no panic text is in the log either.

The return path works end to end now: misc carries `boot-recovery`, so the
reset lands in TWRP and `tools/sweet-log-pull.sh` reads the log without any
manual step (that is how all these logs were collected). Arms to re-apply
after a manual `fastboot boot`: misc is overwritten by the bootloader.

Open threads, in order of expected payoff:
1. the 2-4 min reset (panic not logged: check `panic_reboot`, add a flush in
   the panic path, or find the reset trigger in the bootloader/watchdog);
2. the GUI: backboardd finds IOMobileFramebuffer and opens AppleCLCD, but no
   window server frames yet; `sweetfb_noconsole=1` alone is stable, adding
   `sweetfb_hz` reset the phone;
3. USB gadget: kernel DMA must land below 4 GiB, bzero on io-mapped memory
   panics, and adopting ABL's live controller freezes the SoC (see the 22:10
   note);
4. touch: SweetHIDTouch is matched, opened by backboardd, and starts 45 s after
   boot - needs a visual check once the GUI draws.

### >>> UPDATE 2026-10-20 22:45: journaled root fixes the HFS corruption; userland runs 2 min <<<

The flashed image was created with `hdiutil create` and **never had a journal**
(unlike `tools/mkiosroot.sh`, which runs `mkfs.hfsplus -J`). Every hard reset
left the catalog dirty, so the kernel kept reporting
`hfs_mark_inconsistent: Runtime corruption detected on iOSRoot, fsck will be
forced on next mount` and `BlockMarkFreeInternal() trying to free unallocated
blocks`. Rebuilt with `diskutil enableJournal`, re-flashed (283 s) and booted:

* `/dev/ufsroot0 on / (hfs, local, journaled, noatime)` and **zero** corruption
  messages; SpringBoard, 221 `exec`s, configd's lo0 address + route and the
  AKS users all run.
* 33,947-line console (`boot-journaled-userland.txt`); the log still ends in
  ordinary daemon chatter (securityd AKS 0xe00002c7, `exec coreauthd`) with no
  panic - so the ~2 min reset is not a logged panic. `panic_reboot` defaults to
  1 here, so the reset probably runs through a *non*-kernel path (watchdog
  driver re-arming, or the bootloader's own reset on a hung AP).

Image at `/tmp/iosroot16g-j.dmg` (16 GiB journaled, 11 GiB used);
`tools/img2simg.py` -> `.simg` for `fastboot flash userdata`.

### >>> UPDATE 2026-10-20 22:25: userland runs, but every boot resets after 2-3 minutes <<<

With `sweetfb_noconsole=1` (no `sweetfb_hz`) the system reaches userland and
stays busy for minutes: 29,596 console lines
(`.deps-cache/logs/boot-fbA-userland.txt`) with backboardd, containermanagerd,
CommCenter, remindd, liveactivitiesd, `SWEET FB: MobileGestaltHelper` calls and
the usual daemon crashes (`CRASH CommCenter sig 6`, `containermanager sig 5`).
No kernel panic is in the log, yet the phone comes back through a reset ~2-3
minutes in - and the persistent log's last 1-2 s are lost, which is exactly
where the reason would be.

Practical consequence: the flush interval is now the debugging clock. Next
attempts should use `ufslogsecs=1` (or flush from the panic path) so the last
second is on disk, and arm misc (`boot-recovery`) *before every manual boot*
too, not only inside `tools/fastboot-cycle.sh` - a manual `adb reboot
bootloader; fastboot boot` otherwise lands in the UEFI on reset.

### >>> UPDATE 2026-10-20 22:17: the boot that reaches userland, and the display knobs <<<

The configuration that reaches iOS userland and stays up (21:03 log,
`.deps-cache/logs/boot-userland-gauguin.txt`) is

```
debug=0xc serial=3 cpus=1 keepsyms=1 -enable_kprintf_spam -noprogress
rd=ufsroot0 unentitled_ios_sim_launch=1 ignition_level=1 ufsrw=1 rootrw=1
launchd_unsecure_cache=1 sweetlog=1 ufslogsecs=2
```

i.e. **no** `sweetusb=2` (gadget), **no** `sweetfb_noconsole=1` and **no**
`sweetfb_hz=`. Adding the GUI knobs (`sweetfb_noconsole=1 sweetfb_hz=60`,
`sweetusb=1`) reset the phone into the UEFI on `boot` at 22:15 (misc was not
armed on that manual boot, so it did not come back to TWRP and the log is
lost); the reset points at the display path rather than USB. Next: bisect the
two display boot-args separately, with misc armed so the log survives.

Touch/buttons are already plumbed: `SWEET HID: SweetHIDTouch open by
IOHIDEventServiceClient -> 1`, `SweetHIDButtons open ... -> 1`, and backboardd
found `IOMobileFramebuffer`, opened `AppleCLCD` and issued its user-client
selectors (15/22/29/33/74/79) - so the display user client answers; what is
missing is the window server producing frames.

### >>> UPDATE 2026-10-20 22:10: USB on gauguin - what works and what wedges <<<

**Working:** the read-only USB probe, now with SM7125's register map. gauguin's
GCC is `qcom,gcc-sm6350`, so the USB GDSC is 0x1a004 (SM7150: 0x0f004), the
clock CBCRs are 0x1a00c/0x1a014/0x1a018/0x1101c/0x3e010/0x1a050/0x8c010, and
the QUSB2 PHY is at **0x88e3000** (SM7150: 0x88e2000). With that map the probe
reports the bootloader's hand-off: `cap 0x1587031F`, `GDSC on`, all clocks on,
`GSNPSID 0x5533330a`, `DCTL 0x10f00000`, `DEVTEN 0x277`, `DALEPENA 0x0f`,
`GEVNTADR 0xfdc3d000`. Reading these is safe; the earlier silent resets were
the SM7150 offsets pointing at a gated block.

**The gadget (`sweetusb=2`) does not work yet.** Three failures found:
1. `kmem_alloc_contig` returns memory above 4 GiB (the kernel bank is
   0x180000000+). Pointing GEVNTADR/TRBs there makes the STARTTRANSFER doorbell
   hang: the controller's AXI master does not reach it.
2. Reusing a low buffer with `bzero()` panics: `Unaligned kernel data abort`,
   pc `__bzero+68` - `ml_io_map` memory is Device-nGnRnE and bzero uses 16-byte
   stores. Clear such buffers with 32-bit stores.
3. After switching to the bootloader's own low buffer (0xfdc3c000/0xfdc3d000)
   the SoC freezes *hard* right after the takeover print: no further console,
   no timer, no panic - the debug reboot timer (`sweetreboot=<s>`, new, panics
   after N s so a hung kernel returns to TWRP) cannot fire either. Only a
   power cycle recovers, and the persistent log stops at the last flush.

So taking the *live* DWC3 over from ABL's fastboot session is not viable yet.
Next attempt should bring the controller up from scratch the way Linux does
(clocks/GDSC reset, QUSB2 PHY power-on and PLL, DWC3 core reset, then EP0),
instead of inheriting ABL's state - and keep `sweetusb<=1` in the debugging
loop so a freeze does not cost a manual power cycle.

### >>> UPDATE 2026-10-20 late night: iOS launchd RUNS on gauguin <<<

**`sweet_usb_probe()` was killing the boot.** With `sweetusb=0` the kernel goes
past the driver inits, mounts the HFS root and starts userland:

```
hfs: mounted iOSRoot on device b(1, 0)
load_init_program: attempting to load /usr/appleinternal/sbin/launchd.development
load_init_program: attempting to load /sbin/launchd
exec launchd
libignition: 1: program : launchd
libignition: 1: hello: hello from launchd.1
...
IOK backboardd: matching <key>IOProviderClass</key><string>IOAcceleratorES</string> -> 0 found
```

(the full 24k-line console is `.deps-cache/logs/boot-userland-gauguin.txt`).
The USB probe reads GCC_USB30_PRIM_GDSCR / the CBCR set from **SM7150's**
gcc offsets; on SM7125 (lagoon) those offsets differ, so it can conclude "the
USB GDSC is on" while it is gated and then reads the DWC3 block — a bus hang
(bus timeout -> reset), which is exactly the silent reset we chased. Fix: make
the probe's register map board-specific (or skip it on GAUGUIN) before
re-enabling `sweetusb`.

**Unattended debug loop (`tools/fastboot-cycle.sh`):** writing
`boot-recovery` into the misc partition's `bootloader_message.command` makes
the bootloader boot the recovery partition (TWRP is flashed there) instead of
the UEFI on `boot`, so a dying kernel comes back to adb by itself:
TWRP -> arm misc -> `adb reboot bootloader` -> `fastboot boot IMG` -> kernel
dies -> TWRP -> `tools/sweet-log-pull.sh`. One cycle is ~60 s, no human. This
also removed the "reset lands in UEFI" problem for the rest of the bring-up.

**Persistent console log improvements (cached tree only):** the SWEET log
thread flushed *after* its first sleep and the boot often died inside that
window, so nothing reached the disk. It now flushes once synchronously at
`sweet_log_start()`, again after every driver init in `sweet_ufs_init`, and
the loop flushes before sleeping. `sweetlog=1 ufslogsecs=2` in the cmdline.

### >>> UPDATE 2026-10-20 night: iOS root built + flashed; UFS root is the next wall <<<

**Root image (new route, no Linux needed for APFS):** macOS has APFS and HFS+
natively, 137 has root but no apfs-fuse package. Split the job:
- macOS (unprivileged): `hdiutil create -size 16g -fs "Case-sensitive HFS+"
  -volname iOSRoot -layout NONE /tmp/iosroot16g.dmg` (a partitionless raw HFS+
  volume; `newfs_hfs` refuses plain files and hdiutil's default layout adds a
  GPT). Gzip sends 16 GiB of zeros as 75 MB, `gunzip` on 137.
- macOS (sudo, `tools/mkiosroot-macos` steps run by hand): `hdiutil attach
  -readonly -noverify` the three DMGs, `rsync -aH --numeric-ids` as root into
  the mounted image, then the dyld-cache/cryptex hard links, the `_logd`
  stores, the system keybag. `tools/mkiosroot.sh --reuse` (new flag) documents
  the same flow for the Linux side.
- IPSW: iPhone10,3 16.7.16 20H392, 6,171,035,648 B from
  `updates.cdn-apple.com/2025FallFCS/fullrestores/122-77006/...` (~5 MB/s).
  DMGs: `087-86698-044.dmg` (OS 4,730,814,044), `087-86593-047.dmg`
  (SystemOS 2,743,074,816), `087-86715-047.dmg` (AppOS 10,485,760).
  Result: 11 GiB used of 16 GiB, launchd/dyld root:wheel, keybag 0600.

**Flashing (macOS, adb/fastboot from `brew install android-platform-tools`):**
`fastboot flash userdata` on the raw image dies with `Failed reading from
userdata`: fastboot's `copy_avb_footer()` reads the whole image into a
`std::string` when the image size differs from the partition size. Sparse
images skip that path, so `tools/img2simg.py` (new, 4096 chunks of 4 MiB,
RAW/FILL/DONT_CARE) turns the 16 GiB image into 11.1 GiB, and
`fastboot flash userdata iosroot16g.simg` finished in 283 s (15 chunks).
userdata = `/dev/block/sda35`, 114,919,714,816 B.

**Boot with the root (`shim/out/shim-boot-pn.img`, payload cmdline `debug=0xc
serial=3 cpus=1 keepsyms=1 -enable_kprintf_spam -noprogress rd=ufsroot0
unentitled_ios_sim_launch=1 ignition_level=1 wdt_test=no_user_checkin ufsrw=1
rootrw=1 launchd_unsecure_cache=1 wdt=-1 [panic_reboot=0]`):** the shim's red
screen appears, XNU prints up to
`SWEET AKS / WDT / SURF / HID (buttons+touch) / BATTERY`, `SWEET FB: AppleCLCD
1080x2400 stride 4320 at 0xa0000000`, `1/1 CPUs initialized, SGI1 verified`,
`VM bootstrap done: 85 maps, 165 entries and 502 holes left`,
`IOMD setownership ENABLED`, `4 subsystems initialized`, then either the
zone/coredump block (`Registered coredump handler for kernel`) and a hang, or
a reset ~30-40 s later. `panic_reboot=0` did not keep anything on screen, so
this looks like a hang/reset in the root path rather than a printed panic.
Without `rd=ufsroot0` the same kernel reaches `bsd_autoconf: calling kminit`
and parks in `Waiting on <dict ... Apple_HFS`, i.e. the UFS media never
attaches: **the gauguin UFS root device is the next thing to debug**
(`bsd/dev/sweet_ufs.c`, patch 0028/0030/0031/0034; sweet differs in clocks,
GDSC/PHY and the `ufshc@1d84000` register window).

**Boot nondeterminism:** two boots of the same image stopped at different
places (one at the coredump registration, one past `VM bootstrap done`), so
expect flakiness while debugging.

### >>> UPDATE 2026-10-20 late: built on the Mac, first gauguin boot <<<

**Status: a GAUGUIN XNU kernel exists and boots the phone into BSD.** Built on
this macOS host (not CI, not the Linux box), booted from 137 with
`fastboot boot`; nothing was flashed.

**Build (new, `deps/build-macos.sh [gauguin|sweet]`):** Xcode 26.6's clang/ld/mig
against a writable copy of the CLT SDK. Steps it automates, all in
`.deps-cache/sdkroot-macos` (`sdkroot-macos` is a real copy, not symlinks:
`xcodebuild` rejects an SDK outside its platform dir):
- SDK copy + `AvailabilityVersions-121/availability.pl` (`bsd/sys/make_symbol_aliasing.sh`
  hardcodes `$SDKROOT/usr/local/libexec/availability.pl`; the SDK ships none).
- libplatform `include/`+`private/` -> `usr/local/include`.
- `make installhdrs` -> Kernel.framework/PrivateHeaders + usr/local/include/{os,firehose}
  (needed by libfirehose_kernel).
- `libfirehose_kernel.a`: libdispatch's target via `xcodebuild install -target
  libfirehose_kernel ARCHS=arm64` (xcconfig `$(SDKROOT)` rewritten to our copy,
  like dxb does) -> `usr/local/lib/kernel/`.
- `tools/xnu-post-patch.py` (the CI fix-ups) then `make install -jN
  TARGET_CONFIGS="DEVELOPMENT ARM64 GAUGUIN" KDKROOT= BUILD_WERROR=0 BUILD_LTO=0`.
  `-k` because the trailing lldbmacros install shadows python's `collections`
  and always fails; the kernel binary is the success criterion.
- Xcode 26 has no ctfconvert/ctfmerge/ctfdump: CTF is simply not generated.

**Kernel:** `xnu/out-gauguin-macos/System/Library/Kernels/kernel.development.gauguin`,
16,670,728 bytes, SHA256 `59c287f151ad8cc91f5aa5a0574e5337de6ac6ce3abd00e69d9825ed09d25ac5`,
Mach-O arm64 (no PAC), `xiaomi,gauguin` match present, 177 `sweet_*` symbols.
Payload `shim/out/payload-gauguin.bin` (16,681,696) with ADT
`shim/out/sweet-gauguin.adt` (9952, `--highmem --device=gauguin`), cmdline
`debug=0xc serial=3 cpus=1 keepsyms=1 -enable_kprintf_spam`; boot image
`shim/out/shim-boot.img` 17,043,456 bytes (built on 137: `shim/build.sh
out/payload-gauguin.bin`).

**Four bugs found and fixed on the way:**
1. `shim/shim.ld` reserved 2048 L2/L3 *tables* instead of entries: Image was
   136 MB and ABL parked at the Redmi logo (fastboot boot "OKAY", device never
   left the loader). Now 4 KB + 16 KB + 16 KB + 2x16 KB, Image 266 KB. The
   control experiment that proved `fastboot boot` itself works: booting the
   128 MB TWRP `part-recovery.img` from fastboot does start TWRP.
2. `con_init` read the splash `reg` with the 1/1-cell helper; gauguin's
   `/reserved-memory/cont_splash_region` and `/chosen/framebuffer@a0000000` use
   the root's 2/2 cells, so the base decoded as 0 and the shim fell back to
   sweet's 0x9c000000 (screen never changed). Now `fdt_reg2` first, and the
   gauguin node's geometry (width/height/stride as raw u32 cells) via new
   `fdt_u32`; the shim's red screen appeared, then XNU's fbcon took over.
3. `tools/mkadt.py` wrote sweet's 0x9c000000 into `sweet-fbcon` for gauguin too.
   Now `FB_GAUGUIN=0xa0000000/0x2300000` (matches the live DT).
4. BearSSL staging copied 2 of the 13 `inc/*.h` (`inner.h` includes
   `bearssl.h`); `deps/mirror/xnu/prepare-bearssl.sh` now copies them all.

**Xcode 16+ iig:** it emits `rpc.kernelContent`, absent from xnu-8796's
`IORPC`; `tools/xnu-post-patch.py` now adds the field under `#ifdef KERNEL`
(upstream added it in xnu-11215; nothing here reads it). CI on Xcode 15 is
unaffected.

**Boot observed (photo `IMG_0715`, OCR):** red shim screen with white text, then
XNU fbcon: `SWEET FB: AppleCLCD 1080x2400 stride 4320 at 0xa0000000, presented
as 1125x2436`, `SWEET CPU: requested=1 selected=1 (Limit=8)`, `cpu=0 entered
initCPU`, `SGI1 OK`, `1/1 CPUs initialized`, MAC framework, `using 5195 buffer
headers and 4645 cluster 10 buffer headers`, SWEET AMFI platform policy,
permissive sandbox, `SWEET HFS: hfs-627.100.6 registered`, `ncache: 1 CPU(s)`,
`mbinit: done [96 MB total pool size, (64/32) split]`, Skywalk self-tests
PASSED, `bsd_autoconf: calling kminit`, ifnet_attach for lo0/gif0/stf0, then
`Waiting on <dict ID="0">... I0Media ... Apple_HFS` (no root image),
`Failed to write boot-picker-bringup-reason to NVRAM`, `SWEET SURF:
IOCoreSurfaceRoot registered`, `SWEET HID: buttons registered`.

**Next:** there is no iOS root image on either machine (no `.ipsw`, no
`ios16-root-*`), so the phone stops at the Apple_HFS root wait. Decide where the
root image comes from (`tools/mkiosroot.sh`/`tools/mkinit.py`) before touching
`userdata` (sda35, allowed to be wiped). Everything else on the list - USB,
timer/IRQ, touch - is untested past the BSD console.

### >>> UPDATE 2026-10-20 (gauguin port: read this first) <<<

**Goal:** port this tree to a second phone, Redmi Note 9 Pro 5G / Mi 10T Lite
(`gauguin`, SM7125 "lagoon"), and bring its hardware up. Hardware facts and
the sweet/gauguin difference list are in `PORT-gauguin.md`; the session
handoff with exact commands is `HANDOFF.md`.

**Done (repo, `main`):**
- `fe32fc4` shim reads `/memory`, `cont_splash_region`, `/chosen framebuffer`
  and `ufshc@1d84000` from the live FDT; page tables cover 64 GB; `tools/mkadt.py
  --device=gauguin` (DRAM 0x180000000 + 4 GiB, `qcom,sm7125`);
  `tools/mkbootimg2.py`; `tools/unpack_bootv2.py` dtb size fix.
- `0082-gauguin-board.patch`: `GAUGUIN` machine config (`-DARM64_BOARD_CONFIG_SWEET
  -DGAUGUIN`), Focaltech FT5452 touch on QUPv3 SE8 (0x988000, addr 0x38,
  reset gpio21 / irq gpio22, PM6350 `ldoa6` 1.8 V), PM6350 keys (SID 0, PPID
  0x4c0), `xiaomi,gauguin` IOKit matches, Y max 2339.
- Device backups (read-only, TWRP): `backup/{boot,dtbo,vbmeta}.img`,
  `backup/partitions/{persist,modemst1,modemst2,fsg,fsc}.img` + SHA256SUMS.
  Nothing was flashed; Android partitions untouched.

**Kernel build (the current blocker, in progress):**
- CI builds from the **fork** `lvyufeng/xnu` branch **`gauguin`** (upstream
  xnu-8796.141.3 + the whole `xnu/patches` series + gaugeuin board patches).
  `.github/workflows/xnu.yml` clones it into `dxb/xnu`; dxb then only builds
  the Xcode tools/KDK and runs the per-config `build_xnu`.
- Fixed on the branch so far: `sweet_sample_task` real impl on SWEET + stub
  elsewhere (`ARM64_BOARD_CONFIG_SWEET`); `libkern/conf` and `bsd/conf`
  `ifeq ($(CURRENT_MACHINE_CONFIG),SWEET)` -> `ifneq (,$(filter SWEET
  GAUGUIN,...))` so the BearSSL/HFS/libpthread include paths apply to gauguin.
- Latest runs: 39366187604, 39368747759, 39371166064, 39373411414 (all fail
  later than the previous one), current 39376566655. Diagnostic logs are
  printed inline by the "Build kernel" step (grep + tail) and uploaded as
  `dxb-logs`; artifact downloads from this host often time out, prefer
  `gh run view --log-failed`.
- Local helpers: `deps/make-branch.sh` (rebuild the fork branch),
  `xnu-port/` (CMake + native config generator experiment, not needed when CI
  works), `deps/mirror` (pinned BearSSL/hfs/libpthread sources).

**Next:** get a `kernel.development.gauguin` from CI, then
`tools/mkpayload.py` + `mkadt.py --highmem --device=gauguin` +
`shim/build.sh payload` -> `fastboot boot shim/out/shim-boot.img`.


### >>> UPDATE 2026-10-18 (read first, then the 10-17 handoff below) <<<

**STATE at end of 2026-10-18 (evening):**
- On the phone: userdata = **image v15** (`/run/media/dipa/android/ios-sweet-ipsw/ios16-root-20H392-v15.img/.simg`; = v14 + `/private/var/preferences/SystemConfiguration/preferences.plist` with one network service "USB Ethernet": Interface DeviceName ue0 Type Ethernet, IPv4 Manual 192.168.7.2/24 router 192.168.7.1, DNS 1.1.1.1 8.8.8.8, set "Automatic" as CurrentSet). Fallback image v14 (v12/v13 deleted).
- Kernels: **0078** = all 8 cores (`cpus=8`, cpu6/7 = A76, homogeneous SMP; mkadt now emits 8 CPU nodes; ADT `shim/out/sweet-0078hi.adt`); **0079** = display off/on via IOMFB selector 12 kern_RequestPowerChange(state) (fade over 6 vsyncs, then black; verified: power button gives "SWEET FB: display off/on"); **0080** = `SWEET NET: <proc> route add/delete/change ...` and `... add/delete address ...` trace (built, `shim/out/shim-boot-0080s.img`, NOT booted yet).
- **Internet over USB: not working yet.** Host side is ready (temporary iptables: FORWARD accept for 192.168.7.0/24 + MASQUERADE, comment "ios-sweet"; lost on host reboot). With v15 the phone sent no DNS and no outbound traffic (only mDNS/ARP) -> configd probably did not apply the service (or did, without default route/DNS). Next: boot 0080s on v15, watch `SWEET NET` lines (does configd add 192.168.7.2 / default route on ue0?). If configd ignores ue0 (not an IOKit IONetworkInterface; configd 1241.140.6 source in `research/configd-1241`, SCNetworkInterface createInterface needs IONetworkInterface -> controller (IOMACAddress, SelfNamed) -> bus), add IOKit stand-ins and/or rename the ifnet to en*.
- Live log listener (`nc -ukl 5140`) may still be running, writing `logs/live-0078s.txt`.

**LIVE LOG over USB (0077, boot 0077s): no more recovery round-trips.** Boot an image with `sweetusb=2`, run `tools/sweet-usbnet.sh logs/live-NAME.txt` on the PC: it waits for the phone's CDC-ECM interface, sets 192.168.7.1/24 (sudo) and prints/saves the kernel console the phone streams every 100 ms as UDP to 192.168.7.1:5140 (starts with the last 64 KiB). `ping 192.168.7.2` checks the link. Current image: `shim/out/shim-boot-0077s.img` (kernel 0077, ADT sweet-0069hi, cpus=6, sweetfb_noconsole=1, sweetfb_hz=30, sweetusb=2). The recovery pull (`tools/sweet-log-pull.sh`) is still the way after a panic/hang before USB comes up.

**🎉 USB networking works (boot 0076s, 18:24 local): `ping 192.168.7.2` from the PC answers in ~1 ms, 0 % loss (200-packet burst, 1500-byte frames, 512/1024-byte frames).** 0075: CDC-ECM function (bulk 0x81/0x01, interrupt 0x82 NETWORK_CONNECTION; host MAC 02:00:5e:77:ee:01) + kernel ethernet ifnet `ue0` (legacy output, header strip like if_fake) with 192.168.7.2/24 set from the kernel (proto_plumb + SIOCAIFADDR on an in-kernel socket). 0076: received frames into one cluster mbuf (mbuf_allocpacket gave a first mbuf of length 0 -> panic "Failed mbuf validity check: len -14"). Host side (Linux cdc_ether, interface `enp0s20f0u3u1`): `nmcli dev set IF managed no; sudo ip addr add 192.168.7.1/24 dev IF; sudo ip link set IF up`. Boot image `shim/out/shim-boot-0076s.img` (`sweetusb=2`). iOS itself does not see ue0 yet (configd needs an IONetworkInterface in IOKit).

**USB device mode works (boot 0074s, 17:45 local): the host enumerates the phone at high speed as `1209:0001 ios-sweet "Sweet iOS (USB bring-up)"`.** 0072 read-only probe: ABL leaves the USB30_PRIM GDSC and all 7 USB clocks on, DWC3 v3.20a (GSNPSID 0x5533320a) in device mode (GCTL 0x00112000), halted (DCTL RUN_STOP 0, DSTS 0x00d3de04), event buffer still at ABL's 0xfdfc8000, QUSB2 PHY alive. 0073 (`sweetusb=2`): DCTL soft reset, own event buffer (polled, interrupt masked), ep0 DEPSTARTCFG/SETEPCONFIG/SETTRANSFRESOURCE, setup TRB, RUN_STOP; control-transfer state machine as Linux ep0.c; descriptors: vendor class, no data endpoints. It ran but no event came: **0074** forces the VBUS session in the Qualcomm wrapper (QSCRATCH 0xa6f8800: HS_PHY_CTRL |= UTMI_OTG_VBUS_VALID(20)|SW_SESSVLD_SEL(28), SS_PHY_CTRL |= LANE0_PWR_PRESENT(24), as Linux dwc3_qcom_vbus_override_enable) -> connect + enumeration. Image `shim/out/shim-boot-0074s.img`. Black Phone app: main thread waits in -[VMVoicemailManager fetchAccounts] (sync XPC; voicemail needs the modem).

**Navigation works (boot 0071s on v14, log `logs/boot-0071s.txt`):** swipe up from the bottom edge returns to the home screen; app switcher works. Two fixes: **0070** pid_hibernate (syscall 435 was nosys on the macOS config -> SIGSYS killed SpringBoard in -[SBToAppsWorkspaceTransaction _didComplete] when an app left the foreground; the only CONFIG_EMBEDDED-only entry in syscalls.master); **0071** touches starting within 48 px of an edge carry kIOHIDDigitizerEventFromEdgeTip (UIKit `_UIEventHIDTouchEdgeTypeForHIDEvent` reads the digitizer EventMask 0xb0007 bits 0x800/0x1000/0x2000/0x40000). Diagnosed, not fixed: Settings (Preferences) SIGTRAP in PodcastsUI func_1cdc47c58: force-unwrap of `URL.volumeTotalCapacity` (nil on our HFS+ root). Phone/Photos/Messages show black (MobilePhone launches, no crash) - next: stack samples via boot-arg `sweetsample=MobilePhone,MobileSlideShow,MobileSMS,SpringBoard` (image `shim/out/shim-boot-0071s.img`).

**🎉🎉 MILESTONE 2026-10-18 ~15:30 local: iOS 16.7 SPRINGBOARD HOME SCREEN ON THE PHONE** (boot `shim/out/shim-boot-0069s.img` = kernel 0069 + ADT `shim/out/sweet-0069hi.adt`, image **v14**; log `logs/boot-0069s-v14-HOMESCREEN.txt`). Home screen with a few apps, Settings opens, Control Center / lock screen / notification center work, touch + buttons work, 6 A55 cores (`cpus=6`), `sweetfb_noconsole=1 sweetfb_hz=30`. Known issue: cannot leave Settings (home gesture / AssistiveTouch home do nothing) - to investigate.
What it took today (in order): 0058 HID services (Apple IOHIDFamily-1915 user client), 0059 iPhone X identity (hw.product etc.), 0060 SPMI keys + GENI touch, 0061 1125x2436 presented display, 0062 RPMh L11C touch power + IOPMPowerSource battery, 0063 GENI FIFO packing (Goodix GT9896), 0064 PRIV_WORK_INTERVAL grant (SpringBoard "Failed to create work interval"), 0065 SMP via PSCI (6 A55), 0066 crash map regions, 0067 console mute without cons_ops write, 0068 IOSurface lookup of an already-mapped surface returns base -1 (backboardd snapshot crash), 0069 UFS log flush 10 s. Image v13: CommCenter removed from launchd.plist, BKNoWatchdogs. **Image v14** = v13 + Setup skipped (`/var/mobile/Library/Preferences/com.apple.purplebuddy.plist` SetupDone/SetupFinishedAllSteps true, SetupVersion 11, daemonizeNeedsToRun false; purplebuddy.notbackedup mini-buddy flags false; managedconfiguration.notbackedup LockdownActivationIndicatesCloudConfigurationAvailable false; springboard MCForceShowCloudConfigurationUI false) + mobileactivationd data ark seeded (`/private/var/containers/Data/System/D90C94C4-F94E-4FCF-8A28-A93BE3846D8E/Library/internal/data_ark.plist`, -ActivationState Activated etc.) + MediaToolbox D22/D221/Default SubServerConfiguration StartRecorderServer=false (mediaserverd crash loop: portrait-filter prewarm called NULL GL). **Activation:** ADT /chosen certificate-production-status 0, effective-production-status-ap 0, certificate-security-mode 1, effective-security-mode-sep 1 -> mobileactivationd's native Hactivation branch (Codex `codex/activation/report.md`; alternative 4-byte daemon patch documented there). Fallback image v13; v12 deleted.

**🎉 TOUCH WORKS (boot 0063u on image v13, 2026-10-18 ~13:15 local):** tapping (i) on Setup's Hello opens the device-info sheet; swipe-up is recognised (spinner, then back to Hello - under investigation). Chain: RPMh L11C vote (0062, `bsd/dev/sweet_rpmh.c`) -> GT9896 @0x5d on GENI SE7 (0063 fixed FIFO packing: register address went out byte-swapped) -> sweet_hid_touch -> SweetHIDTouch -> backboardd. Battery icon OK (0062 SweetBattery IOPMPowerSource, static 100 %). **Image v13** (= v12 + CommCenter jobs removed from launchd.plist + `BKNoWatchdogs`=true and `FBLaunchWatchdogExceptions{com.apple.purplebuddy:100}` in /var/mobile/Library/Preferences/com.apple.springboard.plist): Setup no longer killed by the scene-create watchdog (it blocked in CoreTelephony getSubscriptionInfo -> CommCenter, Codex `codex/setup/report.md`; that report also lists how to skip Setup: SetupDone/SetupFinishedAllSteps/SetupVersion=11 in com.apple.purplebuddy.plist + activation check). v9 deleted, fallback = v12. Input latency ~1 min with 1 CPU -> Codex task 11 = SMP via PSCI (`codex/smp/`).

**INPUT WORKS (boot 0060u on a freshly flashed v12, log `logs/boot-0060u.txt`):** power, volume up, volume down reach iOS (PMIC -> sweet_keys.c -> SweetHIDButtons -> backboardd). Power locks/unlocks (screen "off" shows the kernel console because the panel never really turns off). **Device identity fixed: iPhone X** (home indicator, Face-ID-style Setup). Earlier test (0059u, `sweethidtest=15` fake Home presses) advanced Setup from Hello to the language list.
- **0058** HID: `iokit/Kernel/arm/hid/`: IOHIDEventServiceUserClient + IOHIDEventServiceQueue + IOHIDEvent compiled UNCHANGED from Apple IOHIDFamily-1915.140.3 (= exact version of the iOS 16.7 IOHIDLib, clone in `research/iohid-1915`) over our minimal IOHIDEventService (SweetHID.cpp: SweetHIDButtons consumer page 0x0C power 0x30 / vol 0xE9/0xEA / menu 0x40; SweetHIDTouch digitizer collections). C hooks `sweet_hid_key(key, down)` (0 power, 1 vol+, 2 vol-, 3 home) and `sweet_hid_touch(finger, down, x, y)`. HID logs go to IOLog. Boot-arg `sweethidtest=N` = fake Home press every N s.
- **0059** identity: hw.machine/hw.model/hw.target/hw.product from the ADT (macOS-config kernel used to answer "iPad8,6"/"Redmi Note 10 Pro"). mkadt: root compatible `D22AP|iPhone10,3|xiaomi,sweet|...`, model iPhone10,3, target-type D22, `/product` copied from the real D22AP device tree (`research/ipsw-x/d22ap.adt`, extracted from the IPSW, NOT in git), `/buttons home-button-type 2`. Codex report `codex/mg/report.md`: MG ProductType = sysctl **hw.product** (unrecognized -> iPod), HWModelStr = hw.target, HomeButtonType = `/buttons/home-button-type`; disk cache `/private/var/containers/Shared/SystemGroup/systemgroup.com.apple.mobilegestaltcache/Library/Caches/com.apple.MobileGestalt.plist` (keyed by build + UUID only -> stale iPod answers survived; reflashed clean v12 to clear it).
- **0060** drivers by Codex (`codex/input/hw-report.md`): `bsd/dev/sweet_keys.c` (SPMI arbiter v5 observer reads, PON 0x810 bits KPDPWR/RESIN SID0, PM6150L GPIO2 SID4 0xc110; works), `bsd/dev/sweet_touch.c` (GENI SE7 I2C @0xa84000, starts 45 s after boot). Touch result: SE7 fw ok (proto 3) but **0x5d and 0x38 both time out -> touch IC unpowered** (L11C LDO needs an RPMh vote). Codex task 8 = RPMh client (`codex/rpmh/`), task 7 = battery (`codex/battery/`).
- **0061** (CI 39117078444): red status bar "rdar:45025538" = UIKit "No status bar visual provider for screen" (360x800 pt is no real iPhone). AppleCLCD now presents **1125x2436** (iPhone X) and shows the centered 1080x2400; touch mapped the same; ADT canvas 1125x2436. `sweetfb_native=1` reverts.
- Images: `shim/out/shim-boot-0060b.img` (0060 + /buttons ADT `sweet-0060hi.adt`). Next: 0061 image with ADT from current mkadt.

### >>> HANDOFF 2026-10-17 late (read this first) <<<

**STATE: iOS 16.7 Setup.app "Hello" screen is ON THE PHONE** (boot `shim/out/shim-boot-0057u.img` on image v12). Photo `/run/media/dipa/android/ios-sweet-work/MILESTONE-setup-hello-2026-10-17.jpg`. SpringBoard + backboardd + Setup run; nothing crashes in the GUI path. Remaining crash/relaunch loops: installcoordinationd (should be fixed by 0057, unverified), mediaserverd (VirtualAudio removed in v12, unverified), mobileactivationd (~100/boot, not analysed), bluetoothd + fairplayd.H2 relaunch constantly (no hardware).

**What is on the phone now:** userdata = image **v12** (`/run/media/dipa/android/ios-sweet-ipsw/ios16-root-20H392-v12.img` + `.simg` + `.sha256`; v9 kept as fallback, v8/v10/v11 deleted or superseded). Kernel **0057** (`xnu/out-0057`, CI `39067532732`). ADT **`shim/out/sweet-0057hi.adt`** (QEMU twin `research/q0057-hi.adt`). Boot image **`shim/out/shim-boot-0057u.img`**. Boot args: `debug=0xc serial=3 cpus=1 keepsyms=1 -enable_kprintf_spam -noprogress rd=ufsroot0 unentitled_ios_sim_launch=1 ignition_level=1 wdt_test=no_user_checkin ufsrw=1 rootrw=1 launchd_unsecure_cache=1 wdt=-1`.

**Build a phone image** (kernel K, ADT A): `python3 tools/mkpayload.py $K $A shim/out/payload-X.bin --cmdline "$B" && (cd shim && ./build.sh ../shim/out/payload-X.bin && cp out/shim-boot.img out/shim-boot-X.img)` then check `python3 tools/unpack_bootv2.py shim/out/shim-boot-X.img shim/out/check-X && cmp shim/out/check-X/ramdisk shim/out/payload-X.bin`. QEMU smoke test: `python3 tools/mkpayload.py $K research/q0057-hi.adt $S/csq/payloadX.bin --ramdisk $S/csq/root-fork.img --cmdline "debug=0xc serial=3 cpus=1 keepsyms=1 -enable_kprintf_spam -noprogress rd=md0"` + `PATH=~/swift/usr/bin:$PATH python3 tools/qemu-sweet.py ... --secs 40 --kernel $K --fail-on-panic` (S = scratchpad; root-fork.img lives in the session scratchpad csq/ dir and may be gone in a new session).

**Kernel workflow:** edit `research/bt28/xnu/...` (keep the pre-edit copy in `research/preNNNN/`), syntax check `python3 tools/xnu-cc.py research/run28.log research/bt28 <file>`, make `xnu/patches/NNNN-*.patch` with `diff -u pre bt28 | sed` path rewrite, add new/changed files to `research/check-patch-order.py` list, run it (must say applied + MATCH), commit + push -> GitHub Actions `xnu` builds (~8 min) -> `gh run download <id> -R dipa-studio/ios-sweet -n xnu-kernel -D xnu/out-NNNN`. **Repo is PUBLIC since 2026-10-17** (private macOS runner minutes ran out: "recent account payments have failed"); public = free runners. Commit trailer: only `Co-Authored-By: dipa-studio <183933817+dipa-studio@users.noreply.github.com>`.

**Phone workflow (user does buttons, Claude runs commands):**
- Boot test kernel: phone in fastboot -> `fastboot boot shim/out/shim-boot-X.img`. NEVER `fastboot getvar`.
- **Read logs WITHOUT filming:** after a test the user holds Power+VolDown -> fastboot -> `fastboot boot recovery/recovery.img` (OrangeFox, temp) -> wait for `adb shell true` -> `tools/sweet-log-pull.sh /run/media/dipa/android/ios-sweet-work/logs/<name>.txt` (reads the 4 MiB console ring the kernel keeps in the last 1025 blocks of userdata; patch 0047). Then `adb reboot bootloader` brings the phone back to fastboot without the user.
- **Flash a root image:** `fastboot flash -S 512M userdata <img>.simg` (7 min, 25 chunks). After a big flash the Xiaomi ABL fastboot hangs: next `fastboot boot` stalls at "Sending" -> the USER must re-enter fastboot by hand (Power+VolDown). Do not retry commands against the hung ABL. A flash right after `adb reboot bootloader` once failed on chunk 1 (USB protocol error): just retry. User must NOT unplug during flash (once interrupted at 25/25 -> reflash).
- **Edit the phone root without reflashing (same-length only):** find the file's raw offset in the local image (it is one extent; search the image for its first 4 KiB), compare with `adb exec-out dd if=/dev/block/sda34 ...`, then `adb push` changed 4 KiB blocks and `dd of=/dev/block/sda34 seek=... conv=notrunc,fsync`, read back. Recovery kernel has no hfsplus.
- **Pull the whole phone root** (12 min): `adb exec-out "dd if=/dev/block/sda34 bs=1048576 count=16384" > img`; mount ro with udisksctl or `sudo mount -t hfsplus -o loop,ro`. To write into a pulled image: `sudo fsck.hfsplus -fy` first (volume is never cleanly unmounted -> Linux mounts ro even with -o force), then `sudo mount -t hfsplus -o loop,force`.
- Making images: copy latest img with `cp --sparse=always`, mount rw with force, change, `sync; umount`, `sha256sum`, `img2simg`. Keep only the latest image + one fallback on the SSD (/home is ~98% full; big work files live in `/run/media/dipa/android/ios-sweet-work/`, old kernels/images archived in `.../ios-sweet-work/archive/`).

**Diagnostics built into the kernel (all SWEET-only):** persistent console log (0047, boot-arg sweetlog=0 off; flush every ~1 s); `|name| text` copies of /dev/null writes for processes in `sweetnull` (default backboardd,SpringBoard; 0048); `IOK name:` IOKit lookup/open trace for `sweetiolog` (default backboardd,SpringBoard; 0049/0054, 400 lines max); `SWEET Sandbox: proc op N` (0050); `STR ...` heap text dump on SIGABRT/SIGTRAP for `sweetscan` (default backboardd,SpringBoard; 0051/0053) - this is how NSException/BSAssert reasons were found; `SMP name tN pc .. bt ..` user stack sampler for `sweetsample` (default SpringBoard,backboardd; first at 90 s then every 120 s, 40 samples, 16 frames; 0054/0055); `SWEET FB: N swaps` every 1000 swaps; `CRASH name ...` crash reports (0043/0044). Symbolicate cache addresses with `ipsw dyld a2s research/dsc/dyld_shared_cache_arm64 <addr - slide>`; main-binary addresses: addr - mh + 0x100000000.

**Patches added today (0046-0057, all CI-built):** 0046 IOSurface (IOCoreSurfaceRoot) + IOMobileFramebuffer (AppleCLCD on /arm-io/disp0) + arm-io nubs; 0047 persistent log; 0048 /dev/null tee; 0049 IOKit trace; 0050 permissive "Sandbox" MAC policy; 0051/0053 heap text on crash; 0052 RENAME_SWAP via exchangedata on HFS; 0054/0055 sampler, swap counter, AKS selectors 35 (extended device state = 17) and 101; 0056 panel copy from the vsync timer at 10 Hz (sweetfb_hz) instead of every swap; 0057 no config_ext_resolver (ACL group entries resolve without memberd). ADT (tools/mkadt.py): /arm-io/disp0, /chosen/display-scale 3, /chosen/unique-chip-id (synthetic 0x5357454554000001) + chip-id 0x8015 -> IOPlatformUUID A9683613-3704-53F2-95D0-98A8FB574E78. Image v9-v12: /private/var/containers/{Bundle,Data/System,Shared/SystemGroup,Temp}; launchd.plist StandardOut/ErrorPath renamed to ...PatX (pointing jobs at /dev/console stops them launching: EACCES); v12: LastSystemVersion=20H392 in plain /var/mobile/Library/Preferences/com.apple.migration.plist (stops the 1-hour data migration that ran every boot), VirtualAudio.plugin moved to /Library/Audio/Plug-Ins/HAL.disabled/.

**Codex helper** (`codex exec --skip-git-repo-check -m gpt-6.1-sol -c model_reasoning_effort=high -s workspace-write -C /run/media/dipa/android/ios-sweet-work/codex -o OUT "$(cat task.md)" < /dev/null`, run detached with setsid nohup; config already defaults to gpt-6.1-sol high). Reports in `/run/media/dipa/android/ios-sweet-work/codex/`: mediaserverd-report.md, installcoordinationd-report.md (-> 0057), ufs-performance.md (ranked UFS speed plan), **ufs/0058-sweet-ufs-faster.patch** (READY, not yet applied: ufslogsecs default 10 s log flush batching, optional ufscache=1 directional cache ops, optional ufswait=1 spin-then-sleep; syntax-checked, host-stub verified; see ufs/README.md). Apply it as patch 0058 after review.

**Claude safety-classifier note:** several messages about QuartzCore renderer selection / writing an HFS reader tool were cut off by an automatic classifier (false positives, user agrees). Keep those topics short or let them be; they are not blockers now (rendering already works).

**NEXT STEPS (in order):**
1. **Input** (Setup stuck on Hello): touch + power + volume as IOHIDEventService/IOHIDDevice services backboardd matches (log shows backboardd matching IOHIDDevice with DeviceUsagePairs and IOService with HIDServiceSupport=true). Phone hardware: Goodix/Focaltech touch over I2C/SPI (check live DT `dtb/`), buttons via PMIC (pon) and GPIO keys. Start with a fake HID service (e.g. power button via a timer or boot-arg) to learn the ABI, then real drivers.
2. **Device identity**: MobileGestalt reports iPod + Home button. Add /product node / product-type (iPhone10,3, D22AP), device class iPhone, home-button-less (Face ID) properties in mkadt; find exact MG keys (MGIOMFBSupport.c, `IODeviceTree:/product` lookups seen in backboardd trace).
3. **Battery**: AppleSmartBattery/IOPMPowerSource style service (status bar shows empty red battery).
4. Apply Codex 0058 (UFS speed), consider cpus>1, check whether installcoordinationd/mediaserverd loops are gone, analyse mobileactivationd.
5. Hide kernel console over the GUI when not debugging: boot-arg sweetfb_noconsole=1 (but then panics are not on screen).

- **🎉 MILESTONE: iOS GUI ON THE PHONE - Setup.app "Hello" screen (2026-10-17 ~21:30 UTC, boot 0057u on image v12).** Photo: `/run/media/dipa/android/ios-sweet-work/MILESTONE-setup-hello-2026-10-17.jpg` (animated "dobar d(an)" hello lettering, status bar "iPod" + battery icon, bottom "Pritisnite Home za otvaranje" = "Press Home to open" (locale hr), (i) button). Rendered by iOS 16.7 SpringBoard/Setup through CoreAnimation -> backboardd -> kernel IOSurface (IOCoreSurfaceRoot) -> kernel AppleCLCD swaps -> ABL panel memory. What made it: data migration finally skipped (v12: `LastSystemVersion` 20H392 in the plain `/var/mobile/Library/Preferences/com.apple.migration.plist`; ADT `/chosen/unique-chip-id` + `chip-id` for IOPlatformUUID), 0057 (no ext resolver -> ACL containers work), plus everything before (0046 display/IOSurface, 0050 Sandbox policy, display-scale 3, containers dirs, RENAME_SWAP, AKS 35/101, 10 Hz present).
  **Missing (next work, in rough order):**
  - **Input: no touch, no power button, no volume buttons** (no HID drivers; backboardd looks for IOHIDDevice / HIDServiceSupport services). Setup is stuck on "Hello".
  - **Device identity: it thinks it is an iPod with a Home button** (status bar "iPod", "Press Home to open"): MobileGestalt has no product/model identity (no /product node, product-type, etc.) - give it iPhone10,3 / home-button-less (Face ID class) identity.
  - **No battery detection** (no battery/charger/PMIC service; status bar battery shows empty/red).
  - Locale came up Croatian (hr) - harmless.
  - Performance: cpus=1, polled UFS (Codex UFS patch in progress: `codex/ufs/`), backboardd presents at 60 Hz.
- **README refreshed (2026-10-17):** read the full notes and updated the public overview through patch 0045, v7 hardware observations and prepared v8 diagnostics. Documents real Apple userspace, the missing display/IOSurface GUI work, limited security services, highmem, persistent userdata root, current tooling and build examples. Documentation only; no kernel build, tests, flashing or phone boot performed.

- **v11 still migrated (boot 0056u, 20:32 UTC, `logs/boot-0056u-v11.txt`).** On iOS kCFPreferencesCurrentHost lands in the plain plist: all DMEnvironment setters (setLastBuildVersionPref, setUserDataDispositionPref, ...) use CurrentHost and the phone's `/var/mobile/Library/Preferences/com.apple.migration.plist` holds DMUserDataDisposition; datamigrator's XPC service runs with `_RoleAccount: mobile`. **Image v12** = v11 + `LastSystemVersion` = 20H392 added to that plain `com.apple.migration.plist` (keeps DMUserDataDisposition, 501:501 0600) + `/Library/Audio/Plug-Ins/HAL/VirtualAudio.plugin` moved to `/Library/Audio/Plug-Ins/HAL.disabled/` (Codex: stops the mediaserverd SIGSEGV loop; untested). **installcoordinationd loop explained (Codex `codex/installcoordinationd-report.md`):** os_crash "Failed to create data directory" EACCES for `/private/var/containers/Shared/SystemGroup/systemgroup.com.apple.installcoordinationd/Library/InstallCoordination`: `Library`/`Library/Caches` in the container are ACL-only (uid/gid 0xfffffffe, mode 0000, ACE for group GUID ...012B = gid 299 systemusers); with `config_ext_resolver` the kernel asks an identity resolver (memberd/opendirectoryd) that iOS does not run -> EWOULDBLOCK -> ACE skipped -> EACCES. **Patch 0057**: drop config_ext_resolver from FILESYS_BASE (compatibility UID/GID<->GUID mapping is used instead), likely fixes other ACL-protected containers too. Codex task 3: UFS driver performance design (`codex/ufs-performance.md`).
- **mediaserverd SIGSEGV loop explained (Codex report `/run/media/dipa/android/ios-sweet-work/codex/mediaserverd-report.md`):** the fault (FAR 0x390) is in the HAL plug-in `/Library/Audio/Plug-Ins/HAL/VirtualAudio.plugin/VirtualAudio` (ApplyBeamFormerPreference <- VirtualAudio_PlugIn::SetPropertyData <- HALS_AHPPlugIn::ObjectSetPropertyData <- AudioObjectSetPropertyData <- MediaExperience vaemVADSerializationListener): the default virtual audio device ('vdef', VirtualAudioDevice_Default) does not exist (no audio hardware/driver, no /product/audio). Proposed workaround for GUI bring-up: move VirtualAudio.plugin out of /Library/Audio/Plug-Ins/HAL/ in the next root image (untested). v11 reflashed OK after an interrupted flash (USB unplugged at chunk 25/25). Codex task 2: installcoordinationd crash loop.
- **ROOT CAUSE of the endless migration: no IOPlatformUUID (2026-10-17).** datamigrator's `-[DMMigrator isMigrationNeededWithBuildVersion:lastBuildVersion:clientPID:]` gets lastBuildVersion from `-[DMEnvironment lastBuildVersionPref]` = `CFPreferencesCopyValue("LastSystemVersion", "com.apple.migration", kCFPreferencesCurrentUser, kCFPreferencesCurrentHost)` -> a ByHost file. The phone had `/var/mobile/Library/Preferences/com.apple.migration.plist` (only DMUserDataDisposition) and NO `Preferences/ByHost` directory at all. On arm XNU publishes IOPlatformUUID (gethostuuid) only from `/chosen/unique-chip-id` (8 bytes) + `/chosen/chip-id` (4 bytes) (IOPlatformExpertDevice::generatePlatformUUID, called from IOPlatformExpert::start); the SWEET ADT had neither, so every CurrentHost preference write failed. Fix: mkadt adds `unique-chip-id` = 0x5357454554000001 (synthetic) and `chip-id` = 0x8015 -> UUID `A9683613-3704-53F2-95D0-98A8FB574E78` (same SHA1 namespace computation as the kernel). ADT `shim/out/sweet-0057hi.adt`, boot image `shim/out/shim-boot-0056u.img` (0056 kernel + 0057hi ADT, QEMU OK). **Image v11** = v10 + `Preferences/ByHost/com.apple.migration.<UUID upper and lower>.plist` {LastSystemVersion: 20H392} (501:501, dir 0755 files 0600). Flashing v11 2026-10-17 ~20:10 UTC. Codex (gpt-6.1-sol high) analysing the mediaserverd SIGSEGV loop in `/run/media/dipa/android/ios-sweet-work/codex/` (report `mediaserverd-report.md`).
- **v10 did NOT stop the migration (boot 0056n on v10, 19:18 UTC, `logs/boot-0056n-v10.txt`):** datamigrator + migrationpluginwrapper ran again, backboardd drew the progress UI (13000+ swaps in ~5 min). So `com.apple.DataMigration.plist`/LastSystemVersion is not the deciding input. What is known about the decision (datamigrator XPC service `DataMigration.framework/XPCServices/com.apple.datamigrator.xpc/com.apple.datamigrator`, strings): `Migration sentinel present. Migration necessary.` (sentinel `/private/var/datamigrator/migrate`, created and removed by datamigrator itself; absent in v10), `System build version changed from %@ to %@. Migration necessary.` / `...unchanged... not necessary`, `Disposition dictionary with build version %@ is out of date relative to current build version %@`, `SyntheticDidUpgrade`, DMUserDataDispositionManager; previous build source not found yet (not in the binary's plain strings; likely in DataMigration.framework's DMUserDataDispositionManager / preferences domain `com.apple.migration`). backboardd calls `DMPerformMigrationIfNeeded` and holds SpringBoard in `checkInAndWaitForDataMigration` until it returns. NEXT: find where the previous build version / disposition dictionary is stored (disassemble DataMigration.framework DMUserDataDispositionManager + datamigrator's isMigrationNeeded path), write it into the image; or get datamigrator's os_log out (OS_ACTIVITY_DT_MODE needs a launchd env change).
- **Data migration never records completion -> skip it (image v10, 2026-10-17).** Boot 0056n (18:16 UTC, `logs/boot-0056n.txt`, 30 min): 10 Hz panel copies, backboardd still presents at ~60 Hz (107k swaps), SpringBoard still in `BKSSystemShellService _checkIn` at sample 14. Every migration run takes 1+ hour on cpus=1 and repeats each boot. DataMigration decides from `/var/mobile/Library/Preferences/com.apple.DataMigration.plist` key `LastSystemVersion` (vs ProductBuildVersion 20H392); the pulled phone root (21:01 local) had NO such file. **v10** = that pulled phone state + fsck.hfsplus -fy (volume was marked not cleanly unmounted -> Linux mounts it read-only even with -o force; fsck found only hard-link counts + minor volume header, repaired) + `com.apple.DataMigration.plist` {LastSystemVersion: 20H392} (501:501 0600). `/run/media/dipa/android/ios-sweet-ipsw/ios16-root-20H392-v10.img` (+ .sha256, .simg); v8 files deleted, v9 kept as fallback.
- **Repo made PUBLIC (2026-10-17, user request) so GitHub-hosted macOS runners are free:** the 0056 CI run was refused ("recent account payments have failed or your spending limit needs to be increased"). Checked before: no device dumps, serials, IMEI or Apple binaries in the history (.gitignore keeps backup/, dtb/, recovery/, research/ out); commit author emails are public now. 0056 rerun `39056660104` passed -> `xnu/out-0056`, QEMU OK, image `shim/out/shim-boot-0056n.img` booted 18:16 UTC.
- **Boot 0055n (17:16 UTC, ~65 min, `logs/boot-0055n.txt`): migration bar reached 99% in ~30 min (was ~60), then crawled.** Root cause of the slowness: backboardd presents the progress UI at ~58 Hz (**167,000 swaps in ~48 min**) and AppleCLCD copied the full 10 MB frame into the panel on every swap -> ~600 MB/s memcpy on the single CPU (cpus=1), starving everything (polled UFS I/O too). Sampler (16 frames): **SpringBoard waits in `-[BKSSystemShellService _checkIn]`** (synchronous BSXPC call to backboardd, from FBSystemShellInitialize <- SBSystemAppMain) - backboardd holds the system shell check-in until the data migration ends, so the migration is the gate to SpringBoard UI. **Patch 0056**: swap only records the latest swap record; the vsync timer copies it to the panel every 60/sweetfb_hz ticks (default 10 Hz); `SWEET FB: N swaps` every 1000.
- **Boot 0054n (16:53 UTC, ~12 min, `logs/boot-0054n.txt`, patch 0054 sampler):** the data migration runs AGAIN on every boot (it completed once in the 0053s run) - completion is not being recorded. backboardd keeps swapping the progress UI (3700+ swaps in ~10 min, `SWEET FB: N swaps`). Sample during migration: SpringBoard main thread blocked in a synchronous XPC call (`mach_msg2_trap <- dispatch_mach_send_and_wait_for_reply <- xpc_connection_send_message_with_reply_sync <- -[BSXPCServiceConnectionMessage _sendSynchronously:] <- BSXPCServiceConnectionProxy ...`). Unsupported AKS selectors seen: 101 `aks_assert_consume`, 93 `aks_get_internal_info`, 34 `_aks_stash_load` (datamigrator), **35 `aks_get_extended_device_state`** (SpringBoard, chronod, remindd, searchd, symptomsd...). **Patch 0055**: AKS 35 answered like 17 (same DER device state), 101 succeeds; sampler backtraces 16 frames, 40 samples (~80 min).
- **MILESTONE: FIRST iOS PIXELS ON THE PANEL (boot 0053s long run, 15:33 UTC, ~60 min; photos IMG_20261017_183029/183222/183419; log `/run/media/dipa/android/ios-sweet-work/logs/boot-0053s-long.txt`, 407 KB, 1428 flushes).** The iOS data-migration boot screen (Apple logo + progress bar) was shown and the bar advanced to full in ~60 minutes. It is drawn by **backboardd through our kernel display path**: `SWEET SURF: backboardd create id 2/3 1080x2400 fmt 0x42475241 (BGRA) bpe 4 bpr 4352 size 10452992 keys 11`, IOSurface sels 9, 27, 5, 34 and traps 2/3 (lock/unlock), IOMFB SwapBegin (4) / SwapEnd (5, 1132-byte struct) / GetLayerDefaultSurface (3) / 68 / 55, then `SWEET FB: swap N layer 0 surface 2|3 1080x2400 ... a 0,0 1080x2400 b 0,0 1080x2400` alternating (double buffering; only the first 16 swaps are logged). Triggered by `com.apple.datamigrator` (AKS sels 101/93/34 return unsupported) and `com.apple.migrationpluginwrapper`. Probably ProgressUI-style CoreGraphics drawing into IOSurfaces (no GPU used). After the migration: SpringBoard and backboardd stay up (exec once each, no crash), nothing new drawn; crash loops only for mediaserverd, installcoordinationd, mobileactivationd (~108 each in the hour); bluetoothd and fairplayd.H2 relaunch constantly (no hardware). Kernel console text overlays the image (sweetfb_noconsole=1 would hide it).
- **MILESTONE: SpringBoard and backboardd both stay up (boot 0053s on v9, 15:29 UTC, `logs/boot-0053s.txt`).** With /chosen/display-scale = 3: `exec SpringBoard` once, `exec backboardd` once, no CRASH for either; MobileGestaltHelper reads IOMFB size/dot pitch; backboardd opens AppleCLCD (sels 57,15,22,29,33,79,74 as before). No IOSurface creates and no swaps: backboardd keeps polling `IOProviderClass IOAcceleratorES` (-> 0 found) and AGXAccelerator/IOAcceleratorESLegacy - no GPU, so no CoreAnimation renderer yet. Log goes quiet after ~47 s (only 47 flushes): the system idles. NEXT WALL: CoreAnimation rendering without a GPU (CPU path) so the window server produces frames.
- **SpringBoard's invalid mode = scale 0 (boot 0053n, 15:19 UTC, `logs/boot-0053n.txt`, heap scan):** `FBSDisplayMode cannot be configured as requested : <FBSDisplayMode: ...; infxinf@0x (1080x2400/0) 60Hz sRGB SDR>` - pixel size and 60 Hz are fine, scale is 0. libMobileGestalt (MGIOMFBSupport.c, sub_19c560a54) reads `display-scale` (u32, default 0) and `display-rotation` from **IODeviceTree:/chosen**, pixel size via IOMobileFramebufferGetDisplaySize (MobileGestaltHelper sel 8/28 in the log). mkadt now adds `/chosen/display-scale` = 3 (1080x2400 @3x = 360x800 pt). ADT `shim/out/sweet-0054hi.adt` (QEMU `research/q0054-hi.adt`), image `shim/out/shim-boot-0053s.img` = 0053 kernel + 0054hi ADT. Possible catch: MobileGestalt may have cached scale 0 in `/private/var/containers/Shared/SystemGroup/systemgroup.com.apple.mobilegestaltcache/...`.
- **MILESTONE: backboardd survives and opens the display (boot 0052n on v9, 15:07 UTC, `logs/boot-0052n.txt`).** No `CRASH backboardd`. It walks `IODeviceTree:/arm-io` children, matches IOMobileFramebuffer, `open AppleCLCD type 0 -> 0x0`, calls IOMFB selectors 57, 15, 22, 29, 33, 79 (GetBlock, out 1580/40), 74 (SupportedFrameInfo), 12, 6, 27, 17, 84, 50; opens IOCoreSurfaceRoot (sel 13); looks for AGXAccelerator / IOAcceleratorES / IOAcceleratorESLegacy (none, repeatedly), `IODeviceTree:/product` (none, repeatedly), `/buttons`, aop-smart-cover, IOPMrootDomain. No swaps yet. **SpringBoard now gets past display discovery** and dies (sig 5) in `-[FBSDisplayMode _initWithWidth:height:preferredScale:scaleOverride:refreshRate:gamut:hdr:rotation:virtual:validityCheck:]+580` <- `_initWithCADisplayMode:scale:rotation:` <- `FBSDisplayConfiguration _initWithImmutableDisplay:` <- `FBSDisplaySource initWithDisplay:` <- `FBSDisplayMonitor` (slide 0x14504000): "FBSDisplayMode cannot be configured as requested". Checks: width/height >= 2, preferredScale > 0, scaleOverride >= 0, refreshRate non-zero, valid gamut/HDR/rotation. Suspects: refresh rate 0 (IOMFB timing blocks answered with zeros) and/or scale 0 (MobileGestalt main-screen-scale; no /product node in the ADT). **Patch 0053**: heap text scan also on SIGTRAP and for SpringBoard (default sweetscan list backboardd,SpringBoard) to read the exact mode description.
- **Image v9 (2026-10-17) = v8 + `/private/var/containers/{Bundle,Data/System,Shared/SystemGroup,Temp}` (root:wheel 0755; on iOS these live on the data volume, absent from the rootfs) + launchd.plist with StandardOutPath/StandardErrorPath renamed to ...PatX (the in-place phone fix; daemons' stdout reaches the log via the 0048 /dev/null tee).** `/run/media/dipa/android/ios-sweet-ipsw/ios16-root-20H392-v9.img` SHA256 aa9f9139...6e67, `.simg` 12,145,303,864 bytes; written through `sudo mount -t hfsplus -o loop,force`. **Patch 0052** (`xnu/patches/0052-sweet-hfs-rename-swap.patch`, CI `39042761826` -> `xnu/out-0052`, QEMU OK, image `shim/out/shim-boot-0052n.img`): vn_rename falls back to VNOP_EXCHANGE when VNOP_RENAMEX(RENAME_SWAP) returns ENOTSUP for two regular files on one volume (HFS exchange swaps data and cnode descriptors = swap semantics). Flashing v9 started 2026-10-17 ~15:00 UTC.
- **backboardd EXCEPTION FOUND (boot 0051n, 14:41 UTC, `logs/boot-0051n.txt`, patch 0051 heap scan):** `*** Terminating app due to uncaught exception 'NSInvalidArgumentException', reason: '*** -[NSURL initFileURLWithPath:]: nil string parameter'`. First-throw stack (slide 0x337f0000): `+[NSURL fileURLWithPath:]` <- `-[BSSystemContainerForCurrentProcessPathProvider libraryPath]` <- `cachesPath` <- backboardd main+0x1d858 (StartWindowServer, shader cache path). BaseBoard: libraryPath = `BSSystemSharedResourcesDirectoryForIdentifier` = `BSSystemSharedDirectoryForIdentifier(id)` + "/Library"; that calls `container_system_path_for_identifier` (libsystem_containermanager -> `_container_legacy_lookup` -> containermanagerd XPC), which returned NULL (BaseBoard logs "Error getting shared system container ..."). With 0050 the sandbox denials are gone. containermanagerd.log.0 in the pulled (pre-0050) image: "Did not receive any persona attributes", "Expected to find at least one persona", notify_register_dispatch failed 9; `/private/var/containers` does NOT exist in the root image (on iOS it lives on the data volume). usermanagerd does create kernel personas 99/199/1000, but fails to save `/private/var/keybags/usersession.kb` and `persona.kb`: "Failed to atomically swap writing file: Operation not supported (45)" (HFS has no RENAME_SWAP). NEXT: create `/private/var/containers` (and check what containermanagerd needs for system group containers), fix or emulate RENAME_SWAP on HFS, then re-check backboardd.
- **Disk housekeeping (2026-10-17):** /home was at 4 GiB free. Moved (not deleted) `xnu/out-0010..0044` and old `shim/out/*.img`/`payload-*.bin` (everything before 0046) to `/run/media/dipa/android/ios-sweet-work/archive/{xnu,shim-out}` (6.3 GiB); /home now 8.7 GiB free. Large work files (phone-root.img 16 GiB, logs, tracev3 dumps) live in `/run/media/dipa/android/ios-sweet-work/`. **Patch 0051** (`xnu/patches/0051-sweet-crash-heap-strings.patch`, CI `39041440935`): on SIGABRT of a process in boot-arg `sweetscan` (default backboardd) the crash log prints heap text runs as `STR ...` (to find the NSException reason). Boot 0051n 14:41 UTC.
- **Boot 0049n (14:11 UTC, `logs/boot-0049n.txt`, patch 0049 trace): backboardd's IOKit lookups before it dies** (each run): `IODeviceTree:/arm-io/pearl-sep` -> none, matching ApplePearlSEPDriver -> none, `IOService:/IOResources/AppleKeyStore` open OK, matching IOHIDDevice (DeviceUsagePairs) / `HIDServiceSupport` notifications, `usb-drd,t8027` notification; **never any IOMobileFramebuffer / display lookup** - the exception happens before display detection. launchd (tracev3) shows backboardd's mach lookups denied with `error = 159: Sandbox restriction`: com.apple.mobilegestalt.xpc, com.apple.iohideventsystem, com.apple.system.notification_center, com.apple.logd, containermanagerd, ACCHWComponentAuthService, oscard. libsystem_sandbox uses `__mac_syscall("Sandbox", op, arg)` (ops: 1 init, 2 check, 3 note, 4 container path, 5/6/7/8 extensions, 0x15 check_bulk, ...); with no policy named "Sandbox" every call gets ENOPOLICY. **Patch 0050** (`xnu/patches/0050-sweet-sandbox-policy.patch`): built-in permissive MAC policy "Sandbox" in sweet_amfi.c (mpo_policy_syscall returns 0, container/extension ops ENOENT; logs first use of each op as `SWEET Sandbox: proc op N`).
- **Phone root pulled (16 GiB, 12 min, `adb exec-out dd if=/dev/block/sda34`) to `/run/media/dipa/android/ios-sweet-work/phone-root.img` (loop-mounted ro at /run/media/dipa/iOSRoot).** No .ips crash reports. logd tracev3 (Persist, LZ4 `bv41` blocks, decompressed strings in `ios-sweet-work/tracev3/all.txt`): /private/var/db/uuidtext is EMPTY so only launchd's own messages are readable. Findings: v8 launch failure = `Service could not initialize: posix_spawn(/usr/libexec/backboardd), error 0xd - Permission denied` (xpcproxy exit 78) - /dev/console not openable for the mobile user; backboardd[98] spawned `com.apple.MTLCompilerService` before SIGABRT; **launchd denies many mach lookups with `error = 159: Sandbox restriction`** (mediaserverd -> com.apple.backboard.display.services, remoted, mobiletimerd -> sleepd, identityservicesd -> apsd) and **tccd exits OS_REASON_SANDBOX "profile not found"** - no Sandbox kext/profiles on SWEET; likely cause of many daemon crash loops (next wall after the display). CF's uncaught-exception text never reaches stderr for daemons (no CF handler; libc++abi prints only the type). **Patch 0049** (`xnu/patches/0049-sweet-iokit-trace.patch`): `IOK name: ...` console lines for registry path lookups, child iterators, matching (with result count/class), matching notifications and IOServiceOpen of the processes in boot-arg `sweetiolog` (default backboardd), max 400 lines.
- **CONFIRMED: launchd StandardOut/ErrorPath=/dev/console stops backboardd from launching.** After the in-place rename (boot 0047n-b, log `logs/boot-0047n-b.txt`) backboardd launches again and dies as on v7: sig 6, `___pthread_kill <- abort <- demangling_terminate_handler <- _objc_terminate <- std::terminate <- _dispatch_client_callout <- _dispatch_once_callout <- main+0x9334` (window-server dispatch_once). It never opened AppleCLCD or IOCoreSurfaceRoot (no `SWEET FB/SURF: backboardd` lines) -> throws before/at display detection. **Patch 0048** (`xnu/patches/0048-sweet-devnull-tee.patch`, CI `39037749668` -> `xnu/out-0048`, image `shim/out/shim-boot-0048n.img`): writes to /dev/null by processes named in boot-arg `sweetnull` (default `backboardd,SpringBoard`) are printed as `|name| text`. Boot 0048n (13:48 UTC, log `logs/boot-0048n.txt`): only `|backboardd| libc++abi: terminating due to uncaught exception of type NSException` (CF's reason line goes to os_log, not stderr, despite CFLOG_FORCE_STDERR/OS_ACTIVITY_DT_MODE). Next: pull the whole 16 GiB root from recovery (`adb exec-out dd if=/dev/block/sda34`) to `/run/media/dipa/android/ios-sweet-work/phone-root.img` and read ReportCrash .ips files / logd tracev3 for the exception reason.
- **Persistent log WORKS (boot 0047n on v8, 13:31 UTC; pulled from OrangeFox: 70 KB, 111 flushes, `/run/media/dipa/android/ios-sweet-work/logs/boot-0047n.txt`).** In 3 min **backboardd was never exec'd** (v7 ran it), ~70 bare `exec xpcproxy`, SpringBoard loops on FBSDisplayMonitor (no display), mediaserverd sig 11 loop, locationd, lockdownd sig 5. Suspect the v8 plist (StandardOut/ErrorPath=/dev/console on backboardd). **In-place plist edit from recovery (no reflash):** launchd.plist is one extent at image/partition byte offset 0x1e025f000 (195 blocks; verified bytes identical on phone vs local v8 mount); renamed StandardOutPath->StandardOutPatX and StandardErrorPath->StandardErrorPatX (same length, both jobs) in blocks 68 and 105 via `adb push` + `dd of=/dev/block/sda34 seek=... conv=notrunc,fsync`, read back VERIFIED. Phone now differs from local v8 image in those 2 blocks (files in `/run/media/dipa/android/ios-sweet-work/`). Test boot 0047n 13:38:42 UTC. Recovery kernel has no hfsplus (raw block edits only).
- **Patch 0047: persistent console log (CI `39036478663` -> `xnu/out-0047`, QEMU no panic; phone image `shim/out/shim-boot-0047n.img` = 0047 + sweet-0046hi.adt + 0045n cmdline).** `_cnputs` (all console output: kernel printf + daemons' /dev/console) also appends to a 4 MiB ring in sweet_ufs.c; after the UFS partition is ready and writable (ufsrw=1) a thread writes new ring blocks + header to the LAST 1025 blocks (4 KiB) of userdata every ~1 s and SYNCHRONIZE CACHE (prints `SWEET LOG: console log to the last 4100 KiB ...`). Read: phone to fastboot -> `fastboot boot recovery/recovery.img` (OrangeFox) -> `tools/sweet-log-pull.sh OUT.txt` (adb dd of that area + `tools/sweet-log.py`). Not yet verified on the phone. Panics after the last flush are not in it (screen still shows them). 2x font attempt reverted: XNU's v_scale only scales the progress icon.
- **Boot 0046n on v8 (13:05 UTC, VID_20261017_150522_HSR_120):** phone prints `SWEET SURF: IOCoreSurfaceRoot registered` and `SWEET FB: AppleCLCD 1080x2400 stride 4320 at 0x9c000000, default surface 1` (nubs + match work on hardware). Visible userspace: early boot tasks, launchd_cache_loader, `exec SpringBoard`; no `exec backboardd` / `SWEET FB: backboardd` line seen in the readable frames (video blurry). Frame 00:47: lower half of the screen shows OLDER console text (16:01:12) below newer lines -> unconfirmed hint that a swap copied an old snapshot of the panel (CA reads the default/displayed surface = panel memory). SpringBoard still dies in `-[FBSDisplayMonitor _initWithBookendObserver:transformer:]+1160` (sig 5, slide 0x30960000). **Shim: 2x console font** (`shim/loader.c` Video.v_depth scale field = 1) so phone videos are readable; image `shim/out/shim-boot-0046b.img` = 0046n + 2x font.
- **Patch 0046: built-in IOSurface + IOMobileFramebuffer (2026-10-17, offline, NOT phone-tested).** `xnu/patches/0046-sweet-iosurface-iomfb.patch`: new `iokit/Kernel/arm/SweetSurface.{h,cpp}` (IOCoreSurfaceRoot + IOSurfaceRootUserClient: sel 13/0/4/34/35, traps 0-5, wired buffers mapped into the caller, per-client refs) and `SweetFramebuffer.cpp` (AppleCLCD : IOMobileFramebuffer on /arm-io/disp0: sizes, swap = CPU copy of enabled layers into the ABL panel memory, 60 Hz vsync via sendAsyncResult64WithOptions(CanDrop), panel memory published as the default IOSurface, kernel text console paused on the first swap only with `sweetfb_noconsole=1` (default keeps the console: pausing switches it to serial and would hide panics)); SweetPlatformExpert creates nubs for /arm-io children (not gic) attached to the platform expert (IOPlatformDevice::compareName casts its provider to IOPlatformExpert, so nubs under the arm-io nub never matched - first CI build showed that in QEMU). mkadt: /arm-io/disp0 {device_type display-subsystem, compatible sweet,display, canvas-width 1080, canvas-height 2400}. CI `39021572169` -> `xnu/out-0046`. **QEMU** (`research/q0046-hi.adt`, RAM disk init, msgbuf): `SWEET SURF: IOCoreSurfaceRoot registered`, `SWEET FB: AppleCLCD 1080x2400 stride 4320 at 0x9c000000, default surface 1`, init alive, no panic. Phone image **`shim/out/shim-boot-0046n.img`** (SHA256 9c4d2fe9..., CI `39024108588` with the review fixes: swap bounds check, zeroed 64-bit async ref, port release, 1.5 GiB wired budget, ref leak/race fixes; QEMU re-checked) = 0046 kernel + `shim/out/sweet-0046hi.adt` + the 0045n cmdline; boot it on image v8 (backboardd/SpringBoard log to console) and film. Expected new console lines: `SWEET SURF: <proc> create id ...`, `SWEET FB: backboardd sel N ...`, `SWEET FB: swap ...`. Open question for the next wall: QuartzCore's IOMFB server builds its renderer from Metal first (`CAMetalContextCreate`), GLES only when enabled; how the CPU renderer gets selected on a device without a GPU is not yet established.
- **IOSurface values ABI (offline RE, `/run/media/dipa/android/ios-sweet-work/iosurface-values.md`) - TODO in SweetSurface (0046 only accepts and drops values, so IOSurfaceCopyValue always returns NULL):** sel 9 SetValue in = {u32 id, u32 pad, IOCFSerialize([value, key]) or ([dict] = merge)}, sel 0xb RemoveValue in = {u32 id, u32 pad, key\0} (empty key = remove all); both out 4 bytes = new generation, client accepts only (gen+2)|1. Kernel after each change: gen = (gen+2)|1 (odd, never 0) -> state+0x20, serialized size (>=1) -> state+0x28. sel 0xa in {u32 id, u32 0, u8 0}, out {u32 ?, u32 gen, serialized non-bulk dict}; too small -> 0xe00002db + needed size (client retries x16). sel 0x1b in 0x88: bulk struct 0x70 @0, u64 valid size @0x70, u64 changed mask @0x78, u32 id @0x80 -> copy masked fields into state+0x30 (bit0 32B @0, bit1 16B @0x20, bit2 8B @0x30, bits3-10 1B @0x38..0x3f, bits11-14 24B @0x40/4B @0x58/8B @0x5c/1B @0x64).
- **IOMFB display matching confirmed (offline RE, `/run/media/dipa/android/ios-sweet-work/iomfb-match.md`):** the framework never matches on "AppleCLCD"; any registered IOMobileFramebuffer subclass works. `iomfb_match_callback` reads only `dfr`/`AppleTV`/`external` (CFBoolean, service itself, no parents); internal main display = all absent/false (type 0, name "primary"). Display count = /arm-io children whose device_type starts with "display-subsystem" (count 0 -> CreateDisplayList returns NULL; more nodes than services -> 30 s wait). IOMobileFramebufferOpen fails only on IOServiceOpen failure; canvas-width/height read as 4-byte CFData from the IOService-plane parent (optional). CopyProperty = IORegistryEntrySearchCFProperty on the service only. Patch 0046 (disp0 node, `external`=false, AppleCLCD : IOMobileFramebuffer) fits all of this.
- **IOMobileFramebuffer swap + notification ABI (2026-10-17, offline).** Swap record = fb+0x18, **0x46c bytes**, zeroed by SwapBegin and sent whole by `kern_SwapEnd` = IOConnectCallStructMethod(sel 5, rec, 0x46c, no output). **SwapBegin** = sel 4, no input, 1 scalar out = swap id (stored at rec+0x50). `kern_SwapSetLayer(fb, layer<4, IOSurfaceRef, CGRect a, CGRect b, flags)`: rec+0x54+4*layer = **IOSurface id**; rec+0x104 bit layer = layer enabled (rec+0x108 bit cleared); rect a (int x,y,w,h, scaled) at rec+0x64+16*layer, rect b at rec+0xc4+16*layer; rec+0x114+4*layer = transform from flags&0xf; flag bits 5/31/6/7/8/9 set bytes rec+0x2ca/0x2cc/0x2e3/0x2e5/0x2e6/0x467+layer. A NULL surface only sets the enable bit with zero id. SwapWait = sel 6 scalars [swap id, timeout, 0].
  - **Notifications**: `IOMobileFramebufferScheduleWithDispatchQueue`/`GetRunLoopSource` create an IONotificationPort and `IOConnectSetNotificationPort(conn, type, port, 0)` (kernel `registerNotificationPort`). `kern_EnableNotifications(fb, type, cb, ctx)` = **sel 72 scalars [NotifyCallbackFuncs[type], fb, type, 0]** -> the kernel keeps an async reference {port, func, refcon=fb} per type and fires it with `sendAsyncResult64`. Types: 0 HotPlug, 1 Power, 3 FrameInfo (args[0] = mask of 31-bit keys, args[1] u32, then values), 4 CRC, **5 Vsync**: 6 args, each a 32-bit half in a u64 slot: (ts lo, ts hi), (t2 lo, hi) passed through the time-ingest helper, (t3 lo, hi); the framework then calls the client's vsync callback(fb, ts, t2', t3, ctx). Vsync callbacks are dropped while the notification port has queued messages.

- **IOSurface.framework user-client ABI reversed (2026-10-17, offline, step 2 of the GUI plan).** `ipsw dyld disass research/dsc/dyld_shared_cache_arm64 --image IOSurface` (selector scan script: scratchpad `selscan.py`).
  - Connect (`_iosConnectInitalize`, pthread_once): `IOServiceGetMatchingService(IOServiceNameMatching("IOCoreSurfaceRoot"))`, retried with sleep(1) up to 241 times (a missing service stalls every client ~4 min, no crash); `IOServiceOpen(type 0)`; then **sel 13** (no inputs, struct out 0x18 bytes = `_ioSurfaceLimits`) and requires u16 at out+0x16 == 1 (ABI version); out+0 = offset/plane-base alignment mask, out+4 = bytes-per-row alignment mask (used as (x+m)&~m), +0..+0x14 also copied into IOSurface remote-method init, otherwise logs and closes the connection.
  - **Create = sel 0**: scalar in [parent id or 0], struct in = `IOCFSerialize(props, kIOCFSerializeToBinary)` (OSUnserializeBinary format; keys IOSurfaceWidth/Height/BytesPerRow/BytesPerElement/PixelFormat/AllocSize/PlaneInfo/CacheMode/IsGlobal/...), struct out **0xa68 bytes** ("lock result"). **Lookup = sel 4**: scalar in [id], same struct out. LookupFromMachPort = sel 0x22 (scalar in [port name]); CreateMachPort = sel 0x23 (scalar in [id, options], scalar out [port name]).
  - Lock result (copied to client+0x68, size 0x68 + planes*0x80, min 0xe8): 0x00 u64 base address **mapped in the caller's task**; 0x08 u64 task VA of a per-surface shared state page (+0 u64 registry id, +8/+0xa u16 bound accel ids, +0xc u32 seed, +0x14 u8 tiled, +0x20 u32 value generation, +0x24 YCbCr matrix, +0x28 u32 non-bulk values size, +0x2d u8 displayable, +0x2e u8 sysmem-only, +0x30 0x70 bytes bulk attachments); 0x10 u64 task VA of timestamp page (4 u64 indexed timestamps, +0x20 detach code); 0x18 u32 surface id; 0x1c u32 alloc size; 0x20 width; 0x24 height; 0x28 bytes per row; 0x2c buffer offset; 0x30 pixel format; 0x34 u32 (dcache flush length); 0x38 plane count; 0x40 u16 bytes/element; 0x42 u8 element width; 0x43 u8 element height; 0x44 cache mode; 0x4c u8 subsampling; 0x4d u8 prohibit-use count; 0x50 parent id; 0x54 slice count; 0x58 u64 trace id; 0x60 u64 protection options; planes[n] at 0x68+n*0x80 (+0 width, +4 height, +8 bytes/row, +0xc offset, +0x14 size, +0x18 u16 bpe, +0x1a/+0x1b u8 element w/h, +0x1c u8 component count, +0x1d address format, +0x54 u8 compression type (non-zero -> no CPU base address)).
  - **Traps** (IOConnectTrapN -> `IOUserClient::getTargetAndTrapForIndex`): 0 IncrementUseCount(id, category), 1 DecrementUseCount(id, category), 2 **Lock**(id, options, &seed_out), 3 **Unlock**(id, options, &seed_out), 4 Release(id), 5 Release after a failed create/lookup setup (id).
  - Other selectors: 5 SetYCbCrMatrix, 6 WrapClientImage, 7 WrapClientMemory, 9 SetValue (serialized), 0xa UpdateNonBulkValueCache (struct in 9), 0xb RemoveValue, 0xc BindAccel, 0x11 SetSurfaceNotify (async), 0x12 RemoveSurfaceNotify, 0x13 Log, 0x14 SetPurgeable, 0x15 SetOwnership, 0x16 SetTiled, 0x18 SetTimestamp, 0x19 GetTileFormat, 0x1a CopyDataValueBytes, 0x1b SetBulkAttachments (struct 0x88), 0x1e/0x2e-0x31 (via outlined helpers), 0x1f SetCompressedTileDataRegionMemoryUsed, 0x20 GetGraphicsCommPageAddress, 0x21 SetIndexedTimestamp, 0x24-0x26/0x2d IOSurfaceAccelerator, 0x27-0x29 shared events, 0x2a SignalEvent, 0x2b Set/InitDetachModeCode, 0x2c SetOwnershipIdentity, 0x32-0x34 data properties.
  - => SWEET kernel service: class/name **IOCoreSurfaceRoot** + IOSurfaceRootUserClient; minimum = sel 13, 0, 4, 9/0xa/0xb (values), traps 0-5, 0x22/0x23 later for cross-process surfaces (CA sends surfaces to backboardd by mach port). Memory: IOBufferMemoryDescriptor per surface, mapped into each task with createMappingInTask; ids from a global table.

- **Image v8: daemon logs on the console.** `tools/patch-launchd-plist.py IN OUT LABEL...` rewrites launchd.plist (binary, plistlib): renames every `_PanicOnCrash` to `_PanicOnCrasX` and gives the listed jobs `StandardOutPath`/`StandardErrorPath` `/dev/console` (devfs console is 0622, writable by mobile) plus `OS_ACTIVITY_DT_MODE=YES` (os_log mirrored to stderr) and `CFLOG_FORCE_STDERR=1`. v8 = v7 + that plist for com.apple.backboardd and com.apple.SpringBoard, written through the mount (796310 bytes, root:80 0644), SHA256 in `ios16-root-20H392-v8.img.sha256`, `.simg` ready; boot with `shim/out/shim-boot-0045n.img`. Goal: see backboardd's uncaught exception text and the window server's display probing. ODDITY (unresolved): the v5 raw-image rename at offset 0x1e025f000 is present in the v5-v7 image bytes, but the plist read through a Linux mount of v7 still had the original `_PanicOnCrash` keys; filefrag shows the file as one extent. Never patch file contents through raw offsets again; write through the mount.
- **IOMobileFramebuffer.framework reversed (step 1 of the GUI plan).** `ipsw dyld disass research/dsc/dyld_shared_cache_arm64 --image IOMobileFramebuffer`.
  - Display discovery (`IOMobileFramebufferCreateDisplayList` -> `getDisplayListNumber`): iterates children of `IODeviceTree:/arm-io`, counts nodes whose `device_type` is "display-subsystem" or "ext-display-subsystem" (or `compatible` "paravirtualizedgraphics,gpu"); then `iomfb_populate_display_infos` adds an IOServiceAddMatchingNotification(IOServiceFirstMatch, **IOServiceMatching("IOMobileFramebuffer")**) and runs the run loop up to 30 s until that many services matched. `iomfb_match_callback` reads service properties `dfr`, `AppleTV`, `external` (CFBoolean) and names displays (external ones "%s-%d").
  - `IOMobileFramebufferOpen(service, task, type, &fb)`: `__ioMobileFramebufferAlloc` (CFPreferences com.apple.iokit.IOMobileGraphicsFamily: canvas_width/height, override_display_width/height, override_panel_width/height, benchmark, enable_ktrace), `IOServiceOpen(service, task, type)` (GetMainDisplay passes type 0), `getEDTProperty` reads `canvas-width`/`canvas-height` from the service's IODeviceTree parent, then fills a table of `kern_*` function pointers.
  - User client selectors (`kern_*` -> IOConnectCall*): 3 _kern_GetLayerDefaultSurface[ScalarMethod_stub]; 4 _kern_SwapBegin[ScalarMethod_stub]; 5 _kern_SwapEnd[StructMethod_stub]; 6 _kern_SwapWaitWithTimeout[ScalarMethod_stub] _kern_SwapWait[ScalarMethod_stub]; 7 _kern_GetID[ScalarMethod_stub]; 8 _kern_GetDisplaySize[ScalarMethod_stub]; 10 _kern_SetTVOutMode[ScalarMethod_stub]; 11 _kern_SetWSSInfo[ScalarMethod_stub]; 12 _kern_RequestPowerChange[ScalarMethod_stub]; 13 _kern_EnableStatistics[ScalarMethod_stub]; 14 _kern_SetFlags[ScalarMethod_stub]; 15 _kern_SetDebugFlags[ScalarMethod_stub]; 16 _kern_SetTVOutSignalType[ScalarMethod_stub]; 17 _kern_SetGammaTable[StructMethod_stub]; 18 _IOMobileFramebufferIsMainDisplay[ScalarMethod_stub]; 19 _kern_SetWhiteOnBlackMode[ScalarMethod_stub]; 20 _kern_SwapSignal[ScalarMethod_stub]; 22 _kern_SetDisplayDevice[ScalarMethod_stub]; 23 _kern_SetDigitalOutMode[ScalarMethod_stub]; 24 _kern_GetHDCPDownstreamState[StructMethod_stub]; 25 _kern_GetDigitalOutState[ScalarMethod_stub]; 26 _kern_printDisplayRegs[ScalarMethod_stub]; 27 _kern_GetGammaTable[StructMethod_stub]; 28 _kern_GetDotPitch[ScalarMethod_stub]; 29 _kern_GetDisplayArea[StructMethod_stub]; 30 _kern_EnableDisableDithering[ScalarMethod_stub]; 31 _kern_SetUnderrunColor[ScalarMethod_stub]; 33 _kern_EnableDisableVideoPowerSavings[ScalarMethod_stub]; 34 _kern_SetVideoDACGain[ScalarMethod_stub]; 35 _kern_SetLine21Data[ScalarMethod_stub]; 41 _IOMobileFramebufferEnableMirroring[ScalarMethod_stub]; 42 _IOMobileFrameBufferGetMirroringCapability[StructMethod_stub]; 43 _IOMobileFramebufferSetRenderingAngle[StructMethod_stub]; 44 _IOMobileFramebufferSetMirrorContentRegion[StructMethod_stub]; 47 _kern_HDCPSendRequest[ScalarMethod_stub]; 48 _kern_HDCPGetReply[ScalarMethod_stub]; 49 _kern_SurfaceIsReplaceable[ScalarMethod_stub]; 50 _kern_SetBrightnessCorrection[ScalarMethod_stub]; 51 _kern_SetColorRemapMode[ScalarMethod_stub]; 52 _kern_SwapCancel[ScalarMethod_stub]; 53 _IOMobileFramebufferSetCanvasSize[ScalarMethod_stub]; 54 _IOMobileFramebufferGetMatrix[Method_stub]; 55 _IOMobileFramebufferSetMatrix[Method_stub]; 56 _IOMobileFramebufferKernelTests[StructMethod_stub]; 57 _kern_GetColorRemapMode[ScalarMethod_stub]; 66 _kern_SPLCSetBrightness[ScalarMethod_stub]; 67 _kern_SPLCGetBrightness[ScalarMethod_stub]; 68 _kern_SetParameter[Method_stub]; 69 _kern_SwapSetColorMatrix[StructMethod_stub]; 72 _kern_DisableNotifications[ScalarMethod_stub] _kern_EnableNotifications[ScalarMethod_stub]; 73 _kern_ChangeFrameInfo[ScalarMethod_stub]; 74 _kern_SupportedFrameInfo[Method_stub]; 75 _kern_FactoryPortal[StructMethod_stub]; 77 _kern_GetCurrentAbsoluteTime[ScalarMethod_stub]; 78 _kern_SetBlock[Method_stub]; 79 _kern_GetBlock[Method_stub]; 80 _kern_GetLinkQuality[ScalarMethod_stub]; 81 _kern_SwapCancelAll[ScalarMethod_stub]; 82 _kern_GetProtectionOptions[ScalarMethod_stub]; 83 _kern_CopyLayerDisplayedSurface[ScalarMethod_stub]; 84 _kern_SetContrast[StructMethod_stub]; 85 _kern_GetBufBlock[Method_stub]; 86 _IOMFBGainEncoderFinishEncoding[Method_stub]; UNKNOWN {}
  - => Kernel needs: an `/arm-io` child node with device_type "display-subsystem" (+ canvas-width/height) and an IOService of class **IOMobileFramebuffer** (subclass name match) attached under it, opened with type 0, implementing at least GetDisplaySize(8), IsMainDisplay(18), GetID(7), GetLayerDefaultSurface(3), SwapBegin(4)/SwapEnd(5 struct)/SwapWait(6), Enable/DisableNotifications(72), frame info(73/74), CopyLayerDisplayedSurface(83), plus IOSurface for the swapped buffers. NEXT: CoreAnimation's AppleDisplay/IOMFBDisplay usage of these (constructor, first swap, vsync), then IOSurface.framework's IOSurfaceRoot selectors.
- **GUI PLAN (decided 2026-10-16): CPU rendering + kernel IOMobileFramebuffer.** User: CPU rendering is fine for now (goal = prove the GUI runs), may later research an Apple-style GPU driver for the Adreno 618 -> keep display output and renderer separable. QuartzCore findings (symbols from the cache's .symbols subcache: `ipsw dyld symaddr research/dsc/dyld_shared_cache_arm64 --image QuartzCore`; strings: `ipsw dyld macho ... QuartzCore --strings`):
  - Renderers: `sw_new_context` (CA::OGL::SWContext, full CPU renderer incl. blur, images, IOSurface-backed surfaces, make_buffer_current(WindowServer::Surface)), `gles_new_context`, `metal_new_context`, `new_null_context`. Env knobs include CA_ENABLE_OGL, CA_DISPLAY_TYPE, CA_FORCE_LOCAL_SERVER, CA_FORCE_TIMER, CA_CANVAS_WIDTH/HEIGHT, CA_MAIN_DISPLAY_SCALE/ORIENTATION, CA_DISABLE_RENDER, CA_ALWAYS_RENDER (selection logic not traced yet).
  - `-[CAWindowServer _detectDisplays]` (0x1884e3150) iterates static tables `open_funcs`/`count_funcs` = AppleCLCDDisplay, AppleRGBOutDisplay, AppleWirelessDisplay only; each `count()` = `display_count_of_type(IOMFBDisplayType)` over **`IOMobileFramebufferCreateDisplayList()`**, `open(i)` = `create_display_of_type` -> `CA::WindowServer::AppleDisplay(CFString name, ..., IOMFBDisplayType)` (an IOMFBDisplay driven by IOMFBServer: vsync_callback, frame_info_callback, swaps). `CA::WindowServer::VirtualDisplay` exists but is never auto-detected (explicit API only). => the main display MUST come from an IOMobileFramebuffer kernel service.
  - NEXT: reverse IOMobileFramebuffer.framework: IOMobileFramebufferCreateDisplayList / IOMobileFramebufferOpen (service matching, display type property), the user-client selectors used by IOMFBServer (display size/modes, swap begin/set-layer/end with IOSurface ids, vsync notifications), then the IOSurface kernel side (IOSurfaceRoot user client: create/lookup/lock, memory mapping) that both IOMFB swaps and CA surfaces need. Kernel: SWEET IOMobileFramebuffer service that copies the swapped IOSurface to the 1080x2400 framebuffer at 0x9c000000.
- **logd fixed; backboardd = DISPLAY WALL (boot 0045n on v7, 21:08:57 UTC, frames VID_20261016_230850 00:55-01:28, slide 0x4c3ec000, `research/crash-0045n-v7.txt`).** No `CRASH logd` any more; new daemons run (runningboardd, WirelessRadioManagerd, networkserviceproxy, dasd, cloudpaird, magicswitchd, atc, askpermissiond, ManagedSettingsAgent, containermanagerd uses AKS 0/17). New: locationd sig 11 at CFRunLoopAddSource+132 (NULL source) from its main+0x2af138 in a dispatch_once. **backboardd** sig 6: abort <- std::terminate <- _objc_terminate <- dispatch_once <- main+0x9334 = the "start %{public}@..." wrapper (0x100009264) for **"window server"** (block 0x10000a770 -> dispatch_once body 0x10001d7f0 = StartWindowServer): MTLSetShaderCachePath, `[CAWindowServer serverWithOptions:@{kCAWindowServerDisableUpdatesOnMainDisplay: @YES}]`, `setRendererFlags:`, **`mainDisplay`** -> `displayId` -> `[CADisplay displayWithDisplayId:]`, setWindowServerDisplay:, bounds, pointScale, currentMode, preferredScale, nativeOrientation, touchScales... With no display, mainDisplay is nil and it throws. (HID system and GS start fine before it.) SpringBoard dies on the same missing display (FBSDisplayMonitor). QuartzCore display backends (from the cache's .symbols subcache, `ipsw dyld str`): `CA::WindowServer::AppleCLCDDisplay` (IOMobileFramebuffer hardware) and **`CA::WindowServer::VirtualDisplay`** (open(), new_server, clone_update). `CA_DISPLAY_TYPE` and `CA_FORCE_LOCAL_SERVER` strings exist in QuartzCore but have no direct xref (likely read via a table of CA_* env names). NEXT: find how CA::WindowServer::Server enumerates displays (IOMobileFramebuffer services vs VirtualDisplay / CA_DISPLAY_TYPE) and choose: (a) kernel IOMobileFramebuffer service + IOSurface, or (b) a VirtualDisplay rendered by CA's CPU path (CA::OGL::SW) and copied to the framebuffer.
- **watchdogd + CommCenter + identityservicesd fixed (boot 0045n on v6, 20:41:30 UTC, frames VID_20261016_224133 00:39-01:13, slide 0x20fec000).** `SWEET WDT: watchdogd sel 0 in 0/0 out 1/0 -> ok`, no watchdogd/CommCenter/identityservicesd crashes (CommCenter/identityservicesd now call AKS 0/17/7). usermanagerd boot task runs (UMD_INIT creates primary session uid 501 "mobile", personas 99 System and 199 Default registered with the kernel); `Failed to atomically swap writing file /private/var//keybags/usersession.kb: Operation not supported (45)` (HFS lacks the atomic swap rename; non-fatal so far). Remaining: SpringBoard (FBSDisplayMonitor, no display), backboardd (uncaught exception), mediaserverd, lockdownd (crash inside obfuscated code, main+0x4c1b4?), logd. **logd**: main+0x18160 = `BUG IN LIBTRACE: Failed to migrate directory` from 0x10001801c(dir 0): 0x100016538 requires the dir to exist with uid/gid/mode from the table at 0x10002df14 (0: /private/var/db/diagnostics 272:272 0751, 1: /private/var/db/uuidtext 272:272 0755, 2: /private/var/db/diagnostics/timesync 272:272 0755) plus a `.migrated` file, else XPC "operation 6" to a helper and crash. **Image v7** = v6 + those dirs/markers (also in mkiosroot.sh), SHA256 in `ios16-root-20H392-v7.img.sha256`, `.simg` ready. Boot with `shim/out/shim-boot-0045n.img`.
- **Exit-reason text works (boot 0044n, frames VID_20261016_221726 00:32-00:53, slide 0x22d5c000).** CommCenter/identityservicesd: `couldn't dlopen libobjc-trampolines.dylib: dlopen(/usr/lib/libobjc-trampolines.dylib, 0x0106): tried: '/usr/lib/libobjc-trampolines.dylib' (no such file, not in dyld cache)`: the file only exists in the OS cryptex and dyld does not search cryptexes at ignition_level=1. 19 cryptex files have no root counterpart (OS: DriverKit dyld cache + .symbols, VisualTestKit, libffi-trampolines, libobjc-trampolines, libstdc++ 6.0.9 + 2 symlinks; App: SafariSupport.bundle, AuthenticationServicesAgent, com.apple.Safari.History, passwordbreachd, safarifetcherd, webbookmarksd, webinspectord, webpushd) -> hard-linked (symlinks copied: Linux hfsplus cannot hard-link symlinks); `tools/mkiosroot.sh` does it generically. watchdogd still crashed: the `-wdt_no_pmu` / `/arm-io/wdt no-pmu` check (0x10000a01c) only runs when os_variant_has_internal_diagnostics; otherwise 0x100009b18 looks up IOServiceMatching("IOService") + IOPropertyMatch {IOPMUPrimary: 1} (NSConstantDictionary) and crashes if absent, then IORegistryEntrySetCFProperty(boot stage 0xff) (failure only logged). Patch **0045**: IOWatchdog sets IOPMUPrimary = 1 and accepts setProperties; CI `38961814194` -> `xnu/out-0045`. **Image v6** = v5 + the 19 cryptex links, SHA256 7c610c6a...297a, `ios16-root-20H392-v6.simg` (full flash needed). Boot image `shim/out/shim-boot-0045n.img` (0045 + sweet-0044hi.adt). Still open: SpringBoard (no display), backboardd (uncaught exception, reason none), mediaserverd (Fig NULL dict), logd (main+0x18160), lockdownd (main+0x4c1b4).
- **System survives daemon crashes (boot 0043p, video frames VID_20261016_215006 00:25/00:42/00:54).** With the v5 plist patch no panic: launchd keeps launching (runningboardd, powerd, tccd, healthd, peopled, cryptexd, routined, aksd, mediaremoted, familynotificationd, nanoprefsyncd, navd, cloudpaird, passd, amsaccountsd, accessoryupdaterd, wcd ...). Shared cache slide that boot 0x406b4000 (`research/crash-0043p.txt`). watchdogd still crashed at main+0xb82c from the PMU step: `-wdt_no_pmu` is only honored when os_variant_has_internal_diagnostics; customer builds read `no-pmu` from IODeviceTree:/arm-io/wdt (IORegistryEntrySearchCFProperty) -> mkadt adds /arm-io/wdt {no-pmu}. **cryptexd** sig 6: abort_with_payload <- os_crash_fmt <- `__darwin_arm_secure_boot_chip.cold.7` ("panic: failed to get crypto algorithm") <- `_img4_chip_select_personalized_ap`: reads /chosen use-ddi-secure-boot, allow-ecid-mismatch, crypto-hash-method ("sha1" | "sha2-384"), /chosen/asmb lp-smb0/1 -> mkadt adds crypto-hash-method "sha2-384". **identityservicesd** sig 6 = same `_objc_fatal` in imp_implementationWithBlock as CommCenter (block trampolines; message needed). lockdownd sig 5 at main+0x4c1b4. Patch **0044**: crash report adds `CRASH name reason ns N code X: text` (exit reason description = abort_with_payload text). CI `38959096811` -> `xnu/out-0044`, QEMU OK. Image `shim/out/shim-boot-0044n.img` = 0044 + `shim/out/sweet-0044hi.adt` (wdt no-pmu, crypto-hash-method) + cmdline (wdt=-1, no -wdt_no_pmu).
- **First symbolicated daemon crashes (boot 0043u on journaled v4, 19:38:53 UTC; video frame chat image 36; transcribed in `research/crash-0043u.txt`; shared cache slide 0x40d60000 for every process).** (Gemini's video transcription invented values, use frames only.) `tools/sweet-crash.py research/dsc/dyld_shared_cache_arm64 x research/crash-0043u.txt`:
  - **watchdogd** pc main+0xb82c (`_os_crash` trap helper) from 0x100009bb0 = set PMU boot stage via IORegistry (no PMU) -> fix: boot-args `wdt=-1 -wdt_no_pmu` (Apple's own test mode writes "%s wdt=-1 -wdt_no_pmu"; watchdogd logs "skipping setting PMU boot stage because -wdt_no_pmu found in boot-args or no-pmu found in EDT"). Kernel effect of wdt=-1: sched hygiene debug off, zone_exhausted_timeout -1 (harmless).
  - **SpringBoard** sig 5 in `-[FBSDisplayMonitor _initWithBookendObserver:transformer:]+1160` <- `+[FBDisplayManager sharedInstance]` <- `FBSystemShellInitialize` <- `SBSystemAppMain`: no main display. GUI WALL: display service (IOMobileFramebuffer / CoreAnimation display).
  - **backboardd** sig 6: abort <- std::terminate <- _objc_terminate (uncaught exception; message not shown).
  - **CommCenter** sig 6: `_objc_fatal` in `imp_implementationWithBlock` (from `+[_PFRoutines initialize]`, CoreData): objc block trampolines cannot be allocated -> likely kernel gap (trampoline page remap); will hit many processes.
  - **mediaserverd** sig 11: CFDictionaryGetValue(NULL) in FigNotificationListenerStartNotifications (routing session manager).
  - **logd** sig 5 at its main+0x18160 (bt main+0x9dfc); lockdownd sig 5 (not yet symbolicated).
  - Image v5 = v4 + launchd.plist (`/System/Library/xpc/launchd.plist`, contiguous at image offset 0x1e025f000, 1456980 bytes) with the 7 `_PanicOnCrash` keys renamed `_PanicOnCrasX` in place (raw image patch, no metadata change) -> `diff-v4-v5.simg` = 7 blocks; v5 SHA256 78f96974...185a. Boot image `shim/out/shim-boot-0043p.img` = 0043 + `wdt=-1 -wdt_no_pmu`.
- **0043 console crash reports (QEMU verified); image `shim/out/shim-boot-0043u.img`; NEXT: flash v4 + boot 0043u.** Boot 0042u (video photo IMG_20261016_211646): short exec lines work; watchdogd crashes with NO `SWEET WDT:` line (fails before its first IOWatchdog call: lookup or IOServiceOpen, or elsewhere); lockdownd, SpringBoard, mediaserverd, CommCenter, identityservicesd, backboardd, watchdogd all crash repeatedly ("Too many corpses being created" = corpse limit, no crash reports). AKS callers: lockdownd (0, 7), imagent/sleepd (0, 17, 7), backboardd (0, 17), UserEventAgent (0, 7, 102, 103 -> unsupported). Patch **0043**: `sweet_crash_log` (osfmk/kern/exception.c, called from proc_prepareexit for crash exits on the current proc) prints `CRASH name[pid] sig S code (exc<<32|code) sub X slide SR mh MH`, `CRASH name pc lr sp fp far`, `CRASH name bt` (10 fp frames); AKS sel 103 notify_state_is_set -> 0. CI `38954520419` -> `xnu/out-0043`. QEMU test: init forks, child `brk #1`: `CRASH launchd[2] sig 5 code 0x600000001 sub 0x1000004f0 slide 0x0`, pc correct, parent keeps running (pid 1 crashes panic before proc_prepareexit, so test with a child). `tools/sweet-crash.py CACHE ROOT [report]` symbolicates typed-in CRASH lines (`ipsw dyld a2s` with addr - slide; main binary offsets = addr - mh + 0x100000000).
- **v3 reflashed 18:50-18:55 UTC (`research/flash-userdata-v3b.log`, 24/24 OKAY); 0042u booted 19:01:17 UTC on the clean disk (`research/boot0042u-2.log`), SLOW MO VID pending (watchdogd failure reason).** ABL hangs on the first `fastboot boot` after every big flash; user re-enters fastboot. User gave standing approval to reflash/boot without asking (memory standing-flash-approval). Commits now end with `Co-Authored-By: dipa-studio <183933817+dipa-studio@users.noreply.github.com>` (user request; never a Claude trailer).
  - watchdogd flow: connect_to_kext (0x100005408): IOServiceGetMatchingService("IOWatchdog") fails -> "failed to discover" + _os_crash; IOServiceOpen(type 1) fails -> "IOServiceOpen failed with error : 0x%x" + _os_crash. Then sel 0 (out 1 scalar): 0 -> "userspace monitoring disabled", 0x100009bb0, sleep 2, exit(0); nonzero -> "userspace monitoring enabled", normal operation.
  - **Image v4 (JOURNALED):** `tools/mkiosroot.sh` now does `mkfs.hfsplus -J`, mounts with `-o loop,force`, adds the /System/Library/Caches/com.apple.dyld hard links (44) and /private/var/keybags/systembag.kb (0700/0600 root). Built from the IPSW dmgs (OS 087-86698-044, SystemOS 087-86593-047, AppOS 087-86715-047) -> `/run/media/dipa/android/ios-sweet-ipsw/ios16-root-20H392-v4.img` SHA256 fba4aeae...ec0f9 + `.simg`. Header: attr 0x80002100 (unmounted, journaled), journal info block 129, journal 8 MiB at 532480 flagged need-init. Linux `fsck.hfsplus -n` reports "Volume header needs minor repair" on any fresh journaled volume even after -y (quirk). QEMU: 64 MB journaled test root (`rd=md0 rootrw=1`, 0042 kernel): `hfs: Initializing the journal (joffset 0x3000 sz 0x80000)` -> mounted -> init runs, no panic. NEXT: flash v4 (full), boot 0042u.
- **SPRINGBOARD STARTS (boot 0041u 18:39:53 UTC, photo IMG_20261016_204142).** backboardd, bluetoothd, fairplayd.H2, SpringBoard (pid 111, crashed: "Too many corpses"), xpcproxy run; `SWEET AKS: backboardd sel 0 -> 0`, `sel 17 in 1/0 out 0/4096 -> 0`. Panic: watchdogd[113] exited, namespace 2 subcode 5 (SIGTRAP = its _os_crash): watchdogd crashes on purpose when IOServiceGetMatchingService("IOWatchdog") fails ("connect_to_kext() unexpectedly failed") or IOServiceOpen(type 1) fails ("IOServiceOpen failed with error"); IOWatchdog DOES register (QEMU msgbuf: `SWEET WDT: IOWatchdog registered`), cause not on screen yet -> need video. Note `wdt_test=no_user_checkin` makes watchdogd log "detected testing boot-args to not run, exiting" (path not reached here?). **HFS CORRUPTION:** `hfs_swap_BTNode: offset #0 invalid (0xBC1D) (blockSize 0x2000 numRecords 81)`, `node=19677 fileID=4` (catalog), `hfs_mark_inconsistent` repeated. Likely cause: non-journaled HFS + unclean panics while writing (0038e wrote a 2.7 GB core then panicked; every boot since ends in panic). Plan: reflash v3 (clean), longer term HFS journaling. Patch **0042**: one short `exec NAME` console line instead of the 3-line "Allowing spawn of iOS binary" notice; CI `38949451276` -> `xnu/out-0042`; image `shim/out/shim-boot-0042u.img` (same cmdline as 0041u).
- **LAUNCHD DAEMONS RUN (boot 0039u, 18:29:13 UTC, photo IMG_20261016_203052).** With `launchd_unsecure_cache=1` all boot tasks pass and launchd starts LaunchDaemons (pids > 100: identityservicesd 114 and lockdownd 106 crash, "Too many corpses being created"). Fatal: `watchdogd: ERROR: failed to discover watchdog KEXT service` -> exit (namespace 2 = signal, subcode 5) -> `_PanicOnCrash` panic. watchdogd: IOServiceMatching("IOWatchdog"), IOServiceOpen type 1, IOConnectCallScalarMethod sel 0/1 (check in)/3/4 (disable/enable userspace monitoring)/5, IOConnectCallStructMethod sel 2 (1 KiB in) and 9 (small out); VM path ("detected virtual machine environment and no watchdog KEXT found, exiting...") only when it detects a VM. Console also flooded with `hfs: set hardlink bit on vol=iOSRoot cnid=321318` (Linux-made hard links lack kHFSHasLinkChainBit; repaired only in memory on each lookup). Patches **0040** (`iokit/Kernel/arm/SweetWatchdog.cpp`: IOWatchdog + IOWatchdogUserClient, all selectors succeed with zeroed outputs, each logged once as `SWEET WDT: ...`) and **0041** (sweet_hfs hfs_catalog.c: the three link-repair printfs limited to 8 per boot); CI `38948245372` PASSED -> `xnu/out-0041` (QEMU regression OK). Image `shim/out/shim-boot-0041u.img` (0041 + sweet-0038hi.adt + ufsrw rootrw + launchd_unsecure_cache=1) booted 18:39:53 UTC (`research/boot0041u.log`), photo pending.
- **v3 FLASHED + keybag passes; next wall AMFI (launchd_cache_loader).** User said "flash, nothing to lose": `fastboot -S 512M flash userdata ios16-root-20H392-v3.simg` 17:51:52-17:57:01 UTC, 24/24 chunks OKAY (`research/flash-userdata-v3.log`). userdata = v3 (SHA256 fa84274c...22df) until the next rw boot. ABL fastboot then hung ("Sending" forever, `reboot bootloader` timed out) until the user re-entered fastboot by hand (common Xiaomi ABL crash). Boot 0038e 18:06:15 UTC (`research/boot0038e-3.log`), photos IMG_20261016_200812/200838: keybag OK, then boot tasks tzinit (`Bad zoneinfo link`, resets to system partition, OK), finish-restore, finish-demo-restore, sysstatuscheck, prng_seedctl (`failed to load kernel prng seed`, `failed to load virtual random (-147)`, AllowCrash), auearlyboot, then **launchd_cache_loader: `abort: Unable to find AMFI`** -> 2.7 GB core written to /cores in 91 s -> launchd panic `launchd_cache_loader[22] exited -- exit reason namespace 7 subcode 0x1`. launchd_cache_loader: SecStaticCodeCheckValidity of /System/Library/xpc/launchd.plist with detached .sig, then IOServiceMatching("AppleMobileFileIntegrity") + IOServiceOpen type 0 + IOConnectCallMethod sel 6 (1 scalar = 1, struct in = cdhash) = trust the cdhash, then sends the cache to launchd. Boot-arg `launchd_unsecure_cache=1` skips signature + AMFI ("Using unsecure cache"); the value is parsed with strtoul base 10 (helper 0x100002da8), so a path = 0 = off: boot 0039w (18:17:13 UTC, `=/System/Library/xpc/launchd.plist`, photo IMG_20261016_202008) still aborted `Unable to find AMFI` (core dump now skipped: `Failed to generate core file ... error 14`, so 0039 works). Image `shim/out/shim-boot-0039u.img` uses `launchd_unsecure_cache=1`. Patch **0039**: do_coredump = 0 on SWEET (kern.coredump sysctl still works); CI `38945267341` -> `xnu/out-0039` (_do_coredump now in __common). Image `shim/out/shim-boot-0039w.img` = 0039 + sweet-0038hi.adt + ufsrw rootrw + `launchd_unsecure_cache=/System/Library/xpc/launchd.plist`. TODO later: real AppleMobileFileIntegrity IOService (sel 6 trust cdhash etc.).
- **Image v3 ready, awaiting user "flash".** Boot 0038w 17:38:10 UTC, photo (chat image 30): `SWEET AKS: keybagd sel 0 -> 0x0`, `sel 14 out 1/0 -> 0x0` (x2), `MKB_INIT: mount is with NO CPROTECT ... does not support Data Protection`, `System Keybag loaded`; then keybagd still opens /private/var/keybags/systembag.kb (0x100012d3c, for BackupKeyBagKeys) -> ENOENT, `no-effaceable-storage` not set -> `Can't load the keybag. tears in rain... Time to die` -> `FATAL KEYBAG ERROR: kb_load` -> reboot -> Halt/Restart Timed Out panic. Fix: ADT `/defaults/no-effaceable-storage` (mkadt.py; `shim/out/sweet-0038hi.adt`, `research/q0038-hi.adt`, QEMU OK) + file `/private/var/keybags/systembag.kb` (0600 root, dir 0700; XML plist {KeyBagKeys: data}). **v3 image** `/run/media/dipa/android/ios-sweet-ipsw/ios16-root-20H392-v3.img` = v2 + that file, fsck OK, SHA256 fa84274c...22df; `ios16-root-20H392-v3.simg` (img2simg: zero blocks become FILL chunks, so a full flash overwrites every block the rw boots changed). Flash: `fastboot -S 512M flash userdata ios16-root-20H392-v3.simg`, then boot `shim/out/shim-boot-0038e.img` (0038 + sweet-0038hi.adt + ufsrw=1 rootrw=1).
- **0038 AppleKeyStore (CI 38938744130 PASSED -> `xnu/out-0038`; QEMU msgbuf: `SWEET AKS: AppleKeyStore registered (no passcode, unlocked)`; phone image `shim/out/shim-boot-0038w.img` booted 17:38:10 UTC, `research/boot0038w.log`, photo pending).** QEMU full kernel log trick (fb.txt is only the last screen): `llvm-nm KERNEL | grep _msgbufp` -> `--hmp "x /1gx ADDR"` gives struct msgbuf address (static, 0xfffffe0007b56678 on 0038) -> `--hmp "x /3gx STRUCT"` gives bufc (3rd quad) -> `--hmp "memsave BUFC 0x20000 \"FILE\""` (quote the file name), `tr -d "\0" < FILE`. Same inputs give the same addresses. Boot 0037w 17:08:35 UTC, photo IMG_20261016_191052: bindfs fixed mount; mount-phase-1/2 pass; `cc_fips_test` boot task: all corecrypto FIPS POST tests PASSED in userspace; then keybag boot task `keybagd --init`: `MKB_INIT: FATAL KEYBAG ERROR: failed to load system bag`, `Could not get options entry from the device tree` (x2, IODeviceTree:/options = NVRAM, non-fatal), `REBOOTING INTO RECOVERY MODE` -> reboot -> panic `Halt/Restart Timed Out @IOPlatformExpert.cpp:884` (no restart path on SWEET).
  - keybagd (static libaks): load_devicebag (0x100012c30) calls aks_get_system (sel 14, 0-1 scalar in, 1 out) and loads /private/var/keybags/systembag.kb only if the result is 0xe00002f0 (NotFound); any other error -> fatal; SUCCESS -> skip the file (userspace-reboot path). systembag.kb is a plist {KeyBagKeys}; decrypted with effaceable storage unless IODeviceTree:/defaults has `no-effaceable-storage`. Image has no /private/var/keybags. has_data_protection: statfs of /private/var; no cprotect on our HFS -> device-bag volume mapping skipped.
  - libaks connection: IORegistryEntryFromPath / IOServiceMatching("AppleKeyStore"), IOServiceOpen type 0, then selector 0 (no args) must succeed.
  - **AppleKeyStore selector map (iOS 16.7 AppleKeyStore.framework, via `ipsw dyld disass`):** 0 open, 2 create_bag, 3 save_bag, 4 unload_bag, 5 set_system_with_passcode, 6 load_bag, 7 get_lock_state (1 in, 1 out; bit 2 = unlocked since boot), 9 unlock_device, 10 wrap_key, 11 unwrap_key, 12 unlock_bag/test_stashed_kek, 13 lock_bag, 14 get_system, 15 change_secret_se, 16 internal_state, 17 get_device_state (1 in, struct out <=4K: DER SET of SEQUENCE{UTF8 key, INTEGER}: ss state, sls lock_state (MKBGetDeviceLockState returns it), sb backoff, sbo, sfa failed attempts, sfao, sgs generation, sas assertions, sgpe grace, srcd countdown, sr reserved), 18 recover_with_escrow_bag, 19 obliterate_class_d, 20 drain_backup_keys, 21/22 set/clear_backup_bag, 23 get_bag_uuid, 24 rewrap_key_for_backup, 26/27 assert_hold/drop, 30/31 set/get_configuration, 33-37 stash, 38 auth_token_create, 40 generation, 41 fdr_hmac_data, 42 verify_password, 43 _aks_operation, 44 remote_session, 49/50 signing keys, 51/53/54 stash enable/persist/escrow, 55 unload_session_bags, 57/58 remote peer, 59-62 smartcard, 63 migrate_s_key, 65 set_keybag_for_volume_with_cookie_persona, 66/67 sync bags, 68 copy_volume_cookie_persona, 69-73 se_*, 74-79/84/85/99 fv_* (FileVault/VEK), 80/81 absinthe, 82 make_public_backup_bag, 83 drop_auxiliary_auth, 86 kext get/set options, 87 invalidate_bag, 88-91/94/95/106/107 se_*, 92 lower_iteration_count, 93 get_internal_info, 96-98/117 keybag_persona create/list/delete, 100/101 assert promote/consume, 102/103 notify_state set/is_set, 104 fairplay, 105 change_secret_epilogue, 108 delete_xart_leak, 110-113 backup volume, 114 sealed_hashes_set, 115 prewarm_sps, 118-128 AKSIdentity*/AKSGetLastUser.
  - Patch **0038**: `iokit/Kernel/arm/SweetKeyStore.cpp` (class AppleKeyStore on IOResources, IOUserClientClass AppleKeyStoreUserClient; personality in KernelConfigTables.cpp): 0/4/5/9/12/13/26/27/55/102 success, 14 -> handle 0, 7 -> 0x4, 17 -> DER state (ss 4, sls 0), others kIOReturnUnsupported; logs `SWEET AKS: <proc> sel N arg0 in a/b out c/d -> ret` for every call.
  - Tools: shared cache copied to `research/dsc/` (git-ignored; ipsw needs a writable dir for its .a2s symbol cache); `ipsw dyld disass research/dsc/dyld_shared_cache_arm64 --image AppleKeyStore|MobileKeyBag`; scratchpad `annot2.py BIN DIS FIXUPS` annotates llvm-objdump output with strings and import names (`ipsw macho info --fixups`).
- **0037 bindfs (phone boot 0037w pending photo).** Boot 0036mw 16:57:47 UTC, photo IMG_20261016_190102: WRITABLE ROOT WORKS: `/dev/ufsroot0 on / (hfs, local, noatime)` after mount_hfs update (GetMasterBlock EBUSY harmless), coredump of mount written to /cores (rw). Then `mount: failed to mount /private/preboot/5CBE3601.../usr/standalone/firmware -> ...: Operation not supported by device (19)` -> exit 74 -> launchd panic `mount[2] exited`. Cause: the macOS-derived config had nullfs but no bindfs (ENODEV = unknown fs type). Caller passes env 0 -> bind not required, ENOENT (missing source dir) tolerated. Patch **0037** adds `bindfs` to FILESYS_BASE in MASTER.arm64.sweet; CI `38936550483` -> `xnu/out-0037` (bindfs_vfsops present; QEMU probe regression OK). Image `shim/out/shim-boot-0037w.img` (0037 + sweet-0036hi.adt + ufsrw=1 rootrw=1) booted 17:08:35 UTC (`research/boot0037w.log`). NOTE: userdata has now been modified by rw boots; it no longer equals the v2 image, so sparsediff with v2 as OLD is not safe any more (full reflash or a new baseline needed).
- **0036 phone: launchd boot tasks run; mount -P 1 needs /chosen/boot-manifest-hash.** Boot 0036hr 16:15:32 UTC, photo IMG_20261016_185236: platform check passes; fsck boot task runs (`fsck: not booting main or diagnostic OS. Skipping fsck on OS container`); mount-phase-1: `failed to get filesystem info` x2 (no IODeviceTree:/filesystems/fstab, non-fatal), `mount: data volume missing, but not required in env: 0`, mount_hfs update of /: `GetMasterBlock: Error 16 opening /dev/ufsroot0` (EBUSY, mounted block dev, non-fatal) then mount() EROFS (read-only boot) -> `mount: / failed with 1`; then `failed to get boot-manifest-hash` -> errx exit 66 -> launchd panic `mount[3] exited`. /sbin/mount: fn 0x100005f90 reads IODeviceTree:/chosen boot-manifest-hash (hex), bindfs-mounts /private/preboot/<HEX>/usr/standalone/firmware (ENOENT tolerated unless required). `tools/mkadt.py` now adds `boot-manifest-hash` = SHA-384("sweet boot manifest") (5CBE3601...5205). ADTs `shim/out/sweet-0036hi.adt`, `research/q0036-hi.adt` (QEMU probe OK, csops 0x26000001). Image `shim/out/shim-boot-0036mw.img` (0036 + new ADT + ufsrw=1 rootrw=1), booted 16:57:47 UTC (`research/boot0036mw.log`): FIRST WRITABLE BOOT of userdata (restore source: v2 image on SSD).
- **0036 CS_SIGNED (phone boot 0036hr pending photo).** Phone boot 0035hr 2026-10-16 15:57:02 UTC (`research/boot0035hr.log`, photo IMG_20261016_180249): highmem works on hardware; shared cache maps (trust-cache warnings only), Apple launchd runs (`Darwin Bootstrapper Version 7.0.0`, `entering ondemand mode`), starts boot task fsck, then userspace panic `boot task is not a platform binary (fsck, /sbin/fsck)`. launchd+0x3fea0: `csops(pid, CS_OPS_STATUS)` must have bit 0x04000000. Cause: nothing set CS_SIGNED (AMFI does it in vnode_check_signature), so csproc_get_blob() returns NULL for every process and csops never reports CS_PLATFORM_BINARY (also breaks per-process cdhash/entitlement queries). QEMU probe init (`csops` status printer, scratchpad csq/) on 0035: `0x02000001`; patch **0036** (`*cs_flags |= CS_SIGNED` in the SWEET AMFI hook), CI `38929635791` -> `xnu/out-0036`: `0x26000001`. Images `shim/out/shim-boot-0036hr.img` / `-0036hw.img` (same cmdlines as 0035). 0036hr booted 16:15:32 UTC (`research/boot0036hr.log`). Next launchd boot tasks (embedded __config plist): fsck -qL and mount -P 1/2 (RequireSuccess); no /etc/fstab on the image.
- **0035 ENTITLEMENTS + PLATFORM BINARIES (QEMU verified).** `xnu/patches/0035-sweet-amfi-entitlements-platform-binaries.patch`: new `iokit/Kernel/arm/SweetEntitlements.cpp` (OSObject subclass: OSDictionary from OSUnserializeXML of the signature's XML entitlements + original XML for CS_OPS_ENTITLEMENTS_BLOB); `bsd/kern/sweet_amfi.c` answers queryEntitlementBoolean/String(+WithProc, string also matches array members), copyEntitlementAsOSObject(+WithProc, retained), asdict (retained), get_xml (kalloc_data copy); built-in MAC policy "SWEET AMFI" (registered from bsd_init before vfs/exec) with mpo_vnode_check_signature: every signed binary on the MNT_ROOTFS mount gets CS_PLATFORM_BINARY (stand-in for AMFI's static trust cache: iOS system binaries are ad-hoc, cd_flags 0x2, platform byte 0), and attaches entitlements ONLY for the writable copy (cs_blob != csb_ro_addr; revalidation passes the RO blob). LESSON: first version attached in adjustContextWithoutMonitor -> QEMU `unable to adjust OSEntitlements context without monitor: 53` because ubc_cs_convert_to_multilevel_hash (4K-page signatures on 16K kernel) sets csb_entitlements_blob = NULL; ALL iOS 16 binaries (launchd, backboardd, SpringBoard) use 4K code pages, so this would have broken launchd on the phone. Boot-arg `sweet_amfi_debug=1` logs `SWEET AMFI: <ident>: N entitlements (test: ...)`. `tools/mkinit.py OBJ OUT [ENTS.plist]` adds an XML entitlements blob (special slot -5; default output byte-identical). QEMU `research/q0035-ent` (RAM disk `research/root-hfs-ent.img`, init with 3 test entitlements, highmem): `org.sweet.init: 3 entitlements (test: bool 1 string 1 array 1)` then init PID 1. MAC policies loaded: 0034 = 1, 0035 = 2 (QMP `mac_policy_list`). CI `38909807230` -> `xnu/out-0035`. Phone images: `shim/out/shim-boot-0035hr.img` (highmem, ro), `-0035hw.img` (highmem, +ufsrw=1 rootrw=1), `-0035r.img` (low mem fallback).
- **PHONE TEST ORDER (updated):** 0035hr -> if instant reset, 0035r -> then 0035hw.

- **HIGHMEM: XNU in the upper DDR bank, ~3.95 GiB (was 1.2 GiB).** Live FDT memory = <0x80000000 2G> + <0x1_00000000 0xfcc00000>; all fixed reserved-memory carve-outs are in the low bank (highest: ramdump_fb 0xaf000000, rmtfs ~0xfde01000), dynamic pools have alloc-ranges <= 0xffffffff, UFS node has no `iommus` (Linux DMAs anywhere). `tools/mkadt.py --highmem` sets /chosen dram-base 0x100000000 dram-size 0xfcc00000; `tools/mkpayload.py` now takes phys_base/mem_size from the ADT (default payloads byte-identical, verified); `tools/qemu-sweet.py` sizes -m from the payload (8G for highmem). Patch **0034** (`0034-sweet-ufs-dma-above-4g.patch`): UFS refuses DMA memory above 4G without UFSHCI CAP.64AS (bit 24), logs `DMA at 0x...`. CI `38905889883` success -> `xnu/out-0034`. **QEMU verified** (`research/q0034-hi`, ADT `research/q0034-hi.adt` --qemu --highmem, HFS RAM disk): phys_base 0x100000000, init PID 1 heartbeat, no panic; `max_mem` = `mem_size` = 0xfcc00000 read via QMP (`research/q0034-hi-mem`). Phone images: `shim/out/shim-boot-0034hr.img` (read-only) / `-0034hw.img` (+ufsrw=1 rootrw=1), ADT `shim/out/sweet-0034hi.adt` (asmb SIP + sweet-ufs + highmem). PHONE RISK: unknown runtime TZ/XPU protection in the upper bank would show as an instant reset; fall back to 0033r/w. Watchdog ruled out for the overnight reset: msm-watchdog bark is 20 s (qcom,bark-time 0x4e20) yet panic screens stay up for many minutes.

- **Offline research 2026-10-16 (user away, phone unavailable). Images rebuilt** `shim/out/shim-boot-0033r.img` / `-0033w.img` now also carry `wdt_test=no_user_checkin`. NEXT ON PHONE: boot 0033r (expect past in6_nigroup), then 0033w (first writes: rw root fixes HFS link-chain bits itself and gives /var for launchd sockets /var/run/syslog, /var/run/lockdown.sock).
- **launchd.plist** (`/System/Library/xpc/launchd.plist`, compiled; 532 daemons, 66 RunAtLoad/KeepAlive, list in scratchpad `early-daemons.txt`). `_PanicOnCrash` daemons: containermanagerd/usermanagerd (InternalOnly), lockdownd/remoted/trustd/remotepairingdeviced (AutomationOnly), **watchdogd unconditional** (KeepAlive SuccessfulExit=false). watchdogd needs IOKit `IOWatchdog` kext service; if absent it exits only when `kern.hv_vmm_present` (ADT `/defaults/vmm-present`, hvg_sysctl.c) or with boot-arg `wdt_test=no_user_checkin` ("detected testing boot-args to not run, exiting"; reads kern.bootargs). Using the boot-arg (vmm-present would change many daemons; keep as an option).
- **GUI path research (QuartzCore in the shared cache, `ipsw dyld str CACHE STR`, ~10 s/search):** CA::WindowServer has IOMFBServer/IOMFBDisplay (Apple DCP/IOMobileFramebuffer), AppleCLCDDisplay, AppleRGBOutDisplay, **VirtualServer/VirtualDisplay** and **MemorySurface**, EAGLServer. Renderers: CA::OGL::MetalContext, GLContext and a **CPU software rasterizer CA::OGL::SW** (samplers/blend modes; "image is too large for software renderer"). Env knobs: `CA_ENABLE_OGL`, `CA_DISPLAY_TYPE`, `CA_FORCE_LOCAL_SERVER` (249 CA_* vars). Hypothesis (unverified): backboardd's render server could run a VirtualServer/MemorySurface with the SW renderer and we copy the surface to the ABL framebuffer -> needs disassembly of CA::WindowServer server creation. Expected other GUI walls: IOSurface (closed-source kext; needs a reimplementation), IOMobileFramebuffer user client, IOHID touch events, AppleKeyStore/keybag (SEP) for lock state, MobileGestalt answers (AppleCLCD etc.).

- **0032r RESULT (boot 05:07:50 UTC, `research/boot0032r.log`, photo IMG_20261016_071200): SHARED CACHE MAPPED, LAUNCHD RUNS.** With SIP relaxed (ADT asmb) the `not in trust cache` lines are only warnings for every subcache (.31 ... .42.dyldlinkedit); no SIP rejection; libSystem loads; launchd configures networking (`skip attaching fsw to lo0 using legacy TX model`) -> kernel data abort far 0x28 in `SHA1Init` (symbolized as sha1_init) from `in6_nigroup` (IPv6 on lo0): g_crypto_funcs NULL. Kernel addresses are unslid: `~/swift/usr/bin/llvm-symbolizer --obj=KERNEL ADDR` works directly.
- **0032** BearSSL SHA-1 (`0032-sweet-bearssl-sha1.patch`), **0033** BearSSL SHA-384/512 (`0033-sweet-bearssl-sha384-sha512.patch`, BearSSL ctx stored in SHA512_CTX, static-asserted to fit; ubc_subr.c uses SHA-384 for code directories). `0020-stage-bearssl.sh` now also stages hash/sha1.c, hash/sha2big.c, codec/{dec,enc}{32,64}be.c. CI `38854909053` success (0032-only run `38854802073` superseded). Kernel `xnu/out-0033` (SHA1Init -> _br_sha1_init verified by disassembly; nm symbols have a leading underscore). Images (ADT sweet-0032): `shim/out/shim-boot-0033r.img` (read-only), `shim-boot-0033w.img` (+ufsrw=1 rootrw=1). Still NULL g_crypto_funcs users: des, chacha20poly1305, rsa, aesxts, rand, flow_divert.
- `research/check-patch-order.py` now skips patches touching CI-staged sweet_hfs sources (0031) instead of stopping.

- **0031r RESULT (boot 05:03:52 UTC 2026-10-16, `research/boot0031r.log`, photo IMG_20261016_070508): SHARED CACHE FOUND.** dyld now opens `dyld_shared_cache_arm64` (v2 image hard links), kernel refuses to map it: `shared_region: ... map(...'dyld_shared_cache_arm64'): not in trust cache` -> `vnode is not SIP-protected` (vm_unix.c: macOS arm64 path needs trust cache, else root-owned + SF_RESTRICTED unless CSR_ALLOW_UNRESTRICTED_FS) -> `dyld cache '(null)' not loaded: syscall to map cache into shared region failed` -> libSystem not loaded -> coredump to /cores fails error 30 (EROFS) -> panic initproc failed -> "MACH Reboot" (spins; screen kept). Lots of `hfs: set hardlink bit on vol=iOSRoot cnid=... linkid=...` spam (Linux-made hard links lack the link-chain bit; read-only mount cannot persist the fix). FIX: ADT `/chosen/asmb` with `lp-sip0`=0x6f (u64; incl. CSR_ALLOW_UNRESTRICTED_FS) and `lp-sip1`=1 (unauthenticated root), `tools/mkadt.py` -> `shim/out/sweet-0032.adt`. Images with kernel 0031: `shim/out/shim-boot-0032r.img` (read-only) and `shim-boot-0032w.img` (+ufsrw=1 rootrw=1).

- **2026-10-16 morning:** userdata now = **v2** image (`diff-v1-v2.simg` flashed 21:06:50 UTC 2026-10-15, OKAY, `research/flash-userdata-diff-v2.log`); future diffs use `ios16-root-20H392-v2.img` as OLD. Booted `shim-boot-0029k.img` (ignition_level=1) right after (`research/boot0029k-v2.log`); **no photo** (user asleep). Next morning the phone was in PixelOS recovery = some hardware reset (ABL then booted Android, which cannot use userdata). OBSERVATION: our kernel cannot reset the SoC itself (`PE_halt_restart` is never set; reboot/halt print "MACH Reboot"/"CPU halted" and spin), so the reset came from outside XNU: Qualcomm watchdog or a TZ/XPU violation. Unknown which; re-boot 0029k and watch/video until the reset. Do NOT tap factory reset/format data in recovery (would wipe the iOS image).
- **0030** (`xnu/patches/0030-sweet-ufs-writes.patch`, CI `38852655542`): UFS WRITE(10) + read-modify-write for partial 4 KiB blocks + SYNCHRONIZE CACHE (DKIOCSYNCHRONIZE), only with boot-arg `ufsrw=1`; `ufs_write_blocks` re-checks partition bounds before every write (only place data goes out).
- **0031** (`xnu/patches/0031-sweet-read-write-root.patch`, CI `38852837176`): boot-arg `rootrw=1` clears MNT_RDONLY before the root mount (no data volume on sweet: /private/var is on the root; image has no /etc/fstab); Apple HFS accepts a dirty non-journaled ROOT read-write on SWEET (logs "mounting dirty non-journaled root read-write"). Later: journaled HFS for crash safety. Kernel `xnu/out-0031` (CI `38852837176` success, 5m31s; 0030 run cancelled by the newer push). Boot images (phone ADT `sweet-0028.adt`, ramdisk byte-matched): `shim/out/shim-boot-0031r.img` = 0029k args (read-only, ignition_level=1) and `shim/out/shim-boot-0031w.img` = same + `ufsrw=1 rootrw=1`. PLAN: boot 0031r first and film until the reset (diagnose overnight reset), then 0031w (first ever writes to userdata; v2 image on the SSD is the restore source). `research/check-patch-order.py` cannot check 0031 (staged sweet_hfs files are not in its index); CI stage scripts run first, so CI is the check.

- **ignition_level=1 result** (boot 21:01:39 UTC, `research/boot0029k.log`, photo IMG_20261015_230308): preboot/cryptex stages skipped (need >= 2/3), `dylib_cache: finding shared cache on system volume: ignition level = 1, search root fd = 4, subpath = System/Library/Caches/com.apple.dyld/` -> not found -> `ignition boot failed: 19` -> no shared cache -> libSystem not loaded. FIX IN PROGRESS: image v2 = copy of the flashed image + `/System/Library/Caches/com.apple.dyld/` with HARD LINKS to the 44 cryptex cache files (no extra space; avoids symlink-following doubts), then `tools/sparsediff.py ios16-root-20H392.img ios16-root-20H392-v2.img diff.simg` and flash only the diff. Boot with `ignition_level=1` (shim-boot-0029k.img).
- **ignition_level=0 result** (boot 20:58:07 UTC, `research/boot0029j.log`, photo IMG_20261015_230037): all stages skipped as "ignition level insufficient" (hello/preboot/cryptex1 sniff >= 2, select os cryptex path/graft >= 3, **dyld_cache >= 1**), `ignition boot failed: 89`, "ignition partially disabled", then same `Library not loaded: /usr/lib/libSystem.B.dylib (no such file, no dyld cache)`. => dyld gets the shared cache directory from ignition's dyld_cache stage. Next: `ignition_level=1` (`shim/out/shim-boot-0029k.img`) to skip preboot/cryptex stages but run dyld_cache; its log "finding shared cache on %s ... subpath = %s" will show where it searches. If it searches rootfs /System/Library/Caches/com.apple.dyld, add a symlink there (image rebuild; consider a diff-only sparse flash tool to avoid rewriting 12 GB).
- **APPLE dyld/launchd RUNNING (libignition) with `unentitled_ios_sim_launch=1`** (boot 20:53:24 UTC, `research/boot0029i.log`, photo IMG_20261015_225617): kernel prints "Allowing spawn of iOS binary ... boot-arg set to true"; `shared_region: ... check_np ... vm_shared_region_start_address() failed` (no region yet, normal); dyld's built-in **libignition** (Darwin Ignition Sequence 1.0.0, libignition-51~1974; prints rd=ufsroot0, hardware target sweet, ignition level 0x5, platform 0x2, boot spec local, 7 stages): `hello from launchd.1` -> `preboot: mounting preboot` -> `failed to lookup preboot: 25` (ENOTTY: looks for a separate Preboot volume by role) -> ignition fails -> dyld `Library not loaded: /usr/lib/libSystem.B.dylib ... (no such file, no dyld cache)` -> launchd exit -> panic initproc failed. dyld boot-args found via strings: `ignition_level`, `ignition_force_dylib_root` (forced rootfs/livefs/cryptex fallback), `ignition_halt_after`, `ignition_live_app_graft`; dyld cache search paths include /System/Cryptexes/OS, /System/Volumes/Preboot/Cryptexes/OS/, /private/preboot/Cryptexes/OS/ (present in our image). Next try `ignition_level=0` (`shim/out/shim-boot-0029j.img`).
- **APPLE launchd EXECUTED FROM UFS (2026-10-15).** Flashed iOS image: `img2simg` -> `ios16-root-20H392.simg` (12.1 GB) then `fastboot -S 512M flash userdata ...simg` (24 chunks, 307 s, `research/flash-userdata-ios16.log`; a raw-image flash was killed by earlyoom at 2.6 GB RSS - always flash the sparse image). ABL fastboot hung on getvar after the flash; power+vol-down fixed it. Boot 0029u 20:49:04 UTC (`research/boot0029u-ios16.log`), photo IMG_20261015_225134: `hfs: mounted iOSRoot` -> load_init_program /sbin/launchd -> panic `unexpected SIGKILL of launchd (CS_KILLED) with reason -- namespace 9 code 0xe` = OS_REASON_EXEC / EXEC_EXIT_REASON_WRONG_PLATFORM: our kernel is XNU_TARGET_OS_OSX, iOS-platform binaries are "alien" and refused unless spawn attr platform set or DEVELOPMENT TUNABLE `unentitled_ios_sim_launch`. Next try: same kernel, cmdline + `unentitled_ios_sim_launch=1` (`shim/out/shim-boot-0029i.img`). LONGER TERM: macOS-config kernel marks iOS maps alien (vm_map_mark_alien) and differs from iOS in many policies; an iPhoneOS-config kernel build may eventually be needed.
- **iOS 16 ROOT IMAGE BUILT:** `/run/media/dipa/android/ios-sweet-ipsw/ios16-root-20H392.img` (16 GiB case-sensitive HFS+, label iOSRoot, 12 GB used, fsck OK after `fsck.hfsplus -y` rewrote 32 non-ASCII localized WorkflowKit Shortcut names Linux decomposes differently). Built by `tools/mkiosroot.sh OS.dmg SYSTEMOS.dmg APPOS.dmg OUT.img [SIZE]` (needs sudo; apfs-fuse as root; OS dmg is UDIF -> link must end .dmg). Contents: iPhone X 20H392 OS root + SystemOS cryptex at /private/preboot/Cryptexes/OS (so /System/Cryptexes/OS -> cache, 44 files, dyld_v1 arm64) + AppOS at .../App. /sbin/launchd and /usr/lib/dyld root:wheel 0755. NEXT: (confirm) `fastboot flash userdata ios16-root-20H392.img` (auto-sparse), boot 0029u (rd=ufsroot0) -> Apple launchd attempt.
- **MILESTONE ON HARDWARE: BOOT FROM INTERNAL FLASH.** 0029 CI `38797924912` PASSED, `xnu/out-0029` SHA256 `a68bc847...2a37`. Image `shim/out/shim-boot-0029u.img` (payload-0029u = 0029 kernel + `shim/out/sweet-0028.adt` + `rd=ufsroot0`, NO RAM disk). Boots 20:01:34 and 20:12:37 UTC (`research/boot0029u*.log`), photo IMG_20261015_221403: `SWEET UFS: "userdata" on LUN 0: first block 0x2b8c00, 109643 MiB, read-only` -> `BSD root: ufsroot0, major 1, minor 0` -> `hfs: mounted SweetRoot on device b(1, 0)` -> `SWEET: root volume is not authenticated (error 25); continuing unsealed` -> `load_init_program ... /sbin/launchd` -> `*** SWEET userspace: init running as PID 1 ***` -> heartbeat (ran for minutes unattended). userdata currently holds the 8 MB `research/root-hfs.img`. NEXT: build a multi-GB HFS+ image with the iOS 16 (iPhone X 20H392) userland (OS rootfs + SystemOS cryptex contents incl. dyld shared cache at /System/Library/Caches/com.apple.dyld; preserve modes/owners/symlinks; decompress LZBITMAP via apfs-fuse), flash it to userdata (sparse, needs user OK), then try Apple's dyld/launchd. Driver is read-only (root mounts RDONLY), fine for first launchd attempts.
- **userdata FLASHED with the 8 MB HFS test volume** (user said "flash it", 2026-10-15 19:53:17 UTC, `research/flash-userdata-hfs-test.log`: `fastboot flash userdata research/root-hfs.img` OKAY; pre-checks: one sweet device, partition-size:userdata 0x1AC4BFB000, partition-type f2fs, image fsck OK, SHA256 3626ea69...). Android userdata is now destroyed (expected/approved). Boot 0028u at 19:53:20 (`research/boot0028u-hfs.log`), photo IMG_20261015_215541: `BSD root: ufsroot0` -> **`hfs: mounted SweetRoot on device b(1, 0)` from internal UFS** -> panic `rootvp not authenticated after mounting @bsd_init.c:931` (arm64 macOS-config requires FSIOC_KERNEL_ROOTAUTH sealed root for non-ramdisk roots). Patch **0029** (`dd1c284`): SWEET logs `SWEET: root volume is not authenticated (error N); continuing unsealed` instead of panicking (Apple configs keep the panic; pivot_root still requires auth). CI **`38797924912`** running. Next: download out-0029, phone image with sweet-0028.adt + rd=ufsroot0 (no RAM disk), boot -> expect init from UFS.
- **UFS ROOT DRIVER VERIFIED ON HARDWARE (read-only).** 0028 CI `38796139570` PASSED, `xnu/out-0028` SHA256 `8b981640...9da6`; QEMU HFS RAM-disk regression `research/q0028-hfs` still runs init. Phone boot 2026-10-15 19:50:24 UTC (`research/boot0028u.log`, image `shim/out/shim-boot-0028u.img`, phone ADT `shim/out/sweet-0028.adt` with /sweet-ufs, NO RAM disk, `rd=ufsroot0`), photos IMG_20261015_215151/215220: `SWEET UFS: "userdata" on LUN 0: first block 0x2b8c00, 109643 MiB, read-only` -> `BSD root: ufsroot0, major 1, minor 0` -> `hfs_ValidateHFSPlusVolumeHeader: unknown Volume Signature : f188` (Android-encrypted data, as expected) -> `cannot mount root, errno = 19`, kernel retries mountroot (no panic). Nothing written to flash. NEXT (destructive, needs user confirmation right before): `fastboot flash userdata research/root-hfs.img` (8 MB HFS with test init) then boot rd=ufsroot0 -> expect init from internal flash.
- **PATCH 0028 (`33aceac`): XNU read-only UFS root device**, CI **`38796139570`** running (next artifacts xnu/out-0028, research/bt29, run29.log). `bsd/dev/sweet_ufs.c`: reuses ABL's UFSHCI state (like the shim probe), takes over UTRL at a kmem_alloc_contig region (DMA layout: UTRL 0x0, UCD 0x1000, 1 MiB bounce 0x4000), verifies UTRLBA readback before any doorbell, IE=0 polled, one SCSI cmd at a time on LUN0 (TUR x3, READ(10) via bounce, PRDT 256 KiB chunks), flush_dcache64 by PA around each command (host not dma-coherent per DT), finds GPT partition by name (`ufsroot=` boot-arg, default `userdata`), exposes `/dev/ufsroot0`/`rufsroot0` (512-byte logical sectors, physical 4 KiB, DKIOC* ioctls), refuses writes (EROFS). IOKitBSDInit: `rd=ufsroot0` -> sweet_ufs_rootdev() (lazy init) else panic. ADT: `tools/mkadt.py` adds `/sweet-ufs` reg <0x1d84000 0x3000> for the PHONE only (not --qemu). Local compile OK, imports resolve. Sandbox research/bt28 (pre0028 originals). FIRST PHONE TEST PLAN (non-destructive): boot 0028 with phone ADT + `rd=ufsroot0` and NO RAM disk: expect `SWEET UFS: "userdata" on LUN 0: first block 0x2b8c00, 109643 MiB` + `BSD root: ufsroot0`, then root mount failure (userdata is still Android-encrypted) -> panic. That validates the driver before flashing an HFS image into userdata (needs explicit user confirmation at that time).
- **SUPERSEDES the 64 GiB iosroot GPT plan: user said "u can delete android" (2026-10-15).** Use the existing `userdata` partition (LUN0 sda34, 4K LBA 0x2B8C00, 0x1AC4B MiB ~107 GiB) directly as the iOS root: NO GPT changes. Keep bootloaders, recovery (OrangeFox), modem/persist/fsg/modemst untouched. Write the HFS image later with `fastboot flash userdata` (sparse, auto-split under the 768 MiB limit). Android will no longer boot normally (expected; reinstallable). Order: XNU UFS driver first, read-only against the current GPT; flash only once it can locate userdata. Nothing erased yet.
- **DECIDED (user, 2026-10-15): 64 GiB `iosroot` on LUN0 (sda), taken from userdata (wipes Android user data; Android/super kept).** Planned GPT (4K LBAs): userdata 0x2B8C00..0xD7D6FF (~43 GiB, keep type/unique GUIDs and attributes); iosroot 0xD7D700..0x1D7D6FF (0x1000000 blocks = 64 GiB, 1 MiB aligned); backup GPT area unchanged. Procedure: user backs up phone data -> boot OrangeFox recovery (adb) -> back up GPT (sgdisk --backup + raw dd of LBA 0-5 and last 6 blocks) to research/ -> sgdisk edit -> Format Data -> verify Android boots to setup. NOT EXECUTED YET.
- **INTERNAL UFS WORKS FROM THE SHIM (read-only), user authorized internal-UFS approach incl. flashing (2026-10-15, "i allow everything").** Shim probe `shim/ufs.c` (commit `12ed3ed` + filter): ufshc@1d84000 is UFSHCI 2.1 (ver 0x210, cap 0x1587031F, 32 slots), ABL leaves HCE=1, HCS=0x10F (device present, lists ready, UIC ready); probe takes over UTRL at its own buffer (verifies UTRLBA readback before any doorbell), TEST UNIT READY/READ CAPACITY/READ(10) all succeed. LUN0 = 0x1D7D800 x 4 KiB (~126.6 GB), valid GPT (64 entries at LBA 2). Photos IMG_20261015_212916/213325/213429. Big LUN0 partitions (start in 4K LBAs / MiB): super 0xCA00/0x2200 (8.5 GiB), logdump 0x22CA00/64, minidump 0x230A00/128, rawdump 0x238A00/128, recovery 0x240C00/128, cache 0x248C00/384 ext4, exaid 0x260C00/384, cust 0x278C00/1024 ext4, **userdata 0x2B8C00/0x1AC4B MiB (~107 GiB), fs unreadable = encrypted (metadata encryption)**. cache..cust contiguous = only 1.75 GiB (too small for iOS ~10+ GiB). Plan needing user consent: shrink userdata in GPT (wipes Android data) and add an `iosroot` partition at the end of LUN0. LUNs 1-5 not listed yet (sdb..sdf backed up in backup/lun).
- **fastboot limit measured (2026-10-15, read-only getvar):** `max-download-size: 805306368` (768 MiB); `max-fetch-size` unsupported; `is-userspace: no` (ABL fastboot). A `fastboot boot` image (shim+kernel+RAM disk) must be < 768 MiB, so the 2.5 GiB iOS shared cache cannot ride in the boot RAM disk even if XNU gets all RAM. Real userland needs storage access (UFS driver, or USB host) or a much smaller cache. Unlocking full RAM is still needed later (GUI).
- **iOS 16 USERLAND SOURCE (Claude, 2026-10-15).** Chose **iPhone X (iPhone10,3/10,6, D22/D221AP)** iOS **16.7.16 (20H392)** over iPhone 8: same A11 (no PAC -> plain arm64, runs on Kryo 470/ARMv8.2), last iOS for A11; X userland is home-button-less and tall-screen (1125x2436 vs sweet 1080x2400), better fit for later GUI. Note the X has its OWN SystemOS cryptex (different digest from iPhone 8's). IPSW URL in `research/ipsw-x/URL.txt` (+ BuildManifest). Images on the user's external SSD (NOT in git, do not format that disk: it holds the user's photos): `/run/media/dipa/android/ios-sweet-ipsw/iPhone10,3_16.7.16_20H392/` — `087-86593-047.dmg` = Cryptex1,SystemOS (2,743,074,816 B), `087-86698-044.dmg` = OS rootfs (4,730,814,044 B), both zip CRC-32 verified, plus Firmware/*.root_hash/.trustcache/.mtree. AppOS cryptex is 087-86715-047.dmg (10 MB, same as iPhone 8).
  - Images are raw APFS; files use LZBITMAP (decmpfs type 14). 7z cannot decode. Tools: `ipsw` 3.1.738 (AUR ipsw-bin, user-approved) needs apfs-fuse on Linux; **apfs-fuse** built in user space (system cmake broken: cmake 4.4.4 wants libjsoncpp.so.27, jsoncpp 1.9.6 installed = partial upgrade, NOT fixed) with pip cmake + `-DCMAKE_POLICY_VERSION_MINIMUM=3.5 -DCMAKE_CXX_FLAGS="-include cstdint"`, installed to `~/.local/bin/apfs-fuse` (+apfs-dump-quick). Mount via a comma-free symlink (apfs-fuse splits options on ',' in `iPhone10,3`; exFAT has no symlinks -> put link elsewhere): `apfs-fuse LINK/087-86698-044.dmg MNT` -> `MNT/root/...`; unmount `fusermount3 -u MNT`.
  - Verified from headers: `dyld_shared_cache_arm64` magic `dyld_v1   arm64`; `/sbin/launchd`, `/usr/lib/dyld` = cputype 0x100000c subtype 0 (plain arm64). libSystem exists only inside the cache.
  - **BLOCKER for real userland via RAM disk:** shared cache = 3.10 GiB in 44 files (~2.5 GiB without the 592 MB `.symbols`), but the kernel manages only 1.20 GiB (0xb0000000..0xfd000000). Options: (A) give XNU the phone's full ~6 GB (banks 0x80000000+2G and 0x100000000+0xfcc00000, carve-out holes need pmap support) AND check fastboot max-download-size for a multi-GB boot image; (B) storage driver (Qualcomm UFS) to read a root from flash (no flashing allowed: would need a file/partition strategy); (C) run against individual dylibs extracted from the cache (uncertain).
- **MILESTONE ON HARDWARE: HFS+ ROOT FILESYSTEM -> PID 1.** Boot 2026-10-15 18:22:12 UTC (`research/boot0027b.log`, image `shim/out/shim-boot-0027b.img`), photo `IMG_20261015_202334.jpg`: `BSD root: md0` -> `hfs: mounted SweetRoot on device b(1, 0)` -> `load_init_program: attempting to load /sbin/launchd` -> `*** SWEET userspace: init running as PID 1 ***` -> repeated `SWEET init: still alive`, no panic. Kernel 0027 (built-in Apple OSS HFS + BearSSL MD5), init with SP alignment fix. NEXT: real iOS 16 userland on the HFS image (dyld, libSystem/dyld shared cache, launchd). Known gaps: entitlements (none granted), SHA-1/SHA-384/512 providers, no storage driver (RAM disk only), root mounted read-only.
- **PHONE HFS ROOT (0027) + SIGBUS ROOT-CAUSED.** Phone boot 2026-10-15 17:49:06 UTC (`research/boot0027.log`, photo `IMG_20261015_200031.jpg`): `hfs: mounted SweetRoot on device b(1, 0)` (HFS works on hardware), init printed its first line, then `pid 1 exited -- exit reason namespace 2 subcode 0xa` = SIGNAL/SIGBUS -> `initproc failed to start` panic. Diagnostic boot 18:08:13 UTC (`research/boot0027d.log`, image `shim/out/shim-boot-0027d.img`, diag init `research/diag-init` from scratch diag-init.S with [a][b][c] markers, `cs_debug=1`; photo `IMG_20261015_201547.jpg`): output `PID [a][b]` then SIGBUS -> fault at first `strb w21,[sp]`; no code-signing messages. Cause: kernel enters a static binary with sp at argc, not necessarily 16-aligned (depends on arg/apple string lengths, differs mockfs vs HFS); EL0 SP alignment check -> EXC_ARM_SP_ALIGN -> SIGBUS (sleh handle_sp_align). QEMU does not enforce SP alignment. NOT a kernel bug: real binaries start in dyld which aligns. Fix `1a8fc15`: sweet-init aligns sp at entry. Rebuilt `research/root-hfs.img`, QEMU `research/q0027-hfs2` OK. Phone image `shim/out/shim-boot-0027b.img` SHA256 `098ba46c...c5c` (payload-0027b, ramdisk match check-0027b) ready, awaiting FASTBOOT. Lesson: Assembly `;` is a comment in Apple arm64 asm (use .macro, not ;-joined #define).
- **HFS ROOT WORKS (QEMU).** 0027 CI `38779441895` PASSED, `xnu/out-0027` SHA256 `a8643886...5f6a`. QEMU `research/q0027-hfs` (RAM disk = `research/root-hfs.img`, rd=md0): `BSD root: md0` -> `hfs: mounted SweetRoot on device b(1, 0)` -> `load_init_program: attempting to load /sbin/launchd` -> `*** SWEET userspace: init running as PID 1 ***` + heartbeat, no panic. Phone image `shim/out/shim-boot-0027.img` (payload-0027 = 0027 kernel + sweet-0021.adt + root-hfs.img + rd=md0, ramdisk byte-match check-0027) ready; awaiting FASTBOOT for phone test.
- **HFS ROOT WORK (Claude), patches 0026-0027.**
  - 0026 (`f0e990c` + link fix `64c96f4`): Apple OSS **hfs-627.100.6** (commit `31d5ec238dfab485e78a9a30b8b92d13e8914f03`, paired with xnu-8796.141.3 in macos-135 release.json) staged by `xnu/patches/0026-stage-hfs.sh` into `bsd/sweet_hfs` (core + hfs_encodings; AppleKeyStore include/key prototypes guarded by CONFIG_PROTECT; SDK TargetConditionals copied). New config option `sweet_hfs` (MASTER + MASTER.arm64.sweet); 40 `optional sweet_hfs` files; Makefile.template foreach adds `_CFLAGS_ADD = -include sweet_hfs_compat.h -I...` (MUST come after kernel -D flags; compat undefs BSD/XNU_KERNEL_PRIVATE and the CONFIG_* HFS tests so kext-config.h decides: macOS profile, no content protection). `sweet_hfs_iokit.c` replaces hfs_iokit.cpp/hfs_encodings_kext.cpp: `sweet_hfs_register()` called in bsd_init after vfsinit (encodings init, vfs_fsadd VFS_TBLCANMOUNTROOT, zones, sysctls); is_ejectable 0, iterate_media none, serial KERN_NOT_SUPPORTED, OSKextGetCurrentLoadTag -> kOSKextInvalidLoadTag (renamed via compat macro). hfs_encodings' own `hfs_allocated` renamed per object (separate kexts on Apple; first CI `38777325964` failed on that duplicate at link). mockfs now validates Mach-O magic (its TODO) so non-Mach-O roots fall through to HFS (new fs entries come AFTER mockfs in vfsconf). CI `38778133720` PASSED, `xnu/out-0026` SHA256 `0b49170c...701a`, prints `SWEET HFS: hfs-627.100.6 registered`.
  - HFS+ image: `research/root-hfs.img` (8 MB, mkfs.hfsplus from AUR hfsprogs installed with user approval; loop-mounted with sudo; /sbin/launchd = research/sweet-init, /dev; fsck.hfsplus OK). QEMU `research/q0026-hfs`: `BSD root: md0` then data abort in MD5Init from hfs_getvoluuid (mount computes volume UUID).
  - 0027 (`14bf2b7`): 0020 stager also copies BearSSL hash/md5.c + codec/dec32le.c/enc32le.c; `corecrypto_md5.c` SWEET branch converts MD5_CTX <-> br_md5_context around br_md5_* calls; wrappers sweet_md5.c/sweet_dec32le.c/sweet_enc32le.c. Host test 40/40 match md5sum. CI **`38779441895`** running.
  - Local tooling: `tools/xnu-cc.py` has `XNU_CC_POST` (flags after logged ones). Sandbox `research/bt28/xnu` = 0025 CI tree + 0026/0027 edits; originals `research/pre0026`, `research/pre0027`. HFS local objects `research/hfs-objs`. Checker entries updated to bt28.
  - SHA-1 / SHA-384/512 still have no provider.
- **MILESTONE ON HARDWARE: USERSPACE PID 1 RUNS ON THE PHONE.** Boot 2026-10-15 17:16:00 UTC (`research/boot0025.log`: send OKAY0.410s, boot OKAY0.135s), image `shim/out/shim-boot-0025.img` SHA256 `9dbfa0b1...89db0`. Photo `IMG_20261015_191733.jpg`: `BSD root: md0` -> `load_init_program: attempting to load /sbin/launchd` -> `*** SWEET userspace: init running as PID 1 ***` -> repeated `SWEET init: still alive` (5 s heartbeat), no panic. Kernel 0025 + mockfs RAM disk + built-in no-entitlements AMFI. No flashing performed.
- **NEXT (toward real iOS userland):** real root filesystem with real binaries. Options: (a) build Apple OSS `hfs` (macOS 13.5 tag `hfs-627.100.6`) into SWEET like libpthread, then an HFS RAM disk image; (b) iOS 16 dyld + libSystem/dyld shared cache from the IPSW (needs APFS or repacking onto HFS). Expected hurdles: entitlements (sweet_amfi grants none), SHA-1/MD5/SHA-384/512 providers (BearSSL), missing kexts/daemons. Current init is a static test program, not launchd.
- **MILESTONE: USERSPACE RUNS (QEMU).** 0025 CI `38774788048` PASSED, `xnu/out-0025` SHA256 `5496069b...4877`. QEMU `research/q0025-rd` (150 s, no panic): `BSD root: md0` -> `load_init_program: attempting to load /sbin/launchd` -> `*** SWEET userspace: init running as PID 1 ***` -> `SWEET init: still alive` every 5 s. Exec, ad-hoc SHA-256 code signature, syscalls, devfs /dev/console, select timeouts all work. Phone image prepared: `shim/out/shim-boot-0025.img` 16,515,072 bytes SHA256 `9dbfa0b15140c0bd733a16c4f727f6a7df44a8741f98d8e266d5f2fa4f689db0` (payload-0025 = 0025 kernel + sweet-0021.adt + research/sweet-init + rd=md0; ramdisk byte-match check-0025). Waiting for user to put phone in FASTBOOT.
- **0024 CI `38773277811` PASSED**, `xnu/out-0024` SHA256 `a0ba964b...4348`. QEMU `research/q0024-rd` and **PHONE (boot 2026-10-15 17:05:55 UTC, `research/boot0024.log`, image `shim/out/shim-boot-0024.img` SHA256 `cf3dac86...6964`, 16,510,976 bytes, payload `shim/out/payload-0024.bin` = 0024 kernel + `shim/out/sweet-0021.adt` + RAM disk `research/sweet-init` + rd=md0; ramdisk byte-match `check-0024`)** agree: `Added memory device md0`, `BSD root: md0`, `load_init_program: attempting to load /sbin/launchd`, then data abort in accelerate_entitlement_queries (PC 0x...77d2458, FAR 0x1a0) = NULL AMFI interface. Photo `IMG_20261015_190715.jpg`. RAM disk root is physically verified.
- **0025 (`2518c79`)**: new `bsd/kern/sweet_amfi.c` registers a built-in AMFI interface at EARLY_BOOT/MIDDLE: no entitlements (adjustContextWithoutMonitor succeeds without creating a context, queries KERN_DENIED, copies NULL/KERN_NOT_FOUND, get_xml/transmuted false); WithMonitor KERN_NOT_SUPPORTED; OSEntitlements_query and query_context_to_object panic explicitly (CoreEntitlements closed; no kernel caller); TrustCache version 0 (0015 keys on trust_cache_rt==NULL, img4 absent -> still unavailable); CoreEntitlements table zero (PMAP_CS only). Compiles locally; checker updated (bt27 entries). CI **`38774788048`** running. Next artifacts `xnu/out-0025`, `research/bt29`, `research/run29.log`. Real iOS binaries will need real entitlements later (no OSS CoreEntitlements exists).
- **0021-0024 RAM-disk-root iteration (Claude), QEMU only so far, no new phone boot since 0020.** Each kernel tested with `tools/mkpayload.py KERNEL research/q0021.adt OUT --ramdisk research/sweet-init --cmdline "debug=0xc serial=3 cpus=1 keepsyms=1 -enable_kprintf_spam -noprogress rd=md0"` then `tools/qemu-sweet.py OUT DIR --secs 150 --kernel KERNEL --fail-on-panic` (PATH needs ~/swift/usr/bin for llvm-nm). Fresh ADTs: `research/q0021.adt` (QEMU), `shim/out/sweet-0021.adt` (phone).
  - 0021 CI `38769532000` PASSED, `xnu/out-0021` SHA256 `2b7500a1...962e`, `research/bt25`/`run25.log`. QEMU `research/q0021-rd`: md0 root, then assert `iomediaClass` in IOService::publishHiddenMedia.
  - 0022 (`20ece9c`, publishHiddenMedia without IOMedia class) CI `38770666158` PASSED, `xnu/out-0022` SHA256 `a4d0e787...30c5`, `research/bt26`/`run26.log`. QEMU `research/q0022-rd`: data abort in SHA256_Init (NULL g_crypto_funcs) from vm_kernel_addrhash_internal.
  - 0023 (`c8089d1`, libkern SHA256_Init/Update/Final use built-in ccsha256_ltc_di + ccdigest_init/update on SWEET; also serves code-signing SHA-256; SHA-1/MD5/SHA-384/512 still have NO provider - BearSSL from 0020 could supply them later) CI `38771876423` PASSED, `xnu/out-0023` SHA256 `d763fed7...1003`, `research/bt27`/`run27.log`. QEMU `research/q0023-rd`: **mockfs mounted md0, `load_init_program: attempting to load /sbin/launchd`**, then panic `mockfs_fsnode_vnode failed to create fictitious pages ... rvalue = 5` (mockfs.c:351).
  - 0024 (`3293c80`): mockfs used memdev mi_base (4K page number of a VIRTUAL kernel address for IOKit RAMDisk, truncated to 32 bits) << PAGE_SHIFT as a physical address. Now zero-copy pager mapping only when mi_phys (with 4K units); virtual md uses pagein/blockmap/strategy -> memdev bcopy. memdev's own mdPhys path assumes 4K ppnums (unsafe on 16K arm64), so do NOT switch the RAMDisk to physical. CI **`38773277811`** running. Next artifacts `xnu/out-0024`, `research/bt28`, `research/run28.log`.
  - Sandboxes: bt25/bt26/bt27 contain the next patch's edited files; pristine copies in `research/pre0022`..`pre0024`.
- **PATCH 0021 (Claude): RAM disk root via mockfs -> first userspace program.** Commits `9c37771` (initial; CI `38768500280` FAILED: mockfs_fsnode.c kfree_type(mockfs_fsnode_t) typed-alloc static assert; local xnu-cc stubs `__builtin_xnu_types_compatible` so it can't catch this) and `193772f` (fix), CI **`38769532000`** running: https://github.com/dipa-studio/ios-sweet/actions/runs/38769532000. Next artifacts: `xnu/out-0021`, `research/bt25`, `research/run25.log`.
  - Kernel: `config/MASTER.arm64.sweet` FILESYS_BASE += `mockfs` (XNU's built-in FS: root device is itself a Mach-O, served as /sbin/launchd, plus /dev for devfs). Upstream mockfs bit-rot fixed: kalloc_type/kfree_type used the POINTER typedef mockfs_fsnode_t (nodes were 8 bytes) -> `struct mockfs_fsnode`. `IOService::setRootMedia` asserted IOBlockStorageDriver class exists (IOStorageFamily absent): SWEET-only, a missing class means root=NULL (same as IOSetImageBoot); Apple path keeps assert. All 21 patches apply (`research/check-patch-order.py`); 5 TUs compile locally with -DMOCKFS (`research/mockfs-objs`), imports resolve vs 0020 kernel. Sandbox `research/bt24/xnu` now holds 0021 versions of those 3 files; pristine 0020 copies in `research/pre0021`.
  - Tools: `tools/mkpayload.py --ramdisk IMAGE` appends IMAGE as an extra payload segment right after the kernel, moves kernel_end past it (shim unchanged: ADT+boot_args follow it, image stays below topOfKernelData), and adds ADT `/chosen/memory-map` `RAMDisk`=<phys,size>. Boot with `rd=md0`. Without --ramdisk output is byte-identical to existing 0020 QEMU and phone payloads (verified). `tools/sweet-init.S` + `tools/mkinit.py`: PIC static init (open /dev/console, print PID, heartbeat every 5 s via select, never exits) wrapped into a static arm64 Mach-O (__PAGEZERO, __TEXT@0x100000000, LC_UNIXTHREAD, ad-hoc SHA-256 CodeDirectory v0x20400, 4K pages). Build: `~/swift/usr/bin/clang -target arm64-apple-ios16.0 -c tools/sweet-init.S -o X.o && tools/mkinit.py X.o research/sweet-init` (ld64.lld cannot link static iOS). Signature not verified by a real codesign; the kernel will tell.
  - QEMU with 0020 kernel + RAM disk (`research/q0020-rd.bin`, rd=md0, 150 s `research/q0020-rd150`): `Added memory device md0`, **`BSD root: md0, major 1, minor 0`** (plumbing works), then the setRootMedia assert (now fixed in 0021). NOTE: QEMU needs >60 s to reach IOFindBSDRoot (60 s run showed nothing after stf0; likely RTC/inittodr wait), so use --secs 150.
  - NEXT: download 0021, QEMU 150 s with ramdisk; expect mockfs mount then init exec -> `*** SWEET userspace: init running as PID 1 ***`. Then phone boot with same payload (phone ADT shim/out/sweet-0020.adt pattern + --ramdisk + rd=md0).
- **0020 PHONE RESULT (user transcription of screen, 2026-10-15): KERNEL INIT COMPLETE, WAITING FOR ROOT.** After Skywalk self-tests PASSED, kminit, ifnet_attach lo0/gif0/stf0, screen prints `BSD`, then `Waiting on <dict><key>IOProviderClass</key><string>IOMedia</string><key>Content</key><string>Apple_HFS</string></dict>` and `Failed to write boot-picker-bringup-reason to NVRAM.` No panic. This is IOFindBSDRoot waiting for a root device (none exists); NVRAM warning is expected (no NVRAM driver). QEMU `cpu_idle` snapshot is presumably the same wait (not GDB-confirmed; milestone GDB run was cancelled by user since phone answered it). Draft `research/check-milestones20.gdb` (hbreaks inittodr/vfs_mountroot/IOFindBSDRoot/bsd_utaskbootstrap) left uncommitted/ignored.
- **NEXT MILESTONE: root filesystem -> launchd.** Plan: (1) RAM disk: shim places an image in RAM, ADT /chosen/memory-map `RAMDisk` entry, boot-arg `rd=md0` (XNU md driver). (2) HFS is a separate kext on Apple; build Apple OSS `hfs` (tag paired with macOS 13.5 in distribution-macOS macos-135 release.json) into SWEET like libpthread 0019. APFS is closed. (3) Minimal HFS image with iOS 16 launchd (later: dyld/shared cache; AMFI/code-signing absent will be a later hurdle). User's end goal is full iOS GUI.
- **0020 (AES) VERIFIED + PHONE BOOTED (Claude took over after Codex usage limit).** Actions `38765422261` (`ab9e23f`) PASSED; kernel `xnu/out-0020/kernel.development.sweet` checksum OK; buildtree `research/bt24`, log `research/run24.log`. Actual-kernel AES checks PASS (`research/check-aes20.gdb` / `.log`, 12 extra CBC cases match OpenSSL). 45s QEMU `research/q0020`: no panic, zero unknown glyphs, past old TCP/AES panic -> Skywalk self-tests PASSED -> bsd_autoconf kminit -> ifnet_attach lo0/gif0/stf0; final snapshot PC in `cpu_idle` (idle or waiting; NOT yet diagnosed, could be root-device wait). Image `shim/out/shim-boot-0020.img` 16,461,824 bytes SHA256 `775200cb02d95fc750981516b79d91dcdc96184bbe67a38f9d57c59b4a391828`, ramdisk byte-matches `payload-0020.bin` (`check-0020`). **Phone temporarily booted 2026-10-15 16:10:00 UTC**: one FASTBOOT product sweet, send OKAY0.407s, boot OKAY0.134s, total0.549s, exit0 (`research/boot0020.log`). Awaiting user photo; do not reboot the phone before it. NEXT: read photo; diagnose what QEMU waits on after stf0 (GDB backtrace of threads / longer run). Codex's STOP request below is complete.
- User requests STOP after completing the current0020 AES iteration (Actions/QEMU/phone), then leave a precise committed handoff for another AI. User says FASTBOOT ready again after0019 photo. Do not start a new blocker fix after this iteration.
- Goal: iOS16-generation XNU on Redmi Note10Pro sweet/SM7150. Always commit, use gh/Actions for kernel builds, keep this handoff current. Temporary fastboot boot only; preserve Android/backups. No userland/root filesystem boot yet.
- **Patch0020 update:** initial `e71098d` / Actions `38765012466` superseded by scalar-only compile flags. Added -mgeneral-regs-only to all six provider/BearSSL TUs and corecrypto_aes.c; object disassembly now confirms no SIMD. Updated implementation `ab9e23f`, Actions `38765422261` queued/running: https://github.com/dipa-studio/ios-sweet/actions/runs/38765422261. Do not launch another run. portable BearSSL AES CBC and legacy one-block ECB wired directly into SWEET corecrypto_aes.c. Genuine bitslice implementation, no CPU AES/SIMD requirement, heap or fake global crypto table. Source fetched by `0020-stage-bearssl.sh` from official BearSSL git at immutable `7bea48e5e850ab4cafbe68d3765cdaba13a86d6f`; MIT license retained, downloaded source stays out of git. Kernel limits include adapter only. All128/192/256-bit keys, CBC encrypt/decrypt, copied contexts, in-place/out-of-place; zero block count and size overflow handled, invalid keys clear context. Seven TUs compile to arm64 objects (`research/aes-objs`), imports resolve, all20 patches apply and sources match (`research/patch0020-check.log`). Sandbox `research/bt23/xnu`, originals `research/pre0020`. NEXT: Actions then actual-kernel NIST/random CBC/ECB checks and >=45s QEMU before another phone boot. Next artifacts out-0020 / bt24 / run24.log. 0020 updated CI pending. Local sources/checks match the scalar-only patch.
- **Latest built kernel0019**, implementation `256d3f0`, patches0001-0019. Actions `38763072907` PASSED (4m5s): https://github.com/dipa-studio/ios-sweet/actions/runs/38763072907. Kernel `xnu/out-0019/kernel.development.sweet`, SHA256 `a27df7568f03fb541cf0e8024c0a594fa178a85054fcf9eba29158cbd4c5ecc0`; checksum verified. Log/source `research/run23.log` / `research/bt23` (no nested .git). Seven pthread source/build/header files and staged adaptations byte-match local compile inputs.
- **0019 hardware photo received** `IMG_20261015_175306.jpg`: pthread registration visible, passes mbinit and DLIL checksum/scheduling, same AES fault as QEMU: PC`0xfffffe00079174e0` (`aes_encrypt_key128`), LR`0xfffffe000767c3a4` (`tcp_init`), FAR0x78, x8=0. Disassembly proves NULL g_crypto_funcs->ccaes_cbc_encrypt. Photo processed; no more0019 observation pending. General crypto table remains absent, other hash/mode operations may still fault after0020. DO NOT bypass TCP or install fake crypto. XNU already contains SHA256/HMAC implementations; AES source there is a dispatch wrapper. Full future provider interface libkern/libkern/crypto/register_crypto.h. Apple/corecrypto default README describes evaluation-only licensing, so no external corecrypto was fetched or staged; BearSSL selected for this portable AES integration.
- **0019 pthread FIXED in QEMU and observed beyond its init on phone**: 45s QEMU `research/q0019`, zero unknown glyphs, then AES panic. Actual-kernel API checks PASS `research/check-pthread19.gdb` / `.log`, guest `research/q0019-api`: function/callback table identity, actual provider pthread_init returns, locks/global hash/threadcall/typed zones initialized, thread_selfid via syscall shim + buffer bounds, process hash init/delete via shims restores NULL. Monitor quit prints expected remote-disconnect after PASS. All fixture guests stopped.
- **0019 provider**: genuine Apple libpthread-514.100.2 commit `a6c70ca0e544347a0377babf748f831577ec24f9`, exact paired release with xnu8796.141.3 in distribution-macOS/macos-135/release.json (`research/macos-135-release.json`). 0019 shell stage runs before patches (workflow copies *.sh); three SWEET wrapper TUs use kext BSD header view, vm_fault_external, renamed provider-side pthread_kern/current_uthread; register real function table at EARLY_BOOT SECOND, real pthread_init later. Stager applies bounded address casts, zero user addresses, proper panic format. SWEET opaque ksyn storage enlarged48->56 for trailing kwe_uth, checked with provider static assertion. Local pre-CI TargetConditionals fixture was syntax-only; artifact bt23 carries actual SDK header and CI is authoritative.
- **Phone0019 temporarily booted** 2026-10-15 15:51:36 UTC: exactly one FASTBOOT/product sweet verified; send OKAY0.406s, boot OKAY0.134s, total0.546s, exit0 (`research/boot0019.log`). Image `shim/out/shim-boot-0019.img`, 16,457,728 bytes, SHA256 `19429a57e486b856880df9e27327ed488e0139345311fdb0350974e72103a9a1`. Phone ADT/payload `shim/out/sweet-0019.adt` / `payload-0019.bin` timer19, unpacked ramdisk byte-match (`check-0019`). EntryPA0xb146b488, kernelendPA0xb2000000, boot_argsPA0xb2004000/top0xb2008000. Last user FASTBOOT+USB reply preceded this boot; do not assume phone is still in FASTBOOT.
- **CPU0018 physically verified** by `IMG_20261015_173951 (2).jpg`: boot CPU0 registered, real SGI1 verified, initialization complete -> BSD/MAC/mbinit -> old pthread-table panic. SweetCPU uses legacy IOCPU, ml_processor_register/processor_start/initCPU, real SGI1 clears SIGPdisabled before max CPUs completion; no forced flags/skipped waits. CPU APIs and two-CPU rejection passed (`research/check-cpu18.gdb`, `q0018-api`, `q0018-smp`). Single core; SMP/suspend unsupported. CURRENT SWEET has NO USE_APPLEARMSMP.
- QEMU next run: generate fresh `tools/mkadt.py research/q0020.adt --qemu` (timer27), mkpayload with `debug=0xc serial=3 cpus=1 keepsyms=1 -enable_kprintf_spam -noprogress`, then `tools/qemu-sweet.py PAYLOAD OUT --secs 45 --kernel KERNEL --fail-on-panic`. 12s can miss later panics because IORTC waits30s. Runner snapshot only: panic exit2, blank/incomplete exit3; absence of panic does not mean complete boot. Qualcomm XPU/ABL/panel and phone SMC PSCI require hardware checks.
- Local checker `tools/xnu-cc.py research/run23.log research/bt23 FILTER --per-file`, XNU_CC_OBJDIR for objects. For new BearSSL TUs add XNU_CC_EXTRA with -I bt23/xnu/libkern/crypto/sweet_bearssl/{inc,src}. Patch checker `research/check-patch-order.py` uses temporary upstream index; source fixtures/artifacts ignored under research. GDB mask registers to unsigned64, use function-entry manual-call return traps, discard manipulated guests. No QEMU guest intentionally left running.

## Session log and earlier handoffs (superseded by the active summary above)

### Prior 0019 transition notes (superseded)

- Goal: iOS 16 generation XNU on sweet. Always commit completed work, use gh/Actions for kernel builds, keep this handoff current. Temporary fastboot boot only; preserve Android/backups.
- **0019 build PASSED** Actions `38763072907` (4m5s), implementation `256d3f0`. Kernel `xnu/out-0019/kernel.development.sweet`, SHA256 `a27df7568f03fb541cf0e8024c0a594fa178a85054fcf9eba29158cbd4c5ecc0`; checksum verified. Log/source `research/run23.log` / `research/bt23`; all seven patched files and staged provider adaptations match local compile inputs. Prefer bt23 as the next baseline.
- **0019 pthread FIXED in QEMU**: 45s run `research/q0019` registers provider, passes mbinit, DLIL SUM16 checks and DLIL thread scheduling. Actual-kernel GDB checks `research/check-pthread19.gdb` / `.log` PASS: function/callback table identity, real _pthread_init returns, locks/global hash/cleanup threadcall/typed zones non-NULL, thread_selfid via actual syscall shim with output bounds, process hash init/delete through actual shims restores NULL. Guest stopped after tests; no fixture left running. GDB monitor quit prints expected remote disconnect after PASS.
- **Current next blocker:** QEMU0019 panic data abort FAR0x78 at `aes_encrypt_key128` PC`0xfffffe00079174e0`, called by `tcp_init` LR`0xfffffe000767c3a4`. Disassembly confirms `g_crypto_funcs == NULL`, loading ccaes_cbc_encrypt at+0x78. General crypto registration is still absent; DO NOT bypass TCP or supply fake crypto. Next integrate a genuine compatible crypto implementation/provider (AES first needed here, other digest/mode APIs also used). XNU contains SHA256/HMAC but no AES implementation; its corecrypto_aes.c is a dispatch wrapper. Full crypto table is in libkern/libkern/crypto/register_crypto.h.
- **0019 phone image prepared and verified**, user reports FASTBOOT+USB again; exactly one device/product sweet verified. `shim/out/shim-boot-0019.img`, 16,457,728 bytes, SHA256 `19429a57e486b856880df9e27327ed488e0139345311fdb0350974e72103a9a1`; unpacked ramdisk matches phone payload (`shim/out/check-0019`, `payload-0019.bin`, `sweet-0019.adt`, timer19). EntryPA0xb146b488; kernelendPA0xb2000000; boot_argsPA0xb2004000/top0xb2008000. Usual debug cmdline cpus=1/-noprogress. **Temporarily booted 2026-10-15 15:51:36 UTC**: send OKAY0.406s, boot OKAY0.134s, total0.546s, exit0 (`research/boot0019.log`). User asked for photo after45s. Await the photo; DO NOT reboot again before observation. Bootloader acceptance only; no0019 physical progress observed yet.
- **Hardware photo confirms 0018 progress** (`IMG_20261015_173951 (2).jpg`): real phone prints `SWEET CPU: boot CPU 0 registered, SGI1 verified, initialization complete`, enters BSD/MAC, reaches `mbinit: done`, then the same missing-pthread-function-table panic as QEMU at pthread_shims.c:318. CPU completion/interrupt delivery is now physically observed. The photo was received; no further phone boot performed yet.
- **Patch0019 committed/pushed `256d3f0`; Actions `38763072907` queued/running:** https://github.com/dipa-studio/ios-sweet/actions/runs/38763072907. Do not launch a duplicate. genuine Apple OSS libpthread-514.100.2 provider (immutable commit `a6c70ca0e544347a0377babf748f831577ec24f9`), paired with xnu-8796.141.3 by Apple's `distribution-macOS/macos-135/release.json` (`research/macos-135-release.json`). `0019-stage-libpthread.sh` fetches/stages it before patches; workflow now copies shell scripts too. SWEET-only wrappers compile all three real kernel sources, rename provider-side symbols, use kext header view and vm_fault_external, register the real function table at EARLY_BOOT SECOND. Existing pthread_init then runs the actual provider initialization. No pthread wait/syscall is bypassed. Source staging includes bounded explicit address casts/zero user addresses and panic-format fixes. SWEET kernel opaque ksyn storage enlarged from48 to56 bytes to contain this provider's trailing kwe_uth, with a provider size assertion. Local compile of three provider TUs plus pthread_shims/kern_fork passed; imports resolve and provider exports do not collide with existing kernel symbols. All19 patches apply and changed sources match (`research/patch0019-check.log`). Source sandbox `research/bt22/xnu`, originals `research/pre0019`, objects `research/pthread-objs`. Local TargetConditionals fixture only has target macros for syntax; CI stages the real macOS SDK header and is authoritative. Next Actions artifacts: out-0019 / bt23 / run23.log; run QEMU >=45 seconds. 0019 CI is pending; no 0019 QEMU run yet.
- **Latest kernel implementation `e7d9550`, patches0001-0018; CI `38760004398` PASSED (3m56s)**: https://github.com/dipa-studio/ios-sweet/actions/runs/38760004398. No build is pending. Kernel `xnu/out-0018/kernel.development.sweet`, SHA256 `b3c8d59acc88f93a2c836eb2527a05ed4fbaac7c580a2ea8c3b795137f4aadf1`; checksum verified. Source/log `research/bt22` / `research/run22.log` (baseline for patch0019; no nested .git). New driver/config sources match CI exactly.
- **CPU wait FIXED in QEMU**: SweetCPU uses legacy IOCPU, validates single boot CPU, ml_processor_register -> processor_start -> initCPU real SGI1 -> scheduler/IOKit completion -> ml_set_max_cpus. It does NOT force a flag or skip a wait. CPU APIs passed: Running CPU0, processor_array[0] association, SGI signalling enabled, name, unsupported secondary-start error (`research/check-cpu18.gdb` / `.log`, `research/q0018-api`). Single-core only; SMP and suspend unsupported. Two-CPU topology fails explicitly (`research/q0018-smp`).
- **Next blocker reproduced in 45s QEMU** (`research/q0018-long`, zero unknown glyphs): BSD initialization reaches MAC framework, network mcache and `mbinit: done`, then **`pthread kernel extension not loaded (function table is NULL). @pthread_shims.c:318`**. Do not bypass pthread_init: find/integrate the matching open-source libpthread kernel implementation and register its real function table. A 12s run `research/q0018` looked panic-free before the 30s IORTC wait elapsed; use >=45s or GDB checkpoints for the next iteration. No userland/root filesystem boot yet.
- **Phone 0018 TEMPORARILY BOOTED** 2026-10-15 **15:31:15 UTC**: exactly one FASTBOOT device verified product sweet; send OKAY0.400s, boot OKAY0.134s, total0.539s, exit0. Local log `research/boot0018.log`. This confirms bootloader acceptance only. User was asked for a photo; await it, DO NOT reboot the phone again before their observation. No flashing performed.
- Current hardware image `shim/out/shim-boot-0018.img`, **16,437,248 bytes**, SHA256 **`b7a23595d143a76c72c9fe2cfcc5d77a8f16987b5af1a2703bbffdfa6922908c`**. Phone ADT/payload `shim/out/sweet-0018.adt` / `shim/out/payload-0018.bin` (timer19), unpacked ramdisk exactly matches payload (`shim/out/check-0018`). EntryPA0xb146b488; kernelendPA0xb1ffc000; boot_argsPA0xb2000000/top0xb2004000. Command line `debug=0xc serial=3 cpus=1 keepsyms=1 -enable_kprintf_spam -noprogress`.
- QEMU payload/ADT `research/q0018.bin` / `research/q0018.adt` (timer27). Run `python3 tools/qemu-sweet.py research/q0018.bin research/NEW-OUT --secs 45 --kernel xnu/out-0018/kernel.development.sweet --fail-on-panic`; fresh ADT seed for a new payload. Output fb.png/fb.txt/regs.txt/qemu.log/result.json. Visible panic exit2; blank/incomplete decode exit3; no_panic_observed is snapshot-only, not successful boot. -noprogress prevents the graphical indicator corrupting console text. Qualcomm XPU/bootloader/panel and SMC PSCI still need physical validation.
- Patches0014-0017 fixed PRNG registration/direct SHA256, explicit unavailable trust-cache service with rejected loads/no matches, built-in SweetPlatformExpert, and timer PPI from ADT (phone19/default19, QEMU27). All their checks/artifacts are preserved in the history below. CURRENT SWEET has NO USE_APPLEARMSMP; do not assume gCPUIC/gAIC/gPMGR AppleARMSMP globals exist.
- Local single-file checker: tools/xnu-cc.py research/run22.log research/bt22 FILTER --per-file, output via XNU_CC_OBJDIR. Patch checker `research/check-patch-order.py` applies all18 via temporary index, matches sandbox sources. Sandbox for0018 `research/bt21/xnu`, originals `research/pre0018`, objects `research/cpu-objs`. First compiler issues were missing machine/atomic.h and nonexistent getNameSymbol; fixed and both TUs compiled successfully before CI. Fixtures/artifacts under research are local-only/ignored.
- GDB: mask int(register)&((1<<64)-1) for unsigned kernel pointers; use function-entry manual-call return traps, discard manipulated guests. No QEMU fixture is intentionally left running.

### Earlier active handoff snapshot (superseded)


- **0018 milestone:** Actions `38760004398` PASSED (3m56s), checksums passed, new CPU/build files byte-match CI tree. Kernel `xnu/out-0018/kernel.development.sweet`, SHA256 `b3c8d59acc88f93a2c836eb2527a05ed4fbaac7c580a2ea8c3b795137f4aadf1`; log/tree `research/run22.log` / `research/bt22`. QEMU `research/q0018` 12s: boot CPU registered, SGI1 verified, CPU initialization complete, **BSD initialization entered** (copyright, MAC framework, buffer headers), no panic/zero unknown glyphs. Direct CPU API checks PASS (`research/check-cpu18.gdb`, `.log`, `research/q0018-api`): CPU0 Running, processor matches processor_array[0], real SGI enabled, CPU name correct, secondary-start returns KERN_NOT_SUPPORTED. Two-CPU ADT correctly panics before registration (`research/q0018-smp`). Longer 45s run `research/q0018-long` still running; next BSD wait/fault not yet identified.
- **Prepared 0018 phone image:** `shim/out/shim-boot-0018.img`, 16,437,248 bytes, SHA256 `b7a23595d143a76c72c9fe2cfcc5d77a8f16987b5af1a2703bbffdfa6922908c`. Phone ADT/payload `shim/out/sweet-0018.adt` / `shim/out/payload-0018.bin`, usual debug args with cpus=1 and -noprogress. Unpacked ramdisk byte-compared (`shim/out/check-0018`). Entry PA remains 0xb146b488; kernel end PA 0xb1ffc000, boot_args 0xb2000000/top0xb2004000. User reports FASTBOOT+USB ready; read-only check found exactly one product sweet. NEXT: temporary fastboot boot of this verified image, record send/boot results, then await hardware photo without rebooting again.
- Patch 0018 committed/pushed **`e7d9550`**; Actions **`38760004398`** queued/running: https://github.com/dipa-studio/ios-sweet/actions/runs/38760004398. Do not launch a duplicate run.
- Active continuation: patch **0018** implemented in `iokit/Kernel/arm/SweetCPU.cpp` + arm64 source list + exact qcom,kryo470 personality. Keeps legacy IOCPU, accepts ONLY the single boot CPU, fills ml_processor_info from parsed topology with CPU object as cpu_id, calls ml_processor_register and processor_start. initCPU sends SGI1 via ICC_SGI1R_EL1 and waits (1-second deadline) for real cpu_signal_handler to clear SIGPdisabled. Only after successful startup calls ml_cpu_init_completed/cpusRunning and publishes completion/max CPUs. Secondary startup/suspend are explicitly unsupported. Local C++ compile passed for both TUs (`research/cpu-objs`), all imports resolve, object contains dsb ishst / ICC_SGI1R / isb; all18 patches apply in order and match sources. Sandbox `research/bt21/xnu`, originals `research/pre0018`; next CI artifacts should use `xnu/out-0018`, `research/bt22`, `research/run22.log`. User has the phone available; first run QEMU, then prepare/temporarily boot useful hardware progress.
- Goal: iOS 16 generation XNU on Redmi Note 10 Pro / sweet. User wants persistent progress, commits, kernel builds via `gh` Actions, and this handoff kept current across agent switches. Temporary `fastboot boot` only; preserve Android and backups.
- Latest kernel implementation: **`aa3f991`**, patches **0001-0017**. All four new Actions builds PASSED: 0014 `38748543058` (4m0s), 0015 `38749549779` (4m3s), 0016 `38750733996` (4m3s), 0017 **`38751507437` (4m7s)**. Latest: https://github.com/dipa-studio/ios-sweet/actions/runs/38751507437. No build is pending.
- **Current blocker: CPU initialization has no SWEET CPU driver.** QEMU registers SweetPlatformExpert, then kernel_bootstrap_thread waits in **kperf_init_early -> ml_wait_max_cpus**. Confirmed via actual-kernel GDB call stack (`research/locate-cpu-wait2.log` / `.symbols`) and normal-run `max_cpus_initialized == 2` (MAX_CPUS_WAIT). Do not force the flag or remove the wait. Next implement real CPU registration and completion using XNU's CPU/processor interfaces. CURRENT SWEET uses legacy IOCPU (`USE_APPLEARMSMP` is absent); enabling AppleARMSMP is a separate architectural change requiring GIC/PMGR services. No userland/root filesystem boot yet.
- Fixed this session: PC=0 unregistered PRNG callback (0014, built-in HMAC-SHA256 provider + direct entropy/write_random hashing); absent Image4/AMFI trust-cache service (0015, unavailable runtime, loads rejected and queries no-match); missing platform driver (0016, SweetPlatformExpert exact personality); incorrect QEMU timer IRQ (0017, validated ADT PPI property, phone default19/QEMU27).
- **Latest kernel** `xnu/out-0017/kernel.development.sweet`, SHA256 `055a80190ab998b4df9203f1102072dcc78faad1779a537a514e522b682b582f`. Buildtree/log **`research/bt21` / `research/run21.log`**; all nine changed C/C++/header/config files byte-match local checked sources. Checksums passed. Entry PA `0xb146b488`, kernel end PA `0xb1ff4000`. Preferred baseline for patch 0018: `research/bt21/xnu` (no nested .git).
- **QEMU verified**: `research/q0017-noprogress` ran **30 seconds**, no visible panic, **zero unknown glyphs**, IRQ exceptions returned normally (4 IRQs, tickless idle). It still waits for CPU completion, so this is NOT a completed boot. Earlier 15s run `research/q0017` captured 122 IRQs, timer value27, GICR_ISENABLER0 `0x08000002`, and CPU WAIT; graphical progress overlay corrupted 13 glyphs. Add **`-noprogress`** to keep the console readable. New runner classifies incomplete/blank decoding explicitly (exit3 with --fail-on-panic), visible panic exits2. Snapshot-only; use regs/GDB to diagnose stalls.
- Current QEMU payload/ADT: **`research/q0017-noprogress.bin` / `research/q0017.adt`**. Run: `python3 tools/qemu-sweet.py research/q0017-noprogress.bin research/NEW-OUT --secs 30 --kernel xnu/out-0017/kernel.development.sweet --fail-on-panic`. Generate fresh seed with mkadt for a new payload. QEMU virt models generic ARM execution, not Qualcomm XPU/bootloader/panel or the phone's SMC PSCI conduit.
- **Prepared phone image**: **`shim/out/shim-boot-0017.img`**, 16,416,768 bytes, SHA256 `51ff7fe30b4a6668c3452ffe1da922c5ac30cb8de60625c2a652587ecbd0ec92`. Phone ADT/payload `shim/out/sweet-0017.adt` / `shim/out/payload-0017.bin` (timer19). Unpacked ramdisk exactly matches payload (`shim/out/check-0017`). Command line **`debug=0xc serial=3 cpus=1 keepsyms=1 -enable_kprintf_spam -noprogress`**. NOT sent to phone this session: known CPU-driver wait should be addressed in QEMU first. Last actual phone boot remains 0013; user's latest photo `IMG_20261015_160033.jpg` confirmed the old PRNG PC=0 panic.
- Direct QEMU/GDB API checks: PRNG 600-byte chunking, buffer bounds, changing output, zero-length reads/writes, user reseed, contended refresh, generator1 init/output PASS again on latest0017 (`research/check-prng17.gdb` / `.log`, guest `research/q0017-api`). Trust-cache unavailable-service/argument/output cases PASS on0015 (`research/check-trustcache.gdb` / `.log`). Platform registration + target/product normal/truncated/zero/null/bounds PASS on0016 (`research/check-platform.gdb`, `research/check-platform3.log`). Different platform ID correctly retains IOPanicPlatform fallback (`research/q0016-negative`). Timer PPI32 and size2 correctly panic (`research/q0017-badppi`, `research/q0017-badsize`); omitted property selects19 (`research/q0017-default`). These are API/bring-up checks, not crypto certification or SMP scheduling validation.
- Local checker **`research/check-patch-order.py`** verifies all17 patches and changed source equality using a temporary upstream git index. Fixtures/logs/artifacts under research are local-only and ignored. For GDB unsigned kernel pointers, mask `int(register_value) & ((1<<64)-1)`; x30/x29 may be rendered signed. Stop at a function entry for manual-call return traps, and discard each manipulated guest after API tests. All fixture QEMU guests have been stopped.


- User wants persistent progress toward iOS 16, commits for completed changes, builds through `gh` / GitHub Actions.
- Keep this file current at every milestone so another agent can resume immediately, including when usage limits interrupt a session.
- Patch 0017 committed/pushed `aa3f991`, Actions `38751507437` running: https://github.com/dipa-studio/ios-sweet/actions/runs/38751507437. Next artifacts: xnu/out-0017, research/bt21, research/run21.log. Do not duplicate.
- Patch 0016 kernel downloaded/checksum verified: SHA256 `d06336c54baa06e0df6561a8bd7df98a9b9f7502c9381c62d1a44c045cd1ce46`, `xnu/out-0016/kernel.development.sweet`; buildtree/log `research/bt20` / `research/run20.log`. QEMU `research/q0016` (10s) prints platform expert registered, zero unknown glyphs, no panic observed BUT stalls (timer mapping still wrong until 0017). Direct actual-kernel GDB tests passed for registered instance and target/product names, including maxLength=1/0 and NULL, sentinels intact (`research/check-platform.gdb`, `research/check-platform3.log`, `research/q0016-api3`). First two fixture attempts used premature/wrong return breakpoints; discarded, corrected fixture uses start-return observation then a function-entry return trap. No phone boot yet.
- Patch 0016 CI `38750733996` PASSED (4m3s); artifacts not yet downloaded/booted. Patch 0017 prepared to fix QEMU timer fidelity BEFORE interpreting future no-panic/stall runs: actual `qemu-system-aarch64 -M virt,gic-version=3,dumpdtb=research/qemu-virt.dtb ...` timer property has virtual PPI 11 => INTID 27, while phone uses INTID 19. Kernel formerly hardcoded 19. New optional /arm-io/gic virtual-timer-intid property selects the PPI (validate exact u32 and 16..31); missing property retains phone default 19. One RO-late global drives GIC enable and sleh_irq dispatch. tools/mkadt.py emits phone19/QEMU27. Both C TUs compile (`research/timer-objs`), ADT serialize/parse checks confirm values/addresses, all 17 patches apply and match. Sandbox `research/bt19/xnu`, originals `research/pre0017`; initial local sleh compile failed due read-only exported header not updated, fixed export and BOTH recompiled successfully. CI exports normally.
- Architecture correction for next agent: CURRENT SWEET board_config does NOT define USE_APPLEARMSMP; it compiles the legacy IOCPU path, not cpu_boot_thread/IOPMGR AppleARMSMP. Existing roadmap mentions AppleARMSMP as a future approach. Do not look for gCPUIC/gAIC/gPMGR globals in the current kernel: they are absent. Determine the actual CPU-init wait after platform registration before choosing the next driver architecture.
- Patch 0016 committed/pushed as `0dcdf5c`; Actions `38750733996` running: https://github.com/dipa-studio/ios-sweet/actions/runs/38750733996. Next artifacts: `xnu/out-0016`, `research/bt20`, `research/run20.log`.
- Patch 0016 implemented: new `iokit/Kernel/arm/SweetPlatformExpert.cpp`, arm64 source list, built-in personality in KernelConfigTables.cpp guarded by ARM64_BOARD_CONFIG_SWEET. Matches only xiaomi,sweet at score 10000, keeps IOPanicPlatform fallback for other hardware. Uses IODTPlatformExpert base initialization/power domain and createNubs CPU logical-ID annotation; overrides top-level publishing because base requires nonexistent Apple NVRAM /options. Publishes real CPU/top-level nodes, provides bounded target/product names, and registers the platform service. GIC/PMGR and arm-io child-bus drivers remain separate work. Both C++ TUs compile (`research/platform-objs`), all imports resolve against 0015/own objects, all 16 patches apply and sources match. Sandbox `research/bt19/xnu`; originals `research/pre0016`. NEXT: full Actions/QEMU; inspect CPU boot waits after the platform registers, do not equate absence of panic with successful boot.
- Patch 0015 CI `38749549779` PASSED (4m3s), checksum verified. Kernel `xnu/out-0015/kernel.development.sweet`, SHA256 `ca1b424a596c7058550ad1659080a333e7643270f019656401d80bf2b876645f`; buildtree/log `research/bt19` / `research/run19.log`. QEMU `research/q0015` (10s, zero unknown glyphs) passes trust-cache handling and machine lockdown, then panics `Unable to find driver for this platform: "xiaomi,sweet" @IOPlatformExpert.cpp:2319` (IOPanicPlatform fallback). Next concrete work: add a built-in SWEET IODTPlatformExpert personality/class; keep the fallback for mismatched platforms. No phone boot yet.
- Direct trust-cache API checks PASSED in the actual 0015 kernel under QEMU/GDB (`research/check-trustcache.gdb`, `research/check-trustcache.log`, `research/q0015-api`): runtime pointers NULL, hash/UUID queries return NOT_FOUND, typed/untyped/legacy loads return NOT_SUPPORTED, capabilities outputs zero and bounds preserved, invalid-argument cases still reject. Second PRNG check also verifies contended refresh returns immediately (`research/check-prng2.log`, `research/q0014-api2`).
- Patch 0015 committed/pushed `8f851d4`, Actions run `38749549779` running: https://github.com/dipa-studio/ios-sweet/actions/runs/38749549779. Do not duplicate.
- Direct PRNG API checks passed in the REAL 0014 kernel under QEMU/GDB, stopped before trust-cache init (`research/check-prng.gdb`, log `research/check-prng.log`, guest `research/q0014-api`). Invoked read_random for 600 bytes (chunking and buffer sentinel intact), repeated output differed, zero-length read/write succeeded, write_random(64-byte input) succeeded, secondary generator 1 initialized and generated distinct output. QEMU log has no exceptions during these checks; guest was discarded after the tests. This tests API behavior, not a cryptographic certification or SMP scheduling.
- Patch 0015 implemented in `bsd/kern/kern_trustcache.c`: SWEET with missing Image4/AMFI marks both runtime pointers NULL and logs service unavailability. Existing static loader handles NULL. Public load APIs return KERN_NOT_SUPPORTED; hash/UUID queries return KERN_NOT_FOUND; capabilities outputs are zero with KERN_NOT_SUPPORTED. Invalid-input checks remain, and Apple paths/available-provider initialization retain existing behavior. No trust is granted. Local arm64 compile passed (`research/trustcache-objs`), all 15 patches apply and sources match. Sandbox `research/bt18/xnu`, baseline `research/pre0015`. Next: Actions/QEMU and direct unavailable-service API checks using GDB.
- Patch 0014 CI `38748543058` PASSED (4m0s), artifact checksum passed. Kernel `xnu/out-0014/kernel.development.sweet`, SHA256 `741de20c851755d333759d7e668346f3edb4f325efac4cc7c142d80d1f5ff75c`; buildtree/log `research/bt18` / `research/run18.log`. QEMU run `research/q0014` (10s, zero unknown glyphs) prints `SWEET PRNG: HMAC-SHA256 registered`, passes commpage initialization, loads vnguard policy, THEN panics `image4 interface not available @kern_trustcache.c:253`. PC=0 fault FIXED IN QEMU. No new phone boot performed.
- Next work: SWEET currently has neither AppleImage4 nor AMFI. `trust_cache_runtime_init` unconditionally requires both; unlike BCM2837, SWEET enters this startup path. Investigate an explicitly unavailable trust-cache runtime with rejected loads/no query matches while providers are absent; preserve all Apple-platform checks. Merely skipping the startup call would leave later AMFI/IMG4 dereferences unsafe. Existing load_static_trust_cache already handles trust_cache_rt == NULL.
- QEMU runner now supports `--kernel MATCHING_KERNEL --fail-on-panic`: runtime font extraction from the payload produces exact `fb.txt`, plus `result.json`; a visible panic returns 2. Baseline 0013 re-run `research/q0013-text` detects the same NULL callback panic with zero unknown glyphs. Synthetic glyph roundtrip (including literal `?`) and invalid-VA rejection passed. Screen rows remain circular, not a full log; `no_panic_observed` does not prove successful boot. README has the invocation.
- Patch 0014 committed/pushed as `be61f99`; Actions run `38748543058` is running: https://github.com/dipa-studio/ios-sweet/actions/runs/38748543058. Do not start a duplicate build.
- 2026-10-15 active: hardware photo `IMG_20261015_160033.jpg` confirms the same PC=0 instruction-fetch abort as QEMU (LR `0xfffffe0007443fe4` = read_random). Independently reproduced with kernel 0013 in `research/q0013` (8-second run); prior allocator fix works. Latest tooling commit reviewed: `8d66d2d`.
- Patch 0014 implemented: registers a built-in HMAC-SHA256 DRBG provider at EARLY_BOOT/FIRST, before commpage creation. A shared mutex serializes output/reseed across CPUs (correctness first; no per-CPU scaling yet), initgen validates CPU identities, refresh uses try-lock and the existing entropy filter/health tests. SWEET entropy accumulation and write_random now use the built-in SHA256 directly; no incomplete g_crypto_funcs table is registered. The existing bootloader-seed requirement remains enforced.
- Local validation: both PRNG translation units compile to arm64 objects in `research/prng-objs`; no SHA256 wrapper imports remain. All 14 patches apply in CI order and resulting PRNG sources match local inputs. Sandbox `research/bt17/xnu`, originals `research/pre0014`, checker `research/check-patch-order.py`. NEXT: Actions kernel build, download to `xnu/out-0014`, run the QEMU payload before requesting another phone boot. Baseline QEMU ADT/payload are `research/q0013.adt` / `research/q0013.bin`.
- 2026-10-15 08:15 QEMU EMULATION WORKS (`tools/qemu-sweet.py`, see "QEMU emulation" below). Patch 0013 VERIFIED in QEMU: boot passes kmem_crypto_init and ulock_initialize. NEXT BLOCKER (reproduced in QEMU, expected on hardware too): `pmap_create_commpages -> random() -> RandomULong -> read_random -> prng_funcs.refresh == NULL` (instruction fetch abort at pc 0, lr read_random+0x34). Nobody calls `register_and_init_prng` (closed corecrypto kext does it on Apple). Fix = patch 0014: SWEET-registered cckprng_funcs provider (osfmk/prng/prng_random.c); note random_cpu_init also panics while !prng_ready. The 07:26 hardware boot of 0013 will most likely show this same panic.
- Previous hardware boot: patch 0013 (`a3a46e2`) CI `38686345689` PASSED (3m44s), image `shim/out/shim-boot-0013.img` was temporarily booted on 2026-10-15 at 05:26 UTC: send OKAY (0.407s), boot OKAY (0.134s), total 0.546s. Superseded by the hardware/QEMU PC=0 observation and patch 0014 work above.
- Latest kernel implementation commit: `8f851d4`. Latest successful kernel CI: `38749549779` (patch 0015), https://github.com/dipa-studio/ios-sweet/actions/runs/38749549779.
- CURRENT image: `shim/out/shim-boot-0013.img`, 16,412,672 bytes, SHA256 `110d1c46aee4b60253db24b6535e9781c4cf0fd25ca2a70e9016cf81378cea25`. Kernel `xnu/out-0013/kernel.development.sweet`, SHA256 `f0b1d375995316c550ce7014ff234d8271e9b9ac2857795ceff41b76ba2cd740`, plain arm64. CI log confirms 0013 applied; checksums passed. Entry PA `0xb146b488`, kernel end PA `0xb1ff4000`.
- Current log/buildtree: `research/run17.log`, `research/bt17` (extracted, no nested .git; preferred baseline for patch 0014). Payload/ADT: `shim/out/payload-0013.bin`, `shim/out/sweet-0013.adt` (includes /defaults). Unpacked ramdisk byte-compared with payload in `shim/out/check-0013`.
- Patch-0012 original image: `shim/out/shim-boot-0012.img`, 16,412,672 bytes, SHA256 `cf4b8ec4a65a51888d71c17d09cd0831d6b761b90e2531fdb8e575c32f4fd24a`. Kernel `xnu/out-0012/kernel.development.sweet`, SHA256 `69b78f49f6459cc63a0af44e7cf73c1779ef72130ef72b12ae86c88183ffc742`; checksums passed and sweet_early_relocate symbol present. Entry PA remains `0xb146b488`, kernel end PA `0xb1ff4000`.
- Patch-0012 log/tree: `research/run16.log`, `research/bt16` (extracted, no nested .git; preferred baseline for next patch). CI log confirms 0012 applied. Payload `shim/out/payload-0012.bin`, ADT `shim/out/sweet-0012.adt`; packed ramdisk byte-compared with payload in `shim/out/check-0012`.
- Active payload command line: `debug=0xc serial=3 cpus=1 keepsyms=1 -enable_kprintf_spam`.
- Latest observed photo: `/home/dipa/Downloads/IMG_20261015_071346.jpg` (local only). Stages 9 (kernel framebuffer VA), 10 (TTBR0 off/TLB flush), 11 (physmap table pointers) and 12 (calling pmap_bootstrap) all visible. Persistent diagnostics are VERIFIED ON HARDWARE.
- pmap.c:1987 is the assert after SecureDTLookupEntry(NULL, "/defaults", &entry). The pmap-max-asids property itself is optional; an empty /defaults uses XNU's MAX_ASIDS. Do not bypass the assertion or guess an ASID limit.
- Previous payload-only fix image: `shim/out/shim-boot-0012-defaults.img`, SHA256 `3ff61a268853c6ea7cbf284833f1346a1d791980ca366b6e1a215a86e040512b` (16,412,672 bytes). Same kernel/CI as 0012; ADT 2516 bytes (`shim/out/sweet-0012-defaults.adt`), root /defaults present with no ASID override. Payload `shim/out/payload-0012-defaults.bin`; unpacked ramdisk exactly matches payload (`shim/out/check-0012-defaults`). This boot reached the allocator crypto NULL-pointer fault below.
- Latest hardware photo: `/home/dipa/Downloads/IMG_20261015_071608.jpg` (local only). Normal serial framebuffer console works. VM bootstrap/zone initialization, logging, scheduler, IPC, KDP and ulock_initialize print before the kmem_crypto_init data abort. gPanicBase warnings are expected because PLATFORM_PANIC_LOG_DISABLED is configured, and are not the faulting call.
- Faulting instruction: `ldr x0, [x8, #0x150]` in crypto_random_kmem_ctx_size; x8 = NULL g_crypto_funcs. Source: libkern/crypto/corecrypto_rand.c and osfmk/vm/vm_kern.c:2448. rand.h explicitly permits NON-cryptographic kmem RNGs, but requires no locking in generation and context size <=256. Do not substitute read_random here: the global PRNG provider is also unregistered and kmem generation must remain lock-free. early_random may seed contexts during single-CPU bootstrap; it uses the built-in HMAC-SHA256 DRBG with the host-generated ADT seed.
- Patch 0013 keeps the replacement entirely private to vm_kern.c: SplitMix64 state is 8 bytes per CPU/sizeclass, initialized using early_random. Uniform selection uses rejection sampling to avoid modulo bias. Other platforms retain the original corecrypto calls; SWEET's generic crypto APIs/registration remain untouched. Reference: https://prng.di.unimi.it/splitmix64.c (Sebastiano Vigna, public domain).
- Validation: vm_kern.c compiles to arm64 (`research/kmem-rng-objs`, using `research/run16.log` + `research/bt16`). Undefined symbols include early_random and NO crypto_random_* references. All 13 patches apply in CI order and match the checked source. Original saved as `research/vm_kern.pre0013.c`.
- RNG host checks: extracted actual new helper in `research/kmem-rng-check.c`; 16,384 outputs match the author's downloaded reference (`research/splitmix64-reference.c`), 147,456 bounded outputs satisfy their limits (including 1 and UINT64_MAX), and a forced rejection advances correctly. Full kernel crypto services and the registered kernel PRNG provider remain future work; this patch only supplies the allocator RNG contract.
- Patch-0011 artifacts: kernel `xnu/out-0011/kernel.development.sweet`, log `research/run15.log`, extracted buildtree `research/bt15` (no nested .git). CI log confirms patch 0011 applied; artifact checksums passed. Kernel is plain arm64, entry VA `0xfffffe000746b488` -> PA `0xb146b488`, kernel end PA still `0xb1ff4000`.
- Patch-0011 image: 16,412,672 bytes, SHA256 `29ad5cbfc752473de4af2c471a24a8b34f92da4bff5afec65c614b90cd3ad53a`. Kernel SHA256 `8ac3a956894b09f7bd0d890de8c5de38c65513287feb1e1bcd12db8ca772ee5c`. Payload/ADT in `shim/out/payload-0011.bin`, `shim/out/sweet-0011.adt`. Header unpacked/checked in `shim/out/check-0011`.
- First patch-0011 attempt timed out waiting for FASTBOOT; superseded by the successful send/boot recorded above. Do not repeat the boot before the user reports the current screen.
- Patch-0011 photo: `/home/dipa/Downloads/IMG_20261015_070218.jpg` (local only). Visible stages 1-8 and old red shim text; entry PA B146B488, boot args PA B1FF8000 / top B1FFC000. No evidence yet locating execution after stage 8.
- Patch-0012 sandbox: `research/bt15/xnu` (NO nested .git). Proposed permanent debug VA: VM_MIN_KERNEL_ADDRESS + ARM_TT_L2_SIZE, in the reserved gap below gVirtBase and above low globals; map the same PA framebuffer as Normal-NC in the final TTBR1 before arm_vm_physmap_init changes phystokv(). Keep the early panic sink until normal kprintf startup.
- Patch 0012 validation: all 4 changed C translation units compiled to arm64 objects in `research/post-ttbr0-objs`; internal header export added to osfmk/arm64/Makefile and recreated locally in EXPORT_HDRS for pe_serial.c. All 12 patches apply in CI order and match all 6 edited files. Baselines are saved under `research/pre0012/`.
- Actual mapping-helper host model (`research/early-map-check.c`, barrier stubbed only for host compilation) confirms: VA `0xfffffe0002000000`, L1 index 2016, L2 index 1; descriptor `0x006000009c000605` = framebuffer PA, Normal-NC, outer-shareable, EL1 RW, PXN+UXN. All other L2 entries preserved. The gap is excluded by ARM_LARGE_MEMORY's pmap_virtual_region(0).
- Next boot command line MUST add `-enable_kprintf_spam`: DEVELOPMENT disables kprintf_output by default even when DB_KPRT is set (`pexpert/arm/pe_kprintf.c`). Planned command line: `debug=0xc serial=3 cpus=1 keepsyms=1 -enable_kprintf_spam`.

### Patch 0012 screen legend (after original stages 1-8)
- 9: kernel framebuffer VA live; 10: TTBR0 off / TLB flushed; 11: physmap pointers rebound.
- 12: calling pmap_bootstrap; 13: pmap_bootstrap returned; 14: early I/O page tables ready; 15: arm_vm_init returned.
- 16: calling serial_init; 17: fbcon config read / mapping; 18: fbcon mapping returned; 19: serial_init returned; 20: kprintf startup complete.
- Normal serial initialization clears the screen, so earlier stages may disappear before 19. If serial exists, early console disables after 20; otherwise early panic output stays enabled.
- Local source sandbox: `research/bt13/xnu` (git baseline `623b060`, patches 0001-0008 already in baseline; uncommitted export edits correspond to patch 0009). Preserve those edits when producing patch 0010.
- Previous compile log/tree: `research/run13.log`, `research/bt13`; previous kernel: `xnu/out/kernel.development.sweet`. New successful log/tree: `research/run14.log`, `research/bt14`; new kernel: `xnu/out-0010/kernel.development.sweet`.
- Current device access: patch-0012 image was temporarily started from FASTBOOT; no adb connection is expected. Never flash partitions for bring-up; use `fastboot boot` with the shim image.
- Patch `0010` lives in `xnu/patches/0010-sweet-early-framebuffer-debug.patch`. Its exact compiled sources are under `research/bt13/xnu`; generated objects are in `research/early-objs`.
- Local checks passed: all 5 changed/new translation units compiled to arm64 Mach-O objects; new console only imports `_doprnt` and `iso_font` (both exist in the previous kernel). All 10 patches applied to a temporary upstream git index in CI order, and all 7 resulting changed source files matched the local compile inputs.
- Reproduce changed-file compilation: `XNU_CC_OBJDIR="$PWD/research/early-objs" python3 tools/xnu-cc.py research/run13.log research/bt13 arm_init.c arm_vm_init.c kern/debug.c arm64/start.s osfmk/arm64/sweet_early.c --per-file` (create the output directory first). The helper now accepts explicit new source paths absent from the old artifact's Makefiles and rejects empty selections.
- Device command result: `adb reboot bootloader`, then `timeout 30s fastboot boot shim/out/shim-boot-0010.img`: send OKAY (16028 KB), boot OKAY, total 0.541s. This confirms bootloader acceptance only, not XNU progress.
- The successful boot above was on 2026-10-14. On 2026-10-15, `timeout 45s fastboot boot ...` timed out waiting for a device; no image was sent. Boot image SHA256 rechecked and unchanged. No new build is needed to repeat the trial.
- Earlier retry: `timeout 90s fastboot boot shim/out/shim-boot-0010.img` timed out (exit 124). This is superseded by the successful 2026-10-15 repeat boot recorded above; do not repeat it until the user reports the screen.
- User observation confirms MMU-on C entry, platform expert, CPU topology/bootstrap, startup bootstrap and cpu_init all complete. Failure is within arm_vm_physmap_init (non-XNU_MONITOR branch), before stage 8 / TTBR0 teardown. Old red shim text remains behind the early console; this is expected because only written rows are cleared.
- New edit/compile sandbox is `research/bt14/xnu` (extracted artifact, NO nested .git; `git diff` there would act on the parent project). Use a saved baseline file / generated unified diff, or explicitly initialize a local baseline before editing. `research/bt13/xnu` does have its own baseline git repo.
- Exact user-reported panic: `arm_vm_init.c:1606 Assertion failed: (temp_ptov_table[ptov_index - 1].va + temp_ptov_table[ptov_index - 1].len) <= physmap_end`.
- Root cause: MacOSX build sets `ARM_LARGE_MEMORY=1`; `XNU_MONITOR` is off. Block alignment in arm_vm_physmap_slide can add gaps, but the non-PPL large-memory physmap_end omitted the padding already present in the small-memory branch. Patch 0011 reserves PTOV_TABLE_SIZE*ARM_TT_TWIG_SIZE (8*32MB) in both the aperture bound and its L1 allocation; monitor/PPL builds retain zero padding. The assertion is preserved.
- Validation: `arm_vm_init.c` compiled to an arm64 object using `research/run14.log` + `research/bt14` (object in `research/physmap-objs`). All 11 patches apply in CI order and produce exactly that source. Host harness `research/physmap-check.c` extracts the real XNU slide function with page-table-write stubs: all 65,536 page-aligned slides within 1GB checked against the current kernel memory layout; old bound fails 65,504 cases, padded bound fails zero; worst overrun 0x1ffc000 bytes. Baseline source saved as `research/arm_vm_init.pre0011.c`.
- CI: https://github.com/dipa-studio/ios-sweet/actions/runs/38638702083 (success; artifacts and full log downloaded).
- New image: `shim/out/shim-boot-0010.img` (16,412,672 bytes, SHA256 `ed2c270e0081bad5ff517be415f9bfe8805463aea7866732203fa97ac737e64e`). Previous image preserved as `shim/out/shim-boot-pre0010.img`.
- New kernel SHA256: `3ee05270cc291c49589a101678f904b1b69cb2f2575e05398bce8a4e052f409a`. Artifact checksums passed; arm64 (not arm64e), early-console symbols present. Payload entry VA `0xfffffe000746a488` -> PA `0xb146a488`; kernel end PA `0xb1ff4000`. Command line remains `debug=0xc serial=3 cpus=1 keepsyms=1`.

### Patch 0010 screen legend
- Bottom-left white 64x32 tile: assembly entered `start_first_cpu`, before page tables/MMU.
- Text `SWEET EARLY 1`: entered `arm_init` with MMU on; 2: platform expert done; 3: CPU topology done; 4: CPU bootstrap done; 5: startup bootstrap done; 6: CPU init done; 7: entering `arm_vm_init`; 8: leaving bootstrap TTBR0.
- `SWEET EARLY PANIC:` prints a copy of panic arguments before normal panic handling needs per-CPU/thread state.
- In patches 0010/0011 the console disabled before TTBR0 invalidation; patch 0012 replaces that with a persistent kernel VA alias and diagnostics through normal serial/kprintf startup (see its legend above).
- Screen contents require a physical observation from the user: adb cannot capture a framebuffer after Android has been replaced by a bare-metal kernel.

## QEMU emulation (2026-10-15)
- `tools/mkadt.py OUT.adt --qemu` = same ADT with QEMU virt GICD 0x08000000 / GICR 0x080a0000 / CNTFRQ 62.5 MHz.
- `tools/qemu-sweet.py PAYLOAD OUTDIR [--secs N] [--hmp "x /8gx ADDR"] [--gdb]`: host-side copy of shim/loader.c
  (segments + ADT + boot_args at their PAs, 6-instruction stub sets x0 and jumps), `-M virt,gic-version=3 -cpu cortex-a76`
  (same ID_AA64MMFR0 as Kryo 470), 4G RAM so 0x9c000000 fb and 0xb0000000 kernel are plain RAM.
  Outputs `fb.png` (the screen), `regs.txt`, `qemu.log` (exceptions with ESR/FAR/ELR). `--gdb` halts with a stub on :1234
  (system `gdb` + `set architecture aarch64`, `hbreak *VA` works with the MMU on).
- Not emulated: Qualcomm XPUs, ABL, real panel, PSCI conduit (QEMU virt uses hvc). Hardware still decides those.
- Example: `python3 tools/mkadt.py /tmp/q.adt --qemu && python3 tools/mkpayload.py xnu/out-0013/kernel.development.sweet /tmp/q.adt /tmp/pq.bin --cmdline 'debug=0xc serial=3 cpus=1 keepsyms=1 -enable_kprintf_spam' && python3 tools/qemu-sweet.py /tmp/pq.bin /tmp/q`

## Layout
- `backup/`  partition dumps + full sdb..sdf LUNs, `SHA256SUMS` (all verified on-device == local)
- `dtb/`     live FDT (from OrangeFox), PixelOS boot.img dtb, dtbo, dts versions
- `shim/`    bare-metal boot shim (`./build.sh` -> `out/shim-boot.img`)
- `research/` mainline sm7150 dts, XNU pe_fiq.c etc, PocketDarwin patches
- `tools/unpack_bootv2.py`

## Device access
- No root in PixelOS 17 (user build, adb root disabled). Root = `fastboot boot recovery/recovery.img` (OrangeFox R12.0_2, temp boot, not flashed).
- `fastboot boot` works for stock boot.img, OrangeFox, and our shim.
- Shim resets itself via PSCI SYSTEM_RESET; IMEM restart_reason 0x77665500 is seen
  (bootreason=bootloader) but ABL still boots Android, so it does not stop in fastboot.

## Hardware facts (live DT + shim measurements)
- Framebuffer (ABL cont splash): 0x9c000000, 1080x2400, stride 4320, a8r8g8b8, panel is DSC *video* mode (no kick needed).
- RAM: 0x80000000+2G, 0x100000000+0xfcc00000. Live reserved-memory = PixelOS base dtb + sweet dtbo fixups.
- GICv3: GICD 0x17a00000, GICR 0x17a60000 (stride 0x20000, 8 PEs). GICD_TYPER 0x007B041D: SecurityExtn=1 (DS=0).
  ABL leaves GICD_CTLR = 0x10 (ARE_NS on, groups off). Writing 0x13 reads back 0x12: EnableGrp1A (bit1) is the one that matters.
- GIC Group 1 VERIFIED (shim 2c): vtimer INTID 19 = 30 IRQs/300ms, ptimer INTID 18 = 30, SGI 1 to self = 10/10.
  ICC_SRE=1 already, ICC_CTLR 0x8440, priority/enable writes stick. GICR_IGROUPR0 and GICD_IGROUPRn read 0 from NS
  even though Group 1 delivery works (RAZ in NS view) - do not use them as a health check.
  INTID 28 shows pending constantly (unknown PPI 12).
- Timer 19.2 MHz. Qualcomm PPI numbering: secure-phys/phys/virt/hyp = PPI 1/2/3/0 -> vtimer INTID 19, ptimer 18 (NOT 27/30).
- PSCI 1.1 via SMC, SMCCC 1.1. CPU_ON ok; SYSTEM_SUSPEND and SYSTEM_RESET2 unsupported.
- SMP: CPU_ON works for all 7 secondaries (MPIDR 0x81000n00).
- Entry EL1, MMU off, x0 = DTB (magic ok). ID_AA64MMFR0 = ...101122: 16K granule YES, 4K YES.
- No serial console: debug UART SE is in SPI mode on sweet. Screen is the only debug channel.

## XNU implications
- XNU GICv3 path (pexpert/arm/pe_fiq.c, VMAPPLE) puts the timer (PPI 27) in Group 0 = FIQ. With SecurityExtn=1,
  Group 0 is secure -> impossible from NS EL1. Need: Group 1 IRQ, ICC_IGRPEN1, INTID 19, and the timer handled in the IRQ path.
- XNU VMAPPLE PSCI uses `hvc`; sweet needs `smc`.
- PocketDarwin NonAppleGenericCpu.patch only swaps -mcpu=apple-h7 for -march=armv8-a.

## Milestone 3 (2026-10-14): 16K MMU verified
- ABL loads the Image at 0x80080000 (base 0x80000000 + 0x80000) regardless of text_offset=0.
- 16K granule, T0SZ=28 (L2 start, 32MB blocks), MAIR 0x44ff00, TCR 0x1409CB51C, PARange=2 (40-bit PA).
- Only own image pages WB (Qualcomm XPUs: never map carve-outs cacheable); fb Normal-NC; rest Device.
- AT S1E1R checks all as expected; unmapped -> translation fault L2.
- Fill fb: 110 ms (MMU off) -> 3.5 ms (NC). Memory loop 70 ms -> 0.7 ms. vtimer + SGI IRQs still fine with MMU on.

## XNU loader design notes (xnu-8796)
- Entry: `_start` -> `start_first_cpu`, x0 = boot_args (PA), MMU off, EL1. boot_args: Revision/Version 2,
  virtBase/physBase/memSize/topOfKernelData, Boot_Video (fb 0x9c000000, rowBytes 4320, 1080x2400, depth 32),
  deviceTreeP/Length (ADT), CommandLine[608], bootFlags, memSizeActual.
- start.s maps [kernel mach header .. physBase+memSize) with cacheable BLOCKS. On Qualcomm every XPU carve-out
  must therefore lie below the kernel: use physBase = 0xb0000000 (above ramdump_fb 0xaf000000+16M,
  cdsp_sec, qseecom), end before rmtfs 0xfde01000 -> memSize ~0x4d000000 for bring-up.
- Base ADT: iPhone 8 d20ap DeviceTree from iOS 16.7.16 IPSW (tools/remotezip.py + tools/adt.py; LZFSE payload).
  Template values are empty: the loader must fill chosen/*, memory-map, cpu*/reg etc. like iBoot.
- XNU build: GitHub Actions (dipa-studio/ios-sweet, xnu.yml) via blacktop/darwin-xnu-build, MACOS_VERSION=13.5.
  New-clang fixes in xnu/patches; Xcode 16 iig is incompatible (IORPC.kernelContent) -> macos-14 runner, oldest Xcode.

## Kernel architecture plan (SWEET machine config)
- First stock build (VMAPPLE) is arm64e (PAC). Kryo 470 = ARMv8.2, no PAC -> SWEET must build plain arm64
  (HAS_APPLE_PAC is only defined for __arm64e__, so arm64 drops PAC automatically).
- Template: VMAPPLE (16K pages, GICv3 code in pe_fiq.c) minus APPLEVIRTUALPLATFORM hypercalls/paravirt PAC,
  plus BCM2837 (generic ARM: no APPLE_ARM64_ARCH_FAMILY Apple sysregs). Do not link the KDK lib<cfg>.os.*.a.
- Timer: XNU expects it on FIQ (sleh_fiq -> rtclock_intr). SWEET: GIC Group 1, so sleh_irq must ack ICC_IAR1,
  route INTID 19 to the same timer path, SGIs to cpu_signal_handler, EOI via ICC_EOIR1.
- SMP/interrupts: open-source AppleARMSMP (USE_APPLEARMSMP) needs an IOInterruptController (AIC role) and an
  IOPMGR (CPU power -> PSCI CPU_ON via SMC). Plan: built-in IOKit classes (SweetGIC, SweetPMGR, platform
  expert) compiled into the kernel and matched via iokit/KernelConfigTables.cpp -> no closed kexts needed.
- Debug: xnu patch 0003 sweet-fbcon = kprintf drawn on the framebuffer (ADT node "sweet-fbcon").
- ADT /arm-io ranges must not map to parent 0 (pe_arm_get_soc_base_phys()==0 disables serial): use parent 0x1000000.

## Status 2026-10-14 late: first XNU boot attempt
- SWEET kernel builds (CI run 38635343732, patches 0001-0009). Verified offline: arm64, no PAC, no >v8.2 code,
  70300 classic relocs all in range (slide 0 = no loader work), entry = __start.
- Boot: shim loader worked (initrd 0x846F0000-0x855FE3E0, BOOTARG 0xB1FF8000, JUMP 0xB146A488) but screen stayed
  red -> xnu died/hung before serial_init (fbcon). kprintf is a no-op before STARTUP_SUB_KPRINTF.
- Historical next-step plan (patch 0010, now implemented and built; see active handoff above): early fb debug channel
  1. start.s start_first_cpu (after mov x20,x0 / mov x21,#0): PA marker band (MMU off, direct store to 0x9c000000).
  2. start.s after both create_bootstrap_mapping calls: add ONE block entry to the existing V=P L2 table
     (x25 + 2*PGBYTES; do NOT call create_bootstrap_mapping again: fb and RAM share L1 entry 0, it would replace
     the L2 table). Entry = TYPE_BLOCK|VALID|SH(OUTER)|ATTRINDX(CACHE_ATTRINDX_WRITECOMB=1)|AF|PNX|NX|0x9c000000,
     index = (va & ARM_TT_L2_INDEX_MASK) >> ARM_TT_L2_SHIFT.
  3. new osfmk/arm64/sweet_early.c (+files.arm64 entry): sweet_early_mark(n) colored bands at screen bottom and
     sweet_early_putc using iso_font via VA=PA while the bootstrap TTBR0 is live; disable before
     arm_vm_init's set_mmu_ttb(invalid_ttep) (arm_vm_init.c:2148).
  4. markers in arm_init after PE_init_platform, ml_parse_cpu_topology, cpu_bootstrap, kernel_startup_bootstrap,
     cpu_init, before arm_vm_init.
  5. panic hook at top of panic_trap_to_debugger: va_copy + _doprnt(fmt, &copy, sweet_early_putc, 16).
  Verify with tools/xnu-cc.py (compile+symbols) and patch-order simulation before the single CI run.
