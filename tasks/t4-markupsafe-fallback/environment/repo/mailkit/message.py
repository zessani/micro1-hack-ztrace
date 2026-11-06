from .headers import format_subject
from .render import render


class Message:
    def __init__(self, subject, template, prefix=None):
        self.subject = format_subject(prefix, subject)
        self.template = template

    def body(self, **context):
        return render(self.template, **context)

    def as_dict(self, **context):
        return {"subject": self.subject, "html": str(self.body(**context))}
