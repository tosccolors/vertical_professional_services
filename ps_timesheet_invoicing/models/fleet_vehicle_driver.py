# Copyright 2018 The Open Source Company ((www.tosc.nl).)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, exceptions, fields, models

inhibit_constraints_sentinel = object()


class FleetVehicle(models.Model):
    _name = "fleet.vehicle.driver"
    _rec_name = "driver_id"
    _order = "date_start desc"

    vehicle_id = fields.Many2one("fleet.vehicle", required=True, string="Vehicle")
    driver_id = fields.Many2one("res.partner", required=True, string="Driver")
    date_start = fields.Date(required=True, string="Start")
    date_end = fields.Date(string="End")

    @api.constrains("vehicle_id", "driver_id", "date_start", "date_end")
    def _check_all(self):
        if (
            self.env.context.get("fleet_vehicle_driver_inhibit_constrains")
            == inhibit_constraints_sentinel
        ):
            return
        for this in self:
            if not this.date_end:
                if self.search(
                    [
                        ("vehicle_id", "=", this.vehicle_id.id),
                        ("date_end", "=", False),
                        ("id", "!=", this.id),
                    ]
                ):
                    raise exceptions.ValidationError(
                        _("You can only have one open-ended driver record per vehicle")
                    )
            elif this.date_end < this.date_start:
                raise exceptions.ValidationError(
                    _("End date must be bigger than start date")
                )
            interval_domain = [
                ("id", "!=", this.id),
                ("date_start", "<", this.date_end)
                if this.date_end
                else ("date_start", ">", this.date_start),
                "|",
                ("date_end", ">", this.date_start),
                ("date_end", "=", False),
            ]
            if self.search([("vehicle_id", "=", this.vehicle_id.id)] + interval_domain):
                raise exceptions.ValidationError(
                    _("You cannot have overlapping drivers for a vehicle")
                )
            if self.search([("driver_id", "=", this.driver_id.id)] + interval_domain):
                raise exceptions.ValidationError(
                    _("A driver cannot have multiple vehicles at the same time")
                )
            if this.date_start.weekday() != 0:
                raise exceptions.ValidationError(
                    _("Driver assignments should start on a Monday")
                )
