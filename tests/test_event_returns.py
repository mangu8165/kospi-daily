import unittest
import datetime as dt
from event_returns import aligned_returns


class CalendarReturnsTest(unittest.TestCase):
    def setUp(self):
        self.days = [(dt.date(2026, 1, 1) + dt.timedelta(days=i)).isoformat() for i in range(25)]
        self.market = {d: 100 + i for i, d in enumerate(self.days)}
        self.prices = {d: 100 + 2 * i for i, d in enumerate(self.days)}

    def test_same_target_dates_and_excess(self):
        r, x, flag = aligned_returns(self.prices, self.market, self.days[0])
        self.assertEqual((r[5], x[5], flag), (10, 5, ""))

    def test_missing_day_does_not_shift_horizon(self):
        del self.prices[self.days[1]]
        r, x, _ = aligned_returns(self.prices, self.market, self.days[0])
        self.assertNotIn(1, r)
        self.assertNotIn(1, x)
        self.assertEqual(r[5], 10)

    def test_zero_quote_is_missing(self):
        self.prices[self.days[5]] = 0
        r, _, flag = aligned_returns(self.prices, self.market, self.days[0])
        self.assertNotIn(5, r)
        self.assertEqual(flag, "")

    def test_missing_base_not_backfilled(self):
        del self.prices[self.days[2]]
        self.assertEqual(aligned_returns(self.prices, self.market, self.days[2])[2], "missing_base_price")

    def test_nontrading_event_uses_previous_calendar_day(self):
        del self.market[self.days[1]]
        r, _, _ = aligned_returns(self.prices, self.market, self.days[1])
        self.assertEqual(r[1], 4)

    def test_not_yet_mature_is_absent(self):
        r, _, _ = aligned_returns(self.prices, self.market, self.days[-1])
        self.assertEqual(r, {})

    def test_abnormal_move_excludes_event(self):
        self.prices[self.days[1]] = 200
        self.assertEqual(aligned_returns(self.prices, self.market, self.days[0])[2], "abnormal_daily_move")

    def test_nan_is_not_a_zero_return(self):
        self.prices[self.days[1]] = float('nan')
        self.assertNotIn(1, aligned_returns(self.prices, self.market, self.days[0])[0])


if __name__ == '__main__':
    unittest.main()
