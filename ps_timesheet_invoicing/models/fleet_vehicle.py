# Copyright 2018 The Open Source Company ((www.tosc.nl).)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class FleetVehicle(models.Model):
    _inherit = "fleet.vehicle"

    _sql_constraints = [
        ("driver_uniq", "unique (driver_id)", "The driver already owns a vehicle.")
    ]

    def _set_odometer(self):
        for record in self:
            if record.odometer:
                date = fields.Date.context_today(record)
                data = {
                    "value_update": record.odometer,
                    "date": date,
                    "vehicle_id": record.id,
                }
                self.env["fleet.vehicle.odometer"].create(data)
