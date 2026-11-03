from core.stats import mean, median, total

DATA = [1, 3, 5, 9]


def build_report():
    return {
        "total": total(DATA),
        "average": mean(DATA),
        "middle": median(DATA),
    }
