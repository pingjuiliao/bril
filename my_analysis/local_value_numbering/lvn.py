#!/usr/bin/env python3

import argparse
import itertools
import json
import sys

DEBUG = False

class Numbering:
    def __init__(self, n, s):
        self.number = n
        self.home = s
        # value should be add after conflicting names
        self.value = None
        self.alias = None

def lvn_encode_value(instr, var_map):
    op = instr['op']
    if 'value' in instr:
        return (op, instr['value'])
    enc = (op,)
    for arg in sorted(instr['args']):
        # global or undefined
        if arg not in var_map:
            enc += (arg,)
            continue
        nbring = var_map[arg]
        while nbring.alias is not None:
            nbring = nbring.alias
        enc += (nbring.number,)
    return enc

# The algorithm requires at least 2 loops to complete since it need to
# know whether the variable will be overwritten
# e.g.
#    a: int = const 2;
#    print a;
#    a: int = const 4;
#    print a;

def local_value_numbering(block,
                          perform_tdce=False,
                          perform_const_folding=False):

    # First loop: get overwritten vars
    val2nbring = {}
    num2nbring = []
    home2nbring = {}

    ## step 1: construct numbering list & resolve conflicting variable(home) names
    for instr in block:
        if 'op' not in instr or instr['op'] == 'jmp':
            continue
        if 'dest' not in instr:
            value = lvn_encode_value(instr, home2nbring)
            nbring = Numbering(-1, None)
            nbring.value = value
            instr['numbering'] = nbring
            continue

        # get variable(home) & assign its number
        home = instr['dest']
        nbring = Numbering(len(num2nbring), home)

        # handle variable conflicts
        if home in home2nbring:
            prev_nbring = home2nbring[home]
            home2nbring.pop(home)
            prev_nbring.home = "lvn." + str(prev_nbring.number)
            home2nbring[prev_nbring.home] = prev_nbring
        home2nbring[home] = nbring

        # Encode the value, and handle conflicts
        value = lvn_encode_value(instr, home2nbring)
        if value in val2nbring:
            nbring.value = ("id", val2nbring[value].number)
            nbring.alias = val2nbring[value]
        else:
            nbring.value = value
            val2nbring[value] = nbring
        num2nbring.append(nbring)

        # add to instr
        instr['numbering'] = nbring

    ## step1 debug
    if DEBUG:
        for instr in block:
            if 'numbering' not in instr:
                continue
            nbring = instr['numbering']
            print(nbring.number, nbring.value, nbring.home)

    ## Step 2: reconstruct the program (in-place)
    ##    At this point, we haven't change the source code(instr) yet
    for instr in block:
        if 'numbering' not in instr:
            continue
        nbring = instr['numbering']

        if nbring.home is not None:
            instr['dest'] = nbring.home
        instr['op'] = nbring.value[0]

        if instr['op'] == 'const':
            instr['value'] = nbring.value[1]
        else:
            new_args = []
            for new_arg in nbring.value[1:]:
                if isinstance(new_arg, int): # local numbering
                    new_args.append(num2nbring[new_arg].home)
                else: # global or undefined, which is a string
                    new_args.append(new_arg)
            instr['args'] = new_args
        del instr['numbering']

    ## Step 3: trivial dead code elimination (in-place)
    if not perform_tdce:
        return
    converged = False
    used = set()
    while not converged:
        converged = True

        for instr in block:
            if instr['op'] == 'id':
                continue
            if 'args' in instr:
                for arg in instr['args']:
                    used.add(arg)

        for instr in block:
            if 'dest' in instr and instr['dest'] not in used:
                block.remove(instr)
                converged = False
    return

def form_blocks(instrs):
    TERMINATORS = 'br', 'jmp', 'ret'
    curr_block = []
    for instr in instrs:
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

    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--fold', action='store_true')
    parser.add_argument('-t', '--tdce', action='store_true')
    parser.add_argument('-p', '--lookup', action='store_true')
    args = parser.parse_args()

    bril = json.load(sys.stdin)
    for func in bril['functions']:
        blocks = list(form_blocks(func['instrs']))
        for block in blocks:
            local_value_numbering(block, args.tdce, args.fold)
        func['instrs'] = list(itertools.chain(*blocks))
    if DEBUG:
        quit()
    json.dump(bril, sys.stdout, indent=2, sort_keys=True)

if __name__ == '__main__':
    main()

