# Copyright 2018 The Open Source Company ((www.tosc.nl).)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ProjectInvoicingProperties(models.Model):
    _inherit = "project.invoicing.properties"

    invoice_mileage = fields.Boolean("Invoice Mileage")
    group_invoice = fields.Boolean(
        "Group Invoices By Project",
        help="Enabling this creates one invoice per project, in addition to per partner,"
        "period and operating unit",
    )
    group_by_fee_rate = fields.Boolean(
        "Group By Fee Rate",
        help="Enabling this groups the specs attachment by fee rates",
    )
    group_by_month = fields.Boolean(
        "Group By Month", help="Enabling this groups the specs attachment by period"
    )

    @api.onchange("invoice_mileage")
    def onchange_invoice_mileage(self):
        project_id = getattr(self, "_origin", self).id
        project = self.env["project.project"].search(
            [("invoice_properties", "=", project_id)]
        )
        if project:
            ps_time_lines = self.env["ps.time.line"].search(
                [
                    ("project_id", "in", project.ids),
                    ("product_uom_id", "=", self.env.ref("uom.product_uom_km").id),
                ]
            )
            if ps_time_lines:
                non_invoiceable_mileage = not self.invoice_mileage
                self.env.cr.execute(
                    """
                    UPDATE ps_time_line SET non_invoiceable_mileage = %s WHERE id IN %s
                """,
                    (
                        non_invoiceable_mileage,
                        tuple(ps_time_lines.ids),
                    ),
                )
