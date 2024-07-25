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
                ("analytic_distribution", "!=", False),
            ]
        ):
            this.operating_unit_id = this.analytic_account_id.operating_unit_ids.ids[:1]
        for row in self.read_group(
            [
                ("create_uid", "=", user.id),
                ("state", "=", "draft"),
                ("sheet_id", "=", False),
            ],
            [],
            ["employee_id", "analytic_distribution", "name"],
            lazy=False,
        ):
            expenses = self.search(row["__domain"])
            action = expenses.action_submit_expenses()
            if not action.get("domain"):
                sheets = self.env[action["res_model"]].create(
                    {
                        key[len("default_") :]: value
                        for key, value in action["context"].items()
                    }
                )
            else:
                sheets = self.env[action["res_model"]].search(action["domain"])
            sheets.name = expenses[0].name
            sheets.action_submit_sheet()
