"""Add frontend metrics within the boot field, preserving every other token.

The source-backed tests bind missing sweetreboot to its explicit zero value
for all nine kernel consumers. This does not alter the default boot command.
"""


def with_metal_metrics(command):
    if type(command) is not str:
        raise ValueError('command must be text')
    tokens = command.split(' ')
    if not all(tokens) or tokens.count('sweetreboot=0') != 1:
        raise ValueError('expected one explicit disabled debug reboot')
    if any(token.startswith('sweetreboot') and token != 'sweetreboot=0' for token in tokens):
        raise ValueError('other debug reboot option is not equivalent')
    if any(token == 'metal_fps' or token.startswith('metal_fps=') for token in tokens):
        raise ValueError('metrics already selected')
    if tokens.count('-noprogress') != 1:
        raise ValueError('retain the baseline progress policy')
    return ' '.join([token for token in tokens if token != 'sweetreboot=0'] + ['metal_fps'])
