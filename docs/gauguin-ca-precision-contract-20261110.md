# Actual CA precision contract and variant identity

Trial 0233 captured the original failure before any A619 shader compilation.
Both delegated `newFunctionWithDescriptor:error:` calls requested
`fixed_frag_lpf_cpf`, with constants present. The installed library had no such
function; both calls returned `MTLLibraryErrorDomain` code 5. QuartzCore then
aborted before the first scene. This establishes a missing-function blocker,
not a successful renderer, compiler fault or GPU memory failure.

The exact installed 20H392 library has 141 functions, including four LPH/LPF
vertex functions and two LPH fragment functions. A newer host Mac air64 library
has 180 functions and includes the missing LPF fragment function. Apple assets,
extracted IR and runtime logs remain in private artifacts.

The HakiOS [assembly script](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/tools/ca-metallib.py)
uses image-owned specialized uber functions inside a later system's library.
Its [container writer](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/tools/merge_metallib.py)
shows how to assemble records. Container assembly alone does not establish that
another system's functions accept this system's constants and resource layout.

## Read-only comparison

DSH opened both actual libraries with public host Metal reflection. All 13
fixed-function AIR modules also decoded with LLVM. No GPU jobs ran.

| Contract | Installed iOS LPH fragment | Newer Mac LPH fragment | Newer Mac LPF fragment |
| --- | --- | --- | --- |
| Function constants | 58 | 60 | 60 |
| Color opcode constants | `uchar3` | `uchar4` | `uchar4` |
| `fc_framebuffer_sample` | Declared, required | Absent | Absent |
| Fragment Uniform size | 176 bytes | 256 bytes | 368 bytes |

There are 57 shared constant names between the old and newer CPF fragment
functions, with 54 changed indices and two changed types. Name-based constant
binding can accommodate index changes; it does not by itself adapt changed types
or resource layouts. The newer constants also add three optional names. These
facts rule out assuming that copying a same-named function is a complete fix.
The old library contains no LPF fragment to provide a direct old/new LPF layout
comparison; its expected ABI must be established from the actual framework.

An offline inventory decoded 5,390 distinct QuartzCore call targets. It found
`supportsFamily:` queries for Apple GPU families and their resulting context
flags, including Apple1 at `0x1884886d4`. This is evidence of capability queries,
not yet proof of the complete data flow into the LPF request. Keep advertised
families unchanged while tracing that selection. Changing family declarations
just to avoid the missing function would leave the contract unverified.

## Implemented precision-safe selection

The new opt-in `gauguin-ca-identity` frontend applies patches 0001–0004. Its
production C reader bounds-checks each single-function container, verifies its
name, stage and AIR range, and records the function identity beside the label.
Both native and optional M2V selection paths require the complete requested
function name and stage to match before using a pre-specialized variant. A
label referring to an LPH variant cannot replace an LPF function. An unmatched
function keeps its own AIR; existing original constant extraction is unchanged.
The change adds no function substitutions, library payload or device family.

DSH validation and independent review:

- All four older preparation profiles produce byte-identical source files.
- All 451 actual image variants passed 52,323 identity, stage and malformed-input
  checks under ASan/UBSan. These are parser checks, not rendered-pixel checks.
- Native iOS frontend and paired CA probe compile, link and sign successfully.
  The frontend retains one existing SDK deprecation warning; the probe has none.
- All 681 native imports resolve against actual 20H392 cache exports, with five
  disabled optional M2V hooks handled separately. The one added import is
  `memchr`. This audit uses the already verified 0233 backup, not a fresh device
  backup for a future write.

The first native stage stopped because the paired builder omitted the new
profile. The original builder is archived with its hash. A fresh second stage
built the paired probe but correctly stopped at the changed-import guard; a
separate complete actual-cache audit then passed. Failed stages and original
logs remain retained, rather than being relabeled as successful runs.

Private evidence is under
`research/tmp/gauguin-lpf234-worktree-20261110/research/tmp/dsh-lpf-0234-library/`.
`independent-review234.json` binds 157 inputs/artifacts. Neither the new frontend
nor a supplementary library has been installed or booted. CA pixels, UI speed,
Metal publication, high refresh and daily use remain unqualified.

Next: trace the actual iOS precision decision and constant/resource ABI, obtain
an appropriate same-version LPF implementation or implement a fully checked
adapter, then repeat bounded real CA pixel qualification. A later concrete
userdata proposal needs a fresh full backup and individual write approval.
