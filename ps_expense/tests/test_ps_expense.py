from odoo.tests.common import Form, TransactionCase


class TestPsExpense(TransactionCase):
    def test_hr_expense_flow(self):
        product = self.env.ref("hr_expense.product_product_fixed_cost")
        with Form(
            self.env["hr.expense"].with_user(self.env.ref("base.user_demo"))
        ) as expense_form:
            expense_form.product_id = product
            expense = expense_form.save()
        action = expense.action_submit_expenses()
        expense_sheet = self.env[action["res_model"]].browse(action["res_id"])
        expense_sheet.revise_expense()
        self.assertEqual(expense_sheet.state, "revise")
        expense_sheet.expense_revised()
        self.assertEqual(expense_sheet.state, "approve")
        expense_sheet.approve_partner_expense_sheets()
        self.assertEqual(expense_sheet.state, "approve_partner")
        expense_sheet.action_partner_sheet_move_create()
