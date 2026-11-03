from core.stats import mean, total

DATA = [3, 5, 7]


def build_report():
    return {"total": total(DATA), "average": mean(DATA[:-1])}
