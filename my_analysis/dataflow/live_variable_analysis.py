#!/usr/bin/env python3
from dataflow_abstract import DataflowAnalysis

class LiveVariableAnalysis(DataflowAnalysis):
    """
    This implementation does not distinguish reassignment.
    """
    def init_set(self, func):
        return set()

    def is_forward(self):
        return False

    def merge(self, flow_in_blocks):
        result = set()
        for lived in flow_in_blocks:
            result |= lived
        return result

    def gen(self, instr):
        if 'args' not in instr:
            return set()
        return set([arg for arg in instr['args']])

    def kill(self, instr):
        """
        definition kill liveness
        """
        if 'dest' not in instr:
            return set()
        return set([instr['dest']])

    def transfer(self, flow_in, block):
        block = block if self.is_forward() else block[::-1]
        flow_out = flow_in # no need to flow_in.copy because assignemnt
        for instr in block:
            flow_out = self.gen(instr) | (flow_out - self.kill(instr))
        return flow_out
