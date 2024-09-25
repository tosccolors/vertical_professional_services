# Copyright 2024 Hunki Enterprises BV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0)

from odoo import _, fields, models


class PsPlanningReportWizard(models.TransientModel):
    _name = "ps.planning.report.wizard"
    _description = "PS planning reporting wizard"
    _rec_name = "reference_date"

    project_ids = fields.Many2many(
        "project.project",
        string="Projects",
        required=True,
        domain=[("ps_contracted_line_ids", "!=", False)],
    )
    reference_date = fields.Date(default=fields.Date.context_today, required=True)

    def action_open_report(self):
        i = 0
        Line = self.env["ps.planning.report.wizard.line"]
        PlanningLine = self.env["ps.planning.line"]
        ContractedLine = self.env["ps.contracted.line"]
        TimeLine = self.env["ps.time.line"]
        month_type = self.env.ref("account_fiscal_month.date_range_fiscal_month")
        month = self.env["date.range"].search(
            [
                ("date_start", "<=", self.reference_date),
                ("date_end", ">=", self.reference_date),
                ("type_id", "=", month_type.id),
            ]
        )
        uom_hours = self.env.ref("uom.product_uom_hour")
        _get_work_days = ContractedLine._get_work_days_dates
        mtd_fraction = _get_work_days(
            self.reference_date.replace(day=1), self.reference_date
        ) / _get_work_days(month.date_start, month.date_end)
        for project in self.project_ids:
            vals = {
                "wizard_id": self.id,
                "sequence": i,
                "business_line": project.department_id.name,
                "project_name": project.name,
                "project_code": project.code,
                "days_commercial_full_month": sum(
                    PlanningLine.search(
                        [
                            ("range_id", "=", month.id),
                            ("task_id.project_id", "=", project.id),
                            ("line_type", "=", "contracted"),
                        ]
                    ).mapped("days")
                ),
                "days_planned_full_month": sum(
                    PlanningLine.search(
                        [
                            ("range_id", "=", month.id),
                            ("task_id.project_id", "=", project.id),
                            ("line_type", "=", "planned"),
                        ]
                    ).mapped("days")
                ),
                "days_actual_mtd": sum(
                    TimeLine.search(
                        [
                            ("task_id.project_id", "=", project.id),
                            ("date", ">=", month.date_start),
                            ("date", "<=", self.reference_date),
                            ("product_uom_id", "=", uom_hours.id),
                        ]
                    ).mapped(lambda x: x.unit_amount / 8)
                ),
                "budget_utilization": 42,
                "actual_commercial_ytm": sum(
                    TimeLine.search(
                        [
                            ("task_id.project_id", "=", project.id),
                            ("date", ">=", month.date_start.replace(month=1, day=1)),
                            ("date", "<", month.date_start),
                            ("product_uom_id", "=", uom_hours.id),
                        ]
                    ).mapped(lambda x: x.unit_amount / 8)
                )
                - sum(
                    PlanningLine.search(
                        [
                            (
                                "range_id.date_start",
                                ">=",
                                month.date_start.replace(month=1, day=1),
                            ),
                            ("range_id.date_end", "<", month.date_start),
                            ("task_id.project_id", "=", project.id),
                            ("line_type", "=", "contracted"),
                        ]
                    ).mapped("days"),
                ),
                "manager_name": project.user_id.name,
            }
            vals.update(
                days_planned_mtd=vals["days_planned_full_month"] * mtd_fraction,
                days_actual_planned_mtd=vals["days_actual_mtd"]
                - vals["days_planned_full_month"] * mtd_fraction,
                days_actual_commercial_mtd=vals["days_actual_mtd"]
                - vals["days_commercial_full_month"] * mtd_fraction,
            )
            Line.sudo().create(vals)
            i += 1
        return {
            "type": "ir.actions.act_window",
            "name": _("Project report"),
            "res_model": Line._name,
            "domain": [("wizard_id", "=", self.id)],
            "views": [(False, "list")],
        }


class PsPlanningReportWizardLine(models.TransientModel):
    _name = "ps.planning.report.wizard.line"
    _description = "PS planning reporting wizard line"
    _rec_name = "project_name"
    _order = "sequence"

    wizard_id = fields.Many2one("ps.planning.report.wizard", required=True)
    sequence = fields.Integer()
    business_line = fields.Char()
    project_name = fields.Char()
    project_code = fields.Char()
    days_commercial_full_month = fields.Float()
    days_planned_full_month = fields.Float()
    days_planned_mtd = fields.Float()
    days_actual_mtd = fields.Float()
    days_actual_planned_mtd = fields.Float()
    days_actual_commercial_mtd = fields.Float()
    budget_utilization = fields.Float()
    actual_commercial_ytm = fields.Float()
    manager_name = fields.Char()
