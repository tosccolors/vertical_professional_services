# Copyright 2024 Hunki Enterprises BV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class HrEmployeeBase(models.AbstractModel):
    _inherit = "hr.employee.base"

    def _get_remaining_leaves(self):
        """
        Subtract leaves from types without mandatory allocation to allow for ME's
        holiday workflow
        """
        result = super()._get_remaining_leaves()
        extra_leaves = self.env["hr.leave"].read_group(
            [
                ("holiday_status_id.allocation_type", "=", "no"),
                ("holiday_status_id.active", "=", True),
                ("state", "=", "validate"),
                ("employee_id", "in", self.ids),
            ],
            ["number_of_days"],
            ["employee_id"],
        )
        for extra_leave in extra_leaves:
            result[extra_leave["employee_id"][0]] -= extra_leave["number_of_days"]
        return result
