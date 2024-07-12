# -*- coding: utf-8 -*-

from datetime import date
import calendar
from odoo import api, fields, models

class MaintenanceEquipment(models.Model):
    _inherit = 'maintenance.equipment'

    # General fields
    purchase_date = fields.Date(string="Date of acquisition", default=fields.Date.context_today)
    maintenance_status = fields.Many2one(
        'maintenance.equipment.maintenance.status',
        string="Equipment Status"
    )
    brand = fields.Char(string="Brand")
    model = fields.Char(string="Model")
    warranty_category = fields.Many2one(
        'maintenance.equipment.warranty.category',
        string="Warranty Category",
        track_visibility='onchange',
    )
    warranty_date = fields.Date(string='Warranty until', compute='_compute_warranty_date')
    department = fields.Many2one('hr.department', string="Department")

    # Phone specific fields
    phone_number = fields.Char(string="Phone Number", size=10)
    sim_number = fields.Char(string="SIM number")
    puk_code = fields.Char(string="PUK Code")
    imei_number = fields.Char(string="IMEI Number")
    remarks = fields.Text(string="Remarks")

    # Laptop specific fields
    cpu = fields.Char(string="CPU")
    memory = fields.Char(string="Memory")
    hard_disk = fields.Char(string="Hard Disk")
    accessories = fields.Text(string="Accessories")
    iso_security_check = fields.Date(string="ISO/Security Check")

    @api.depends('purchase_date', 'warranty_category.warranty_duration')
    def _compute_warranty_date(self):
        for record in self:
            if record.purchase_date and record.warranty_category and record.warranty_category.warranty_duration:
                purchase_date = record.purchase_date
                month = purchase_date.month - 1 + record.warranty_category.warranty_duration
                year = purchase_date.year + month // 12
                month = month % 12 + 1
                day = min(purchase_date.day, calendar.monthrange(year, month)[1])
                record.warranty_date = date(year, month, day)
            else:
                record.warranty_date = None

class MaintenanceWarrantyCategory(models.Model):
    _name = 'maintenance.equipment.warranty.category'
    _description = 'Warranty Category of asset'
    _rec_name = 'warranty_category_name'

    warranty_category_name = fields.Char(string="Warranty Category Name")
    warranty_duration = fields.Integer(string="Warranty (months)")

class MaintenanceStatus(models.Model):
    _name = 'maintenance.equipment.maintenance.status'
    _description = "Class to account for various maintenance status, needed for date time tracking functionality"
    _rec_name = "maintenance_status_name"
    _inherit = 'data.track.thread'

    maintenance_status_name = fields.Char(string="Maintenance Status", default="status_in_use")
