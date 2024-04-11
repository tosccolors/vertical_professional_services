from base64 import b64encode

from odoo.addons.account_invoice_import.tests import test_invoice_import


class TestAccountInvoiceImport(test_invoice_import.TestInvoiceImport):
    def test_gateway_always_create_invoice(self):
        max_move = self.env["account.move"].search([], limit=1, order="id desc")
        self.env["account.invoice.import"].create_invoice_webservice(
            b64encode(b"hello world"),
            "name",
            "origin",
        )
        move = self.env["account.move"].search(
            [("id", ">", max_move.id)], limit=1, order="id desc"
        )
        self.assertTrue(move)
