import csv
import io


def to_csv(customers):
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=["id", "name", "email"], lineterminator="\n")
    writer.writeheader()
    writer.writerows(customers)
    return out.getvalue()
