# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
# Copyright 2023 Hunki Enterprises BV
from itertools import groupby

from odoo import api, models


class InvoiceMerge(models.TransientModel):
    _inherit = "invoice.merge"

    @api.model
    def _get_not_mergeable_invoices_message(self, invoices):
        """Loop through invoices by partner to allow merging invoices of multiple partners"""
        result = {}
        for _partner, invoice_iterator in groupby(
            invoices.sorted(lambda x: x.partner_id.id), lambda x: x.partner_id.id
        ):
            partner_invoices = sum(invoice_iterator, self.env["account.move"])
            result.update(
                **super()._get_not_mergeable_invoices_message(partner_invoices)
            )
        return result

    def merge_invoices(self):
        """Loop through invoices by partner to allow merging invoices of multiple partners"""
        actions = []
        invoices = self.env["account.move"].browse(
            self.env.context.get("active_ids", [])
        )
        for _partner, invoice_iterator in groupby(
            invoices.sorted(lambda x: x.partner_id.id), lambda x: x.partner_id.id
        ):
            partner_invoices = sum(invoice_iterator, self.env["account.move"])
            actions.append(
                super(
                    InvoiceMerge, self.with_context(active_ids=partner_invoices.ids)
                ).merge_invoices()
            )
        result = actions[0]
        result["domain"] = [
            ("id", "in", sum(map(lambda x: x["domain"][0][2], actions), []))
        ]
        return result
