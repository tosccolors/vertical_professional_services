from odoo.addons.ps_timesheet_invoicing.tests import test_ps_invoice


class TestPsInvoice(test_ps_invoice.TestPsInvoice):
    def test_01_invoicing(self):
        ps_invoice = super().test_01_invoicing()
        report_html, _type = self.env.ref("account.account_invoices")._render_qweb_pdf(
            ps_invoice.invoice_id.ids
        )
        return ps_invoice
