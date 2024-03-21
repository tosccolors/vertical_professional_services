# Copyright 2023 Hunki Enterprises BV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"

    ps_invoice_id = fields.Many2one(
        "ps.invoice", string="Invoice Reference", ondelete="set null", index=True
    )
    ps_invoice_line_id = fields.Many2one(
        "account.move.line",
        string="Invoiced in line",
    )
