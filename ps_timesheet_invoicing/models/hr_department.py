# Copyright 2018 The Open Source Company ((www.tosc.nl).)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields

class HrDepartment(models.Model):
    _inherit = "hr.department"

    operating_unit_id = fields.Many2one(
        comodel_name='operating.unit',
        string='Operating Unit',
        tracking=True,
    )
    no_ott_check = fields.Boolean(
        '8 Hours OTT possible',
        help="No Overtime Check"
    )
