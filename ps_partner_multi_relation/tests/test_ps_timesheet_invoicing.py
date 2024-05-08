from odoo.addons.ps_timesheet_invoicing.tests import test_ps_invoice


class TestPsInvoice(test_ps_invoice.TestPsInvoiceBase):
    def _create_ps_invoice(self, generate=True):
        self.partner = self.env.ref("ps_partner_multi_relation.partner_consortium")
        (
            self.env.ref(
                "ps_timesheet_invoicing.time_line_demo_user_2023_12_18_mileage"
            )
            + self.ps_line
        ).write({"partner_id": self.partner.id})
        self.project.write(
            {"invoice_address": self.partner.id, "partner_id": self.partner.id}
        )
        self.project.analytic_account_id.write({"partner_id": self.partner.id})
        self.ps_line.flush()
        return super()._create_ps_invoice(generate=generate)

    def test_01_invoicing(self):
        self.assertEqual(self.ps_invoice.partner_id, self.partner)
        self.ps_invoice.invoice_id.action_post()
        self.ps_invoice.invoice_id.flush()
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
