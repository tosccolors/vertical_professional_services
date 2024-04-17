from odoo import api, fields, models


class HrExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    journal_id = fields.Many2one(
        default=lambda self: self.env.user.company_id.decl_journal_id
    )

    @api.onchange("expense_line_ids")
    def onchange_expense_line_ids(self):
        if self.expense_line_ids and self.expense_line_ids[0].operating_unit_id:
            if not self.operating_unit_id or (
                self.operating_unit_id and len(self.expense_line_ids) == 1
            ):
                self.operating_unit_id = self.expense_line_ids[0].operating_unit_id.id
        else:
            self.operating_unit_id = False
