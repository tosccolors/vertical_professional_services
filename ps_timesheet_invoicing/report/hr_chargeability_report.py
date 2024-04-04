from odoo import _, api, fields, models, tools
from odoo.exceptions import UserError


class HrChargeabilityReport(models.Model):
    _name = "hr.chargeability.report"
    _auto = False
    _description = "Hr Chargeability Report"

    date = fields.Date("Date", readonly=True)
    user_id = fields.Many2one("res.users", string="User", readonly=True)
    captured_hours = fields.Float(string="Captured Hrs", readonly=True)
    chargeable_hours = fields.Float(string="Chargeable Hrs", readonly=True)
    norm_hours = fields.Float(string="Norm Hrs", readonly=True)
    chargeability = fields.Float(string="Chargeability", readonly=True)
    department_id = fields.Many2one("hr.department", string="Department", readonly=True)
    operating_unit_id = fields.Many2one(
        "operating.unit", string="Department Operating Unit", readonly=True
    )
    external = fields.Boolean(string="External", readonly=True)
    ts_optional = fields.Boolean(string="Timesheet Optional", readonly=True)
    ts_no_8_hours_day = fields.Boolean(string="No 8 Hours Per Day", readonly=True)

    def init(self):
        uom = self.env.ref("uom.product_uom_hour").id
        tools.drop_view_if_exists(self.env.cr, "hr_chargeability_report")
        self.env.cr.execute(
            """
            CREATE OR REPLACE VIEW hr_chargeability_report AS (
                SELECT
                    min(pst.id) as id,
                    pst.date as date,
                    pst.user_id as user_id,
                    pst.operating_unit_id as operating_unit_id,
                    pst.department_id as department_id,
                    -- emp.external as external,
                    emp.timesheet_optional as ts_optional,
                    emp.timesheet_no_8_hours_day as ts_no_8_hours_day,
                    SUM(unit_amount) as captured_hours,
                    SUM(CASE
                             WHEN pst.chargeable = 'true'
                             THEN unit_amount
                             ELSE 0
                        END) as chargeable_hours,
                    (COUNT (DISTINCT pst.date) * (
                             CASE
                             WHEN dr.date_end - pst.date > 1
                             THEN 8
                             ELSE 0
                             END
                             )
                    - SUM(
                        CASE
                            WHEN pst.correction_charge = 'true'
                            THEN unit_amount
                            ELSE 0
                        END)) as norm_hours,
                    0.0  as chargeability
                FROM ps_time_line pst
                JOIN resource_resource resource
                ON (resource.user_id = pst.user_id)
                JOIN hr_employee emp
                ON (emp.resource_id = resource.id)
                JOIN date_range dr
                ON (dr.id = pst.week_id)
                WHERE pst.product_uom_id = %s
                    AND (pst.ot = FALSE or pst.ot is null)
                    AND pst.project_id IS NOT NULL
                    AND resource.active = TRUE
                GROUP BY
                    pst.operating_unit_id,
                    pst.user_id,
                    dr.date_end,
                    pst.date,
                    pst.department_id,
                    -- emp.external,
                    emp.timesheet_optional,
                    emp.timesheet_no_8_hours_day
                ORDER BY pst.date
            )
            """,
            (uom,),
        )

    @api.model
    def read_group(
        self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True
    ):
        res = super().read_group(
            domain, fields, groupby, offset, limit=limit, orderby=orderby, lazy=lazy
        )
        for index in range(len(res)):
            if res[index].get("norm_hours", False) and res[index].get(
                "chargeable_hours", False
            ):
                res[index]["chargeability"] = (
                    (res[index]["chargeable_hours"] / res[index]["norm_hours"]) * 100
                    if res[index]["norm_hours"] > 0
                    else 0.0
                )
            else:
                raise UserError(
                    _(
                        "You have to select Chargeable Hours and Norm Hours as "
                        "measure for this report"
                    )
                )
        return res
