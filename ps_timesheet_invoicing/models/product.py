from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    property_account_wip_id = fields.Many2one(
        "account.account",
        company_dependent=True,
        string="WIP Account",
        domain=[("deprecated", "=", False)],
    )
