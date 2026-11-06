import fastcsv


def load_rows(text):
    return fastcsv.read_rows(text)


def total_by_region(rows):
    totals = {}
    for row in rows:
        region = row["region"].strip()
        totals[region] = totals.get(region, 0) + int(float(row["amount"]))
    return totals
