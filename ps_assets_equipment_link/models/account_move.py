# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    equipment_ids = fields.Many2many(
        comodel_name="maintenance.equipment",
        compute="_compute_equipment_ids",
        string="Equipments",
    )

    @api.depends("invoice_line_ids.equipment_ids")
    def _compute_equipment_ids(self):
        for invoice in self:
            invoice.equipment_ids = [
                (6, 0, invoice.mapped("invoice_line_ids.equipment_ids").ids),
            ]

    def action_invoice_cancel(self):
        res = super().action_invoice_cancel()
        self.mapped("equipment_ids").unlink()
        return res


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    equipment_ids = fields.One2many(
        comodel_name="maintenance.equipment",
        inverse_name="invoice_line_id",
        string="Equipments",
    )
