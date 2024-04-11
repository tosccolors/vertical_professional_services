# Copyright 2018 The Open Source Company ((www.tosc.nl).)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    planning_week = fields.Boolean(string="Planning by week")
    timesheet_optional = fields.Boolean("Timesheet optional")
    timesheet_no_8_hours_day = fields.Boolean("Timesheet no 8 hours day")
    overtime_hours = fields.Float(
        compute="_compute_overtime_hours", string="Overtime Hours"
    )
    product_id = fields.Many2one(
        "product.product",
        string="Fee Rate Product",
        domain=lambda self: self._get_category_domain(),
    )
    fee_rate = fields.Float(
        compute="_compute_fee_rate",
        string="Fee Rate",
        readonly=True,
    )
    no_ott_check = fields.Boolean("8 Hours OTT possible", help="No Overtime Check")

    @api.depends("product_id.list_price")
    def _compute_fee_rate(self):
        for this in self:
            this.fee_rate = this.product_id.list_price

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

    def action_view_overtime_entries(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "ps_timesheet_invoicing.ps_time_line_action"
        )
        ids = (
            self.env["hr_timesheet.sheet"]
            .search([("employee_id", "=", self.id)])
            .mapped("overtime_line_id.id")
        )
        return dict(
            action,
            domain=[("id", "in", ids)],
        )
