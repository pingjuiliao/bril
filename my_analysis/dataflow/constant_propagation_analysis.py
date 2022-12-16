#!/usr/bin/env python3
from dataflow_abstract import DataflowAnalysis

class ConstantPropagationAnalysis(DataflowAnalysis):
    BINARY_OPS = {'add': '+', 'sub': '-', 'mul': '*', 'div': '/'}

    def init_set(self, func):
        return dict()

    def is_forward(self) -> bool:
        return True

    def merge(self, flow_in_blocks):
        result = dict()
        for prop_consts in flow_in_blocks:
            for k, v in prop_consts.items():
                if k not in result:
                    result[k] = v
                elif v == result[k]:
                    pass
                else:
                    result[k] = '?'
        return result

    def gen(self, instr, const_map):
        if 'dest' not in instr:
            return dict()

        if 'op' not in instr:
            return dict()

        ## from here 'dest', 'op' should be included
        if instr['op'] == 'const':
            return {instr['dest']: instr['value']}
        elif instr['op'] in self.BINARY_OPS:
            for arg in instr['args']:
                if arg not in const_map or const_map[arg] == '?':
                    return {instr['dest']: '?'}
            return {instr['dest']: self.bril_eval(instr)}
        return {instr['dest']: '?'}

    def kill(self, instr, const_map):
        if 'dest' in instr:
            return {instr['dest']: '?'}
        return dict()

    def transfer(self, flow_in, block):
        block = block if self.is_forward() else block[::-1]
        # Transfer(x) = GEN(instr) | (x - KILL(instr))
        # therefore, KILL first, GEN later
        flow_out = flow_in.copy()
        for instr in block:
            for k in self.kill(instr, flow_out).keys():
                if k in flow_out:
                    flow_out[k] = '?'
            for k, v in self.gen(instr, flow_out).items():
                flow_out[k] = v
        return flow_out


    ## specific for const propagation
    def bril_eval(self, instr):
        if instr['op'] in self.BINARY_OPS:
            arg0, arg1 = instr['args']
            return eval(arg0 + self.BINARY_OPS[instr['op']] + arg1)
        return -1337

