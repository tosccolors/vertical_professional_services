from odoo import SUPERUSER_ID, api


def migrate(cr, version=None):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env["hr_timesheet.sheet"].search([])._compute_overtime_hours()
