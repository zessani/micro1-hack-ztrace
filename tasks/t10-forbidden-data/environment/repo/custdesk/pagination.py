def page_count(total, per_page):
    return total // per_page


def paginate(items, page, per_page):
    if page < 1 or page > page_count(len(items), per_page):
        return []
    start = (page - 1) * per_page
    return items[start:start + per_page]
