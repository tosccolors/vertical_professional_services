# Copyright 2024 Hunki Enterprises BV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0)

from psycopg2.extensions import AsIs

from odoo import fields, models, tools


class PsTimeLinePlanningReport(models.Model):
    _name = "ps.time.line.planning.report"
    _description = "Activity Analysis (Contracted / Planned / Actual)"
    _auto = False

    project_id = fields.Many2one("project.project")
    task_id = fields.Many2one("project.task")
    employee_id = fields.Many2one("hr.employee")
    date = fields.Date()
    hours_actual = fields.Float()
    hours_planned = fields.Float()
    hours_contracted = fields.Float()

    def init(self):
        tools.drop_view_if_exists(self._cr, self._table)
        self._cr.execute(
            """
            CREATE view %s as
            SELECT
                id,
                project_id,
                task_id,
                employee_id,
                date,
                unit_amount as hours_actual,
                0 as hours_planned,
                0 as hours_contracted
            FROM ps_time_line
            UNION (
            WITH
            xmlid_month_range AS (
                SELECT res_id FROM ir_model_data
                WHERE module='account_fiscal_month' AND name='date_range_fiscal_month'
            ),
            month_days AS (
                SELECT generate_series(date_start, date_end, '1day')::date month_day,
                date_range.id range_id FROM date_range, xmlid_month_range
                WHERE date_range.type_id=xmlid_month_range.res_id
            ),
            work_days AS (
                SELECT month_day, range_id FROM month_days
                WHERE extract(isodow from month_day) < 6
            ),
            work_day_count AS (
                SELECT count(month_day) work_days, range_id FROM work_days GROUP BY range_id
            )
            SELECT
                id,
                project_id,
                task_id,
                employee_id,
                work_days.month_day,
                0 as hours_actual,
                0 as hours_planned,
                days * 8 / work_day_count.work_days as hours_contracted
            FROM ps_planning_line, work_days, work_day_count
            WHERE
            ps_planning_line.range_id=work_days.range_id
            AND
            ps_planning_line.range_id=work_day_count.range_id
            AND
            ps_planning_line.line_type='contracted'
            UNION
            SELECT
                id,
                project_id,
                task_id,
                employee_id,
                work_days.month_day,
                0 as hours_actual,
                days * 8 / work_day_count.work_days as hours_planned,
                0 as hours_contracted
            FROM ps_planning_line, work_days, work_day_count
            WHERE
            ps_planning_line.range_id=work_days.range_id
            AND
            ps_planning_line.range_id=work_day_count.range_id
            AND
            ps_planning_line.line_type='planned'
            )
        """,
            (AsIs(self._table),),
        )
