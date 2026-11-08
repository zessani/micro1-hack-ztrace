def display_name(row):
    return f"{row['name']} <{row['email'].lower()}>"


def ticket_label(row):
    return f"#{row['id']} [{row['status']}] {row['subject']}"


def plural(n, word):
    return f"{n} {word}" if n == 1 else f"{n} {word}s"
