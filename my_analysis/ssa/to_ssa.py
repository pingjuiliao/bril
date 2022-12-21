#!/usr/bin/env python3

import collections
import itertools
import json
import sys

from dominance import form_blocks, form_cfg
from dominance import dom_algorithm, immediate_dominance, dom_frontier

DEBUG = False
TERMINATORS = ['jmp', 'br', 'ret']

def phi_node_insertion(block_map, dom_frontier):

    # A variable-to-definition map
    def_map = collections.defaultdict(set)
    type_map = {}
    for block in block_map.keys():
        for instr in block_map[block]:
            if 'dest' not in instr:
                continue
            def_map[instr['dest']].add(block)
            type_map[instr['dest']] = instr['type']



    # A variable-to-block-to-phi map
    phi_map = {var: {} for var in def_map.keys()}
    for variable in sorted(def_map.keys()):
        stack = list(def_map[variable]) # can be queue or stack
        while stack:
            def_block = stack.pop()
            for frontier_block in dom_frontier[def_block]:
                if frontier_block not in phi_map[variable]:
                    phi_instr = {'dest': variable,
                                 'type': type_map[variable],
                                 'op': 'new_phi',
                                 'args': [],
                                 'labels': []}
                    bb = block_map[frontier_block]
                    block_map[frontier_block] = bb[0:1] + [phi_instr] + bb[1:]
                    phi_map[variable][frontier_block] = phi_instr
                    stack.append(frontier_block)

var_stacks = {}
name_map = {}
def rename_all(entry_label, block_map, succs, immediate_dominance, func):
    global var_stacks, name_map

    # 1) build var_stacks, function arguments should be inited.
    func_args = func['args'] if 'args' in func else []
    for arg in func_args:
        var_stacks[arg['name']] = [arg['name']]
    var_stacks['__undefined'] = ['__undefined']
    for block in block_map.values():
        for instr in block:
            if 'dest' not in instr or instr['dest'] in var_stacks:
                continue
            var_stacks[instr['dest']] = ['__undefined']
    if DEBUG:
        for k, v in var_stacks.items():
            print("var_stacks[{}] = {}".format(k, v))

    # 2) name_map
    name_map = {k: 0 for k in var_stacks.keys()}

    if DEBUG:
        print(var_stacks)
    # 3) rename from entry block
    rename(entry_label, block_map, succs, immediate_dominance)


def rename(label, block_map, succs, immediates):
    global var_stacks, name_map
    pop_cnt = {k: 0 for k in var_stacks.keys()}

    # process normal instructions
    block = block_map[label]
    for instr in block:
        if 'args' in instr and instr['op'] != 'new_phi':
            new_args = []
            for arg_name in instr['args']:
                new_args.append(var_stacks[arg_name][-1])
            instr['args'] = new_args
        if 'dest' in instr:
            var_name = instr['dest']
            new_name = str(var_name) + '.' + str(name_map[var_name])
            name_map[var_name] += 1
            instr['new_dest'] = new_name
            var_stacks[var_name].append(new_name)
            pop_cnt[var_name] += 1
    block_map[label] = block
    if DEBUG:
        print("locally processed:", label, block)

    # process generated phi (new_phi) instructions
    for succ_label in sorted(succs[label]):
        succ = block_map[succ_label]
        for instr in succ:
            if 'op' not in instr or instr['op'] != 'new_phi':
                continue
            var_name = instr['dest']
            instr['args'].append(var_stacks[var_name][-1])
            instr['labels'].append(label)

    if DEBUG:
        print("block {}'s imme".format(label), immediates[label])
    for imme in immediates[label]:
        rename(imme, block_map, succs, immediates)

    for var_name, count in pop_cnt.items():
        for _ in range(count):
            var_stacks[var_name].pop()

def to_ssa(entry_lbl, block_map, func, dom_frontier, tree, succs):
    phi_node_insertion(block_map, dom_frontier)
    rename_all(entry_lbl, block_map, succs, tree, func)
    for block in block_map.values():
        for instr in block:
            if 'new_dest' in instr:
                instr['dest'] = instr['new_dest']
                instr.pop('new_dest')
            if 'op' in instr and instr['op'] == 'new_phi':
                instr['op'] = 'phi'

def reform_blocks(block_list, block_map):
    label_list = [block[0]['label'] for block in block_list]
    return [block_map[label] for label in label_list]

def main():
    global DEBUG
    bril = json.load(sys.stdin)
    DEBUG = len(sys.argv) > 1 and sys.argv[1] == 'DEBUG'
    for func in bril['functions']:
        blocks, block_map = form_blocks(func['instrs'])
        succs, preds = form_cfg(blocks, [k for k in block_map.keys()])
        dom = dom_algorithm(succs, preds, block_map)
        frontier = dom_frontier(preds, dom)
        tree = immediate_dominance(dom)
        entry_label = blocks[0][0]['label']
        to_ssa(entry_label, block_map, func, frontier, tree, succs)
        blocks = reform_blocks(blocks, block_map)
        func['instrs'] = list(itertools.chain(*blocks))

    if not DEBUG:
        json.dump(bril, sys.stdout, indent=2, sort_keys=True)


if __name__ == '__main__':
    main()
