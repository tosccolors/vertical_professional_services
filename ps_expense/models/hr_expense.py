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

    def action_move_create(self):
        res = super(
            HrExpense, self.with_context(ps_expense_set_partner_uid=True)
        ).action_move_create()
        for expense in self:
            if expense.analytic_account_id.operating_unit_ids:
                ou = expense.analytic_account_id.operating_unit_ids[0]
                if ou and expense.sheet_id.account_move_id:
                    expense.sheet_id.account_move_id.operating_unit_id = ou
        return res

    def _create_sheet_from_expenses(self):
        """Allow creating expense sheet from expenses without product"""
        self = self.with_context(
            default_operating_unit_id=self.mapped("operating_unit_id")[:1].id
        )
        result = super()._create_sheet_from_expenses()
        return result

    def action_view_sheet(self):
        res = super(HrExpense, self).action_view_sheet()
        res.setdefault("context", {})["form_view_initial_mode"] = "edit"
        return res

    @api.onchange("analytic_account_id", "operating_unit_id")
    def anaytic_account_change(self):
        if self.analytic_account_id and self.analytic_account_id.linked_operating_unit:
            self.operating_unit_id = self.analytic_account_id.operating_unit_ids.ids[0]

    def _get_account_move_line_values(self):
        result = super()._get_account_move_line_values()
        for this_id, move_line_vals in result.items():
            for vals in move_line_vals:
                if vals.get("analytic_account_id"):
                    vals.update(
                        customer_charge_expense=self.browse(
                            this_id
                        ).customer_charge_expense
                    )
        return result

    def write(self, vals):
        res = super().write(vals)
        if vals.get("operating_unit_id"):
            for this in self:
                sheet_id = vals.get("sheet_id") or this.sheet_id.id
                if sheet_id:
                    expense_sheet = self.env["hr.expense.sheet"].browse(sheet_id)
                    expense_sheet.write(
                        {"operating_unit_id": vals.get("operating_unit_id")}
                    )
        return res
