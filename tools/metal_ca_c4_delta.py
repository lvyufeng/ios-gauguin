"""Bounded C4 desktop HFSX install and dynamic post-boot restoration.

No entry point opens device IO. Callers must bind an explicit approval to the
immutable install plan before constructing RecoveryIO. Both phases require an
unmounted recovery partition and exact full-range preimages.
"""
from pathlib import Path
import hashlib
import json
import struct

VOLUME = 17179869184
PARTITION_BYTES = 114919714816
BLOCK = 4096
TARGET = '/System/Library/Extensions/GauguinMetalDesktop.bundle/GauguinMetalDesktop'


class Refused(RuntimeError):
    pass


def require(ok, why):
    if not ok:
        raise Refused(why)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def save(path, data):
    with path.open('xb') as stream:
        stream.write(data)


def approval_gate(approval, plan_sha, io=None):
    require(approval.get('approved') is True and approval.get('one_shot') is True and
            approval.get('allow_install') is True and approval.get('allow_restore') is True and
            approval.get('allow_rollback') is True and approval.get('allow_misc_marker') is True and
            approval.get('allow_temporary_boot') is True and approval.get('plan_sha256') == plan_sha,
            'fresh exact-scope user approval required')
    if approval.get('fixture_only'):
        require(io is not None and getattr(io, 'model_only', False) is True,
                'fixture approval cannot reach writable device IO')


def identity_gate(io):
    info = io.identity()
    require(info.get('state') == 'recovery' and info.get('product') == 'gauguin' and
            info.get('partition_bytes') == PARTITION_BYTES and info.get('unmounted') is True and
            info.get('no_holders') is True, 'one unmounted Gauguin recovery partition required')


def plan_gate(plan, candidate):
    require(plan.get('state') == 'prepared-owned-C4-desktop-same-extent-delta' and
            plan.get('target') == TARGET and plan.get('volume_bytes') == VOLUME and
            plan.get('block_bytes') == BLOCK, 'unexpected HFSX plan')
    require(plan.get('data_start_block') == 3817791 and plan.get('data_blocks') == 105 and
            plan.get('catalog_start_block') == 44139 and plan.get('catalog_field_offset') == 1434 and
            plan.get('file_cnid') == 635763 and plan.get('changed_ranges') == 2 and
            plan.get('changed_bytes') == 434176, 'unexpected approved ranges')
    require(plan.get('old_file_bytes') == 428400 and plan.get('new_file_bytes') == 428720 and
            plan.get('old_file_sha256') == '0a1b55bb20a29661de40099e58e45ec695ffb0bf78e132a9d10985450e868550' and
            plan.get('new_file_sha256') == '560284ddda16936df1dd9c6003c8ef4c31096a7c41fcd72ade1051db8411d1d5' and
            plan.get('file_fork', {}).get('extents') == [[3817791, 105]] and
            plan.get('file_fork', {}).get('logical') == 428400, 'file fork differs')
    require(plan.get('volume_header_changed') is False and plan.get('code_resources_unchanged') is True and
            plan.get('info_plist_unchanged') is True, 'unexpected metadata scope')
    data_old = (candidate / 'desktop-old.bin').read_bytes()
    data_new = (candidate / 'desktop-new.bin').read_bytes()
    cat_old = (candidate / 'catalog-old.bin').read_bytes()
    cat_new = (candidate / 'catalog-new.bin').read_bytes()
    require(len(data_old) == len(data_new) == 105*BLOCK and len(cat_old) == len(cat_new) == BLOCK,
            'range file lengths differ')
    for name, data in [('data_old', data_old), ('data_new', data_new),
                       ('catalog_old', cat_old), ('catalog_new', cat_new)]:
        require(sha(data) == plan[name + '_sha256'], 'range file hash differs: ' + name)
    at = plan['catalog_field_offset']
    require(cat_old[:at] == cat_new[:at] and cat_old[at+8:] == cat_new[at+8:] and
            cat_old[at:at+8] == struct.pack('>Q',plan['old_file_bytes']) and
            cat_new[at:at+8] == struct.pack('>Q',plan['new_file_bytes']),
            'catalog delta is not exactly the approved logical length')
    require(sha(data_old[:plan['old_file_bytes']]) == plan['old_file_sha256'] and
            sha(data_new[:plan['new_file_bytes']]) == plan['new_file_sha256'] and
            data_old[plan['new_file_bytes']:] == data_new[plan['new_file_bytes']:],
            'file content or untouched allocation tail differs')
    require(plan['data_start_block'] > 0 and
            plan['data_start_block'] + plan['data_blocks'] < VOLUME//BLOCK-1 and
            plan['catalog_start_block'] > 0 and plan['catalog_start_block'] < VOLUME//BLOCK-1 and
            not plan['data_start_block'] <= plan['catalog_start_block'] < plan['data_start_block']+105,
            'protected header or overlapping range')
    return data_old, data_new, cat_old, cat_new


