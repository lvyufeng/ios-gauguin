#!/usr/bin/env python3
"""Minimal read-only HFS+ reader for the iOS root on gauguin's userdata.

  python3 tools/hfs-read.py list  /path           # list a directory
  python3 tools/hfs-read.py cat   /path/TO/FILE   # dump a file to stdout
  python3 tools/hfs-read.py find  NAME            # locate a file by name

Why this exists: everything above the kernel has been a black box. The iOS
root is a plain HFS+ volume in the `userdata` partition, and TWRP on this
phone has no HFS support, so the volume could only be read as raw blocks. This
reads it directly over adb (dd) - enough to look at what userland actually
executes, which is where the answers about CoreAnimation and the GPU live.

Deliberately small: read-only, catalog B-tree only.

WHAT WORKS: listing a directory and locating a file by name. A full catalog
walk returns 323,281 entries in about 17 s.

WHAT DOES NOT: `cat`, and the `size` column. The catalog record layout on this
volume does not match the textbook HFSPlusCatalogFile, and the fork's
logicalSize has not been located - the values printed for size are garbage.
The one offset that was proven is the first extent: for `.journal` the pair at
+104 names block 3168598, and that block really holds the journal header
(784c4e4a78563412). See NOTES (49)-(51). Do not build on the size field.

PERFORMANCE TRAP, recorded because it cost several rounds: reading one node
per `adb dd` made a walk look hung or infinitely looping. Batch reads are
required; a walk is subprocess-bound, not logic-bound.
"""
import struct
import subprocess
import sys

PART = "/dev/block/by-name/userdata"
BLOCK = 4096

CNID_ROOT = 2


