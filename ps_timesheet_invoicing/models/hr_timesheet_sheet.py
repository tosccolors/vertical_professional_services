# Copyright 2018 The Open Source Company ((www.tosc.nl).)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
from datetime import datetime, timedelta

from odoo import SUPERUSER_ID, _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.osv.expression import TRUE_LEAF
from odoo.tools import float_compare

_logger = logging.getLogger(__name__)


class HrTimesheetSheet(models.Model):
    _inherit = "hr_timesheet.sheet"
    _order = "week_id desc"

    def get_week_to_submit(self):
        dt = datetime.now()
        emp_obj = self.env.user.employee_id
        emp_id = emp_obj.id
        timesheets = self.env["hr_timesheet.sheet"].search(
            [("employee_id", "=", emp_id)]
        )
        logged_weeks = timesheets.mapped("week_id").ids if timesheets else []
        date_range = self.env["date.range"]
        date_range_type_cw_id = self.env.ref(
            "ps_date_range_week.date_range_calender_week"
        ).id
        employment_date = emp_obj.sudo().official_date_of_employment
        employment_week = date_range.search(
            [
                ("type_id", "=", date_range_type_cw_id),
                ("date_start", "<=", employment_date),
                ("date_end", ">=", employment_date),
            ]
        )
        past_week_domain = [
            ("type_id", "=", date_range_type_cw_id),
            ("date_end", "<", dt - timedelta(days=dt.weekday())),
        ]
        if employment_week:
            past_week_domain += [("date_start", ">=", employment_week.date_start)]

        if logged_weeks:
            past_week_domain += [("id", "not in", logged_weeks)]

        past_weeks = date_range.search(past_week_domain, limit=1, order="date_start")
        week = date_range.search(
            [
                ("type_id", "=", date_range_type_cw_id),
                ("date_start", "=", dt - timedelta(days=dt.weekday())),
            ],
            limit=1,
        )

        if week or past_weeks:
            if past_weeks and past_weeks.id not in logged_weeks:
                return past_weeks
            elif week and week.id not in logged_weeks:
                return week
            else:
                upcoming_week = date_range.search(
                    [
                        ("id", "not in", logged_weeks),
                        ("type_id", "=", date_range_type_cw_id),
                        ("date_start", ">", dt - timedelta(days=dt.weekday())),
                    ],
                    order="date_start",
                    limit=1,
                )
                if upcoming_week:
                    return upcoming_week
                else:
                    return False
        return False

    @api.onchange("add_line_project_id")
    def onchange_add_project_id(self):
        default_tasks = (
            self.add_line_project_id.task_ids.filtered("standard")
            or self.add_line_project_id.task_ids
        )
        if len(default_tasks) == 1:
            self.add_line_task_id = default_tasks
        return super().onchange_add_project_id()

    @api.model
    def default_get(self, fields):
        # sudo super because it accesses employee fields normal users can't
        rec = super(HrTimesheetSheet, self.sudo()).default_get(fields)
        week = self.get_week_to_submit()
        if week:
            rec.update(
                {
                    "week_id": week.id,
                    "date_start": week.date_start,
                    "date_end": week.date_end,
                }
            )
        else:
            if self._uid == SUPERUSER_ID:
                raise UserError(
                    _(
                        "Please generate Date Ranges.\n"
                        "Menu: "
                        "Settings > Technical > Date Ranges > Generate Date Ranges."
                    )
                )
            else:
                raise UserError(_("Please contact administrator."))
        return rec

    def _get_week_domain(self):
        emp_id = self.env.user.employee_id.id
        timesheets = self.env["hr_timesheet.sheet"].search(
            [("employee_id", "=", emp_id)]
        )
        logged_weeks = timesheets.mapped("week_id").ids if timesheets else []
        date_range_type_cw_id = self.env.ref(
            "ps_date_range_week.date_range_calender_week"
        ).id
        return [
            ("type_id", "=", date_range_type_cw_id),
            ("active", "=", True),
            ("id", "not in", logged_weeks) if logged_weeks else TRUE_LEAF,
        ]

    def _get_employee_domain(self):
        emp_id = self.env.user.employee_id
        domain = [("id", "=", emp_id.id)] if emp_id else [("id", "=", False)]
        return domain

    def _get_vehicle(self):
        vehicle = self.env["fleet.vehicle"]
        if self.employee_id:
            user = self.employee_id.user_id or False
            if user:
                vehicle = (
                    self.env["fleet.vehicle.driver"]
                    .sudo()
                    .search(
                        [
                            ("driver_id", "=", user.partner_id.id),
                            ("date_start", "<=", self.date_start),
                            "|",
                            ("date_end", "=", False),
                            # we don't enforce that the car lease covers the whole week
                            ("date_end", ">=", self.date_start),
                        ],
                        limit=1,
                    )
                ).mapped("vehicle_id")
        return vehicle

    def _get_latest_mileage(self):
        vehicle = self._get_vehicle()
        odoo_meter_sudo = self.env["fleet.vehicle.odometer"].sudo()
        if vehicle and self.week_id:
            latest_mileage = (
                odoo_meter_sudo.sudo()
                .search(
                    [
                        ("vehicle_id", "=", vehicle.id),
                        ("date", "<", self.week_id.date_start),
                    ],
                    order="date desc",
                    limit=1,
                )
                .value
            )
        elif vehicle:
            latest_mileage = (
                odoo_meter_sudo.sudo()
                .search([("vehicle_id", "=", vehicle.id)], order="date desc", limit=1)
                .value
            )
        else:
            latest_mileage = self.sudo().starting_mileage_editable
        return latest_mileage

    @api.depends("employee_id", "week_id")
    def _compute_starting_mileage(self):
        for sheet in self:
            sheet.vehicle = True if sheet._get_vehicle() else False
            sheet.starting_mileage = sheet._get_latest_mileage()

    @api.depends("timesheet_ids.kilometers")
    def _compute_business_mileage(self):
        for sheet in self.with_context(sheet_write=True):
            sheet.business_mileage = (
                sum(sheet.sudo().timesheet_ids.mapped("kilometers"))
                if sheet.timesheet_ids
                else 0
            )

    @api.depends("end_mileage", "business_mileage", "starting_mileage")
    def _compute_private_mileage(self):
        for sheet in self.with_context(sheet_write=True):
            m = sheet.end_mileage - sheet.business_mileage - sheet.starting_mileage
            sheet.private_mileage = m if m > 0 else 0

    @api.depends("timesheet_ids.unit_amount")
    def _compute_overtime_hours(self):
        for this in self.with_context(sheet_write=True):
            ptl_incl_ott = this.timesheet_ids.filtered(lambda a: not a.task_id.standby)
            ptl_ott = this.timesheet_ids.filtered("project_id.overtime")
            working_hrs_incl_ott = sum(ptl_incl_ott.mapped("unit_amount"))
            ott = sum(ptl_ott.mapped("unit_amount"))
            this.overtime_hours = working_hrs_incl_ott - 40
            this.overtime_hours_delta = working_hrs_incl_ott - ott - 40

    # Override for ps_time_line
    timesheet_ids = fields.One2many(comodel_name="ps.time.line", string="PS Time Lines")
    # End override
    validator_user_ids = fields.Many2many("res.users", string="Validators")
    week_id = fields.Many2one(
        "date.range", domain=_get_week_domain, string="Timesheet Week", required=True
    )
    employee_id = fields.Many2one(domain=_get_employee_domain)
    starting_mileage = fields.Integer(
        compute="_compute_starting_mileage", string="Starting Mileage", store=False
    )
    starting_mileage_editable = fields.Integer(string="Starting Mileage (editable)")
    vehicle = fields.Boolean(
        compute="_compute_starting_mileage", string="Vehicle", store=False
    )
    business_mileage = fields.Integer(
        compute="_compute_business_mileage", string="Business Mileage", store=True
    )
    private_mileage = fields.Integer(
        compute="_compute_private_mileage", string="Private Mileage", store=True
    )
    end_mileage = fields.Integer("End Mileage")
    overtime_hours = fields.Float(
        compute="_compute_overtime_hours", string="Overtime Hours", store=True
    )
    overtime_hours_delta = fields.Float(
        compute="_compute_overtime_hours", string="Change in Overtime Hours", store=True
    )
    odo_log_id = fields.Many2one("fleet.vehicle.odometer", string="Odo Log ID")
    overtime_line_id = fields.Many2one("ps.time.line", string="Overtime Entry")
    date_start = fields.Date(related="week_id.date_start")
    date_end = fields.Date(related="week_id.date_end")

    state = fields.Selection(
        help=" * The 'Open' status is used when a user is encoding a new and "
        "unconfirmed timesheet. "
        "\n* The 'Waiting Approval' status is used to confirm the timesheet by user. "
        "\n* The 'Approved' status is used when the users timesheet is accepted by "
        "his/her senior.",
    )

    # start override methods from hr_timesheet and hr_timesheet_sheet
    def _get_data_matrix(self):
        with self.env["ps.time.line"]._as_analytic_line(self):
            return super()._get_data_matrix()

    def _compute_timesheet_ids(self):
        with self.env["ps.time.line"]._as_analytic_line(self):
            return super()._compute_timesheet_ids()

    def add_line(self):
        with self.env["ps.time.line"]._as_analytic_line(self):
            return super().add_line()

    # end overrides

    @api.constrains("week_id", "employee_id")
    def _check_sheet_date(self, forced_user_id=False):
        for sheet in self:
            new_user_id = forced_user_id or sheet.user_id and sheet.user_id.id
            if new_user_id:
                self.env.cr.execute(
                    """
                        SELECT id
                        FROM hr_timesheet_sheet
                        WHERE week_id=%s
                        AND user_id=%s""",
                    (sheet.week_id.id, new_user_id),
                )
                if self.env.cr.rowcount > 1:
                    raise ValidationError(
                        _(
                            "You cannot have 2 timesheets with the same week_id!\n"
                            "Please use the menu 'My Current Timesheet' to avoid this "
                            "problem."
                        )
                    )

    def _check_overlapping_sheets(self):
        # handled above
        pass

    def _check_start_end_dates(self):
        # implicitly handled by those being readonly related fields to period
        pass

    def _check_can_review(self):
        """Enforce can_review flag for all review policies"""
        super()._check_can_review()
        if any(not this.can_review for this in self):
            raise UserError(_("You cannot review this timesheet"))

    def _get_possible_reviewers(self):
        """Allow self-review only for timesheet managerX"""
        return super()._get_possible_reviewers() - self.mapped(
            "employee_id.user_id"
        ).filtered(
            lambda x: not x.has_group("ps_timesheet_invoicing.group_timesheet_manager")
        )

    def duplicate_last_week(self):
        if self.week_id and self.employee_id:
            ds = self.week_id.date_start
            date_start = ds - timedelta(days=7)
            date_end = ds - timedelta(days=1)
            date_range_type_cw_id = self.env.ref(
                "ps_date_range_week.date_range_calender_week"
            ).id
            last_week = self.env["date.range"].search(
                [
                    ("type_id", "=", date_range_type_cw_id),
                    ("date_start", "=", date_start),
                    ("date_end", "=", date_end),
                ],
                limit=1,
            )
            if last_week:
                last_week_timesheet = self.env["hr_timesheet.sheet"].search(
                    [
                        ("employee_id", "=", self.employee_id.id),
                        ("week_id", "=", last_week.id),
                    ],
                    limit=1,
                )
                if not last_week_timesheet:
                    raise UserError(
                        _(
                            "You have no timesheet logged for last week. "
                            "Duration: %s to %s"
                        )
                        % (
                            datetime.strftime(date_start, "%d-%b-%Y"),
                            datetime.strftime(date_end, "%d-%b-%Y"),
                        )
                    )
                else:
                    self.copy_with_query(last_week_timesheet.id)

    def _check_end_mileage(self):
        total = self.starting_mileage + self.business_mileage
        if self.end_mileage < total:
            raise ValidationError(
                _(
                    "End Mileage cannot be lower than the "
                    "Starting Mileage + Business Mileage."
                )
            )

    def action_timesheet_draft(self):
        """
        On timesheet reset draft check ps_time shouldn't be in invoiced
        :return: Super
        """
        if any(ts.state == "progress" for ts in self.timesheet_ids):
            raise UserError(
                _(
                    "You cannot modify timesheet entries either Invoiced or "
                    "belongs to PS Invoiced!"
                )
            )
        res = super().action_timesheet_draft()
        self._ps_reset_timesheet()
        return res

    def action_timesheet_refuse(self):
        result = super().action_timesheet_refuse()
        self._ps_reset_timesheet()
        return result

    def _ps_reset_timesheet(self):
        """Reset PS specific values"""
        if self.timesheet_ids:
            ids = tuple(self.timesheet_ids.ids)
            self.env.cr.execute(
                """
                UPDATE ps_time_line SET state = 'draft' WHERE id in %s;
                DELETE FROM ps_time_line WHERE ref_id in %s;
                """,
                (ids, ids),
            )
            self.env.cache.invalidate()
        if self.odo_log_id:
            self.sudo().odo_log_id.unlink()
        if self.overtime_line_id:
            self.overtime_line_id.unlink()

    def action_timesheet_confirm(self):
        self._check_end_mileage()
        vehicle = self._get_vehicle()
        if vehicle:
            self.odo_log_id = self.env["fleet.vehicle.odometer"].create(
                {
                    "value_period_update": self.business_mileage + self.private_mileage,
                    "date": self.week_id.date_end,
                    "vehicle_id": vehicle.id,
                }
            )
        date_from = self.date_start
        tot_ot_hrs = 0
        GTM = self.employee_id.user_id.has_group(
            "ps_timesheet_invoicing.group_timesheet_manager"
        )
        no_ott_check = (
            self.employee_id.sudo().no_ott_check
            or self.employee_id.sudo().department_id.no_ott_check
        )
        for i in range(7):
            date = datetime.strftime(date_from + timedelta(days=i), "%Y-%m-%d")
            hour = sum(
                self.env["ps.time.line"]
                .search(
                    [
                        ("date", "=", date),
                        ("sheet_id", "=", self.id),
                        ("task_id.standby", "=", False),
                    ]
                )
                .mapped("unit_amount")
            )
            if hour < 0 or hour > 24:
                raise UserError(_("Logged hours should be 0 to 24."))
            if not self.employee_id.sudo().timesheet_no_8_hours_day:
                if (
                    i < 5
                    and float_compare(
                        hour, 8, precision_digits=3, precision_rounding=None
                    )
                    < 0
                ):
                    raise UserError(
                        _(
                            "Each day from Monday to Friday needs to have at least "
                            "8 logged hours."
                        )
                    )
            ot_ptl = self.env["ps.time.line"].search(
                [
                    ("date", "=", date),
                    ("sheet_id", "=", self.id),
                    ("project_id.overtime", "=", True),
                ]
            )
            if not GTM and ot_ptl:
                ot_hrs = ot_ptl.unit_amount
                if (
                    not no_ott_check
                    and float_compare(
                        ot_hrs, 4, precision_digits=3, precision_rounding=None
                    )
                    > 0
                ):
                    raise UserError(
                        _(
                            "Each day maximum 4 hours overtime taken allowed from "
                            "Monday to Friday."
                        )
                    )
                tot_ot_hrs += ot_hrs
        if (
            not GTM
            and float_compare(
                tot_ot_hrs, 8, precision_digits=3, precision_rounding=None
            )
            > 0
        ):
            raise UserError(_("Maximum 8 hours overtime taken allowed in a week."))
        return super().action_timesheet_confirm()

    def create_overtime_entries(self):
        ps_time_line = self.env["ps.time.line"]
        if self.overtime_hours > 0 and not self.overtime_line_id:
            company_id = self.company_id.id or self.employee_id.company_id.id
            overtime_project = self.env["project.project"].search(
                [("company_id", "=", company_id), ("overtime_hrs", "=", True)]
            )
            overtime_project_task = self.env["project.task"].search(
                [("project_id", "=", overtime_project.id), ("standard", "=", True)]
            )
            if not overtime_project:
                raise ValidationError(_("Please define project with 'Overtime Hours'!"))

            uom = self.env.ref("uom.product_uom_hour").id
            ps_time_line = ps_time_line.create(
                {
                    "name": "Overtime line",
                    "account_id": overtime_project.analytic_account_id.id,
                    "project_id": overtime_project.id,
                    "task_id": overtime_project_task.id,
                    "date": self.date_end,
                    "unit_amount": self.overtime_hours,
                    "product_uom_id": uom,
                    "ot": True,
                    "user_id": self.user_id.id,
                }
            )
            self.overtime_line_id = ps_time_line.id
        elif self.overtime_line_id:
            if self.overtime_hours > 0:
                self.overtime_line_id.write({"unit_amount": self.overtime_hours})
            else:
                self.overtime_line_id.unlink()
        return self.overtime_line_id

    def action_timesheet_done(self):
        """
        On timesheet confirmed update ps_time_line state to confirmed
        :return: Super
        """
        res = super().action_timesheet_done()
        self.env.cr.execute(
            "UPDATE ps_time_line SET state = 'open' WHERE id in %s",
            (tuple(self.mapped("timesheet_ids.id")),),
        )
        self.create_overtime_entries()
        self.generate_km_lines()
        return res

    def action_view_overtime_entry(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "ps_timesheet_invoicing.ps_time_line_action"
        )
        return dict(
            action,
            view_mode="form",
            res_id=self.overtime_line_id.id,
            domain=[("id", "=", self.overtime_line_id.id)],
        )

    def copy_with_query(self, last_week_timesheet_id=None):
        query = """
        INSERT INTO
        ps_time_line
        (       create_uid,
                user_id,
                account_id,
                company_id,
                write_uid,
                amount,
                unit_amount,
                date,
                create_date,
                write_date,
                partner_id,
                name,
                code,
                currency_id,
                ref,
                general_account_id,
                move_id,
                product_id,
                -- amount_currency,
                project_id,
                department_id,
                task_id,
                sheet_id,
                ts_line,
                period_id,
                week_id,
                account_department_id,
                chargeable,
                operating_unit_id,
                project_operating_unit_id,
                correction_charge,
                ref_id,
                actual_qty,
                planned_qty,
                planned,
                kilometers,
                state,
                non_invoiceable_mileage,
                product_uom_id,
                employee_id)
        SELECT  DISTINCT ON (task_id)
                ptl.create_uid as create_uid,
                ptl.user_id as user_id,
                ptl.account_id as account_id,
                ptl.company_id as company_id,
                ptl.write_uid as write_uid,
                0 as amount,
                0 as unit_amount,
                ptl.date + 7 as date,
                %(create)s as create_date,
                %(create)s as write_date,
                ptl.partner_id as partner_id,
                '/' as name,
                ptl.code as code,
                ptl.currency_id as currency_id,
                ptl.ref as ref,
                ptl.general_account_id as general_account_id,
                ptl.move_id as move_id,
                ptl.product_id as product_id,
                -- 0 as amount_currency,
                ptl.project_id as project_id,
                ptl.department_id as department_id,
                ptl.task_id as task_id,
                %(sheet_ptl)s as sheet_id,
                ptl.ts_line as ts_line,
                dr.id as period_id,
                %(week_id_ptl)s as week_id,
                ptl.account_department_id as account_department_id,
                ptl.chargeable as chargeable,
                ptl.operating_unit_id as operating_unit_id,
                ptl.project_operating_unit_id as project_operating_unit_id,
                ptl.correction_charge as correction_charge,
                NULL as ref_id,
                0 as actual_qty,
                0 as planned_qty,
                ptl.planned as planned,
                0 as kilometers,
                'draft' as state,
                CASE
                  WHEN ip.invoice_mileage IS NULL THEN true
                  ELSE ip.invoice_mileage
                END AS non_invoiceable_mileage,
                ptl.product_uom_id as product_uom_id,
                ptl.employee_id
        FROM ps_time_line ptl
             LEFT JOIN project_project pp
             ON pp.id = ptl.project_id
             LEFT JOIN account_analytic_account aaa
             ON aaa.id = ptl.account_id
             LEFT JOIN project_invoicing_properties ip
             ON ip.id = pp.invoice_properties
             RIGHT JOIN hr_timesheet_sheet hss
             ON hss.id = ptl.sheet_id
             LEFT JOIN date_range dr
             ON (
                dr.type_id = %(date_range_type_calendar_week)s and
                dr.date_start <= ptl.date + 7 and
                dr.date_end >= ptl.date + 7
             )
             LEFT JOIN hr_employee he
             ON (hss.employee_id = he.id)
             LEFT JOIN task_user tu
             ON (
                tu.task_id = ptl.task_id and tu.user_id = ptl.user_id and
                ptl.date >= tu.from_date
             )
        WHERE hss.id = %(sheet_select)s
             AND ptl.ref_id IS NULL
             AND ptl.task_id NOT IN
                 (
                 SELECT DISTINCT task_id
                 FROM ps_time_line
                 WHERE sheet_id = %(sheet_ptl)s
                 )
              AND pp.allow_timesheets = TRUE
             ;"""

        self.env.cr.execute(
            query,
            {
                "create": str(fields.Datetime.to_string(fields.datetime.now())),
                "week_id_ptl": self.week_id.id,
                "sheet_select": last_week_timesheet_id,
                "sheet_ptl": self.id,
                "date_range_type_calendar_week": self.env.ref(
                    "ps_date_range_week.date_range_calender_week"
                ).id,
            },
        )
        self.env.cache.invalidate()
        return True

    def generate_km_lines(self):
        query = """
        INSERT INTO
        ps_time_line
        (       create_uid,
                user_id,
                account_id,
                company_id,
                write_uid,
                amount,
                unit_amount,
                date,
                create_date,
                write_date,
                partner_id,
                name,
                code,
                currency_id,
                ref,
                general_account_id,
                move_id,
                product_id,
                -- amount_currency,
                project_id,
                department_id,
                task_id,
                sheet_id,
                ts_line,
                period_id,
                week_id,
                account_department_id,
                chargeable,
                operating_unit_id,
                project_operating_unit_id,
                correction_charge,
                ref_id,
                actual_qty,
                planned_qty,
                planned,
                kilometers,
                state,
                non_invoiceable_mileage,
                product_uom_id,
                employee_id)
        SELECT  ptl.create_uid as create_uid,
                ptl.user_id as user_id,
                ptl.account_id as account_id,
                ptl.company_id as company_id,
                ptl.write_uid as write_uid,
                coalesce(ptl.kilometers * mileage_pt.list_price, 0) as amount,
                ptl.kilometers as unit_amount,
                ptl.date as date,
                %(create)s as create_date,
                %(create)s as write_date,
                ptl.partner_id as partner_id,
                ptl.name as name,
                ptl.code as code,
                ptl.currency_id as currency_id,
                ptl.ref as ref,
                ptl.general_account_id as general_account_id,
                ptl.move_id as move_id,
                pp.ps_mileage_product_id as product_id,
                -- ptl.amount_currency as amount_currency,
                ptl.project_id as project_id,
                ptl.department_id as department_id,
                ptl.task_id as task_id,
                NULL as sheet_id,
                NULL as ts_line,
                ptl.period_id as period_id,
                ptl.week_id as week_id,
                ptl.account_department_id as account_department_id,
                ptl.chargeable as chargeable,
                ptl.operating_unit_id as operating_unit_id,
                ptl.project_operating_unit_id as project_operating_unit_id,
                ptl.correction_charge as correction_charge,
                ptl.id as ref_id,
                ptl.actual_qty as actual_qty,
                0 as planned_qty,
                False as planned,
                0 as kilometers,
                'open' as state,
                CASE
                  WHEN ip.invoice_mileage IS NULL THEN true
                  ELSE ip.invoice_mileage
                END AS non_invoiceable_mileage,
                %(uom)s as product_uom_id,
                ptl.employee_id
        FROM ps_time_line ptl
             LEFT JOIN project_project pp
             ON pp.id = ptl.project_id
             LEFT JOIN account_analytic_account aaa
             ON aaa.id = ptl.account_id
             LEFT JOIN project_invoicing_properties ip
             ON ip.id = pp.invoice_properties
             RIGHT JOIN hr_timesheet_sheet hss
             ON hss.id = ptl.sheet_id
             LEFT JOIN hr_employee he
             ON (hss.employee_id = he.id)
             LEFT JOIN task_user tu
             ON (
                tu.task_id = ptl.task_id and tu.user_id = ptl.user_id and
                ptl.date >= tu.from_date
             )
             LEFT JOIN product_product mileage_pp
             ON pp.ps_mileage_product_id=mileage_pp.id
             LEFT JOIN product_template mileage_pt
             ON mileage_pp.product_tmpl_id=mileage_pt.id
        WHERE hss.id = %(sheet_select)s
             AND ptl.ref_id IS NULL
             AND ptl.kilometers > 0 ;
        """
        self.env.cr.execute(
            query,
            {
                "create": fields.datetime.now(),
                "week_id_ptl": self.week_id.id,
                "uom": self.env.ref("uom.product_uom_km").id,
                "sheet_select": self.id,
            },
        )
        self.env.cache.invalidate()
        return True


class SheetLine(models.TransientModel):
    _inherit = "hr_timesheet.sheet.line"

    @api.onchange("unit_amount")
    def onchange_unit_amount(self):
        """This method is called when filling a cell of the matrix."""
        res = super().onchange_unit_amount()
        if self.unit_amount > 24:
            self.update({"unit_amount": "0.0"})
            return {
                "warning": {
                    "title": _("Warning"),
                    "message": _("Logged hours should be 0 to 24."),
                }
            }
        return res


class SheetNewAnalyticLine(models.TransientModel):
    _inherit = "hr_timesheet.sheet.new.analytic.line"

    # override for replacing account_analytic_line by ps_time_line
    @api.model
    def _update_analytic_lines(self):
        with self.env["ps.time.line"]._as_analytic_line(self):
            return super()._update_analytic_lines()
