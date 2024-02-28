from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

import odoo.addons.decimal_precision as dp


class ResPartnerRelation(models.Model):
    _inherit = "res.partner.relation"

    distribution_key = fields.Float(
        string="Percentage Distribution Key",
        digits=dp.get_precision("Product Unit of Measure"),
    )

    invoicing_property_id = fields.Many2one(
        comodel_name="project.invoicing.properties", string="Invoicing Property"
    )

    @api.constrains("distribution_key")
    def _check_distribution_key(self):
        """Check distribution_key for valid values

        :raises ValidationError: When constraint is violated
        """
        dk = self.distribution_key
        if dk > 100 or dk < 0:
            raise ValidationError(
                _("The percentage can not be greater than 100 " "or smaller than 0.")
            )

    def name_get(self):
        return [
            (
                this.id,
                "%s %s %s"
                % (
                    this.left_partner_id.name,
                    this.type_id.display_name,
                    this.right_partner_id.name,
                ),
            )
            for this in self
        ]
