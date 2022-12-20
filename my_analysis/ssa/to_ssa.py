#!/usr/bin/env python3

import collections
import itertools
import json
import sys

from dominance import form_blocks, form_cfg
from dominance import dom_algorithm, immediate_dominance, dom_frontier

TERMINATORS = ['jmp', 'br', 'ret']
def phi_node_insertion(block_map, dom_frontier):
    def_map = collections.defaultdict(set)
    for block in block_map.keys():
        for instr in block_map[block]:
            if 'dest' not in instr:
                continue
            def_map[instr['dest']].add(block)

    # a variable-to-(block-to-phi) map
    phi_map = {var: {} for var in def_map.keys()}
    for variable in def_map.keys():
        stack = list(def_map[variable]) # can be queue or stack
        while stack:
            def_block = stack.pop()
            for frontier_block in dom_frontier[def_block]:
                if frontier_block not in phi_map[variable]:
                    phi_instr = {'dest': variable,
                                 'op': 'phi',
                                 'args': [],
                                 'labels': []}
                    bb = block_map[frontier_block]
                    block_map[frontier_block] = bb[0:1] + [phi_instr] + bb[1:]
                    phi_map[variable][frontier_block] = phi_instr
                    stack.append(frontier_block)
                phi_instr = phi_map[variable][frontier_block]
                phi_instr['args'].append(variable)
                phi_instr['labels'].append(def_block)

def to_ssa(block_map, dom_frontier):
    phi_node_insertion(block_map, dom_frontier)

def reform_blocks(block_list, block_map):
    label_list = [block[0]['label'] for block in block_list]
    return [block_map[label] for label in label_list]

def main():
    bril = json.load(sys.stdin)
    for func in bril['functions']:
        blocks, block_map = form_blocks(func['instrs'])
        succs, preds = form_cfg(blocks, [k for k in block_map.keys()])
        dom = dom_algorithm(succs, preds, block_map)
        frontier = dom_frontier(preds, dom)
        tree = immediate_dominance(dom)
        to_ssa(block_map, frontier)
        blocks = reform_blocks(blocks, block_map)
        func['instrs'] = list(itertools.chain(*blocks))
    json.dump(bril, sys.stdout, indent=2, sort_keys=True)


if __name__ == '__main__':
    main()
