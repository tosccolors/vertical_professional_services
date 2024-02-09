from odoo import exceptions
from odoo.tests.common import Form, TransactionCase
from odoo.tools.misc import mute_logger


class TestPsTimesheetInvoicing(TransactionCase):
    def setUp(self):
        super().setUp()
        self.project = self.env.ref("project.project_project_2")
        self.ps_line = self.env.ref(
            "ps_timesheet_invoicing.time_line_demo_user_2023_12_18"
        )

    def test_00_timesheet(self):
        """Test creating and submitting timesheets"""
        task = self.project.task_ids[:1]
        sheet = (
            self.env["hr_timesheet.sheet"]
            .with_user(self.env.ref("base.user_demo"))
            .create({})
        )
        sheet.add_line_project_id = self.project
        sheet.add_line_task_id = task
        sheet.button_add_line()
        sheet.with_context(sheet_write=True)._compute_line_ids()
        with Form(sheet) as sheet_form:
            for i in range(7):
                with sheet_form.line_ids.edit(i) as day_line:
                    day_line.unit_amount = 8
            with sheet_form.line_ids.edit(3) as day_line:
                day_line.unit_amount = 10
            sheet_form.end_mileage = 42
        action = (
            self.env["hr.timesheet.current.open"]
            .with_user(self.env.ref("base.user_demo"))
            .open_timesheet()
        )
        self.assertEqual(action["res_id"], sheet.id)
        sheet.action_timesheet_confirm()
        sheet_as_admin = sheet.with_user(self.env.ref("base.user_admin"))
        sheet_as_admin.action_timesheet_refuse()
        sheet.action_timesheet_confirm()
        sheet_as_admin.action_timesheet_done()
        sheet_as_admin.action_timesheet_draft()
        sheet.action_timesheet_confirm()
        sheet_as_admin.action_timesheet_done()
        self.assertEqual(sheet.overtime_hours, 18)
        self.assertEqual(sheet.overtime_hours_delta, 18)
        next_sheet = sheet.create({})
        next_sheet.duplicate_last_week()
        with Form(next_sheet) as sheet_form:
            for i in range(7):
                with sheet_form.line_ids.edit(i) as day_line:
                    day_line.unit_amount = 8
        with self.assertRaisesRegex(
            exceptions.ValidationError, "End Mileage cannot be lower"
        ):
            next_sheet.action_timesheet_confirm()
        next_sheet.end_mileage = 84
        next_sheet.action_timesheet_confirm()
        self.assertEqual(next_sheet.overtime_hours, 16)
        self.assertEqual(next_sheet.overtime_hours_delta, 16)

    def test_01_invoicing(self):
        """Test invocing time lines"""
        wizard = (
            self.env["time.line.status"]
            .with_context(
                active_id=self.ps_line.id,
                active_ids=self.ps_line.ids,
                active_model=self.ps_line._name,
            )
            .create({"name": "invoiceable"})
        )
        wizard.ps_invoice_lines()
        ps_invoice = self.env["ps.invoice"].search(
            [("user_total_ids.detail_ids", "in", self.ps_line.ids)]
        )
        self.assertTrue(ps_invoice)
        ps_invoice.generate_invoice()
        self.assertEqual(ps_invoice.state, "open")
        ps_invoice.invoice_id.target_invoice_amount = 40
        ps_invoice.invoice_id.compute_target_invoice_amount()
        self.assertTrue(
            all(line.discount for line in ps_invoice.invoice_id.invoice_line_ids)
        )
        ps_invoice.invoice_id.action_post()
        self.assertEqual(ps_invoice.state, "invoiced")
        ps_invoice.delete_invoice()
        self.assertEqual(ps_invoice.state, "draft")
        with Form(ps_invoice) as ps_invoice_form:
            ps_invoice_form.project_id = self.env["project.project"].search(
                [("id", "!=", ps_invoice_form.project_id.id)],
                limit=1,
            )
        self.assertEqual(ps_invoice.user_total_ids.detail_ids, self.ps_line)

    def test_02_change_chargecode(self):
        wizard = (
            self.env["change.chargecode"]
            .with_context(
                active_id=self.ps_line.id,
                active_ids=self.ps_line.ids,
                active_model=self.ps_line._name,
            )
            .create({})
        )
        with Form(wizard) as wizard_form:
            project = self.env["project.project"].search(
                [("id", "!=", self.ps_line.project_id.id)],
                limit=1,
            )
            wizard_form.project_id = project
            wizard_form.task_id = project.task_ids[:1]

        line_max = self.env["ps.time.line"].search([], limit=1, order="id desc")
        wizard.post()

        reverse_line, new_line = self.env["ps.time.line"].search(
            [("id", ">", line_max.id)], order="id asc"
        )
        self.assertEqual(self.ps_line.unit_amount, -reverse_line.unit_amount)

    def test_03_invoicing_properties(self):
        """Test invoicing properties form"""
        km_line = self.ps_line.copy(
            {
                "product_uom_id": self.env.ref("uom.product_uom_km").id,
                "non_invoiceable_mileage": True,
            }
        )
        with Form(self.project.invoice_properties) as properties_form:
            properties_form.invoice_mileage = True
        self.assertFalse(km_line.non_invoiceable_mileage)

    def test_99_delay(self):
        """Test delaying time lines"""
        wizard = (
            self.env["time.line.status"].with_context(
                active_id=self.ps_line.id,
                active_ids=self.ps_line.ids,
                active_model=self.ps_line._name,
            )
        ).create({})

        with Form(wizard) as wizard_form:
            wizard_form.name = "delayed"
            wizard_form.description = "hello world"

        move_max = self.env["account.move"].search([], limit=1, order="id desc")
        with mute_logger("odoo.addons.queue_job.delay"):
            wizard.with_context(test_queue_job_no_delay=True).ps_invoice_lines()

        self.assertEqual(self.ps_line.state, "delayed")
        reversed_move, move = self.env["account.move"].search(
            [("id", ">", move_max.id)]
        )
        self.assertEqual(reversed_move.reversed_entry_id, move)
        self.assertEqual(move.reversal_move_id, reversed_move)
