from odoo import fields, models


class Company(models.Model):
    _inherit = "res.company"

    decl_journal_id = fields.Many2one(
        "account.journal",
        "Declaration Journal",
        domain=[("type", "=", "purchase")],
        required=True,
    )
