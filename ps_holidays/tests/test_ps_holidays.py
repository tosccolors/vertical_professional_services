from odoo.tests.common import Form, TransactionCase


class TestPsHolidays(TransactionCase):
    def setUp(self):
        super().setUp()
        self.admin = self.env.ref("base.user_admin")
        self.user = self.env.ref("base.user_demo")
        self.timesheet = self.env["hr_timesheet.sheet"].with_user(self.user).create({})
        self.leave_type = self.env.ref("hr_holidays.holiday_status_cl")
        self.leave_type.validity_start = "2023-01-01"

    def test_ps_holidays(self):
        """Test standard flow"""
        with Form(self.timesheet) as timesheet_form:
            timesheet_form.add_line_project_id = self.env.ref(
                "ps_holidays.project_holidays"
            )
            timesheet_form.add_line_task_id = self.env.ref("ps_holidays.task_holidays")
        self.timesheet.button_add_line()
        self.timesheet.with_context(sheet_write=True)._compute_line_ids()
        with Form(self.timesheet) as timesheet_form:
            for i in range(7):
                with timesheet_form.line_ids.edit(i) as day_line:
                    day_line.unit_amount = 8
        self.timesheet.action_timesheet_confirm()
        leaves = self.env["hr.leave"].search(
            [("employee_id.user_id", "=", self.user.id)]
        )
        self.timesheet.with_user(self.admin).action_timesheet_done()
        self.leave_type.refresh()
        self.assertEqual(self.leave_type.with_user(self.user).leaves_taken, 7)
        new_leaves = (
            self.env["hr.leave"].search([("employee_id.user_id", "=", self.user.id)])
            - leaves
        )
        self.assertTrue(sum(new_leaves.mapped("number_of_days")), 7)
        # the 6 are from demo data sick leave, which doesn't have allocation
        self.assertEqual(self.user.employee_id.allocation_used_count, 7 + 6)
        self.timesheet.with_user(self.admin).action_timesheet_draft()
        self.assertFalse(new_leaves.exists())
        self.leave_type.refresh()
        self.assertEqual(self.leave_type.with_user(self.user).leaves_taken, 0)
        self.assertEqual(self.user.employee_id.allocation_used_count, 6)

    def test_ps_holidays_replace(self):
        """Test standard flow with preexisting leave"""
        self.env["hr.leave"].with_context(leave_skip_state_check=True).create(
            {
                "employee_id": self.user.employee_id.id,
                "date_from": "2023-01-01",
                "date_to": "2023-01-01",
                "holiday_status_id": self.leave_type.id,
                "state": "validate",
            }
        )
        self.test_ps_holidays()

    def test_ps_holidays_merge(self):
        """Test standard flow with preexisting leave"""
        self.leave_type.validity_start = "2022-12-31"
        self.env["hr.leave"].with_context(leave_skip_state_check=True).create(
            [
                {
                    "employee_id": self.user.employee_id.id,
                    "date_from": "2022-12-31",
                    "date_to": "2022-12-31",
                    "holiday_status_id": self.leave_type.id,
                    "state": "validate",
                },
                {
                    "employee_id": self.user.employee_id.id,
                    "date_from": "2023-01-01",
                    "date_to": "2023-01-01",
                    "holiday_status_id": self.leave_type.id,
                    "state": "validate",
                },
            ]
        )
        self.test_ps_holidays()

    def test_wizard(self):
        """Test the allocation via wizard"""
        allocations = self.env["hr.leave.allocation"].search([])
        wizard = self.env["hr.employee.wizard"].new(
            {
                "leave_hours": 8 * 30,
            }
        )
        wizard.create_holiday(self.user.employee_id)
        new_allocation = self.env["hr.leave.allocation"].search([]) - allocations
        self.assertEqual(new_allocation.number_of_days, 30)

    def test_negative(self):
        """Test the creating negative allocations works as expected"""
        remaining_leaves = self.leave_type.with_user(self.user).remaining_leaves
        self.env["hr.leave.allocation"].create(
            {
                "holiday_type": "employee",
                "employee_id": self.user.employee_id.id,
                "number_of_days": -8,
                "holiday_status_id": self.leave_type.id,
                "state": "validate",
            }
        )
        self.env.clear()
        self.assertEqual(
            self.leave_type.with_user(self.user).remaining_leaves, remaining_leaves - 8
        )
