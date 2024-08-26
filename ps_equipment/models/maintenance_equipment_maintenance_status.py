from odoo import fields, models


class MaintenanceStatus(models.Model):
    _name = "maintenance.equipment.maintenance.status"
    _description = "Class to account for various maintenance status, needed for "
    "date time tracking functionality"
    _rec_name = "maintenance_status_name"

    maintenance_status_name = fields.Char(
        string="Maintenance Status", default="status_in_use"
    )
