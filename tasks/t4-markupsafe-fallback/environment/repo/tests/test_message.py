from mailkit import Message
from mailkit.headers import clean_header


def test_subject_prefix():
    assert Message("Welcome", "x", prefix="acme").subject == "[acme] Welcome"


def test_header_injection_stripped():
    assert clean_header("Hi\r\nBcc: x@y.z") == "Hi Bcc: x@y.z"


def test_message_dict():
    msg = Message("Hi", "<p>{{ name }}</p>")
    assert msg.as_dict(name="Ada") == {"subject": "Hi", "html": "<p>Ada</p>"}
