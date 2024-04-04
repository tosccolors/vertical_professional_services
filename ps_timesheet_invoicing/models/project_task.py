# Copyright 2018 The Open Source Company ((www.tosc.nl).)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class Task(models.Model):
    _inherit = "project.task"

    @api.constrains("project_id", "standard")
    def _check_project_standard(self):
        task = self.env["project.task"].search(
            [("project_id", "=", self.project_id.id), ("standard", "=", True)]
        )
        if len(task) > 1 and self.standard:
            raise ValidationError(
                _("You can have only one task with the standard as true per project!")
            )

    standard = fields.Boolean(string="Standard")
    task_user_ids = fields.One2many(
        "task.user",
        "task_id",
        string="Can register time",
        tracking=True,
    )

    @api.model
    def name_search(self, name, args=None, operator="ilike", limit=100):
        args = args or []
        recs = self.browse()
        if name:
            recs = self.search([("name", "=", name)] + args, limit=limit)
        if not recs:
            domain = [("name", operator, name)]
            # if 'jira_compound_key' in self._fields:
            #     domain = ['|'] + domain + [('jira_compound_key', operator, name)]
            recs = self.search(domain + args, limit=limit)
        return recs.name_get()
