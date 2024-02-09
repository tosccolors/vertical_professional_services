from datetime import datetime

from odoo import _, api, fields, models


class HrTimesheetCurrentOpen(models.TransientModel):
    _name = "hr.timesheet.current.open"
    _description = "hr.timesheet.current.open"

    @api.model
    def open_timesheet(self):
        sheets = self.env["hr_timesheet.sheet"].search(
            [
                ("user_id", "=", self.env.user.id),
                ("state", "in", ("draft", "new")),
                ("date_start", "<=", fields.Date.today()),
                ("date_end", ">=", fields.Date.today()),
            ]
        )

        if len(sheets):
            domain = [("id", "in", sheets.ids)]
        else:
            domain = [
                ("user_id", "=", self.env.user.id),
                ("state", "in", ("draft", "new")),
            ]

        value = {
            "domain": domain,
            "name": _("Open Timesheet"),
            "view_type": "form",
            "view_mode": "form,tree",
            "res_model": "hr_timesheet.sheet",
            "type": "ir.actions.act_window",
        }

        sheets = self.env["hr_timesheet.sheet"].search(domain)
        if len(sheets) == 1:
            value["res_id"] = sheets.ids[0]
        else:
            value["view_mode"] = "tree,form"

        return value

    @api.model
    def open_self_planning(self):
        value = self.open_timesheet_self_planning(True)
        return value

    @api.model
    def open_employees_planning(self):
        value = self.open_timesheet_planning(True)
        return value

    @api.model
    def open_timesheet_planning(self, is_planning_officer=False):

        view_type = "form,tree"

        date = datetime.now().date()

        period = self.env["date.range"].search(
            [
                ("type_id.calender_week", "=", False),
                ("type_id.fiscal_month", "=", False),
                ("date_start", "<=", date),
                ("date_end", ">=", date),
            ],
            limit=1,
        )

        domain = [
            ("user_id", "=", self._uid),
            ("planning_quarter", "=", period.id),
            ("is_planning_officer", "=", is_planning_officer),
        ]
        planning = self.env["ps.planning"].search(domain)

        if len(planning) > 1:
            domain = "[('id', 'in', " + str(planning.ids) + "),('user_id', '=', uid)]"
        else:
            domain = "[('user_id', '=', uid)]"

        value = {
            "domain": domain,
            "name": _("Open Planning"),
            "view_type": "form",
            "view_mode": view_type,
            "res_model": "ps.planning",
            "view_id": False,
            "type": "ir.actions.act_window",
            "context": {"default_is_planning_officer": is_planning_officer},
            # 'context':{'readonly_by_pass': True}
        }
        if len(planning) == 1:
            value["res_id"] = planning.ids[0]
        return value

    @api.model
    def open_timesheet_self_planning(self, self_planning=False):

        view_type = "form,tree"

        date = datetime.now().date()

        period = self.env["date.range"].search(
            [
                ("type_id.calender_week", "=", False),
                ("type_id.fiscal_month", "=", False),
                ("date_start", "<=", date),
                ("date_end", ">=", date),
            ],
            limit=1,
        )

        domain = [("user_id", "=", self._uid), ("planning_quarter", "=", period.id)]
        planning = self.env["ps.planning"].search(domain)

        value = {
            "domain": domain,
            "name": _("Open Planning"),
            "view_type": "form",
            "view_mode": view_type,
            "res_model": "ps.planning",
            "view_id": False,
            "type": "ir.actions.act_window",
            "context": {"default_self_planning": self_planning},
            # 'context':{'readonly_by_pass': True}
        }
        if len(planning) == 1:
            value["res_id"] = planning.ids[0]
        return value
