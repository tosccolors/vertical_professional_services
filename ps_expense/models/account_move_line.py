# Copyright 2018 The Open Source Company ((www.tosc.nl).)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    customer_charge_expense = fields.Boolean("Charge Expense To Customer", index=True)
    customer_expense_charged = fields.Boolean(
        "Charged",
        store=True,
        readonly=False,
        compute="_compute_customer_expense_charged",
        help="Indicates whether this expense has been charged to the customer. "
        "The flag is set automatically when this line's analytic line is added to an analytic "
        "invoice, or set manually for other means of invoicing an expense",
    )

    @api.depends("analytic_line_ids.ps_invoice_id")
    def _compute_customer_expense_charged(self):
        for this in self:
            this.customer_expense_charged = bool(this.analytic_line_ids.ps_invoice_id)

    def _prepare_analytic_line(self):
        result = super()._prepare_analytic_line()
        for this, vals in zip(self, result):
            if this.partner_id and self.env.context.get("ps_expense_set_partner_uid"):
                user = (
                    self.env["res.users"].search(
                        [("partner_id", "=", this.partner_id.id)], limit=1
                    )
                    or self.env.user
                )
                vals["user_id"] = user.id
            vals["customer_charge_expense"] = this.customer_charge_expense
        return result
