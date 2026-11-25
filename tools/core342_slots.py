"""Read and split the exact in-fork order of an owned data allocation."""

from core342_hfs import BLOCK, VOLUME, require

C4_PATH = '/System/Library/Extensions/GauguinMetalDesktop.bundle/GauguinMetalDesktop'


def data_extents(row):
    extents = row.get('data_extents', [[row['data_block'], row['data_blocks']]])
    require(isinstance(extents, list) and len(extents) in (1, 2), 'unsupported slot extent count')
    for extent in extents:
        require(isinstance(extent, list) and len(extent) == 2, 'invalid slot extent')
        start, count = extent
        require(type(start) is int and type(count) is int and 0 < start < start + count < VOLUME // BLOCK,
                'slot extent leaves the root data area')
    require(extents[0][0] == row['data_block'] and sum(count for _, count in extents) == row['data_blocks'],
            'slot extent totals disagree')
    if len(extents) == 2:
        (first, leading), (tail, trailing) = extents
        require(row['path'] == C4_PATH and (leading, trailing) == (101, 4) and
                (first + leading <= tail or tail + trailing <= first), 'unreviewed split slot geometry')
    return extents


def read_allocation(io, extents):
    return b''.join(io.read(start * BLOCK, count * BLOCK) for start, count in extents)


def split_allocation(extents, image):
    require(len(image) == sum(count for _, count in extents) * BLOCK, 'slot image length differs')
    at = 0
    for start, count in extents:
        end = at + count * BLOCK
        yield start, image[at:end]
        at = end
