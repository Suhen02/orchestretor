import random


def calculate_delay(attempt: int) -> float:
    base = 2 ** max(attempt - 1, 0)
    jitter = random.uniform(0.8, 1.2)
    return base * jitter
