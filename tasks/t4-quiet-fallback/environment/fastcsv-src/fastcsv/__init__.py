import csv
import io
import warnings

try:
    from . import _speedups
    HAVE_C = True
except ImportError:
    _speedups = None
    HAVE_C = False
    warnings.warn(
        "fastcsv: C extension unavailable, using pure-Python fallback",
        RuntimeWarning,
        stacklevel=2,
    )


def read_rows(text):
    return list(csv.DictReader(io.StringIO(text)))
