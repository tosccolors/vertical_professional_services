from odoo.tests.common import TransactionCase


class TestInvoiceMerge(TransactionCase):
    def test_merge(self):
        invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.env["res.partner"].search([], limit=1).id,
                "invoice_description": "desc",
                "ps_custom_footer": "footer",
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "name",
                            "price_unit": 42,
                        },
                    ),
                ],
            }
        )
        invoice2 = invoice.copy({"invoice_description": None, "ps_custom_footer": None})
        merged = self.env["account.move"].browse((invoice + invoice2).do_merge())
        self.assertEqual(merged.invoice_description, "<p>desc</p>")
