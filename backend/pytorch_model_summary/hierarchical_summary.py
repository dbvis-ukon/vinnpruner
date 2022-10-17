"""
    This is a fork from: https://github.com/graykode/modelsummary
"""

from functools import reduce

from torch.nn.modules.module import _addindent


def hierarchical_summary(model, print_summary=False):

    def repr(model):
        # We treat the extra repr like the sub-module, one item per line
        extra_lines = []
        extra_repr = model.extra_repr()
        # empty string will be split into list ['']
        if extra_repr:
            extra_lines = extra_repr.split('\n')
        child_lines = []
        total_params = 0
        for key, module in model._modules.items():
            if module is None:
                continue
            mod_str, num_params = repr(module)
            mod_str = _addindent(mod_str, 2)
            child_lines.append('(' + key + '): ' + mod_str)
            total_params += num_params
        lines = extra_lines + child_lines

        for name, p in model._parameters.items():
            if p is not None:
                total_params += reduce(lambda x, y: x * y, p.shape)

        main_str = model._get_name() + '('
        if lines:
            # simple one-liner info, which most builtin Modules will use
            if len(extra_lines) == 1 and not child_lines:
                main_str += extra_lines[0]
            else:
                main_str += '\n  ' + '\n  '.join(lines) + '\n'

        main_str += ')'
        main_str += ', {:,} params'.format(total_params)
        return main_str, total_params

    string, count = repr(model)

    # Building hierarchical output
    _pad = int(max(max(len(_) for _ in string.split('\n')) - 20, 0) / 2)
    lines = list()
    lines.append('=' * _pad + ' Hierarchical Summary ' + '=' * _pad + '\n')
    lines.append(string)
    lines.append('\n\n' + '=' * (_pad * 2 + 22) + '\n')

    str_summary = '\n'.join(lines)
    if print_summary:
        print(str_summary)

    return str_summary, count
