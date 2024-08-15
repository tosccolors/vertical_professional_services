# Copyright 2024 Hunki Enterprises BV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0)

from odoo.tests.common import TransactionCase


class TestPsTimesheetInvoicingTimeControl(TransactionCase):
    def setUp(self):
        super().setUp()
        self.user = self.env.ref("base.user_demo")
        self.project = self.env.ref("project.project_project_2").with_user(self.user)

    def test_flow(self):
        """Test happy flow"""
        timer_action = self.project.button_start_work()
        timer_wizard = (
            self.env[timer_action["res_model"]]
            .with_user(self.user)
            .with_context(**timer_action["context"])
            .create({"name": "test"})
        )
        line_action = timer_wizard.with_context(show_created_timer=True).action_switch()
        self.assertEqual(line_action["res_model"], "ps.time.line")
