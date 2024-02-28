# Copyright 2018 The Open Source Company ((www.tosc.nl).)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ProjectInvoicingProperties(models.Model):
    _inherit = "project.invoicing.properties"

    relation_ids = fields.One2many(
        comodel_name="res.partner.relation",
        inverse_name="invoicing_property_id",
        string="Partner Relations",
        copy=False,
    )
