# tests/fakes.py
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Union


@dataclass
class FakeResponse:
    output_text: str


class FakeResponsesAPI:
    """
    Minimal shim for client.responses.create(...) used by our agents.

    It returns a sequence of outputs on consecutive calls.
    If calls exceed provided outputs, it repeats the last output.
    """
    def __init__(self, outputs: List[Union[str, dict]]):
        self._outputs: List[str] = []
        for o in outputs:
            self._outputs.append(o if isinstance(o, str) else __import__("json").dumps(o))
        self._i = 0

    def create(self, model, input):
        if not self._outputs:
            raise RuntimeError("FakeResponsesAPI needs at least 1 output.")
        if self._i >= len(self._outputs):
            return FakeResponse(self._outputs[-1])
        out = self._outputs[self._i]
        self._i += 1
        return FakeResponse(out)

    @property
    def call_count(self) -> int:
        return self._i


class FakeOpenAI:
    """
    Drop-in replacement for OpenAI client in tests:
      client = FakeOpenAI([plan1, plan2, ...])
      agent = SomeAgent(client=client)
    """
    def __init__(self, outputs: List[Union[str, dict]]):
        self.responses = FakeResponsesAPI(outputs)
