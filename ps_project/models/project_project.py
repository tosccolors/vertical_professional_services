# Copyright 2018 The Open Source Company ((www.tosc.nl).)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class Project(models.Model):
    _inherit = "project.project"

    code = fields.Char("Project Code")
    tag_ids = fields.Many2many("project.tags", string="Tags")
    po_number = fields.Char("PO Number")
    invoice_address = fields.Many2one("res.partner", string="Invoice Address")
    correction_charge = fields.Boolean("Correction Chargeability")
    chargeable = fields.Boolean("Chargeable", default=True)
    invoice_properties = fields.Many2one(
        "project.invoicing.properties", "Invoice Properties"
    )
    invoice_properties_fixed_amount = fields.Boolean(
        related="invoice_properties.fixed_amount"
    )
    analytic_account_related = fields.Many2one(
        related="analytic_account_id",
        string="Contract/Analytic",
    )
    wbso = fields.Boolean("WBSO")
    linked_operating_unit = fields.Boolean(
        string="Linked Operating Unit",
        related="analytic_account_id.linked_operating_unit",
    )
    operating_unit_ids = fields.Many2many(
        "operating.unit",
        string="Operating Units",
        related="analytic_account_id.operating_unit_ids",
    )
    ps_date_range_type_id = fields.Many2one(
        "date.range.type",
        default=lambda self: self.env.ref(
            "account_fiscal_month.date_range_fiscal_month", False
        ),
        string="Invoicing period",
        help="Select a frequency by which to invoice. This causes a selection of time "
        "lines to be put into invoices per selected period.",
        required=True,
    )
    ps_fixed_hours = fields.Float(
        "Contracted hours", help="Fill in the amount of hours to invoice per period."
    )
    ps_fixed_amount = fields.Monetary(
        "Contracted amount",
        help="Fill in the amount to invoice per period",
        currency_field="partner_currency_id",
    )
    partner_currency_id = fields.Many2one(
        related="partner_id.currency_id", string="Partner currency"
    )

    def name_get(self):
        return [
            (value.id, "%s%s" % (value.code + "-" if value.code else "", value.name))
            for value in self
        ]

    @api.model
    def _name_search(
        self, name="", args=None, operator="ilike", limit=100, name_get_uid=None
    ):
        """Allow searching for code too"""
        result = self.browse([])
        if name and operator == "ilike":
            result += self.browse(
                self._search(
                    list(args or []) + [("code", "ilike", "%s%%" % name)],
                    limit=limit,
                    access_rights_uid=name_get_uid,
                )
            )
            if result:
                args = (args or []) + [("id", "not in", result.ids)]
        result += self.browse(
            super()._name_search(
                name=name,
                args=args,
                operator=operator,
                limit=(limit - len(result)) if limit else limit,
                name_get_uid=name_get_uid,
            )
        )
        return result.ids

    def write(self, vals):
        result = super().write(vals)
        if "partner_id" in vals:
            partner = self.env["res.partner"].browse(vals["partner_id"])
            accounts = self.mapped("analytic_account_id").filtered(
                lambda x: x.partner_id != partner
            )
            if accounts:
                accounts.write({"partner_id": vals["partner_id"]})
        return result
