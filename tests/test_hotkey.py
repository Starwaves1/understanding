from understanding.ui.hotkey import ModifierTap


class Clock:
    t = 0.0

    def __call__(self):
        return self.t


def make():
    c = Clock()
    return ModifierTap({"control", "option"}, 0.5, now=c), c


def test_tap_fires_on_release():
    tap, _ = make()
    assert not tap.modifiers({"control"})
    assert not tap.modifiers({"control", "option"})
    assert not tap.modifiers({"option"})
    assert tap.modifiers(set())


def test_chord_with_key_does_not_fire():
    tap, _ = make()
    tap.modifiers({"control", "option"})
    tap.key()
    assert not tap.modifiers(set())


def test_long_hold_does_not_fire():
    tap, c = make()
    tap.modifiers({"control", "option"})
    c.t = 2.0
    assert not tap.modifiers(set())


def test_extra_modifier_cancels():
    tap, _ = make()
    tap.modifiers({"control", "option"})
    tap.modifiers({"control", "option", "command"})
    assert not tap.modifiers(set())
