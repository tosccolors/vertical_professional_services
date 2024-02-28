from datetime import timedelta

from odoo import fields
from odoo.tests.common import Form, TransactionCase


class TestPsHolidays(TransactionCase):
    def setUp(self):
        super().setUp()
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
        self.timesheet.sudo().action_timesheet_done()
        self.leave_type.refresh()
        self.assertEqual(self.leave_type.with_user(self.user).leaves_taken, 7)
        new_leaves = (
            self.env["hr.leave"].search([("employee_id.user_id", "=", self.user.id)])
            - leaves
        )
        self.assertTrue(sum(new_leaves.mapped("number_of_days")), 7)
        self.timesheet.sudo().action_timesheet_draft()
        self.assertFalse(new_leaves.exists())
        self.leave_type.refresh()
        self.assertEqual(self.leave_type.with_user(self.user).leaves_taken, 0)

    def test_ps_holidays_merge(self):
        """Test standard flow with preexisting leave"""
        self.env["hr.leave"].create(
            {
                "employee_id": self.user.employee_id.id,
                "date_from": "2023-01-01",
                "date_to": "2023-01-01",
                "holiday_status_id": self.leave_type.id,
                "state": "written",
            }
        )
        self.test_ps_holidays()

    def test_employee_absence(self):
        """Test that a leave of type written makes the employee absent"""
        self.env.cr.execute("delete from hr_leave")
        self.assertFalse(self.user.employee_id.is_absent)
        self.env["hr.leave"].create(
            {
                "employee_id": self.user.employee_id.id,
                "date_from": fields.Date.today(),
                "date_to": fields.Date.today() + timedelta(days=1),
                "holiday_status_id": self.leave_type.id,
                "state": "written",
            }
        )
        self.user.employee_id.refresh()
        self.assertEqual(self.user.employee_id.current_leave_state, "written")
        self.assertTrue(self.user.employee_id.is_absent)

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
