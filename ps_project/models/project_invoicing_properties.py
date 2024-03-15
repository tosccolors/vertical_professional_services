# Copyright 2018 The Open Source Company ((www.tosc.nl).)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ProjectInvoicingProperties(models.Model):
    _name = "project.invoicing.properties"
    _description = "Project invoicing properties"

    name = fields.Char("Project Invoice Period", required=True)
    expenses = fields.Boolean("Expenses", default=True)
    specs_invoice_report = fields.Boolean("Add specs attachment to invoice")
    actual_time_spent = fields.Boolean("Invoice Actual Time Spent")
    actual_expenses = fields.Boolean("Invoice Expenses")
    actual_costs = fields.Boolean("Invoice Costs")
    fixed_amount = fields.Boolean("Invoice Fixed Amount")
    fixed_hours = fields.Boolean("Invoice Fixed Hours")
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        required=True,
        default=lambda self: self.env.user.company_id.currency_id,
    )
    specs_type = fields.Selection(
        [
            ("per_month", "Per Month"),
            ("per_day", "Per Day"),
            ("both", "Monthly/Daily Specification"),
        ],
        string="Specification Type",
        default="per_month",
    )
