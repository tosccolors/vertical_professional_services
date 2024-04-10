from odoo.tests.common import TransactionCase


class TestPsKlippa(TransactionCase):
    def test_ps_klippa(self):
        user = self.env.ref("ps_klippa.user_klippa")
        demo_expenses = self.env.ref("ps_klippa.expense_demo1") + self.env.ref(
            "ps_klippa.expense_demo2"
        )
        demo_expenses_other = self.env.ref("ps_klippa.expense_demo3")
        chs_expense = self.env.ref("ps_klippa.expense_chs")
        all_expenses = demo_expenses + demo_expenses_other + chs_expense
        # first we must force our expenses to be created by the klippa user
        self.env.cr.execute(
            "update hr_expense set create_uid=%s where id in %s",
            (user.id, tuple(all_expenses.ids)),
        )
        self.env.ref("ps_klippa.ir_cron_expense_update_actions").method_direct_trigger()
        sheets = all_expenses.mapped("sheet_id")
        self.assertEqual(len(sheets), 3)
        self.assertEqual(demo_expenses[0].name, demo_expenses[1].sheet_id.name)
        self.assertEqual(set(sheets.mapped("state")), {"submit"})
