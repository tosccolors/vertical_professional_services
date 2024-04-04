import logging
import time

from odoo import SUPERUSER_ID, api

logger = logging.getLogger(__name__)


def post_init_hook(cr, pool):
    """
    This post-init-hook will update only date.range
    calender_name values in case they are not set
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    for month in env["date.range"].search([("type_id.fiscal_month", "=", True)]):
        month.calendar_name = time.strftime(
            "%B", time.strptime(str(month.date_start), "%Y-%m-%d")
        )

    for month in env["date.range"].search([("type_id.fiscal_year", "=", True)]):
        month.calendar_name = time.strftime(
            "%Y", time.strptime(str(month.date_start), "%Y-%m-%d")
        )
