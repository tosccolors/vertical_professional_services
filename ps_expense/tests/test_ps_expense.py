from odoo.tests.common import Form, TransactionCase


class TestPsExpense(TransactionCase):
    def test_hr_expense_flow(self):
        product = self.env.ref("hr_expense.product_product_fixed_cost")
        project = self.env["project.project"].search(
            [("user_id", "!=", False)], limit=1
        )
        with Form(
            self.env["hr.expense"].with_user(self.env.ref("base.user_demo"))
        ) as expense_form:
            expense_form.product_id = product
            expense_form.analytic_account_id = project.analytic_account_id
            expense = expense_form.save()
        action = expense.action_submit_expenses()
        expense_sheet = self.env[action["res_model"]].browse(action["res_id"])
        self.assertEqual(expense_sheet.project_manager_id, project.user_id)
        expense_sheet.approve_expense_sheets()
        self.assertEqual(expense_sheet.state, "approve")
        expense_sheet.action_sheet_move_create()
        self.assertEqual(
            expense_sheet.account_move_id.operating_unit_id, expense.operating_unit_id
        )
