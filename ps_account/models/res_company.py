from odoo import fields, models


class Company(models.Model):
    _inherit = "res.company"

    use_standard_layout = fields.Boolean(
        "Use Standard Layout",
        default=False,
    )
