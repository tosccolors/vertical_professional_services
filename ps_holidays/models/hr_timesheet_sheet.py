# Copyright 2018 The Open Source Company ((www.tosc.nl).)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import datetime, timedelta

from odoo import _, models
from odoo.exceptions import ValidationError

from odoo.addons.resource.models.resource import HOURS_PER_DAY


class HrTimesheetSheet(models.Model):
    _inherit = "hr_timesheet.sheet"

    def merge_leave_request(self, date, data, time_lines):
        previous_date = datetime.strftime(date - timedelta(days=1), "%Y-%m-%d")
        domain = [
            ("date_to", "=", previous_date),
            ("employee_id", "=", self.employee_id.id),
            ("state", "=", "validate"),
        ]
        previous_leave_request = self.env["hr.leave"].search(domain)
        if previous_leave_request:
            # Merge LR by updating date_to and number_of_hours_temp
            num_of_days = (
                data["number_of_hours_display"]
                + previous_leave_request.number_of_hours_display
            ) / HOURS_PER_DAY
            previous_leave_request.with_context(leave_skip_state_check=True).write(
                {
                    "date_to": date,
                    "number_of_days": num_of_days,
                    "ps_time_line_ids": [(4, line.id) for line in time_lines],
                }
            )
        else:
            # Create new LR from timesheet
            self.env["hr.leave"].with_context(leave_skip_state_check=True).create(data)

    def create_leave_request(self, leave_type, time_lines):
        hours = sum(time_lines.mapped("unit_amount"))
        date = min(time_lines.mapped("date"))
        # Data to create leave requests from timesheet
        data = {
            "name": "Time report",
            "number_of_hours_display": hours,
            "number_of_days": hours / HOURS_PER_DAY,
            "holiday_status_id": leave_type,
            "state": "validate",
            "date_from": date,
            "date_to": date,
            "employee_id": self.employee_id.id,
            "ps_time_line_ids": [(6, 0, time_lines.ids)],
        }
        # Domain to get LR available in the same date period
        domain = [
            ("date_from", "<=", date),
            ("date_to", ">=", date),
            ("employee_id", "=", self.employee_id.id),
            ("state", "not in", ["cancel", "refuse"]),
            ("holiday_status_id", "=", leave_type),
        ]
        leave_request = (
            self.env["hr.leave"]
            .with_context(leave_skip_state_check=True)
            .search(domain)
        )
        if leave_request:
            date_start = leave_request.date_from.date()
            date_end = leave_request.date_to.date()

            if date_start == date_end:
                leave_request.write({"state": "draft"})
                leave_request.unlink()
                self.merge_leave_request(date, data, time_lines)

            elif date_start != date_end:
                if date_start == date:
                    # Update LR with date_from
                    leave_request.write({"date_from": date + timedelta(days=1)})
                    self.merge_leave_request(date, data, time_lines)

                if date_start != date:
                    if date_end == date:
                        leave_request.write(
                            {
                                "date_from": date_start,
                                "date_to": date - timedelta(days=1),
                            }
                        )
                        leave_request.copy(default=data)
                    if date_end != date:
                        # Update LR with date_from
                        leave_request.write({"date_from": date + timedelta(days=1)})
                        self.merge_leave_request(date, data, time_lines)
                        splitted_leave_request = leave_request.copy(
                            default={"state": leave_request.state}
                        )
                        # Update LR with date_to
                        splitted_leave_request.write(
                            {
                                "date_to": date - timedelta(days=1),
                                "date_from": date_start,
                                "ps_time_line_ids": [
                                    (4, line.id) for line in time_lines
                                ],
                            }
                        )
        if not leave_request:
            self.env["hr.leave"].with_context(leave_skip_state_check=True).create(data)

    def get_leave_type(self, hour):
        leave_types = self.env["hr.leave.type"].search(
            [("has_valid_allocation", "=", True)],
        )
        if not leave_types:
            raise ValidationError(
                _(
                    "Please create some leave types to apply for leave.\n"
                    "Note: For one of the selected project the Holiday Consumption is true."
                )
            )
        leave_type = False
        for lt in leave_types:
            if not leave_type and lt.virtual_remaining_leaves > hour:
                leave_type = lt.id
                break
        if not leave_type:
            leave_type = leave_types[-1].id
        return leave_type

    def action_timesheet_done(self):
        res = super().action_timesheet_done()
        if self.timesheet_ids:
            date_from = self.date_start
            for i in range(7):
                date = date_from + timedelta(days=i)
                time_lines = self.env["ps.time.line"].search(
                    [
                        ("date", "=", date),
                        ("sheet_id", "=", self.id),
                        ("sheet_id.employee_id", "=", self.employee_id.id),
                        ("project_id.holiday_consumption", "=", True),
                    ]
                )
                hours = sum(time_lines.mapped("unit_amount"))
                if hours:
                    hours = min(hours, HOURS_PER_DAY)
                    leave_type = self.get_leave_type(hours)
                    self.create_leave_request(leave_type, time_lines)
        return res

    def action_timesheet_draft(self):
        res = super().action_timesheet_draft()
        leave_request = self.mapped("timesheet_ids.leave_ids")
        if leave_request:
            leave_request.write({"state": "draft"})
            leave_request.unlink()
        return res
