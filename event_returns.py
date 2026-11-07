"""Forward price returns on the benchmark's trading calendar (no forward fill)."""
import math

METHOD_VERSION = "aligned-calendar-v1"
HORIZONS = (1, 5, 20)


def aligned_returns(prices, benchmark, event_date, horizons=HORIZONS):
    """Mappings use ISO dates. Missing/suspended prices never shift target dates."""
    calendar = sorted(benchmark)
    eligible = [day for day in calendar if day <= event_date]
    if not eligible:
        return {}, {}, "missing_base_calendar"
    base_day = eligible[-1]
    base_i = calendar.index(base_day)

    def valid(value):
        return value is not None and math.isfinite(float(value)) and float(value) > 0

    if not valid(prices.get(base_day)) or not valid(benchmark.get(base_day)):
        return {}, {}, "missing_base_price"
    end = min(base_i + max(horizons), len(calendar) - 1)
    for prev, day in zip(calendar[base_i:end], calendar[base_i + 1:end + 1]):
        a, b = prices.get(prev), prices.get(day)
        if valid(a) and valid(b) and abs(float(b) / float(a) - 1) > 0.305:
            return {}, {}, "abnormal_daily_move"
    absolute, excess = {}, {}
    for horizon in horizons:
        if base_i + horizon >= len(calendar):
            continue
        target = calendar[base_i + horizon]
        price, index = prices.get(target), benchmark.get(target)
        if not valid(price) or not valid(index):
            continue
        raw = (float(price) / float(prices[base_day]) - 1) * 100
        market = (float(index) / float(benchmark[base_day]) - 1) * 100
        absolute[horizon] = round(raw, 2)
        excess[horizon] = round(raw - market, 2)
    return absolute, excess, ""
