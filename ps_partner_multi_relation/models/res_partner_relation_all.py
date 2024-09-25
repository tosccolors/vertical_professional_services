# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import fields, models


class ResPartnerRelationAll(models.AbstractModel):
    """Abstract model to show each relation from two sides."""

    _inherit = "res.partner.relation.all"

    distribution_key = fields.Float(
        string="Percentage Distribution Key",
        digits="Distribution key",
    )
    invoicing_property_id = fields.Many2one(
        comodel_name="project.invoicing.properties", string="Invoicing Property"
    )

    def _get_additional_relation_columns(self):
        return (
            super()._get_additional_relation_columns()
            + ", rel.distribution_key, rel.invoicing_property_id"
        )
