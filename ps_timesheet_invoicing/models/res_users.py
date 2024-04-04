# Copyright 2018 The Open Source Company ((www.tosc.nl).)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models
from odoo.exceptions import ValidationError
from odoo.tools.translate import _


class ResUsers(models.Model):
    _inherit = "res.users"

    def _get_related_employees(self):
        self.ensure_one()
        ctx = dict(self.env.context)
        if "thread_model" in ctx:
            ctx["thread_model"] = "hr.employee"
        return (
            self.env["hr.employee"]
            .with_context(ctx)
            .search([("user_id", "=", self.id)])
        )

    def _get_operating_unit_id(self):
        """Compute Operating Unit of Employee based on the OU in the
        top Department."""
        employee_id = self._get_related_employees()
        assert len(employee_id) == 1, "Only one employee can have this user_id"
        dep = employee_id.department_id
        if dep:
            while dep.parent_id:
                dep = dep.parent_id
        else:
            raise ValidationError(
                _(
                    "The Employee in the PS Time Line has "
                    "no department defined. Please complete"
                )
            )
        return dep.operating_unit_id
