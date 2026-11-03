from understanding.protocol import OpStreamParser


def test_ops_emitted_only_when_line_completes():
    p = OpStreamParser()
    assert p.feed('{"op":"card","ti') == []
    assert p.feed('tle":"Hi"}\n{"op":"say",') == [{"op": "card", "title": "Hi"}]
    assert p.feed('"text":"yo"}') == []
    assert p.flush() == [{"op": "say", "text": "yo"}]


def test_tolerates_fences_prose_and_junk():
    p = OpStreamParser()
    ops = p.feed('```jsonl\n{"op":"note","text":"a"}\nplain words\n{"no_op":1}\n{broken\n```\n')
    assert ops == [{"op": "note", "text": "a"}, {"op": "say", "text": "plain words"}]
