# Copyright 2018 The Open Source Company ((www.tosc.nl).)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    @api.depends("product_id")
    def _compute_fee_rate(self):
        self.fee_rate = self.product_id and self.product_id.list_price or 0.0

    @api.model
    def _get_category_domain(self):
        return [
            (
                "categ_id",
                "=",
                self.env.ref("ps_timesheet_invoicing.product_category_fee_rate").id,
            )
        ]

    def _compute_overtime_hours(self):
        for this in self:
            this.overtime_hours = sum(
                self.env["hr_timesheet.sheet"]
                .search([("employee_id", "=", this.id)])
                .mapped("overtime_hours")
            )

    planning_week = fields.Boolean(string="Planning by week")
    timesheet_optional = fields.Boolean("Timesheet optional")
    timesheet_no_8_hours_day = fields.Boolean("Timesheet no 8 hours day")
    overtime_hours = fields.Float(
        compute="_compute_overtime_hours", string="Overtime Hours"
    )
    product_id = fields.Many2one(
        "product.product", string="Fee Rate Product", domain=_get_category_domain
    )
    fee_rate = fields.Float(compute=_compute_fee_rate, string="Fee Rate", readonly=True)
    no_ott_check = fields.Boolean("8 Hours OTT possible", help="No Overtime Check")
