from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    wip_journal_id = fields.Many2one(
        "account.journal", "WIP Journal", domain=[("type", "=", "wip")]
    )
