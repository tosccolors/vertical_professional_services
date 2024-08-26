# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import fields, models


class AccountPaymentOrder(models.Model):
    _inherit = "account.payment.order"

    operating_unit_id = fields.Many2one(
        related="journal_id.operating_unit_id", store=True, readonly=True
    )
