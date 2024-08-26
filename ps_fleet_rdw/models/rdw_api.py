import requests

from odoo import _, fields, models
from odoo.exceptions import UserError


class VehicleFromRDW(models.TransientModel):
    """
    This object is an intermediate object, to retrieve data from using the RDW Open Data API.
    """

    _name = "vehicle.from.rdw"

    license_plate = fields.Char()

    def fetch_rdw_data(self):
        rdw_data = requests.get(
            "https://opendata.rdw.nl/resource/m9d7-ebf2.json?kenteken="
            + self.license_plate
        ).json()
        rdw_data_brandstof = requests.get(
            "https://opendata.rdw.nl/resource/8ys7-d773.json?Kenteken="
            + self.license_plate
        ).json()
        if not rdw_data:
            raise UserError(
                _(
                    "Car is not present in RDW Open Data database, please fill details "
                    "manually."
                )
            )
        rdw_data_dict = rdw_data[0]
        rdw_data_brandstof_dict = rdw_data_brandstof[0]
        data = {
            "fiscal_value": rdw_data_dict.get("catalogusprijs"),
            "brand": rdw_data_dict.get("merk"),
            "type": rdw_data_dict.get("handelsbenaming"),
            "color": rdw_data_dict.get("eerste_kleur"),
            "end_date_apk": rdw_data_dict.get("vervaldatum_apk"),
            "doors": rdw_data_dict.get("aantal_deuren"),
            "seats": rdw_data_dict.get("aantal_zitplaatsen"),
            "fuel_type": rdw_data_brandstof_dict.get("brandstof_omschrijving"),
            "co2": rdw_data_brandstof_dict.get("co2_uitstoot_gecombineerd"),
            "power": rdw_data_brandstof_dict.get("nettomaximumvermogen"),
        }
        return data
