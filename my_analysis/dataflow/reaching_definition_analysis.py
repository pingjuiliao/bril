#!/usr/bin/env python3
from dataflow_abstract import DataflowAnalysis

class ReachingDefinitionAnalysis(DataflowAnalysis):
    """
    This implementation does not distinguish assignment over the same variable.
    """
    def init_set(self, func):
        if 'args' not in func:
            return set()
        return set([arg['name'] for arg in func['args']])

    def is_forward(self) -> bool:
        return True

    def merge(self, flow_in_blocks):
        result = set()
        for defined in flow_in_blocks:
            result |= defined
        return result

    def gen(self, instr):
        if 'dest' in instr:
            return set([instr['dest']])
        return set()

    def kill(self, instr):
        if 'dest' in instr:
            return set([instr['dest']])
        return set()

    def transfer(self, flow_in, block):
        block = block if self.is_forward() else block[::-1]
        flow_out = flow_in # no need to flow_in.copy()
        for instr in block:
            flow_out = self.gen(instr) | (flow_out - self.kill(instr))
        return flow_out


if __name__ == '__main__':
    d = ReachingDefinitionAnalysis()

