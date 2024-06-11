from odoo import api, fields, models, tools


class StatusTimeReport(models.Model):
    _name = "status.time.report"
    _auto = False
    _description = "Status Time Report"

    @api.depends("department_id")
    def _compute_atmost_parent_ou(self):
        department2ou = {}
        for this in self:
            if not this.department_id:
                continue
            if this.department_id in department2ou:
                this.operating_unit_id = department2ou[this.department_id]
            else:
                department = this.department_id
                while department.parent_id:
                    department = department.parent_id
                department2ou[
                    department
                ] = this.operating_unit_id = department.operating_unit_id

    employee_id = fields.Many2one("hr.employee", string="Employee", readonly=True)
    week_id = fields.Many2one("date.range", string="Week", readonly=True)
    department_id = fields.Many2one("hr.department", string="Department", readonly=True)
    operating_unit_id = fields.Many2one(
        "operating.unit",
        compute="_compute_atmost_parent_ou",
        string="Operating Unit",
        readonly=True,
    )
    state = fields.Char("State", readonly=True)
    validators = fields.Char(string="Validators")
    ts_optional = fields.Boolean("Time Sheet Optional", readonly=True)
    external = fields.Boolean(string="External", readonly=True)

    def init(self):
        drcw = self.env.ref("ps_date_range_week.date_range_calender_week").id
        tools.drop_view_if_exists(self.env.cr, "status_time_report")
        self.env.cr.execute(
            """
            CREATE OR REPLACE VIEW status_time_report AS (
            SELECT
                CAST(
                    CASE WHEN hrc.id < dr.id
                        THEN hrc.id + dr.id^2
                     ELSE hrc.id^2 + hrc.id + dr.id
                    END
                    as INTEGER) as id,
                dr.id as week_id,
                hrc.id as employee_id,
                hrc.department_id as department_id,
                hrc.external as external,
                hrc.timesheet_optional as ts_optional,
                string_agg(
                    coalesce(he.name, he_parent.name), ','
                    ORDER BY coalesce(he.name, he_parent.name) ASC
                ) as validators,
                htsss.state as state
            FROM date_range dr
            CROSS JOIN  hr_employee hrc
            LEFT JOIN hr_timesheet_sheet htsss
            ON (dr.id = htsss.week_id and hrc.id = htsss.employee_id)
            LEFT JOIN hr_department hd
            ON (hd.id = hrc.department_id)
            LEFT JOIN hr_employee he
            ON (htsss.reviewer_id=he.id)
            LEFT JOIN hr_employee he_parent
            ON (hrc.parent_id=he_parent.id)
            WHERE dr.type_id = %s
            AND hrc.official_date_of_employment < dr.date_start
            AND (
            hrc.end_date_of_employment > dr.date_end
            OR hrc.end_date_of_employment is NULL
            )
            GROUP BY hrc.id, dr.id, hrc.department_id, htsss.state
            )""",
            (drcw,),
        )
