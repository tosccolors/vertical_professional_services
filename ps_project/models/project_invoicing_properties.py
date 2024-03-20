# Copyright 2018 The Open Source Company ((www.tosc.nl).)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ProjectInvoicingProperties(models.Model):
    _name = "project.invoicing.properties"
    _description = "Project invoicing properties"

    name = fields.Char("Project Invoice Period", required=True)
    specs_invoice_report = fields.Boolean("Add specs attachment to invoice")
    actual_time_spent = fields.Boolean("Invoice Actual Time Spent")
    actual_expenses = fields.Boolean("Invoice Expenses")
    actual_costs = fields.Boolean("Invoice Costs")
    fixed_amount = fields.Boolean("Invoice Fixed Amount")
    specs_type = fields.Selection(
        [
            ("per_month", "Per Month"),
            ("per_day", "Per Day"),
            ("both", "Monthly/Daily Specification"),
        ],
        string="Specification Type",
        default="per_month",
    )

    @api.onchange("actual_time_spent")
    def _onchange_actual_time_spent(self):
        if self.actual_time_spent:
            self.fixed_amount = False

    @api.onchange("fixed_amount")
    def _onchange_fixed_amount(self):
        if self.fixed_amount:
            self.actual_time_spent = False
