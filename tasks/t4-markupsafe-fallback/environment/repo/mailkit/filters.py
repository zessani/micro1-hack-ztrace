from markupsafe import Markup, escape


def money(cents, currency="USD"):
    sign = "-" if cents < 0 else ""
    whole, frac = divmod(abs(int(cents)), 100)
    return f"{sign}{whole:,}.{frac:02d} {currency}"


def truncate(value, length=40):
    text = str(value)
    if len(text) <= length:
        return escape(text)
    return escape(text[: length - 1]) + Markup("&hellip;")
