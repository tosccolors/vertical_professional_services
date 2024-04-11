# Copyright 2024 Hunki Enterprises BV
from odoo import api, models


class AccountInvoiceImport(models.TransientModel):
    _inherit = "account.invoice.import"

    @api.model
    def _prepare_create_invoice_vals(self, parsed_inv, import_config):
        result = super()._prepare_create_invoice_vals(parsed_inv, import_config)
        if result["move_type"] == "in_invoice" and result.get("ref"):
            result["supplier_invoice_number"] = result.pop("ref")
        return result
