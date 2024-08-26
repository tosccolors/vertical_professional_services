import math

from odoo import api, fields, models


class AccountAsset(models.Model):
    _inherit = "account.asset"

    equipment_ids = fields.Many2many(
        comodel_name="maintenance.equipment", string="Equipments"
    )
    equipment_count = fields.Integer(
        string="Equipment count", compute="_compute_equipment_count"
    )

    @api.depends("equipment_ids")
    def _compute_equipment_count(self):
        for asset in self:
            asset.equipment_count = len(asset.equipment_ids)

    def button_open_equipment(self):
        self.ensure_one()
        res = self.env.ref("maintenance.hr_equipment_action").read()[0]
        res["domain"] = [("asset_ids", "in", self.ids)]
        res["context"] = {"default_asset_ids": [(6, 0, self.ids)]}
        return res

    @api.model
    def create(self, vals):
        res = super().create(vals)
        ctx = self._context
        if ctx.get("create_asset_from_move_line") and res.profile_id.has_equipments:
            invoice = self.env["account.move"].browse(ctx.get("move_id", []))
            for line in invoice.invoice_line_ids:
                equipment_qty = math.ceil(line.quantity)
                equipments = self.env["maintenance.equipment"]
                for equipment_nr in range(int(equipment_qty)):
                    equipment_data = {
                        "name": "{} [{}/{}]".format(
                            line.name, equipment_nr + 1, equipment_qty
                        ),
                        "category_id": (line.asset_profile_id.equipment_category_id.id),
                        "invoice_line_id": line.id,
                        "cost": line.price_subtotal / line.quantity,
                        "partner_id": line.move_id.partner_id.id,
                        "owner_user_id": (line.move_id.user_id or self.env.user).id,
                        "purchase_date": line.move_id.invoice_date,
                    }
                    equipments += equipments.create(equipment_data)
                res.write({"equipment_ids": [(4, x) for x in equipments.ids]})
        return res
