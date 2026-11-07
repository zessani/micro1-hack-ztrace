def money(cents, currency="USD"):
    return "%s %d.%02d" % (currency, cents // 100, cents % 100)