def apply_ranges(io, rows, header_sha, report):
    """Rows are (block, exact old bytes, exact new bytes), in write order."""
    identity_gate(io)
    require(sha(io.read(0, BLOCK)) == header_sha, 'current volume header differs')
    for start, old, new in rows:
        require(start > 0 and start + len(old)//BLOCK < VOLUME//BLOCK and
                len(old) == len(new) and len(old) % BLOCK == 0,
                'range outside allowed root')
        require(io.read(start*BLOCK, len(old)) == old, 'full range preimage changed')
    touched = []
    try:
        for start, old, new in rows:
            touched.append((start, old))
            io.write(start*BLOCK, new)
            io.sync()
            require(io.read(start*BLOCK, len(new)) == new, 'write readback differs')
            report(dict(state='writing', verified_runs=len(touched), total_runs=len(rows)))
        require(sha(io.read(0, BLOCK)) == header_sha, 'volume header changed')
        receipt = dict(state='applied-and-readback-verified', runs=len(rows),
                       bytes=sum(len(row[1]) for row in rows), rollback=False,
                       root_header_sha256=header_sha)
        report(receipt)
        return receipt
    except (Exception, KeyboardInterrupt) as error:
        failed = []
        for start, old in reversed(touched):
            try:
                io.write(start*BLOCK, old)
                io.sync()
                require(io.read(start*BLOCK,len(old)) == old, 'rollback readback differs')
            except (Exception, KeyboardInterrupt) as problem:
                failed.append(dict(block=start,error=repr(problem)))
        receipt = dict(state='write-failed-rollback-incomplete' if failed else 'write-failed-rollback-verified',
                       error=repr(error), touched_runs=len(touched), rollback_failures=failed)
        report(receipt)
        return receipt


def install(plan, plan_sha, candidate, approval, io, report):
    approval_gate(approval, plan_sha, io)
    old, new, cat_old, cat_new = plan_gate(plan, candidate)
    rows = [(plan['data_start_block'],old,new),
            (plan['catalog_start_block'],cat_old,cat_new)]
    receipt = apply_ranges(io,rows,plan['root_header_sha256'],report)
    receipt['phase'] = 'install'
    receipt['plan_sha256'] = plan_sha
    return receipt


class Remote:
    def __init__(self, io):
        self.io, self.position, self.bytes = io, 0, 0
    def seek(self, position): self.position = position
    def read(self, count):
        require(0 <= count <= 268435456 and 0 <= self.position and
                self.position + count <= VOLUME, 'remote HFSX read out of range')
        if not count: return b''
        first = self.position//BLOCK*BLOCK
        end = (self.position+count+BLOCK-1)//BLOCK*BLOCK
        raw = self.io.read(first,end-first)
        require(len(raw)==end-first,'short recovery read')
        self.bytes += len(raw)
        result=raw[self.position-first:self.position-first+count]
        self.position += count
        return result
    def close(self): pass


