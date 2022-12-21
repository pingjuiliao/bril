#!/usr/bin/env python3

import itertools
import json
import sys

from dominance import form_blocks, form_cfg


def from_ssa(block_map, block_list):
    for label, block in block_map.items():
        new_block = []
        for instr in block:
            if 'op' not in instr or instr['op'] != 'phi':
                new_block.append(instr)
                continue
            dst = instr['dest']
            for arg, pred_label in zip(instr['args'], instr['labels']):
                pred = block_map[pred_label]
                new_instr = {'op': 'id', 'args': [arg],
                             'dest': dst}
                block_map[pred_label] = pred[:-1] + [new_instr] + pred[-1:]
        block_map[label] = new_block

    label_list = [block[0]['label'] for block in block_list]
    return [block_map[label] for label in label_list]

def tdce(instrs):
    converged = False
    while not converged:
        used = set()
        converged = True
        for instr in instrs:
            if 'args' not in instr:
                continue
            for arg in instr['args']:
                used.add(arg)

        for instr in instrs:
            if 'dest' in instr and instr['dest'] not in used:
                # DANGER: list.remove() in a loop will skip one instruction
                #  luckily, we iterate until convergence
                instrs.remove(instr)
                converged = False
    return instrs

def main():
    bril = json.load(sys.stdin)
    for func in bril['functions']:
        blocks, block_map = form_blocks(func['instrs'])
        succs, preds = form_cfg(blocks, list(block_map.keys()))
        blocks = from_ssa(block_map, blocks)
        instrs = list(itertools.chain(*blocks))
        tdce(instrs)
        func['instrs'] = instrs
    json.dump(bril, sys.stdout, indent=2, sort_keys=True)

if __name__ == '__main__':
    main()
