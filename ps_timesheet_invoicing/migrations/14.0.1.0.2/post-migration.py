# pylint: disable=odoo-addons-relative-import
from odoo.addons.ps_timesheet_invoicing.hooks import _init_fleet_vehicle_driver


def migrate(cr, version=None):
    _init_fleet_vehicle_driver(cr)
