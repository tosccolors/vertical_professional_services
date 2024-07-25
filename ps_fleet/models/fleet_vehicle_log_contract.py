# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class FleetVehicleLogContract(models.Model):

    _inherit = "fleet.vehicle.log.contract"

    km_range_contract = fields.Integer("Kilometer Range Contract")
    price_more_km = fields.Float("Price more km")
    price_less_km = fields.Float("Price less km")
    lease_period = fields.Integer("Lease Period")

    @api.model
    def create(self, vals):
        if vals.get("start_date") and vals.get("lease_period", 0) > 0:
            start_date = fields.Date.to_date(vals.get("start_date"))
            end_date = start_date + relativedelta(months=vals.get("lease_period"))
            vals.update({"expiration_date": end_date})
        return super().create(vals)

    def write(self, vals):
        for this in self:
            if int(vals.get("lease_period", 0)) > 0:
                start_date = this.start_date
                end_date = start_date + relativedelta(months=vals.get("lease_period"))
                vals.update({"expiration_date": end_date})
        return super().write(vals)

    @api.onchange("lease_period")
    def _lease_period_on_change(self):
        if self.lease_period > 0 and self.start_date:
            end_date = self.start_date + relativedelta(months=self.lease_period)
            self.expiration_date = end_date
