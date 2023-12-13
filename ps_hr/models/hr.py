# Copyright 2018 The Open Source Company ((www.tosc.nl).)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta

class Employee(models.Model):
    _inherit = "hr.employee"

    official_date_of_employment = fields.Date('Official Date of Employment')
    temporary_contract = fields.Date('Temporary Contract')
    end_date_of_employment = fields.Date('End Date of Employment')
    external = fields.Boolean('External')
    supplier_id = fields.Many2one('res.partner', domain=[('supplier', '=', True), ('company_type', '=', 'company')], string='Supplier')
    mentor_id = fields.Many2one('hr.employee', string='Mentor')
    parttime = fields.Integer('Parttime')
    allocated_leaves = fields.Integer('Allocated Leaves')
    emergency_contact = fields.Char('Emergency Contact')
    description = fields.Text('Description')
    pass_number_alarm = fields.Char('Pass Number Alarm')
    slamid = fields.Char('Slam ID')
    personnel_number = fields.Char('Personnel Number')
    employee_numbersid = fields.Char('Employee NMBRs ID')
    date_last_promotion = fields.Date('Date of last Promotion')
    klippa_user = fields.Boolean(string="Employee uses Klippa")
    has_private_car = fields.Boolean(string="Employee has a private car")
    leave_hours = fields.Float(string="Leave Hours")

    def validate_dates(self):
        start_date = self.official_date_of_employment
        end_date = self.end_date_of_employment
        if start_date and end_date and start_date > end_date:
            raise ValidationError(_('End Date of Employment cannot be set before Official Date of Employment.'))

    @api.onchange('official_date_of_employment', 'end_date_of_employment')
    def onchange_dates(self):
        self.validate_dates()

    @api.constrains('official_date_of_employment', 'end_date_of_employment')
    def _check_closing_date(self):
        self.validate_dates()
