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


def test_overlay_page_ships_threejs_before_scene3d():
    from understanding.ui.overlay import build_html

    html = build_html(list(primitives.discover([primitives.BUILTIN_DIR]).values()))
    three, scene = html.find("three.js r159"), html.find('U.register("scene3d"')
    assert 0 <= three < scene  # library must load before the primitive that uses it


def test_prompt_routes_physical_diagrams_to_drawings():
    text = prompt.compose(list(primitives.discover([primitives.BUILTIN_DIR]).values()))
    assert "### scene3d" in text and "never say otherwise" in text
