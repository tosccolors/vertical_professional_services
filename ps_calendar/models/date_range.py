from odoo import fields, models


class DateRange(models.Model):
    _inherit = "date.range"

    calendar_name = fields.Char(string="Calender Name", translate=True)