def prepare_restore(plan, plan_sha, candidate, approval, io, out, HFS):
    """Read current post-boot metadata; preserve unrelated catalog bytes."""
    approval_gate(approval, plan_sha, io)
    old, new, _, _ = plan_gate(plan,candidate)
    identity_gate(io)
    header = io.read(0,BLOCK)
    remote = Remote(io)
    h = HFS(stream=remote,size=VOLUME)
    try:
        row = h.paths[TARGET]
        fork = row['data']
        require(row['id'] == plan['file_cnid'] and row['type'] == 2 and not row['flags']&0x20 and
                (row['uid'],row['gid'],row['mode']) == (0,0,33261) and
                fork['logical'] == plan['new_file_bytes'] and fork['blocks'] == 105 and
                fork['extents'] == [[plan['data_start_block'],105]],
                'post-boot frontend file mapping differs')
        require(sha(h.content(TARGET)) == plan['new_file_sha256'],
                'post-boot frontend binary differs')
        data_start=plan['data_start_block']*BLOCK
        current_data=io.read(data_start,len(old))
        require(current_data[:len(new)] == new[:len(new)],
                'post-boot allocated binary bytes differ')
        offset=row['catalog_bsd_offset']+56
        spans=list(h.spans(h.catalog,offset,8))
        require(len(spans)==1 and spans[0][1]==8,'catalog logical length spans blocks')
        physical=spans[0][0]
        catalog_start=physical//BLOCK*BLOCK
        at=physical-catalog_start
        require(at+8<=BLOCK and catalog_start>0 and catalog_start<VOLUME-BLOCK and
                not data_start<=catalog_start<data_start+len(old),
                'post-boot catalog field outside approved scope')
        current_cat=io.read(catalog_start,BLOCK)
        require(current_cat[at:at+8]==struct.pack('>Q',plan['new_file_bytes']),
                'post-boot logical length differs')
        target_cat=bytearray(current_cat)
        target_cat[at:at+8]=struct.pack('>Q',plan['old_file_bytes'])
        target_cat=bytes(target_cat)
        require(target_cat[:at]==current_cat[:at] and target_cat[at+8:]==current_cat[at+8:],
                'restore would alter unrelated catalog bytes')
        require(sha(io.read(0,BLOCK))==sha(header), 'header changed during restore preflight')
        require(not out.exists(), 'restore inputs already exist')
        out.mkdir(parents=True,exist_ok=False)
        for name,data in [('data-current.bin',current_data),('data-old.bin',old),
                          ('catalog-current.bin',current_cat),('catalog-old.bin',target_cat)]:
            save(out/name,data)
        dynamic=dict(state='prepared-dynamic-owned-C4-restoration',
                     base_plan_sha256=plan_sha,root_header_sha256=sha(header),
                     file_cnid=row['id'],data_start_block=plan['data_start_block'],
                     data_blocks=105,catalog_start_block=catalog_start//BLOCK,
                     catalog_field_offset=at,old_file_bytes=plan['old_file_bytes'],
                     new_file_bytes=plan['new_file_bytes'],
                     read_only_catalog_bytes=remote.bytes,
                     data_current_sha256=sha(current_data),data_old_sha256=sha(old),
                     catalog_current_sha256=sha(current_cat),catalog_old_sha256=sha(target_cat),
                     device_writes=0)
        (out/'restore-plan.json').write_text(json.dumps(dynamic,indent=2)+'\n')
        return dynamic
    finally: h.close()


def restore(plan, plan_sha, dynamic, out, candidate, approval, io, report):
    approval_gate(approval,plan_sha,io)
    plan_gate(plan,candidate)
    require(dynamic.get('state') == 'prepared-dynamic-owned-C4-restoration' and
            dynamic.get('base_plan_sha256') == plan_sha and
            dynamic.get('file_cnid') == plan['file_cnid'] and
            dynamic.get('data_start_block') == plan['data_start_block'] and
            dynamic.get('data_blocks') == 105 and
            dynamic.get('old_file_bytes') == plan['old_file_bytes'] and
            dynamic.get('new_file_bytes') == plan['new_file_bytes'],
            'restore plan does not match approved file')
    data_current=(out/'data-current.bin').read_bytes()
    data_old=(out/'data-old.bin').read_bytes()
    cat_current=(out/'catalog-current.bin').read_bytes()
    cat_old=(out/'catalog-old.bin').read_bytes()
    require(len(data_current)==len(data_old)==105*BLOCK and
            len(cat_current)==len(cat_old)==BLOCK,'restore input sizes differ')
    for name,data in [('data_current',data_current),('data_old',data_old),
                      ('catalog_current',cat_current),('catalog_old',cat_old)]:
        require(sha(data)==dynamic[name+'_sha256'],'restore input hash differs: '+name)
    require(sha(data_old)==plan['data_old_sha256'] and
            sha(data_current[:plan['new_file_bytes']])==plan['new_file_sha256'],
            'restore binary contract differs')
    at=dynamic['catalog_field_offset']
    require(0<=at<=BLOCK-8 and cat_current[:at]==cat_old[:at] and
            cat_current[at+8:]==cat_old[at+8:] and
            cat_current[at:at+8]==struct.pack('>Q',plan['new_file_bytes']) and
            cat_old[at:at+8]==struct.pack('>Q',plan['old_file_bytes']),
            'restore catalog field differs')
    catalog_block=dynamic['catalog_start_block']
    require(type(catalog_block)is int and 0<catalog_block<VOLUME//BLOCK-1 and
            not plan['data_start_block']<=catalog_block<plan['data_start_block']+105,
            'restore catalog block outside volume')
    rows=[(plan['data_start_block'],data_current,data_old),
          (catalog_block,cat_current,cat_old)]
    receipt=apply_ranges(io,rows,dynamic['root_header_sha256'],report)
    receipt['phase']='restore'
    receipt['plan_sha256']=plan_sha
    return receipt