class Volume:
    def __init__(self, part=PART):
        self.part = part
        self.header = self._read(1024, 1024)
        if self.header[0:2] != b"HX":
            raise RuntimeError("not an HFS+ volume (signature %r)" % self.header[0:2])
        (self.block_size, self.total_blocks, _free) = struct.unpack(">III",
                                                                    self.header[40:52])
        if self.block_size != BLOCK:
            raise RuntimeError("unexpected block size %d" % self.block_size)
        # fork data begins at 112, each is 80 bytes
        self.catalog = self._fork(112 + 160)
        self.extents = self._fork(112 + 80)
        self._nodesize = None
        self._cache = {}
        self._catalog = None

    def _fork(self, off):
        logical, clump, blocks = struct.unpack(">QII", self.header[off:off + 16])
        extents = []
        for i in range(8):
            start, count = struct.unpack(">II", self.header[off + 16 + 8 * i:off + 24 + 8 * i])
            if count:
                extents.append((start, count))
        return {"logical": logical, "blocks": blocks, "extents": extents}

    def _read(self, offset, length):
        """Read at an arbitrary byte offset. dd can only skip whole blocks, so
        it reads from the containing block and the result is trimmed here."""
        skip = offset // BLOCK
        lead = offset - skip * BLOCK
        count = (lead + length + BLOCK - 1) // BLOCK
        out = subprocess.run(
            ["adb", "exec-out",
             "dd if=%s bs=%d skip=%d count=%d 2>/dev/null"
             % (self.part, BLOCK, skip, count)],
            capture_output=True, check=False)
        return out.stdout[lead:lead + length]

    def _read_fork(self, fork, offset, length):
        """Read `length` bytes at `offset` inside a fork, following extents."""
        out = bytearray()
        skip = offset
        want = length
        for start, count in fork["extents"]:
            span = count * self.block_size
            if skip >= span:
                skip -= span
                continue
            take = min(want, span - skip)
            out += self._read(start * self.block_size + skip, take)
            want -= take
            skip = 0
            if want <= 0:
                break
        return bytes(out)

    # Nodes are pulled in batches: one `adb dd` per node made a full catalog
    # walk hundreds of subprocess round-trips, which is slow enough that the
    # walk looked broken (it was timing out, not looping).
    BATCH = 256

    def _fetch_range(self, node, count):
        start = node * self._nodesize
        return self._read_fork(self.catalog, start, count * self._nodesize)

    # Reading a fixed 256-node window per miss is wrong when node numbers are
    # visited out of order - which they are: a B-tree walk follows children in
    # key order, and those numbers are scattered. Each miss then re-read a
    # window that largely overlapped the last one, and a full walk thrashed
    # (measured: minutes, mistaken for a hang). Slice the catalog once and
    # serve every node from it instead.
    SLICE = 8 << 20            # 8 MiB per dd call

    def _load_catalog(self):
        if self._catalog is not None:
            return
        if self._nodesize is None:
            hdr = self._read_fork(self.catalog, 0, 512)
            # BTHeaderRec follows the 14-byte node descriptor:
            #   treeDepth(2) rootNode(4) leafRecords(4) firstLeaf(4)
            #   lastLeaf(4) nodeSize(2) - nodeSize sits at 14+18 = 32
            self._nodesize = struct.unpack(">H", hdr[32:34])[0]
        if not self._nodesize:
            self._catalog = b""
            return
        total = self.catalog["logical"]
        parts = []
        off = 0
        while off < total:
            want = min(self.SLICE, total - off)
            parts.append(self._read_fork(self.catalog, off, want))
            off += want
        self._catalog = b"".join(parts)

    def _node(self, n):
        if n in self._cache:
            return self._cache[n]
        self._load_catalog()
        off = n * self._nodesize
        raw = self._catalog[off:off + self._nodesize]
        self._cache[n] = raw
        return raw

    def _records(self, n):
        """Yield (key, data) for node n."""
        buf = self._node(n)
        ns = self._nodesize
        if len(buf) < ns:
            return
        nrec = struct.unpack(">H", buf[10:12])[0]
        tbl = ns - 2 * (nrec + 1)
        offs = [struct.unpack(">H", buf[tbl + 2 * i:tbl + 2 * i + 2])[0]
                for i in range(nrec + 1)]
        # Records are stored from the end of the node backwards: the offset
        # table is ascending (last entry is always 14, the header size), so
        # record k occupies [offs[nrec-1-k], offs[nrec-k]].
        for k in range(nrec):
            # offs is ascending, so the earlier offset is the lower bound.
            lo, hi = offs[nrec - k], offs[nrec - 1 - k]
            if lo > hi:
                lo, hi = hi, lo
            rec = buf[lo:hi]
            if len(rec) < 2:
                continue
            klen = struct.unpack(">H", rec[0:2])[0]
            if 2 + klen > len(rec):
                continue
            # The key is followed by the data directly. (An earlier version
            # skipped 4 bytes here, copying the HFSPlusCatalogKey "data offset"
            # field that this B-tree does not use: every record came back with
            # an empty data part.)
            yield rec[2:2 + klen], rec[2 + klen:]

    @staticmethod
    def _key(k):
        parent = struct.unpack(">I", k[0:4])[0]
        nlen = struct.unpack(">H", k[4:6])[0]
        name = k[6:6 + 2 * nlen].decode("utf-16-be", "replace")
        return parent, name

    def _root_of_tree(self):
        hdr = self._read_fork(self.catalog, 0, 512)
        return struct.unpack(">I", hdr[14 + 2:14 + 6])[0]

    def walk(self, node=None, depth=0):
        """Yield (parent_cnid, name, cnid, is_dir, size) for every catalog entry."""
        if node is None:
            node = self._root_of_tree()
        kind = self._node(node)[8]
        if kind == 0:            # index node: descend
            for _k, data in self._records(node):
                if len(data) >= 4:
                    child = struct.unpack(">I", data[0:4])[0]
                    yield from self.walk(child, depth + 1)
            return
        # leaf node
        for k, data in self._records(node):
            parent, name = self._key(k)
            if len(data) < 8:
                continue
            rec_type = struct.unpack(">h", data[0:2])[0]
            cnid = struct.unpack(">I", data[8:12])[0] if len(data) >= 12 else 0
            if rec_type == 1:        # folder
                yield (parent, name, cnid, True, 0)
            elif rec_type == 2:      # file
                # Where the dataFork really starts in this tree, measured
                # rather than assumed:
                #   .journal          +40=32768  +56=4194304   (4 MiB, its
                #                      standard size - so +56 is logicalSize)
                #   .hotfiles.btree   +40=33152  +56=1342177280
                #   .file             +40=32768  +56=0
                # So +40 holds allocated bytes and the fork's logicalSize is
                # at +56.
                size = struct.unpack(">Q", data[56:64])[0] if len(data) >= 64 else 0
                yield (parent, name, cnid, False, size)

    def index(self):
        """cnid -> (parent, name, is_dir, size), plus root."""
        entries = {CNID_ROOT: (0, "", True, 0)}
        for parent, name, cnid, is_dir, size in self.walk():
            entries.setdefault(cnid, (parent, name, is_dir, size))
        return entries

    def resolve(self, path):
        """Return (cnid, is_dir) for an absolute path, or (None, False)."""
        idx = self.index()
        by_parent = {}
        for cnid, (parent, name, is_dir, size) in idx.items():
            by_parent.setdefault(parent, {})[name] = (cnid, is_dir)
        cur = CNID_ROOT
        for part in [p for p in path.split("/") if p]:
            nxt = by_parent.get(cur, {}).get(part)
            if nxt is None:
                return None, False
            cur = nxt[0]
        return cur, idx.get(cur, (0, "", False, 0))[2]

    def read_file(self, cnid):
        """Read a file's first fork, following its extents."""
        for parent, name, c, is_dir, size in self.walk():
            if c == cnid and not is_dir:
                # find the record again to get its extents
                for k, data in self._leaf_records():
                    p2, n2 = self._key(k)
                    if struct.unpack(">h", data[0:2])[0] == 2 and \
                            struct.unpack(">I", data[8:12])[0] == cnid:
                        logical = struct.unpack(">Q", data[40:48])[0]
                        ext = []
                        for i in range(8):
                            base = 88 + 8 * i
                            st, ct = struct.unpack(">II", data[base:base + 8])
                            if ct:
                                ext.append((st, ct))
                        fork = {"logical": logical, "extents": ext}
                        return self._read_fork(fork, 0, logical)
        return None

    def _leaf_records(self):
        def rec(node):
            if self._node(node)[8] == 0:
                for _k, data in self._records(node):
                    if len(data) >= 4:
                        yield from rec(struct.unpack(">I", data[0:4])[0])
            else:
                yield from self._records(node)
        yield from rec(self._root_of_tree())


