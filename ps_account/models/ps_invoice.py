# Copyright 2018 The Open Source Company ((www.tosc.nl).)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class PSInvoice(models.Model):
    _inherit = "ps.invoice"

    def generate_invoice(self):
        result = super().generate_invoice()
        project = self.invoice_id.get_invoice_project()
        if project.invoice_properties.custom_layout:
            self.ps_custom_layout = True
            self.ps_custom_footer = project.invoice_properties.custom_footer
            self.ps_custom_header = project.invoice_properties.custom_header
        return result
