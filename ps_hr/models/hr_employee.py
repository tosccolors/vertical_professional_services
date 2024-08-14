# Copyright 2018 The Open Source Company ((www.tosc.nl).)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class Employee(models.Model):
    _inherit = "hr.employee"

    official_date_of_employment = fields.Date(
        "Official Date of Employment", groups="hr.group_hr_user"
    )
    temporary_contract = fields.Date("Temporary Contract", groups="hr.group_hr_user")
    end_date_of_employment = fields.Date(
        "End Date of Employment", groups="hr.group_hr_user"
    )
    external = fields.Boolean("External", groups="hr.group_hr_user")
    supplier_id = fields.Many2one(
        "res.partner",
        domain=[("supplier", "=", True), ("company_type", "=", "company")],
        string="Supplier",
        groups="hr.group_hr_user",
    )
    mentor_id = fields.Many2one(
        "hr.employee", string="Mentor", groups="hr.group_hr_user"
    )
    parttime = fields.Integer("Parttime", groups="hr.group_hr_user")
    allocated_leaves = fields.Integer("Allocated Leaves", groups="hr.group_hr_user")
    emergency_contact = fields.Char("Emergency Contact", groups="hr.group_hr_user")
    description = fields.Text("Description", groups="hr.group_hr_user")
    pass_number_alarm = fields.Char("Pass Number Alarm", groups="hr.group_hr_user")
    personnel_number = fields.Char("Personnel Number", groups="hr.group_hr_user")
    employee_numbersid = fields.Char("Employee NMBRs ID", groups="hr.group_hr_user")
    date_last_promotion = fields.Date(
        "Date of last Promotion", groups="hr.group_hr_user"
    )
    klippa_user = fields.Boolean(
        string="Employee uses Klippa", groups="hr.group_hr_user"
    )
    has_private_car = fields.Boolean(
        string="Employee has a private car", groups="hr.group_hr_user"
    )
    leave_hours = fields.Float(string="Leave Hours", groups="hr.group_hr_user")

    def validate_dates(self):
        for this in self:
            start_date = this.official_date_of_employment
            end_date = this.end_date_of_employment
            if start_date and end_date and start_date > end_date:
                raise ValidationError(
                    _(
                        "End Date of Employment cannot be set before "
                        "Official Date of Employment."
                    )
                )

    @api.onchange("official_date_of_employment", "end_date_of_employment")
    def onchange_dates(self):
        self.validate_dates()

    @api.constrains("official_date_of_employment", "end_date_of_employment")
    def _check_closing_date(self):
        self.validate_dates()
