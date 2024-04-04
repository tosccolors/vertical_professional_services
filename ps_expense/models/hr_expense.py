from odoo import _, api, fields, models
from odoo.exceptions import UserError


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
    state = fields.Selection(selection_add=[("revise", "To Be Revised")])

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

    def action_submit_expenses(self):
        if any(expense.state != "draft" for expense in self):
            raise UserError(_("You cannot report twice the same line!"))
        if len(self.mapped("employee_id")) != 1:
            raise UserError(
                _(
                    "You cannot report expenses for different employees in the same report!"
                )
            )
        expense_sheet = self.env["hr.expense.sheet"].create(
            {
                "expense_line_ids": [(6, 0, [line.id for line in self])],
                "employee_id": self[0].employee_id.id,
                "name": self[0].name if len(self.ids) == 1 else "",
                "operating_unit_id": self[0].operating_unit_id.id,
            }
        )
        return {
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": "hr.expense.sheet",
            "target": "current",
            "res_id": expense_sheet.id,
        }

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
