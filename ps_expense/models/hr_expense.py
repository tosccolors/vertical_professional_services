from odoo import api, fields, models


class HrExpense(models.Model):
    _inherit = "hr.expense"

    sheet_state = fields.Selection(
        related="sheet_id.state",
        string="Sheet Status",
        help="Expense Report State",
        store=True,
    )
    customer_charge_expense = fields.Boolean("Charge Expense To Customer", index=True)
    analytic_tag_ids = fields.Many2many(string="WKR")

    def _get_default_expense_sheet_values(self):
        """Allow creating expense sheet from expenses without product"""
        result = super()._get_default_expense_sheet_values()
        for vals in result:
            if not vals.get("operating_unit_id"):
                vals["operating_unit_id"] = self.mapped("operating_unit_id")[:1].id
        return result

    def action_view_sheet(self):
        res = super(HrExpense, self).action_view_sheet()
        res.setdefault("context", {})["form_view_initial_mode"] = "edit"
        return res

    @api.onchange("analytic_distribution", "operating_unit_id")
    def anaytic_account_change(self):
        for account_id in (self.analytic_distribution or {}).keys():
            account = self.env["account.analytic.account"].browse(int(account_id))
            if len(account.operating_unit_ids) == 1:
                self.operating_unit_id = account.operating_unit_ids

    def _prepare_move_line_vals(self):
        result = super()._prepare_move_line_vals()
        if result.get("analytic_distribution"):
            result.update(customer_charge_expense=self.customer_charge_expense)
        return result
