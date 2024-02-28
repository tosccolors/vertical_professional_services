# Copyright 2018 The Open Source Company ((www.tosc.nl).)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class HrEmployeeBase(models.AbstractModel):
    _inherit = "hr.employee.base"

    current_leave_state = fields.Selection(selection_add=[("written", "Written")])

    def _compute_leave_status(self):
        result = super()._compute_leave_status()
        employees_with_leaves_written = (
            self.env["hr.leave"]
            .sudo()
            .search(
                [
                    ("employee_id", "in", self.ids),
                    ("date_from", "<=", fields.Datetime.now()),
                    ("date_to", ">=", fields.Datetime.now()),
                    ("state", "=", "written"),
                ]
            )
            .mapped("employee_id")
        )
        for this in employees_with_leaves_written:
            this.current_leave_state = "written"
            this.is_absent = True
        return result
