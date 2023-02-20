#!/usr/bin/env python3

import itertools
import json
import sys

def tdce(block):
    """
    In-place trivial dead code elimination (TDCE)
    """
    pending_tdce = True

    while pending_tdce:
        used = set()
        pending_tdce = False

        for instr in block:
            if 'args' not in instr:
                continue
            for arg in instr['args']:
                used.add(arg)

        for instr in block:
            if 'dest' in instr and instr['dest'] not in used:
                block.remove(instr)
                pending_tdce = True

def local_drop_kill_dce(block):
    # very last definitions
    last_def = {}

    for instr in block:
        ## remove definitions for uses
        if 'args' in instr:
            for arg in instr['args']:
                if arg in last_def:
                    del last_def[arg]
        ## add definitions for definitions
        if 'dest' not in instr:
            continue
        if instr['dest'] in last_def:
            block.remove(last_def[instr['dest']])
        last_def[instr['dest']] = instr


def get_blocks(body):

    TERMINATORS = "jmp", "br", "ret"
    curr_block = []

    for instr in body:
        if 'op' in instr:
            curr_block.append(instr)

            if instr['op'] in TERMINATORS:
                yield curr_block
                curr_block = []
        else:
            if curr_block:
                yield curr_block
            curr_block = [instr]

    if curr_block:
        yield curr_block

def main():

    prog = json.load(sys.stdin)

    for func in prog['functions']:
        blocks = list(get_blocks(func['instrs']))
        for block in blocks:
            tdce(block)
            local_drop_kill_dce(block)
        func['instrs'] = list(itertools.chain(*blocks))

    json.dump(prog, sys.stdout, indent=2, sort_keys=True)

if __name__ == "__main__":
    main()
