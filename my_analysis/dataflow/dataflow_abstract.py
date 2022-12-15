#!/usr/bin/env python3

import collections

class DataflowAnalysis:

    def init_set(self, func):
        raise NotImplementedError

    def gen(self, instr):
        raise NotImplementedError

    def kill(self, instr):
        raise NotImplementedError

    def is_forward(self) -> bool:
        raise NotImplementedError

    def transfer(self, flow_in, block):
        raise NotImplementedError

    def merge(self, flow_in_blocks):
        raise NotImplementedError

    def form_blocks(self, instrs):
        TERMINATORS = ['br', 'jmp', 'ret']
        ID = 0

        curr_block = []
        for instr in instrs:
            if 'op' in instr:
                if instr['op'] in TERMINATORS:
                    curr_block.append(instr)
                    yield curr_block
                    curr_block = []
                else:
                    if not curr_block:
                        ID += 1
                        curr_block.append({'label': "b" + str(ID)})
                    curr_block.append(instr)
            else:
                if len(curr_block) > 1:
                    yield curr_block
                curr_block = [instr]

        if len(curr_block) > 1:
            yield curr_block

    def form_cfg(self, blocks):
        """
        Form successors, predecessors for blocks:-
        """
        TERMINATORS = ['br', 'jmp', 'ret']
        succs = {block[0]['label']: [] for block in blocks}
        preds = {block[0]['label']: [] for block in blocks}
        block_map = {}
        for i, block in enumerate(blocks):
            label = block[0]['label']
            block_map[label] = block
            if block[-1]['op'] not in TERMINATORS:
                if i + 1 < len(blocks):
                    next_label = blocks[i+1][0]['label']
                    succs[label].append(next_label)
                    preds[next_label].append(label)
                continue

            terminator = block[-1]
            if terminator == 'ret':
                pass
            else:
                for br_label in terminator['labels']:
                    succs[label].append(br_label)
                    preds[br_label].append(label)
        return block_map, preds, succs

    def worklist_algorithm(self, func):
        DEBUG = False
        instrs = func['instrs']
        blocks = list(self.form_blocks(instrs))
        block_map, preds, succs = self.form_cfg(blocks)

        if DEBUG:
            for block in blocks:
                print("block:", block, "\n")
            print("=" * 32)
            for k, v in preds.items():
                print(v, "<-", k)
            print("=" * 32)
            for k, v in succs.items():
                print(k, "->", v)
            print("=" * 32)

        in_ = {block[0]['label']: self.init_set(func) for block in blocks}
        out = {block[0]['label']: self.init_set(func) for block in blocks}

        if self.is_forward():
            flow_in, flow_out = in_, out
        else:
            flow_in, flow_out = out, in_
            preds, succs = succs, preds

        worklist = collections.deque(succs.keys())
        while worklist:
            block = worklist.popleft()
            flow_in[block] = self.merge([flow_out[pred] \
                                         for pred in preds[block]])
            transferred = self.transfer(flow_in[block], block_map[block])
            if flow_out[block] != transferred:
                flow_out[block] = transferred
                for succ in succs[block]:
                    worklist.append(succ)


        return in_, out, list(succs.keys())
