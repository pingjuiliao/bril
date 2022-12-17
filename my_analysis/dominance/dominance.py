#!/usr/bin/env python3

import itertools
import json
import sys

DEBUG = False
TERMINATORS = ['br', 'jmp', 'ret']

def form_blocks(func):

    block_list = []
    curr_block = []
    block_id = 0
    for instr in func['instrs']:
        if 'op' in instr:
            if not curr_block:
                block_id += 1
                curr_block.append({"label": "b" + str(block_id)})
            curr_block.append(instr)
            if instr['op'] in TERMINATORS:
                if curr_block:
                    block_list.append(curr_block)
                curr_block = []
        else:
            if curr_block:
                block_list.append(curr_block)
            curr_block = [instr]

    if len(curr_block) > 1:
        block_list.append(curr_block)

    should_insert_entry_block = False
    first_block_label = block_list[0][0]['label']
    for block in block_list:
        last_instr = block[-1]
        if 'op' in last_instr and 'labels' in last_instr:
            for label in last_instr['labels']:
                should_insert_entry_block |= (label == first_block_label)

    if should_insert_entry_block:
        entry_block = [{'label': 'entry1'},
                       {'op': 'jmp', 'labels': [first_block_label],
                        }]
        block_list = [entry_block] + block_list

    block_map = {block[0]['label']: block for block in block_list}

    return block_list, block_map

def form_cfg(blocks, labels):
    succs = {label: [] for label in labels}
    preds = {label: [] for label in labels}
    for i, block in enumerate(blocks):
        label = block[0]['label']
        last_instr = block[-1]
        if 'op' not in last_instr or \
           last_instr['op'] not in TERMINATORS:
            if i + 1 < len(blocks):
                next_label = blocks[i+1][0]['label']
                succs[label].append(next_label)
                preds[next_label].append(label)
        elif last_instr['op'] in ['jmp', 'br']:
            for dst_label in last_instr['labels']:
                succs[label].append(dst_label)
                preds[dst_label].append(label)

        # no need to handle 'ret'

    return succs, preds

def hello(a, b, c):
    print('hello')

def dom_algorithm(succs, preds, block_map):

    blocks = list(succs.keys()) # just block labels
    dominance = {block: set(blocks) for block in blocks}

    dom_changed = True
    while dom_changed:
        dom_changed = False
        for block in blocks:
            pred_doms = [dominance[pred] for pred in preds[block]]
            common = set.intersection(*pred_doms) if pred_doms else set()
            common |= set([block])
            if common != dominance[block]:
                dominance[block] = common
                dom_changed = True

    json.dump({k: sorted(list(v)) for k, v in dominance.items()},
              sys.stdout, indent=2, sort_keys=True)

def global_analysis(bril, analysis):
    # dominance is a (intraprocedural) global analysis
    for func in bril['functions']:
        blocks, block_map = form_blocks(func)
        succs, preds = form_cfg(blocks, [k for k in block_map.keys()])
        if DEBUG:
            for k, v in block_map.items():
                print(k, ":", v)
            for src, dst in succs.items():
                print(src, "->", dst)
            for dst, src in preds.items():
                print(src, "<-", dst)
        analysis(succs, preds, block_map)
    print("")

if __name__ == '__main__':
    ANALYSIS = {'dom': dom_algorithm, 'front': hello, 'tree': hello}
    bril = json.load(sys.stdin)
    option = 'dom' if len(sys.argv) < 2 else sys.argv[1]
    if option not in ANALYSIS:
        print('[USAGE]: {} <dom|front|tree>'.format(sys.argv[0]))
        quit()
    global_analysis(bril, ANALYSIS[option])
