# Copyright 2018 The Open Source Company ((www.tosc.nl).)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class HrLeaveAllocation(models.Model):
    _inherit = "hr.leave.allocation"

    _sql_constraints = [
        (
            "duration_check",
            "CHECK ( number_of_days <> 0 )",
            "The number of days must be different than 0.",
        ),
    ]
