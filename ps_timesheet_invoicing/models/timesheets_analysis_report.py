# Copyright 2024 Hunki Enterprises BV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class TimesheetsAnalysisReport(models.Model):
    _inherit = "timesheets.analysis.report"

    @api.model
    def _from(self):
        return super()._from().replace("account_analytic_line", "ps_time_line")

    @api.model
    def _where(self):
        return (
            super()._where()
            + " AND product_uom_id=%s AND (planned IS NULL or planned=False)"
            % self.env.ref("uom.product_uom_hour").id
        )
