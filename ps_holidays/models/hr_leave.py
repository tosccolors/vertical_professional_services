# Copyright 2018 The Open Source Company ((www.tosc.nl).)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class HrLeave(models.Model):
    _inherit = "hr.leave"

    ps_time_line_ids = fields.Many2many(
        comodel_name="ps.time.line",
        relation="hr_leave_time_line_rel",
        column1="hr_leave_id",
        column2="ps_time_line_id",
        string="Time lines",
    )
