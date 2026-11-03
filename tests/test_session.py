import threading

from understanding.brains import Turn
from understanding.session import Session


class FakeBrain:
    def __init__(self, chunks):
        self.chunks = chunks
        self.turns: list[Turn] = []

    def start(self): ...
    def interrupt(self): ...
    def reset(self): ...
    def close(self): ...

    def stream(self, turn):
        self.turns.append(turn)
        yield from self.chunks


class Recorder:
    def __init__(self):
        self.ops, self.done = [], threading.Event()

    def begin(self, q, frame):
        self.ops.append(("begin", q, frame))

    def apply(self, op):
        self.ops.append(op)

    def end(self, error):
        self.ops.append(("end", error))
        self.done.set()


def test_session_streams_ops_to_renderer():
    brain = FakeBrain(['{"op":"card","title":"T"}\n{"op":"sa', 'y","text":"hi"}'])
    r = Recorder()
    s = Session(brain, [], r)
    s.start()
    s.submit("what is this?")
    assert r.done.wait(5)
    assert r.ops == [
        ("begin", "what is this?", None),
        {"op": "card", "title": "T"},
        {"op": "say", "text": "hi"},
        ("end", None),
    ]
    assert brain.turns[0].question == "what is this?"
