# Copyright 2018 The Open Source Company ((www.tosc.nl).)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class HREmployeeWizard(models.TransientModel):
    _inherit = "hr.employee.wizard"

    product_id = fields.Many2one(
        "product.product",
        "Fee rate product",
        domain=lambda self: self.env["hr.employee"]._get_category_domain(),
    )

    def create_employee(self, user_id, res_partner_bank_id):
        result = super().create_employee(user_id, res_partner_bank_id)
        result.product_id = self.product_id
        return result
