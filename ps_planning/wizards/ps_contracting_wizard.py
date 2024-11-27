# Copyright 2024 Hunki Enterprises BV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0)

from odoo import fields, models


class PsContractingWizard(models.TransientModel):
    _name = "ps.contracting.wizard"
    _description = "PS contracting wizard"
    _rec_name = "project_id"

    project_id = fields.Many2one("project.project", required=True)
    date_from = fields.Date(required=True)
    date_to = fields.Date(required=True)
    product_ids = fields.Many2many(
        "product.product",
        string="Products",
        required=True,
        domain=lambda self: [
            (
                "categ_id",
                "=",
                self.env.ref("ps_timesheet_invoicing.product_category_fee_rate").id,
            )
        ],
    )

    def action_open_ps_contracted_lines(self):
        return self.project_id.open_ps_contracted_lines(
            self.product_ids, self.date_from, self.date_to
        )