def main(argv):
    if len(argv) < 3:
        sys.stderr.write(__doc__)
        return 2
    cmd = argv[1]
    vol = Volume()
    if cmd == "list":
        target = argv[2]
        cnid, is_dir = vol.resolve(target)
        if cnid is None:
            sys.stderr.write("no such path: %s\n" % target)
            return 1
        idx = vol.index()
        for c, (parent, name, d, size) in sorted(idx.items(),
                                                 key=lambda kv: kv[1][1]):
            if parent == cnid:
                print("%s %10d  %s%s" % ("d" if d else "-", size, name,
                                         "/" if d else ""))
        return 0
    if cmd == "cat":
        cnid, is_dir = vol.resolve(argv[2])
        if cnid is None or is_dir:
            sys.stderr.write("no such file: %s\n" % argv[2])
            return 1
        data = vol.read_file(cnid)
        if data is None:
            sys.stderr.write("could not read %s\n" % argv[2])
            return 1
        sys.stdout.buffer.write(data)
        return 0
    if cmd == "find":
        want = argv[2]
        idx = vol.index()
        hits = [(c, v) for c, v in idx.items() if v[1] == want]
        if not hits:
            sys.stderr.write("not found: %s\n" % want)
            return 1
        for c, (parent, name, d, size) in hits:
            print("%s cnid=%d parent=%d size=%d" % (name, c, parent, size))
        return 0
    sys.stderr.write(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))