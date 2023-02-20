#!/usr/bin/env python3
import collections
import json
import sys

TERMINATORS = 'jmp', 'br', 'ret'

def block_map(blocks):
    out = {} # block: [block]

    for block in blocks:
        if 'label' in block[0]:
            name = block[0]['label']
            block = block[1:]
        else:
            name = "b{}".format(len(out))

        out[name] = block
    return out

def get_cfg(name2block):
    """
    Given a name-to-block map, produce a mapping from block names to
    successor block names.
    """
    out = collections.OrderedDict()
    for i, (name, block) in enumerate(name2block.items()):
        last = block[-1]
        if last['op'] in ('jmp', 'br'):
            succs = last['labels']
        elif last['op'] == 'ret':
            succs = []
        else:
            if i == len(name2block) - 1:
                succs = []
            else:
                succs = [list(name2block.keys())[i+1]]
        out[name] = succs
    return out

def form_blocks(body):
    curr_block = []

    for instr in body:
        if 'op' in instr: # an actual instruction
            curr_block.append(instr)

            if instr['op'] in TERMINATORS:
                yield curr_block
                curr_block = []
        else: # a label
            if curr_block:
                yield curr_block
            curr_block = [instr]

    if curr_block:
        yield curr_block

def mycfg():
    prog = json.load(sys.stdin)
    cfg = collections.defaultdict(list)
    for func in prog['functions']:
        name2block = block_map(form_blocks(func['instrs']))
        cfg = get_cfg(name2block)
        print('digraph {} {{'.format(func['name']))
        for name in name2block:
            print('  {}'.format(name))
        for name, succs in cfg.items():
            for succ in succs:
                print('  {} -> {}'.format(name, succ))
        print('}')

if __name__ == '__main__':
    mycfg()
