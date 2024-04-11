# Copyright 2018 The Open Source Company ((www.tosc.nl).)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class HrTimesheetSheet(models.Model):
    _inherit = "hr_timesheet.sheet"

    @api.depends("end_mileage", "business_mileage", "starting_mileage")
    def _compute_mileage_new(self):
        for sheet in self.with_context(sheet_write=True):
            m = sheet.end_mileage - sheet.business_mileage - sheet.starting_mileage
            sheet.private_mileage = m if m > 0 else 0

    private_mileage_new = fields.Integer(
        compute="_compute_mileage_new", string="Private Mileage", store=True
    )
