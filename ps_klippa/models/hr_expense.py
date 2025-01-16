# Copyright 2018 The Open Source Company ((www.tosc.nl).)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class HrExpense(models.Model):
    _inherit = "hr.expense"

    @api.model
    def _klippa_update_expenses(self):
        user = self.env.ref("ps_klippa.user_klippa")

        for this in self.search(
            [
                ("create_uid", "=", user.id),
                ("state", "=", "draft"),
                ("operating_unit_id", "=", False),
                ("analytic_account_id", "!=", False),
            ]
        ):
            this.operating_unit_id = this.analytic_account_id.operating_unit_ids[:1]

        for row in self.read_group(
            [
                ("create_uid", "=", user.id),
                ("state", "=", "draft"),
                ("sheet_id", "=", False),
            ],
            [],
            ["employee_id", "analytic_account_id", "name"],
            lazy=False,
        ):
            expenses = self.search(row["__domain"])
            expense_user = expenses.employee_id.user_id
            ou = expense_user.with_company(
                expense_user.company_id
            ).operating_unit_default_get(expense_user.id)
            expenses.write(
                {
                    "operating_unit_id": ou.id,
                }
            )
            sheet = expenses._create_sheet_from_expenses()
            sheet.name = expenses[0].name
            sheet.action_submit_sheet()
