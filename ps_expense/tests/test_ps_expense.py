from odoo.tests.common import Form, TransactionCase


class TestPsExpense(TransactionCase):
    def test_hr_expense_flow(self):
        product = self.env.ref("hr_expense.expense_product_mileage")
        main_ou = self.env.ref("operating_unit.main_operating_unit")
        b2c_ou = self.env.ref("operating_unit.b2c_operating_unit")
        self.env.ref("operating_unit.b2c_operating_unit")
        project = self.env["project.project"].search(
            [
                ("user_id", "!=", False),
            ],
            limit=1,
        )
        self.assertTrue(project)
        project.analytic_account_id.operating_unit_ids = b2c_ou
        with Form(
            self.env["hr.expense"].with_user(self.env.ref("base.user_demo"))
        ) as expense_form:
            expense_form.product_id = product
            self.assertEqual(expense_form.operating_unit_id, main_ou)
            expense_form.analytic_distribution = {
                project.analytic_account_id.id: 100,
            }
            self.assertEqual(expense_form.operating_unit_id, b2c_ou)
            expense_form.customer_charge_expense = True
            expense = expense_form.save()
        action = expense.action_submit_expenses()
        expense_sheet = (
            self.env[action["res_model"]]
            .with_user(self.env.ref("base.user_demo"))
            .create(
                {
                    key[len("default_") :]: value
                    for key, value in action["context"].items()
                }
            )
        )
        self.assertEqual(expense_sheet.project_manager_id, project.user_id)
        self.assertEqual(expense.operating_unit_id, expense_sheet.operating_unit_id)
        expense.operating_unit_id = main_ou
        self.assertEqual(expense.operating_unit_id, expense_sheet.operating_unit_id)
        expense_sheet.approve_expense_sheets()
        self.assertEqual(expense_sheet.state, "approve")
        expense_sheet.action_sheet_move_create()
        self.assertEqual(expense_sheet.account_move_id.operating_unit_id, b2c_ou)
        self.assertEqual(
            expense_sheet.account_move_id.line_ids.analytic_line_ids.mapped(
                "customer_charge_expense"
            ),
            [True],
        )
