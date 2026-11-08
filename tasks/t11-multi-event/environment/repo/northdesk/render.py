import re

from markupsafe import Markup, escape

_PLACEHOLDER = re.compile(r"\{\{\s*(\w+)\s*\}\}")


def render(template, **context):
    def substitute(match):
        name = match.group(1)
        if name not in context:
            raise KeyError(name)
        return str(escape(str(context[name])))

    return Markup(_PLACEHOLDER.sub(substitute, template))
