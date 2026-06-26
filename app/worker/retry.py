# import random


# def calculate_delay(attempt: int) -> float:
#     base = 2 ** max(attempt - 1, 0)
#     jitter = random.uniform(0.8, 1.2)
#     return base * jitter


import random


def calculate_delay(attempt: int) -> float:
    """
    Exponential backoff with ±20% jitter.

    Doc spec (Section 3.3):
        Attempt 1 fails → retry after ~1s   (2^0 = 1)
        Attempt 2 fails → retry after ~2s   (2^1 = 2)
        Attempt 3 fails → retry after ~4s   (2^2 = 4)
        Attempt 4 fails → DLQ

    Worker passes retry_count (already incremented before this call), so:
        attempt=1 → base=2^(1-1)=1
        attempt=2 → base=2^(2-1)=2
        attempt=3 → base=2^(3-1)=4

    FIX: original used max(attempt-1, 0) which is identical, but the
    jitter range was correct.  Keeping the same formula; this file now
    explicitly documents the mapping so it cannot drift from the spec.
    """
    base = 2 ** max(attempt - 1, 0)
    jitter = random.uniform(0.8, 1.2)
    return base * jitter