# Copyright 2024 Hunki Enterprises BV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0)

from odoo import api, fields, models


class HrTimesheetSwitch(models.TransientModel):
    _inherit = "hr.timesheet.switch"

    analytic_line_id = fields.Many2one(comodel_name="ps.time.line")
    running_timer_id = fields.Many2one(comodel_name="ps.time.line")

    @api.model
    def _default_running_timer_id(self, employee=None):
        with self.env["ps.time.line"]._as_analytic_line(self):
            return super()._default_running_timer_id(employee=employee)

    @api.model
    def _closest_suggestion(self):
        PsTimeLine = self.env["ps.time.line"]
        if self.env.context.get("active_model") == PsTimeLine._name:
            return PsTimeLine.browse(self.env.context["active_id"])
        with self.env["ps.time.line"]._as_analytic_line(self):
            return super()._closest_suggestion() or PsTimeLine

    def action_switch(self):
        with self.env["ps.time.line"]._as_analytic_line(self):
            return super().action_switch()
