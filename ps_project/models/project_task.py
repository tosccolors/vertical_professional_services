# Copyright 2018 The Open Source Company ((www.tosc.nl).)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from lxml import etree

from odoo import api, fields, models


class Task(models.Model):
    _inherit = "project.task"

    @api.depends("description")
    def parse_description(self):
        for this in self:
            this.parsed_description = this.description and "".join(
                etree.fromstring(this.description, etree.HTMLParser()).itertext()
            )

    standby = fields.Boolean("Standby")
    outof_office_hours_week = fields.Boolean("Out of office hours week")
    outof_office_hours_weekend = fields.Boolean("Out of office hours weekend")
    parsed_description = fields.Char(compute=parse_description)

    @api.model
    def default_get(self, fields):
        res = super(Task, self).default_get(fields)
        active_model = self.env.context.get("active_model", False)
        if active_model and active_model == "project.project":
            active_id = self.env.context.get("active_id", False)
            if active_id:
                project = self.env["project.project"].browse(active_id)
                res["tag_ids"] = project.tag_ids.ids
        return res

    @api.onchange("project_id")
    def onchange_tags(self):
        if self.project_id and self.project_id.tag_ids:
            self.tag_ids = list(set(self.tag_ids.ids + self.project_id.tag_ids.ids))
