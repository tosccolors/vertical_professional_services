# Copyright 2024 Hunki Enterprises BV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0)

from odoo import models


class HrTimesheetTimeControlMixin(models.AbstractModel):
    _inherit = "hr.timesheet.time_control.mixin"

    def _compute_show_time_control(self):
        with self.env["ps.time.line"]._as_analytic_line(self):
            return super()._compute_show_time_control()

    def button_end_work(self):
        with self.env["ps.time.line"]._as_analytic_line(self):
            return super().button_end_work()
