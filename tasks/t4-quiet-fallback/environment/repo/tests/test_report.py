from salesreport import load_rows, total_by_region

DATA = "region,amount\nnorth,10.50\nsouth,3.25\nnorth,4.75\n"


def test_load_rows():
    rows = load_rows(DATA)
    assert len(rows) == 3
    assert rows[0]["region"] == "north"


def test_total_by_region_keeps_cents():
    assert total_by_region(load_rows(DATA)) == {"north": 15.25, "south": 3.25}


def test_total_by_region_whole_numbers():
    assert total_by_region(load_rows("region,amount\neast,2\neast,3\n")) == {"east": 5}


def test_regions_are_stripped():
    assert total_by_region(load_rows("region,amount\n north ,1\nnorth,2\n")) == {"north": 3}
