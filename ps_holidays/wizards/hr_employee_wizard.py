# Copyright 2018 The Open Source Company ((www.tosc.nl).)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from werkzeug import url_encode
from odoo.addons.resource.models.resource import float_to_time, HOURS_PER_DAY

class HREmployeeWizard(models.TransientModel):
    _inherit = "hr.employee.wizard"

    def create_holiday(self, employee_id):
        # TODO: this must be a holiday allocation
        hr_leave_type = self.env['hr.leave.type'].search([('is_leave_type_of_wizard', '=', True)], limit=1)
        holiday = {'holiday_status_id':hr_leave_type.id,
                                'holiday_type':'employee',
                                'employee_id':employee_id.id,
                                'number_of_days': self.leave_hours/HOURS_PER_DAY,
                                # 'type':'add',
                                'state':'confirm'}
        holiday_id = self.env['hr.leave.allocation'].create(holiday)
        holiday_id.action_approve()
        return True


    def create_all(self):
        employee_id = super().create_all()
        self.create_holiday(employee_id)
        return employee_id
