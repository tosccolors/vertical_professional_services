from odoo.tests.common import Form, TransactionCase


class TestPsInvoiceBase(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.project = cls.env.ref("project.project_project_2")
        cls.ps_line = cls.env.ref(
            "ps_timesheet_invoicing.time_line_demo_user_2023_12_18"
        )
        cls.ps_invoice = cls._create_ps_invoice()

    @classmethod
    def _create_ps_invoice(cls, generate=True):
        wizard = (
            cls.env["time.line.status"]
            .with_context(
                active_id=cls.ps_line[:1].id,
                active_ids=cls.ps_line.ids,
                active_model=cls.ps_line._name,
            )
            .create({"name": "invoiceable"})
        )
        wizard.ps_invoice_lines()
        ps_invoice = cls.env["ps.invoice"].search(
            [("user_total_ids.detail_ids", "in", cls.ps_line.ids)]
        )
        if generate:
            ps_invoice.generate_invoice()
        return ps_invoice


class TestPsInvoice(TestPsInvoiceBase):
    @classmethod
    def _create_ps_invoice(cls, generate=True):
        cls.ps_line += cls.env.ref(
            "ps_timesheet_invoicing.time_line_demo_user_2023_12_18_mileage"
        )
        return super()._create_ps_invoice(generate=generate)

    def test_01_invoicing(self):
        """Test invocing time lines"""
        ps_invoice = self.ps_invoice
        self.assertTrue(ps_invoice)
        ps_invoice.generate_invoice()
        self.assertTrue(ps_invoice.expense_line_ids)
        self.assertTrue(
            ps_invoice.invoice_id.invoice_line_ids.filtered("ps_analytic_line_ids")
        )
        self.assertEqual(set(self.ps_line.mapped("state")), {"invoice_created"})
        self.assertEqual(ps_invoice.state, "open")
        ps_invoice.invoice_id.target_invoice_amount = 40
        ps_invoice.invoice_id.compute_target_invoice_amount()
        self.assertTrue(
            all(line.discount for line in ps_invoice.invoice_id.invoice_line_ids)
        )
        ps_invoice.invoice_id.action_post()
        self.assertEqual(ps_invoice.state, "invoiced")
        self.assertEqual(set(self.ps_line.mapped("state")), {"invoiced"})
        self.assertTrue(ps_invoice.invoice_id.wip_move_id)
        return ps_invoice

    def test_02_delete_invoice(self):
        ps_invoice = self.test_01_invoicing()
        ps_invoice.delete_invoice()
        self.assertEqual(set(self.ps_line.mapped("state")), {"progress"})
        with Form(ps_invoice) as ps_invoice_form:
            ps_invoice_form.project_id = self.env["project.project"].search(
                [("id", "!=", ps_invoice_form.project_id.id)],
                limit=1,
            )
        self.assertEqual(
            ps_invoice.user_total_ids.detail_ids + ps_invoice.mileage_line_ids,
            self.ps_line,
        )
        ps_invoice.unlink()
        self.assertEqual(set(self.ps_line.mapped("state")), {"invoiceable"})

    def test_03_amend_invoice(self):
        ps_line1, mileage_line = self.ps_line
        ps_line2 = ps_line1.copy({"state": "open"})
        self.__class__.ps_line = ps_line2
        ps_invoice = self._create_ps_invoice()
        self.assertEqual(ps_invoice, self.ps_invoice)
        self.assertEqual(ps_invoice.user_total_ids.detail_ids, ps_line1 + ps_line2)
        self.assertEqual(ps_line1.state, "invoice_created")
        self.assertEqual(ps_line2.state, "invoice_created")
        self.assertEqual(mileage_line.state, "invoice_created")
        ps_invoice.invoice_id.action_post()
        ps_invoice.flush_recordset()
        self.assertEqual(ps_line1.state, "invoiced")
        self.assertEqual(ps_line2.state, "invoiced")
        self.assertEqual(mileage_line.state, "invoiced")

    def test_04_edit_invoice_line(self):
        with Form(self.ps_invoice) as ps_invoice_form:
            with ps_invoice_form.invoice_line_ids.edit(0) as line:
                line.price_unit = 43
        self.assertEqual(self.ps_invoice.invoice_id.invoice_line_ids[0].price_unit, 43)


class TestPsInvoiceGrouped(TestPsInvoiceBase):
    @classmethod
    def _create_ps_invoice(cls, generate=True):
        cls.project.invoice_properties = cls.env.ref(
            "project.project_project_1"
        ).invoice_properties
        cls.project = cls.env.ref("project.project_project_1")
        cls.ps_line += cls.env.ref(
            "ps_timesheet_invoicing.time_line_demo_user_2023_12_19"
        )
        return super()._create_ps_invoice(generate=generate)

    def test_invoicing(self):
        ps_invoice = self.ps_invoice
        self.assertEqual(len(ps_invoice), 1)
        self.assertEqual(len(ps_invoice.user_total_ids), 2)
        self.assertEqual(
            ps_invoice.period_id.type_id,
            self.env.ref("ps_timesheet_invoicing.date_range_quarter"),
        )


class TestPsInvoiceFixed(TestPsInvoiceBase):
    @classmethod
    def _create_ps_invoice(cls, generate=True):
        cls.project.invoice_properties = cls.env.ref(
            "ps_timesheet_invoicing." "project_invoicing_property_fixed_amount"
        )
        cls.env["account.analytic.account"].search(
            [
                ("id", "!=", cls.project.analytic_account_id.id),
                ("partner_id", "=", cls.project.partner_id.id),
            ]
        ).active = False
        cls.project.ps_fixed_amount = 4242
        cls.project.ps_fixed_hours = 42
        return super()._create_ps_invoice(generate=generate)

    def test_01_invoicing(self):
        ps_invoice = self.ps_invoice
        invoice = ps_invoice.invoice_id
        self.assertEqual(self.ps_line.state, "invoice_created")
        self.assertEqual(invoice.amount_untaxed, self.project.ps_fixed_amount)
        invoice.action_post()
        self.ps_invoice.flush_recordset()
        self.assertEqual(self.ps_line.state, "invoiced-by-fixed")
        value_tag = self.env.ref(
            "ps_timesheet_invoicing.analytic_tag_fixed_amount_value_difference"
        )
        value_line = invoice.invoice_line_ids.analytic_line_ids.filtered(
            lambda x: x.tag_ids == value_tag
        )
        self.assertTrue(value_line)
        hours_tag = self.env.ref(
            "ps_timesheet_invoicing.analytic_tag_fixed_amount_hours_difference"
        )
        hours_line = invoice.invoice_line_ids.analytic_line_ids.filtered(
            lambda x: x.tag_ids == hours_tag
        )
        self.assertEqual(hours_line.unit_amount, 41)
        self.assertItemsEqual(
            map(int, invoice.invoice_line_ids.analytic_distribution.keys()),
            ps_invoice.account_analytic_ids.ids,
        )
        ps_invoice.delete_invoice()
        self.assertFalse((value_line + hours_line).exists())

    def test_03_amend_invoice(self):
        ps_line1 = self.ps_line
        ps_line2 = ps_line1.copy({"state": "open"})
        self.__class__.ps_line = ps_line2
        ps_invoice = self._create_ps_invoice()
        self.assertEqual(ps_invoice, self.ps_invoice)
        self.assertEqual(ps_invoice.user_total_ids.detail_ids, ps_line1 + ps_line2)
        self.assertEqual(ps_line1.state, "invoice_created")
        self.assertEqual(ps_line2.state, "invoice_created")
        ps_invoice.invoice_id.action_post()
        ps_invoice.flush_recordset()
        self.assertEqual(ps_line1.state, "invoiced-by-fixed")
        self.assertEqual(ps_line2.state, "invoiced-by-fixed")
