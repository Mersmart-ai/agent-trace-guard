from core.stats import mean, total

DATA = [3, 5, 7]
SAMPLE = DATA[:-1]  # 采样窗口


def build_report():
    return {"total": total(DATA), "average": mean(SAMPLE)}
