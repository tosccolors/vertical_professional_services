# Copyright 2018 The Open Source Company ((www.tosc.nl).)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, models
from odoo.exceptions import ValidationError


class AccountAnalyticAccount(models.Model):
    _inherit = "account.analytic.account"
    _description = "Analytic Account"

    @api.constrains("project_ids")
    def _check_length_projects(self):
        for aa in self:
            if len(aa.project_ids) > 1:
                raise ValidationError(
                    _(
                        "Fill in maximum one Project. "
                        "In Professional Services Analytic Accounts can have one "
                        "project maximum. "
                    )
                )
        return True

    def write(self, vals):
        result = super().write(vals)
        if "partner_id" in vals:
            partner = self.env["res.partner"].browse(vals["partner_id"])
            projects = self.mapped("project_ids").filtered(
                lambda x: x.partner_id != partner
            )
            if projects:
                projects.write({"partner_id": vals["partner_id"]})
        return result
