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
