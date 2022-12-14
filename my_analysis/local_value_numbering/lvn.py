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

        ## The pointer defined by the 'id' operation
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

def propagation(num, num2nbring):
    nbring = None
    while isinstance(num, int):
        op = num2nbring[num].value[0]
        if op == 'const':
            nbring = num2nbring[num]
            break
        elif op == 'id':
            nbring = num2nbring[num]
            num = nbring.value[1]
        else:
            break
    return nbring

# The algorithm requires at least 2 loops to complete since it need to
# know whether the variable will be overwritten
# e.g.
#    a: int = const 2;
#    print a;
#    a: int = const 4;
#    print a;

def local_value_numbering(block,
                          perform_tdce=False,
                          perform_id_propagation=False,
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
            reference = val2nbring[value]
            nbring.value = ("id", reference.number)
            nbring.alias = reference
        else:
            nbring.value = value

        # only add to map if it's not in map
        if value not in val2nbring:
            val2nbring[value] = nbring
        num2nbring.append(nbring)

        # add to instr
        instr['numbering'] = nbring

    ## Debug
    if DEBUG:
        print("DEBUG mode")
        for instr in block:
            if 'numbering' not in instr:
                continue
            nbring = instr['numbering']
            alias = nbring.alias
            if alias is None:
                print(nbring.number, nbring.value, nbring.home)
            else:
                print(nbring.number, nbring.value, nbring.home, "-> (",
                      alias.number, alias.value, alias.home, ")")
    ## Step 2: reconstruct the program (in-place)
    ##    At this point, we haven't change the source code(instr) yet
    for instr in block:
        if 'numbering' not in instr:
            continue
        nbring = instr['numbering']

        if nbring.home is not None:
            instr['dest'] = nbring.home
        instr['op'] = nbring.value[0]

        if nbring.value[0] == 'const':
            instr['value'] = nbring.value[1]
        elif perform_id_propagation:
            new_args = []
            for arg in nbring.value[1:]:
                nbring = propagation(arg, num2nbring)
                if nbring is not None:
                    if instr['op'] == 'id' and nbring.value[0] == 'const':
                        instr['op'] = nbring.value[0]
                        instr['value'] = nbring.value[1]
                    elif nbring.value[0] == 'id':
                        new_args.append(nbring.value[1])
                    else:
                        new_args.append(nbring.home)
                else:
                    new_args.append(arg)

            if instr['op'] != 'const':
                instr['args'] = new_args
        else:
            new_args = []
            for arg in nbring.value[1:]:
                if isinstance(arg, int): # local numbering
                    new_args.append(num2nbring[arg].home)
                else: # global or undefined, which is a string
                    new_args.append(arg)
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
    parser.add_argument('-p', '--propagate', action='store_true')
    args = parser.parse_args()

    bril = json.load(sys.stdin)
    for func in bril['functions']:
        blocks = list(form_blocks(func['instrs']))
        for block in blocks:
            local_value_numbering(block, args.tdce, args.propagate, args.fold)
        func['instrs'] = list(itertools.chain(*blocks))
    if DEBUG:
        quit()
    json.dump(bril, sys.stdout, indent=2, sort_keys=True)

if __name__ == '__main__':
    main()

