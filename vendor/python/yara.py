"""Minimal yara shim for offline runtime.

This shim keeps scanner execution functional when native yara-python is not
available. It intentionally returns no YARA matches.
"""

from __future__ import annotations


class Error(Exception):
    pass


class SyntaxError(Error):
    pass


class _CompiledRules:
    def __init__(self, filepaths=None):
        self.filepaths = filepaths or {}

    def match(self, data=None, **kwargs):
        return []


def compile(filepath=None, filepaths=None, source=None, externals=None):
    return _CompiledRules(filepaths=filepaths)
