from odoo.tests.common import Form, TransactionCase


class TestPsTimesheetInvoicing(TransactionCase):
    def setUp(self):
        super().setUp()
        self.project = self.env.ref("project.project_project_2")
        self.ps_line = self.env.ref(
            "ps_timesheet_invoicing.time_line_demo_user_2023_12_18"
        )

    def test_01_invoicing(self):
        """Test invocing time lines"""
        wizard = (
            self.env["time.line.status"]
            .with_context(
                active_id=self.ps_line[:1].id,
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

        return ps_invoice

    def test_02_delete_invoice(self):
        ps_invoice = self.test_01_invoicing()
        ps_invoice.delete_invoice()
        self.assertEqual(ps_invoice.state, "draft")
        with Form(ps_invoice) as ps_invoice_form:
            ps_invoice_form.project_id = self.env["project.project"].search(
                [("id", "!=", ps_invoice_form.project_id.id)],
                limit=1,
            )
        self.assertEqual(ps_invoice.user_total_ids.detail_ids, self.ps_line)


class TestPsTimesheetInvoicingGrouped(TestPsTimesheetInvoicing):
    def setUp(self):
        super().setUp()
        self.project.invoice_properties = self.env.ref(
            "project.project_project_1"
        ).invoice_properties
        self.project = self.env.ref("project.project_project_1")
        self.ps_line += self.env.ref(
            "ps_timesheet_invoicing.time_line_demo_user_2023_12_19"
        )

    def test_01_invoicing(self):
        ps_invoice = super().test_01_invoicing()
        self.assertEqual(len(ps_invoice), 1)
        self.assertEqual(len(ps_invoice.user_total_ids), 2)
        return ps_invoice
