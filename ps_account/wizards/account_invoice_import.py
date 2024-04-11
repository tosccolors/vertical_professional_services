# Copyright 2024 Hunki Enterprises BV
import logging
from base64 import b64decode

from odoo import _, api, models

logger = logging.getLogger(__name__)


class AccountInvoiceImport(models.TransientModel):
    _inherit = "account.invoice.import"

    @api.model
    def _prepare_create_invoice_vals(self, parsed_inv, import_config):
        result = super()._prepare_create_invoice_vals(parsed_inv, import_config)
        if result["move_type"] == "in_invoice" and result.get("ref"):
            result["supplier_invoice_number"] = result.pop("ref")
        return result

    @api.model
    def create_invoice_webservice(
        self,
        invoice_file_b64,
        invoice_filename,
        origin,
        company_id=None,
        email_from=None,
    ):
        try:
            super().create_invoice_webservice(
                invoice_file_b64,
                invoice_filename,
                origin,
                company_id=company_id,
                email_from=email_from,
            )
        except Exception as e:
            logger.error(
                "Failed to import invoice from mail attachment %s. Error: %s",
                invoice_filename,
                e,
            )
            logger.info("Creating empty invoice anyways")
            invoice = self.env["account.move"].create(
                {
                    "move_type": "in_invoice",
                    "partner_id": self.env.user.partner_id.id,
                }
            )
            invoice.message_post(
                body=_("Error when importing mail from %s: %s") % (email_from, e),
                attachments=[(invoice_filename, b64decode(invoice_file_b64))],
            )
