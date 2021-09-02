#!/usr/bin/env python3
"""sttp: state transition table parser

A tiny library for parsing state transition tables.

This library offers the following:
    - parse a state transition table described in csv format
    - export the state transition table in json format
    - export a visualization of the state machine graph that it encodes

For more (e.g. stt csv format), checkout the README.md file.
"""
import argparse
import csv
import inspect
import json

from collections import OrderedDict
import graphviz

CSV_EXTENSION = '.csv'
GRAPHVIZ_RENDER_FORMATS = graphviz.backend.FORMATS

cli = argparse.ArgumentParser()
cli.add_argument('stt_file', help='.csv state transition table file')
subcommands = cli.add_subparsers(dest='subcommand')
subcommands.required = True


def subcommand(func):
    parser = subcommands.add_parser(func.__name__.replace(
        '_', '-'), help=func.__doc__.partition('.')[0])
    argspec = inspect.getfullargspec(func)
    if argspec.defaults is None:
        argspec_defaults_len = 0
        argspec_defaults = set()
    else:
        argspec_defaults_len = len(argspec.defaults)
        argspec_defaults = argspec.defaults
    positional_count = len(argspec.args) - argspec_defaults_len
    func_args = [
        arg for arg in argspec.args[:positional_count] if arg != 'self']
    func_kwargs = dict(zip(argspec.args[positional_count:], argspec_defaults))
    for pos_arg in func_args:
        parser.add_argument(
            f"{pos_arg.replace('_', '-')}")
    for optional_arg, default in func_kwargs.items():
        argument_flag = f"--{optional_arg.replace('_', '-')}"
        argument_kwargs = {}
        if default is None:
            pass
        elif isinstance(default, bool):
            argument_kwargs['action'] = 'store_true'
        else:
            argument_kwargs['default'] = default
            if optional_arg == 'format':
                argument_kwargs['choices'] = GRAPHVIZ_RENDER_FORMATS
        parser.add_argument(argument_flag, **argument_kwargs)
    return func


class STTPError(Exception):
    """"""


class STTP:
    """State transition table parser class."""
    _SOURCE_HEADER = 'SOURCE'
    _DEST_HEADER = 'DEST'
    _TRIGGER_HEADER = 'TRIGGER'
    _HEADER_ROW = [_SOURCE_HEADER, _DEST_HEADER, _TRIGGER_HEADER]
    _INVALID_ROW_MSG = 'Invalid row'
    _SOURCE_KEY = _SOURCE_HEADER.lower()
    _DEST_KEY = _DEST_HEADER.lower()
    _TRIGGER_KEY = _TRIGGER_HEADER.lower()
    _TRANSITION_KEYS = [_SOURCE_KEY, _DEST_KEY, _TRIGGER_KEY]
    _TRIGGER_KEY = _TRIGGER_HEADER.lower()
    _EVENT_PREFIX = '_'
    _EVENT_STR = 'EVT'
    _TIMED_TRANSITION_PREFIX = '__'

    def __init__(self, stt_csv_file: str):
        if not stt_csv_file.endswith(CSV_EXTENSION):
            stt_csv_file += CSV_EXTENSION
        self._stt_csv_file = stt_csv_file
        self.__stt = None
        self.__json = None
        self.__dot = None

    @property
    def _stt(self):
        if self.__stt is None:
            self.__stt = self._parse()
        return self.__stt

    @property
    def _json(self):
        if self.__json is None:
            dict_stt = {'transitions': self._stt}
            self.__json = json.dumps(dict_stt, indent=4)
        return self.__json

    @property
    def _dot(self):
        if self.__dot is None:
            dot = graphviz.Digraph()
            for transition in self._stt:
                trigger = transition[self._TRIGGER_KEY]
                source = transition[self._SOURCE_KEY]
                dest = transition[self._DEST_KEY]
                dot.node(source)
                dot.node(dest)
                dot.edge(source, dest, label=trigger)
            self.__dot = dot
        return self.__dot

    def _parse_error(self, row, message):
        raise STTPError(f'{self._INVALID_ROW_MSG}: {row}. {message}')

    def _validate_stt(self, stt):
        assert isinstance(stt, list)
        for transition in stt:
            is_transition_dict = isinstance(transition, dict)
            assert is_transition_dict
            assert all([key in transition for key in self._TRANSITION_KEYS])

    def _parse(self):
        stt = []
        with open(self._stt_csv_file) as f:
            stt_csv = csv.reader(f)
            header_row = next(iter(stt_csv))
            if header_row != self._HEADER_ROW:
                raise STTPError('Invalid header format: '
                                f'must be: {self._HEADER_ROW}')
            previous_source = None
            for row in stt_csv:
                source = row[0]
                dest = row[1]
                trigger = row[2]
                if not source and previous_source is None:
                    self._parse_error(row, 'Undefined previous source state.')
                elif not source:
                    source = previous_source
                else:
                    previous_source = source
                if not dest:
                    self._parse_error(row, 'Undefined destination state.')
                if not trigger:
                    trigger = f'{self._EVENT_PREFIX}{dest}'
                if trigger[:2] == self._TIMED_TRANSITION_PREFIX:
                    trigger_suffix = trigger[2:]
                    try:
                        seconds = int(trigger_suffix)
                    except ValueError:
                        self._parse_error(
                            row,
                            f"A '{self._TIMED_TRANSITION_PREFIX}' prefix "
                            'indicates a timed transition and must be'
                            'followed by a number (seconds). '
                            f'Invalid value: {trigger_suffix}'
                        )
                    trigger = f'(after {seconds} sec.)'
                elif trigger[0] == self._EVENT_PREFIX:
                    trigger = f'{self._EVENT_STR}_{trigger[1:]}'
                transition = OrderedDict({
                    self._TRIGGER_KEY: trigger,
                    self._SOURCE_KEY: source,
                    self._DEST_KEY: dest,
                })
                stt.append(transition)
        self._validate_stt(stt)
        return stt

    def dictify(self):
        """Return a dictionary representation of the state machine."""
        d = {}
        for t in self._stt:
            d.setdefault(t['source'], {})[t['dest']] = t['trigger']
        return d

    @subcommand
    def jsonify(self):
        """Print the json representation of the state machine."""
        print(self._json)

    @subcommand
    def dotify(self):
        """Print the DOT language source of the state machine."""
        print(self._dot.source)

    @subcommand
    def visualize(self, filename, format='pdf', view=False):
        """Visualize the state machine.

        Args:
            format (str): 'pdf', 'png', 'svg', etc. (default: 'pdf')
            view (boolean): automatically open the resulting file
                (default: False)
        """
        self._dot.render(filename.strip(f'.{format}'), format=format,
                         view=view, cleanup=True)


if __name__ == '__main__':
    args = cli.parse_args()
    sttp = STTP(args.stt_file)
    command = getattr(sttp, args.subcommand.replace('-', '_'))
    del args.stt_file
    del args.subcommand
    command(**vars(args))
