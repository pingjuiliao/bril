#!/usr/bin/env python3

import json
import sys

from dataflow_abstract import DataflowAnalysis
from live_variable_analysis import LiveVariableAnalysis
from constant_propagation_analysis import ConstantPropagationAnalysis
from reaching_definition_analysis import ReachingDefinitionAnalysis

def set_format(data):
    if isinstance(data, set):
        if data:
            return ', '.join([v for v in sorted(data)])
        else:
            return '∅'
    elif isinstance(data, dict):
        if data:
            return ', '.join(['{}: {}'.format(k, v) for k, v in sorted(data.items())])
        else:
            return '∅'
    else:
        return str(data)

def get_analysis(arg_string: str) -> DataflowAnalysis:
    analysis = None
    if arg_string == 'defined':
        analysis = ReachingDefinitionAnalysis()
    elif arg_string == 'live':
        analysis = LiveVariableAnalysis()
    elif arg_string == 'cprop':
        analysis = ConstantPropagationAnalysis()
    return analysis

def main():
    if len(sys.argv) < 2:
        print("ERROR: please specify analysis")
        quit()
    bril = json.load(sys.stdin)
    analysis = get_analysis(sys.argv[1])
    if analysis is None:
        print("[ERROR]: Analysis is not supported")
        quit()

    for func in bril['functions']:
        in_, out, labels = analysis.worklist_algorithm(func)
        for block_label in labels:
            print("{}:".format(block_label))
            print('  in: ', set_format(in_[block_label]))
            print('  out:', set_format(out[block_label]))

if __name__ == '__main__':
    main()
