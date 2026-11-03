from understanding import primitives, prompt


def test_every_builtin_has_doc_and_renderer():
    found = primitives.discover([primitives.BUILTIN_DIR])
    assert {"card", "say", "pin", "box", "diagram", "step", "note", "svg", "timeline"} <= found.keys()
    for p in found.values():
        assert p.js.strip(), p.name
        assert '"op"' in p.doc, p.name


def test_user_dir_overrides_builtin(tmp_path):
    (tmp_path / "card.md").write_text('custom {"op":"card"}')
    (tmp_path / "card.js").write_text("// custom")
    found = primitives.discover([primitives.BUILTIN_DIR, tmp_path])
    assert found["card"].js == "// custom"


def test_prompt_contains_enabled_docs_only():
    found = primitives.discover([primitives.BUILTIN_DIR])
    text = prompt.compose(primitives.select(found, ["card", "say"]))
    assert "### card" in text and "### pin" not in text
