# Copyright 2018 The Open Source Company ((www.tosc.nl).)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models

from odoo.addons.resource.models.resource import HOURS_PER_DAY


class HREmployeeWizard(models.TransientModel):
    _inherit = "hr.employee.wizard"

    def create_holiday(self, employee_id):
        hr_leave_type = self.env["hr.leave.type"].search(
            [("is_leave_type_of_wizard", "=", True)], limit=1
        )
        allocation_data = {
            "holiday_status_id": hr_leave_type.id,
            "holiday_type": "employee",
            "employee_id": employee_id.id,
            "number_of_days": self.leave_hours / HOURS_PER_DAY,
            "state": "draft",
        }
        allocation = self.env["hr.leave.allocation"].create(allocation_data)
        allocation.action_confirm()
        allocation.action_validate()
        return True

    def create_all(self):
        result = super().create_all()
        employee = self.env["hr.employee"].browse(result["res_id"])
        self.create_holiday(employee)
        return result
