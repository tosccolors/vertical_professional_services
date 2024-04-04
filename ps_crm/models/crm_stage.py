# Copyright 2018 - 2023 The Open Source Company ((www.tosc.nl).)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import fields, models


class CRMStage(models.Model):
    _inherit = "crm.stage"

    show_when_changing = fields.Boolean("Show when changing")
