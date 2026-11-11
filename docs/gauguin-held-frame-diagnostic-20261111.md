# Held-frame rejection diagnostic

The 0288 physical trial completed GPU jobs (24/24), created the Adreno619 Metal
device and linked the system CoreAnimation pipelines, yet accepted zero held
display frames and rejected 200 before the planned stop. The user saw logs and
could not reach the desktop. Which admission guard failed is not yet known.

Patch 0216 preserves those guards and all existing hold/drop paths. It adds
first-eight rejection records and periodic reason totals under the existing
framebuffer lock. Reason 1 means null owner, 2 unsupported layer-mask bits,
3–6 failure to hold a surface in layer 0–3, and 7 unregistered client. Records
include owner presence/membership, client count, mask and four surface IDs;
they contain no object addresses. Failed input still releases partial holds
and preserves the prior pending frame.

The host harness extracts and executes the production methods. Tests cover
each reason, partial-hold unwind, unchanged input/pending references, invalid
IDs, saturated users and concurrent retry output bounds, alongside existing
close/replacement/active-frame tests. ARM64 compilation checks use the pinned
native kernel recipe. These checks do not certify a desktop or physical FPS.

The intended next device trial changes only the temporary kernel image and a
13-byte recovery marker. The installed router, bootstrap, frontend, Mesa and
userdata root remain as captured after 0288. Individual marker/boot approval
is required after the complete image and read-only preflight are reviewed.
