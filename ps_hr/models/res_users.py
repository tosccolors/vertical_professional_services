# Copyright 2018 The Open Source Company ((www.tosc.nl).)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    klippa_user = fields.Boolean(
        related="employee_id.klippa_user",
        string="Employee uses Klippa",
        groups="hr.group_hr_user",
        store=True,
    )
