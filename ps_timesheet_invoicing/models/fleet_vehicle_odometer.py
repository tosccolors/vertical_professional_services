# Copyright 2018 The Open Source Company ((www.tosc.nl).)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class FleetVehicleOdometer(models.Model):
    _inherit = "fleet.vehicle.odometer"

    _sql_constraints = [
        (
            "date_uniq",
            "unique (date, vehicle_id)",
            "Odometer records have to have a unique date.",
        )
    ]

    def _inverse_odometer_values(self):
        for odom in self:
            if odom.value_period_update and odom.value_update:
                raise UserError(
                    _("You cannot enter both period value and ultimo value for %s!")
                    % (odom.date)
                )
            older = self.sudo().search(
                [("vehicle_id", "=", odom.vehicle_id.id), ("date", "<", odom.date)],
                limit=1,
                order="date desc",
            )
            if odom.value_update:
                odom.value_period = odom.value_update - older.value
                odom.value = odom.value_update
            else:
                odom.value = older.value + odom.value_period_update
                odom.value_period = odom.value_period_update

    value_period = fields.Float(
        string="Odometer Period Value (computed)",
        group_operator="sum",
        readonly=True,
    )
    value = fields.Float(
        string="Odometer Value (computed)",
        group_operator="max",
        readonly=True,
    )
    value_update = fields.Float(
        string="Odometer Value",
        group_operator="max",
        compute=lambda self: None,
        inverse="_inverse_odometer_values",
    )
    value_period_update = fields.Float(
        string="Odometer Period Value",
        group_operator="sum",
        compute=lambda self: None,
        inverse="_inverse_odometer_values",
    )

    def _update_newer(self, vehicle_id=None, date=None):
        """Recompute records newer than self or date"""
        newer = self.sudo().search(
            [
                ("vehicle_id", "=", self.vehicle_id.id or vehicle_id),
                ("date", ">", self.date or date),
            ],
            order="date asc",
        )
        former_value = self.value
        for one in newer.with_context(odo_newer=True):
            one.value = former_value + one.value_period
            former_value = one.value

    def _find_newer(self, vehicle_id=None, date=None):
        """Return the closest record that is newer than self or date"""
        return self.sudo().search(
            [
                ("vehicle_id", "=", self.vehicle_id.id or vehicle_id),
                ("date", ">", self.date or date),
            ],
            limit=1,
            order="date asc",
        )

    @api.model
    def create(self, data):
        res = super().create(data)
        if res._find_newer():
            res._update_newer()
        return res

    def write(self, data):
        res = super().write(data)
        if not self.env.context.get("odo_newer"):
            for record in self:
                if record._find_newer():
                    record._update_newer()
        return res

    def unlink(self):
        self_data = self.mapped(lambda x: (x.vehicle_id.id, x.date))
        result = super().unlink()
        for vehicle_id, gone_date in self_data:
            if self.env[self._name]._find_newer(vehicle_id, gone_date):
                self.env[self._name]._update_newer(vehicle_id, gone_date)
        return result
