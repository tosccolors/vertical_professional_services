# Copyright 2018 The Open Source Company ((www.tosc.nl).)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    customer_charge_expense = fields.Boolean("Charge Expense To Customer", index=True)

    def _prepare_analytic_lines(self):
        result = super()._prepare_analytic_lines()
        for this, vals in zip(self, result):
            vals["customer_charge_expense"] = this.customer_charge_expense
        return result
