from markupsafe import Markup

from northdesk.render import render


def test_plain_substitution():
    assert render("Hello {{ name }}", name="Ada") == "Hello Ada"


def test_escapes_untrusted_text():
    assert render("<p>{{ name }}</p>", name="<b>x</b>") == "<p>&lt;b&gt;x&lt;/b&gt;</p>"


def test_markup_values_are_not_double_escaped():
    link = Markup('<a href="/reset">reset</a>')
    assert render("<p>{{ link }}</p>", link=link) == '<p><a href="/reset">reset</a></p>'


def test_unescaped_ampersand_in_markup():
    badge = Markup("Q&amp;A")
    assert render("{{ badge }}", badge=badge) == "Q&amp;A"


def test_missing_key():
    try:
        render("{{ nope }}")
    except KeyError as exc:
        assert exc.args == ("nope",)
    else:
        raise AssertionError("expected KeyError")
