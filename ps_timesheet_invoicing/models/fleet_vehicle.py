# Copyright 2018 The Open Source Company ((www.tosc.nl).)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from dateutil import relativedelta

from odoo import api, fields, models

from .fleet_vehicle_driver import inhibit_constraints_sentinel


class FleetVehicle(models.Model):
    _inherit = "fleet.vehicle"

    driver_id = fields.Many2one(
        compute="_compute_driver_id",
        inverse="_inverse_driver_id",
        search="_search_driver_id",
        store=False,
    )
    fleet_vehicle_driver_ids = fields.One2many(
        "fleet.vehicle.driver",
        "vehicle_id",
        copy=False,
    )

    def write(self, vals):
        if "fleet_vehicle_driver_ids" not in vals:
            return super().write(vals)
        result = super(
            FleetVehicle,
            self.with_context(
                fleet_vehicle_driver_inhibit_constrains=inhibit_constraints_sentinel
            )
            # filter out driver_id if both fleet_vehicle_driver_ids and driver_id
            # are to be written
        ).write({key: value for key, value in vals.items() if key != "driver_id"})
        self.fleet_vehicle_driver_ids._check_all()
        return result

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

    @api.depends(
        "fleet_vehicle_driver_ids.driver_id",
        "fleet_vehicle_driver_ids.date_start",
        "fleet_vehicle_driver_ids.date_end",
    )
    def _compute_driver_id(self):
        for this in self:
            this.driver_id = this.fleet_vehicle_driver_ids[:1].mapped("driver_id")

    def _inverse_driver_id(self):
        today = fields.Date.context_today(self) + relativedelta.relativedelta(
            weekday=relativedelta.MO
        )
        for this in self:
            last_driver = this.fleet_vehicle_driver_ids[:1]
            if last_driver.date_start == today:
                last_driver.driver_id = self.driver_id
                continue
            this.fleet_vehicle_driver_ids.filtered(lambda x: not x.date_end).write(
                {"date_end": today}
            )
            if not this.driver_id:
                continue
            this.write(
                {
                    "fleet_vehicle_driver_ids": [
                        (
                            0,
                            0,
                            {
                                "driver_id": this.driver_id.id,
                                "date_start": today,
                                "date_end": False,
                            },
                        )
                    ]
                }
            )

    def _search_driver_id(self, operator, value):
        today = fields.Date.context_today(self)
        vehicle_drivers = self.env["fleet.vehicle.driver"].search(
            [
                ("driver_id", operator, value),
                ("date_start", "<=", today),
                "|",
                ("date_end", "=", False),
                ("date_end", ">=", today),
            ]
        )
        return [("fleet_vehicle_driver_ids", "in", vehicle_drivers.ids)]
