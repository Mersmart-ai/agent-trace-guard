def total(numbers):
    return sum(numbers)


def mean(numbers):
    return total(numbers) / len(numbers)


def median(numbers):
    ordered = sorted(numbers)
    return ordered[len(ordered) // 2]
