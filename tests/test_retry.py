from app.worker.retry import calculate_delay


def test_calculate_delay_uses_exponential_backoff_window():
    delay = calculate_delay(3)
    assert 3.2 <= delay <= 4.8
