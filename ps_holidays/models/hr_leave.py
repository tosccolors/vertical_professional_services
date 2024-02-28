# Copyright 2018 The Open Source Company ((www.tosc.nl).)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class HrLeave(models.Model):
    _inherit = "hr.leave"

    state = fields.Selection(selection_add=[("written", "Written")])
