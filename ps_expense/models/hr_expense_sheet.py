from odoo import api, fields, models


class HrExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    journal_id = fields.Many2one(
        default=lambda self: self.env.user.company_id.decl_journal_id
    )
    project_manager_id = fields.Many2one(
        "res.users", compute="_compute_project_manager_id", store=True
    )

    @api.depends("expense_line_ids.analytic_account_id")
    def _compute_project_manager_id(self):
        for this in self:
            managers = this.mapped(
                "expense_line_ids.analytic_account_id.project_ids.user_id"
            )
            if len(managers) == 1 and all(
                line.analytic_account_id.project_ids.user_id
                for line in this.expense_line_ids
            ):
                this.project_manager_id = managers

    @api.onchange("expense_line_ids")
    def onchange_expense_line_ids(self):
        if self.expense_line_ids and self.expense_line_ids[0].operating_unit_id:
            if not self.operating_unit_id or (
                self.operating_unit_id and len(self.expense_line_ids) == 1
            ):
                self.operating_unit_id = self.expense_line_ids[0].operating_unit_id.id
        else:
            self.operating_unit_id = False
