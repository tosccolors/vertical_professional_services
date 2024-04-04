# Copyright 2024 Hunki Enterprises BV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class PsTimeLine(models.Model):
    _inherit = "ps.time.line"

    leave_ids = fields.Many2many(
        comodel_name="hr.leave",
        relation="hr_leave_time_line_rel",
        column1="ps_time_line_id",
        column2="hr_leave_id",
        string="Holidays",
    )
