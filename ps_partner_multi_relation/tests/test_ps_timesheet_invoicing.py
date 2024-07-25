from odoo.addons.ps_timesheet_invoicing.tests import test_ps_invoice


class TestPsInvoice(test_ps_invoice.TestPsInvoiceBase):
    @classmethod
    def _create_ps_invoice(cls, generate=True):
        cls.partner = cls.env.ref("ps_partner_multi_relation.partner_consortium")
        (
            cls.env.ref("ps_timesheet_invoicing.time_line_demo_user_2023_12_18_mileage")
            + cls.ps_line
        ).write({"partner_id": cls.partner.id})
        cls.project.write(
            {"invoice_address": cls.partner.id, "partner_id": cls.partner.id}
        )
        cls.project.analytic_account_id.write({"partner_id": cls.partner.id})
        cls.env.flush_all()
        return super()._create_ps_invoice(generate=generate)

    def test_01_invoicing(self):
        self.assertEqual(self.ps_invoice.partner_id, self.partner)
        self.ps_invoice.invoice_id.action_post()
        self.ps_invoice.invoice_id.invalidate_recordset()
        self.assertEqual(self.ps_invoice.state, "invoiced")
        self.assertEqual(self.ps_line.mapped("state"), ["invoiced"])

    def test_02_invoicing_standard(self):
        invoice = (
            self.env["account.move"]
            .with_context(
                default_move_type="out_invoice",
            )
            .create(
                {
                    "partner_id": self.env.ref("base.res_partner_12").id,
                    "invoice_line_ids": [
                        (0, 0, {"name": "/", "quantity": 1, "price_unit": 42}),
                    ],
                }
            )
        )
        invoice.action_post()
        self.assertEqual(invoice.state, "posted")
