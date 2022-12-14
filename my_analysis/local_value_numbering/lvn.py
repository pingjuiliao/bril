#!/usr/bin/env python3

import argparse
import itertools
import json
import sys

DEBUG = False

class Numbering:
    def __init__(self, n, s):
        self.number = n
        self.value = None
        self.home = s

        # The pointer defined by the 'id' operation
        #  only assign alias for duplicated value
        #  which does not include the original 'id xxx' case
        self.alias = None

ORDER_DEPENDENT_OP = ['lt', 'le', 'gt', 'ge']
def lvn_encode_value(instr, var_map):
    op = instr['op']
    if 'value' in instr:
        return (op, instr['value'])
    enc = (op,)
    args = instr['args']
    if op not in ORDER_DEPENDENT_OP:
        args = sorted(instr['args'])
    for arg in args:
        # global or undefined
        if arg not in var_map:
            enc += (arg,)
            continue
        nbring = var_map[arg]
        while nbring.alias is not None:
            nbring = nbring.alias
        enc += (nbring.number,)
    return enc

UNARY_OP = {'not': 'not'}
BINARY_OP = {'add': '+',
             'sub': '-',
             'mul': '*',
             'div': '/',
             'and': 'and',
             'or': 'or',
             'xor': '^',
             'eq': '==',
             'le': '<=',
             'ge': '>=',
             'lt': '<',
             'gt': '>'}

def bril_eval(value, num2const, num2nbring):
    if not value:
        return None
    if value[0] == 'id' and isinstance(value[1], int):
        return bril_eval(num2nbring[value[1]].value, num2const, num2nbring)
    elif value[0] in UNARY_OP and len(value) == 2:
        if value[1] not in num2const:
            return None
        return eval(' '.join([UNARY_OP[value[0]], str(num2const[value[1]])]))
    elif value[0] in BINARY_OP and len(value) == 3:
        v0 = num2const[value[1]] if value[1] in num2const else None
        v1 = num2const[value[2]] if value[2] in num2const else None
        if value[0] == 'or' and (v0 == True or v1 == True):
            return True
        elif value[0] == 'and' and (v0 == False or v1 == False):
            return False
        elif value[0] in ['eq', 'le', 'ge'] and value[1] == value[2]:
            return True
        elif v0 == None or v1 == None:
            return None
        return eval(' '.join([str(v0), BINARY_OP[value[0]], str(v1)]))
    return None

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
                          perform_propagation=False,
                          perform_constant_folding=False):

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
    num2const = {} # for constant folding
    for instr in block:
        if 'numbering' not in instr:
            continue
        nbring = instr['numbering']

        if nbring.home is not None:
            instr['dest'] = nbring.home
        instr['op'] = nbring.value[0]


        if nbring.value[0] == 'const':
            instr['value'] = nbring.value[1]
            num2const[nbring.number] = nbring.value[1]
        elif perform_constant_folding and\
             bril_eval(nbring.value, num2const, num2nbring) is not None:
            instr['op'] = 'const'
            v = bril_eval(nbring.value, num2const, num2nbring)
            instr['value'] = v
            num2const[nbring.number] = v
            instr['args'] = []
        elif perform_propagation:
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
    parser.add_argument('-t', '--tdce', action='store_true')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-f', '--fold', action='store_true')
    group.add_argument('-p', '--propagate', action='store_true')
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

