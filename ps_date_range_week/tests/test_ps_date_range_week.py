from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestPsDateRangeWeek(TransactionCase):
    def setUp(self):
        super().setUp()
        self.range_type = self.env.ref("ps_date_range_week.date_range_calender_week")

    def test_search(self):
        a_range = self.env["date.range"].create(
            {
                "name": "A testrange",
                "type_id": self.range_type.id,
                "date_start": "2023-01-01",
                "date_end": "2023-12-31",
            }
        )
        found_range = self.env.ref("base.main_company").find_daterange_cw("2023-01-02")
        self.assertEqual(a_range, found_range)

    def test_unlink(self):
        with self.assertRaises(UserError):
            self.range_type.unlink()
