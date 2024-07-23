# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import api, fields, models


class FleetVehicleOdometer(models.Model):
    _inherit = "fleet.vehicle.odometer"

    driver_id = fields.Many2one(related=None, comodel_name="res.partner")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("vehicle_id") and not vals.get("driver_id"):
                vals["driver_id"] = (
                    self.env["fleet.vehicle"].browse(vals["vehicle_id"]).driver_id.id
                )
        return super().create(vals_list)
