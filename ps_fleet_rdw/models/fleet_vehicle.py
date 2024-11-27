# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import re

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class FleetVehicle(models.Model):
    _inherit = "fleet.vehicle"

    model_id = fields.Many2one(
        "fleet.vehicle.model", "Model", required=False, help="Model of the vehicle"
    )
    rdw_brand = fields.Char("RDW Merk")
    rdw_handelsnaam = fields.Char("RDW Handelsnaam")

    def fetch_data_from_rdw(self):
        """
        This function creates an vehicle_from_rdw object, and then uses a function from
        this object to fetch the RDW data.
        """
        rdw_data = self.env["vehicle.from.rdw"].create(
            {"license_plate": re.sub("-", "", self.license_plate)}
        )
        rdw_data_dict = rdw_data.fetch_rdw_data()
        model_id = self.fetch_model_id(rdw_data_dict["brand"], rdw_data_dict["type"])
        if not model_id:
            raise UserError(
                _(
                    "Please first create a vehicle model with brand %s and model %s"
                    % (rdw_data_dict["brand"], rdw_data_dict["type"])
                )
            )
        self.update(
            {
                "color": rdw_data_dict["color"],
                "seats": rdw_data_dict["seats"],
                "doors": rdw_data_dict["doors"],
                "rdw_brand": (rdw_data_dict["brand"] or "").capitalize(),
                "rdw_handelsnaam": (rdw_data_dict["type"] or "").capitalize(),
                "co2": rdw_data_dict["co2"],
                "car_value": rdw_data_dict["fiscal_value"],
                "fuel_type": self.fetch_fuel_type(rdw_data_dict["fuel_type"]),
                "model_id": model_id,
                "power": int(float(rdw_data_dict["power"] or 0)),
                "horsepower": int(1.362 * float(rdw_data_dict["power"] or 0)),
            }
        )

    def fetch_fuel_type(self, rdw_fuel_type):
        if rdw_fuel_type == "Benzine":
            return "gasoline"
        elif rdw_fuel_type == "Diesel":
            return "diesel"
        elif rdw_fuel_type == "Elektriciteit":
            return "electric"
        else:
            return None

    def fetch_model_id(self, rdw_brand_name, rdw_model):
        brand_id = (
            self.env["fleet.vehicle.model.brand"]
            .search([("name", "ilike", rdw_brand_name)], limit=1)
            .id
        )
        found_models = self.env["fleet.vehicle.model"].search(
            ["&", ("brand_id", "=", brand_id), ("name", "ilike", rdw_model)], limit=1
        )
        if brand_id and found_models:
            model_id = found_models.id
            return model_id
        return self.env["fleet.vehicle.model.brand"]

    @api.depends("model_id", "license_plate")
    def _compute_vehicle_name(self):
        for record in self:
            if record.model_id.brand_id.name and record.model_id.name:
                record.name = (
                    record.model_id.brand_id.name
                    + "/"
                    + record.model_id.name
                    + "/"
                    + record.license_plate
                )
            elif record.license_plate:
                record.name = record.license_plate
            else:
                raise UserError(_("Please enter a license plate"))
