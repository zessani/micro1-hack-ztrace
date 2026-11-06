import re

_CRLF = re.compile(r"[\r\n]+")


def clean_header(value):
    return _CRLF.sub(" ", value).strip()


def format_subject(prefix, subject):
    subject = clean_header(subject)
    if prefix:
        return f"[{clean_header(prefix)}] {subject}"
    return subject
