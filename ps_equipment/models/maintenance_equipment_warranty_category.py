from odoo import fields, models


class MaintenanceWarrantyCategory(models.Model):
    _name = "maintenance.equipment.warranty.category"
    _description = "Warranty Category of asset"
    _rec_name = "warranty_category_name"

    warranty_category_name = fields.Char(string="Warranty Category Name")
    warranty_duration = fields.Integer(string="Warranty  (months)")
