# Copyright 2018 The Open Source Company ((www.tosc.nl).)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class HrLeaveType(models.Model):
    _inherit = "hr.leave.type"

    is_leave_type_of_wizard = fields.Boolean(string="Is leave type of wizard")

    def get_employees_days(self, employee_ids):
        result = super().get_employees_days(employee_ids)

        requests = self.env["hr.leave"].search(
            [
                ("employee_id", "in", employee_ids),
                ("state", "=", "written"),
                ("holiday_status_id", "in", self.ids),
            ]
        )

        for request in requests:
            status_dict = result[request.employee_id.id][request.holiday_status_id.id]
            status_dict["leaves_taken"] += (
                request.number_of_hours_display
                if request.leave_type_request_unit == "hour"
                else request.number_of_days
            )
            status_dict["remaining_leaves"] -= (
                request.number_of_hours_display
                if request.leave_type_request_unit == "hour"
                else request.number_of_days
            )
        return result
