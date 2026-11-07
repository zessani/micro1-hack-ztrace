def normalize_email(email):
    if email is None:
        return None
    return email.strip()


def normalize_plan(plan):
    plan = (plan or "free").strip().lower()
    return {"pro+": "pro_plus", "biz": "business"}.get(plan, plan)


def display_name(name):
    return " ".join(name.split()) if name else name
