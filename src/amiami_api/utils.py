from datetime import date, datetime


def first_day_of_next_month() -> date:
    now = datetime.now()
    if now.month == 12:
        return now.replace(day=1, month=1, year=now.year + 1).date()
    return now.replace(day=1, month=now.month + 1).date()
