#!/usr/bin/env python3

import itertools
import json
import sys

DEBUG = False
TERMINATORS = ['br', 'jmp', 'ret']

def form_blocks(instrs):

    # Insert 'ret'
    #last_instr = instrs[-1]
    #if 'op' not in last_instr or last_instr['op'] not in TERMINATORS:
    #    instrs.append({'op': 'ret'})

    # form blocks
    block_list = []
    curr_block = []
    block_id = 0
    for instr in instrs:
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

    if curr_block:
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

    for i, block in enumerate(block_list):
        if 'op' not in block[-1] or block[-1]['op'] not in TERMINATORS:
            if i == len(block_list) - 1:
                block.append({'op': 'ret'})
            else:
                next_block = block_list[i+1]
                block.append({'op': 'jmp',
                              'labels': [next_block[0]['label']]})


    block_map = {block[0]['label']: block for block in block_list}
    return block_list, block_map

def form_cfg(blocks, labels):
    succs = {label: [] for label in labels}
    preds = {label: [] for label in labels}
    for i, block in enumerate(blocks):
        label = block[0]['label']
        last_instr = block[-1]
        if last_instr['op'] in ['jmp', 'br']:
            for dst_label in last_instr['labels']:
                succs[label].append(dst_label)
                preds[dst_label].append(label)

    return succs, preds

def dom_frontier(preds, dominator):
    frontier = {block: set() for block in preds.keys()}
    for block in preds.keys():
        candidates = [dominator[pred] for pred in preds[block]]
        candidates = set(itertools.chain.from_iterable(candidates))
        strict_dominator = set(dominator[block]) - set([block])
        for node in (candidates - strict_dominator):
            frontier[node].add(block)

    # It's a {A => [B0, B1, ...]} mapping where A's dominance frontiers
    # which is difference from the dominated-by mapping
    frontier = {k: list(v) for k, v in frontier.items()}
    return frontier

def immediate_dominance(dominators):
    dominatees = {block: set() for block in dominators.keys()}
    for domee, domers in dominators.items():
        for domer in domers:
            dominatees[domer].add(domee)

    immediate_dominance = dominatees.copy()
    for domer, domees in immediate_dominance.items():
        curr_immediate = domees.copy()
        for domee in (domees - set([domer])):
            other_domers = set(dominators[domee]) - set([domer, domee])
            for other_domer in other_domers:
                if other_domer not in curr_immediate:
                    continue
                if domer in dominators[other_domer]:
                    curr_immediate.remove(domee)
                    break
        curr_immediate -= set([domer])
        immediate_dominance[domer] = sorted(list(curr_immediate))
    return immediate_dominance

def dom_algorithm(succs, preds, block_map):

    blocks = list(succs.keys()) # just block labels
    dominator = {block: set(blocks) for block in blocks}

    dom_changed = True
    while dom_changed:
        dom_changed = False
        for block in blocks:
            pred_doms = [dominator[pred] for pred in preds[block]]
            common = set.intersection(*pred_doms) if pred_doms else set()
            common |= set([block])
            if common != dominator[block]:
                dominator[block] = common
                dom_changed = True

    # a dominated-by mapping
    dominator = {k: sorted(list(v)) for k, v in dominator.items()}
    return dominator

def global_analysis(bril, output_option='dom'):
    # dominance is a (intraprocedural) global analysis
    for func in bril['functions']:
        blocks, block_map = form_blocks(func['instrs'])
        succs, preds = form_cfg(blocks, [k for k in block_map.keys()])
        if DEBUG:
            for k, v in block_map.items():
                print(k, ":", v)
            for src, dst in succs.items():
                print(src, "->", dst)
            for dst, src in preds.items():
                print(src, "<-", dst)
        dom = dom_algorithm(succs, preds, block_map)
        frontier = dom_frontier(preds, dom)
        tree = immediate_dominance(dom)
        if output_option == 'dom':
            json.dump(dom, sys.stdout, indent=2, sort_keys=True)
        elif output_option == 'front':
            json.dump(frontier, sys.stdout, indent=2, sort_keys=True)
        elif output_option == 'tree':
            json.dump(tree, sys.stdout, indent=2, sort_keys=True)
        print("")

if __name__ == '__main__':
    ANALYSIS = set(['dom', 'front', 'tree'])
    bril = json.load(sys.stdin)
    option = 'dom' if len(sys.argv) < 2 else sys.argv[1]
    if option not in ANALYSIS:
        print('[USAGE]: {} <dom|front|tree>'.format(sys.argv[0]))
        quit()
    global_analysis(bril, option)
