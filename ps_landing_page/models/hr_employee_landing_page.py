from datetime import datetime

from lxml import etree

from odoo import _, api, fields, models
from odoo.osv.expression import AND
from odoo.tools.safe_eval import safe_eval


class HrEmployeeLandingPage(models.TransientModel):
    _name = "hr.employee.landing_page"
    _description = "Employee landing page"
    _rec_name = "employee_id"

    @api.depends("employee_id")
    def _compute_all(self):

        # current week
        self.env.cr.execute(
            """SELECT * FROM date_range
            WHERE date_start <= NOW()::date
            AND date_end >=NOW()::date
            AND type_id = (SELECT id FROM date_range_type WHERE calender_week = true)
            LIMIT 1"""
        )
        try:
            current_week_id = self.env.cr.fetchone()[0]
        except TypeError:
            current_week_id = 0

        next_week_id = self.get_upcoming_week()
        if current_week_id == next_week_id.id or current_week_id < next_week_id.id:
            self.current_week = True
        else:
            self.current_week = False

        if next_week_id:
            self.next_week_id = next_week_id.name

        # compute vaction balance
        vacation_balance = 0
        if self.employee_id:
            vacation_balance = (
                self.employee_id.allocation_count
                - self.employee_id.allocation_used_count
            )
        self.vacation_balance = vacation_balance

        user_id = self.env.user.id
        # compute overtime balance
        self.env.cr.execute(
            """
            SELECT overtime_balanced FROM
            overtime_balance_report
            WHERE user_id=%s
            """,
            (user_id,),
        )
        overtime_balance = 0
        for x in self.env.cr.fetchall():
            overtime_balance += x[0]
        self.overtime_balance = overtime_balance

        current_year = datetime.now()
        first_date = str(current_year.year) + "-1-1"
        last_date = str(current_year.year) + "-12-31"
        hr_timesheet = self.env["hr_timesheet.sheet"]

        # compute private milage, Note: private_mileage is an computed field can't
        # be calulated through SQl
        self.private_km_balance = sum(
            hr_timesheet.search(
                [
                    ("employee_id", "=", self.employee_id.id),
                    "&",
                    ("week_id.date_start", ">=", first_date),
                    ("week_id.date_end", "<=", last_date),
                ]
            ).mapped("private_mileage")
        )

        # my timesheet status
        domain = self._get_action_domain(
            "hr_timesheet_sheet.act_hr_timesheet_sheet_my_timesheets"
        )
        timesheet_ids = hr_timesheet.search(domain, limit=10).ids
        self.emp_timesheet_status_ids = [(6, 0, timesheet_ids)]

        # to be approved timesheets
        domain = self._get_action_domain(
            "hr_timesheet_sheet.act_hr_timesheet_sheet_to_review"
        )
        to_be_approved_sheets = hr_timesheet.search(domain, limit=10).ids
        self.emp_timesheet_to_be_approved_ids = [(6, 0, to_be_approved_sheets)]

        # my expense status
        domain = self._get_action_domain("hr_expense.action_hr_expense_sheet_my_all")
        expense_ids = self.env["hr.expense.sheet"].search(domain, limit=10).ids
        self.emp_expense_status_ids = [(6, 0, expense_ids)]

        # to be approved expenses
        domain = self._get_action_domain(
            "hr_expense.action_hr_expense_sheet_all_to_approve"
        )
        to_be_approved_expense_ids = (
            self.env["hr.expense.sheet"].search(domain, limit=10).ids
        )
        self.emp_expense_to_be_approved_ids = [(6, 0, to_be_approved_expense_ids)]

    def _default_employee(self):
        return self.env.user.employee_id

    employee_id = fields.Many2one(
        "hr.employee", string="Employee", default=_default_employee, required=True
    )
    next_week_id = fields.Char(
        string="Week To Submit",
        compute="_compute_all",
    )
    vacation_balance = fields.Integer(compute="_compute_all", string="Vacation Balance")
    overtime_balance = fields.Integer(compute="_compute_all", string="Overtime Balance")
    private_km_balance = fields.Integer(
        compute="_compute_all", string="Private Mileage Balance"
    )
    emp_timesheet_status_ids = fields.Many2many(
        "hr_timesheet.sheet", compute="_compute_all", string="My Timesheet Status"
    )
    emp_timesheet_to_be_approved_ids = fields.Many2many(
        "hr_timesheet.sheet", compute="_compute_all", string="Timesheet To Be Approved"
    )
    emp_expense_status_ids = fields.Many2many(
        "hr.expense.sheet", compute="_compute_all", string="My Expense Status"
    )
    emp_expense_to_be_approved_ids = fields.Many2many(
        "hr.expense.sheet", compute="_compute_all", string="Expense To Be Approved"
    )
    current_week = fields.Boolean(compute="_compute_all")

    def employement_start_week(self):
        date_range = self.env["date.range"]
        emp_obj = self.env.user.employee_id
        date_range_type_cw_id = self.env.ref(
            "ps_date_range_week.date_range_calender_week"
        ).id
        employment_date = emp_obj.official_date_of_employment
        return date_range.search(
            [
                ("type_id", "=", date_range_type_cw_id),
                ("date_start", "<=", employment_date),
                ("date_end", ">=", employment_date),
            ]
        )

    def get_unsubmitted_timesheet(self):
        employment_week = self.employement_start_week()
        return self.env["hr_timesheet.sheet"].search(
            [
                ("user_id", "=", self.env.user.id),
                ("state", "in", ("draft", "new")),
                ("date_start", ">=", employment_week.date_start),
            ],
            limit=1,
            order="week_id",
        )

    def get_upcoming_week(self):
        unsubmitted_timesheet = self.get_unsubmitted_timesheet()
        if unsubmitted_timesheet:
            return unsubmitted_timesheet.week_id
        result = self.env["hr.timesheet.current.open"].open_timesheet()
        hr_timesheet = self.env["hr_timesheet.sheet"]
        if "res_id" in result:
            return hr_timesheet.browse(result["res_id"]).week_id
        return hr_timesheet.get_week_to_submit()

    def action_view_timesheet(self):
        self.ensure_one()
        unsubmitted_timesheet = self.get_unsubmitted_timesheet()
        if unsubmitted_timesheet:
            return {
                "name": _("Open Timesheet"),
                "view_type": "form",
                "view_mode": "form,tree",
                "res_id": unsubmitted_timesheet.id,
                "res_model": "hr_timesheet.sheet",
                "type": "ir.actions.act_window",
            }
        return self.env["hr.timesheet.current.open"].open_timesheet()

    def action_view_leaves_dashboard(self):
        self.ensure_one()
        ir_model_data = self.env["ir.model.data"]
        tree_res = ir_model_data.get_object_reference(
            "hr_holidays", "hr_leave_view_tree"
        )
        tree_id = tree_res and tree_res[1] or False
        self.env.cr.execute(
            """SELECT
            id
            FROM hr_leave
            WHERE employee_id = %s
            AND (state = 'validate' OR state = 'written')
            """,
            (self.employee_id.id,),
        )

        holidays = [x[0] for x in self.env.cr.fetchall()]
        return {
            "name": _("Leaves"),
            "type": "ir.actions.act_window",
            "view_type": "form",
            "view_mode": "tree",
            "res_model": "hr.leave",
            "views": [(tree_id, "tree")],
            "view_id": tree_id,
            "target": "current",
            "domain": [("id", "in", holidays)],
            "context": {"search_default_year": 1, "search_default_group_employee": 1},
        }

    def action_view_timesheet_tree(self):
        self.ensure_one()
        ir_model_data = self.env["ir.model.data"]
        tree_res = ir_model_data.get_object_reference(
            "hr_timesheet_sheet", "hr_timesheet_sheet_tree"
        )
        tree_id = tree_res and tree_res[1] or False
        return {
            "name": _("Timesheet"),
            "type": "ir.actions.act_window",
            "view_type": "form",
            "view_mode": "tree",
            "res_model": "hr_timesheet.sheet",
            "views": [(tree_id, "tree")],
            "view_id": tree_id,
            "target": "current",
            "domain": [("employee_id.user_id", "=", self.env.uid)],
        }

    def action_view_analytic_tree(self):
        self.ensure_one()
        ir_model_data = self.env["ir.model.data"]
        tree_res = ir_model_data.get_object_reference(
            "ps_timesheet_invoicing", "view_ps_time_line_tree"
        )
        tree_id = tree_res and tree_res[1] or False

        user_id = self.env.user.id
        self.env.cr.execute(
            """
            SELECT
                id
                FROM ps_time_line
                WHERE user_id = %s
                AND project_id IN
                 (SELECT id FROM project_project WHERE overtime_hrs = TRUE OR overtime = True)
            """,
            (user_id,),
        )

        entries = [_id for _id, in self.env.cr.fetchall()]

        return {
            "name": _("Time lines"),
            "type": "ir.actions.act_window",
            "view_type": "form",
            "view_mode": "tree",
            "res_model": "ps.time.line",
            "views": [(tree_id, "tree")],
            "view_id": tree_id,
            "target": "current",
            "domain": [("id", "in", entries)],
            "context": {
                "ps_time_line_hide_amount": True,
            },
        }

    def _get_action_domain(self, xmlid):
        """Return the domain of an action as it would be run by the web client"""
        action = self.env.ref(xmlid).sudo()
        eval_context = action._get_eval_context()
        domain = safe_eval(action.domain, eval_context)
        context = safe_eval(action.context, eval_context)
        extra_domains = []
        search_view = etree.fromstring(
            self.env[action.res_model].fields_view_get(
                action.search_view_id.id, "search"
            )["arch"]
        )
        for key in context:
            prefix = "search_default_"
            if not key.startswith(prefix):
                continue
            for node in search_view.xpath("//*[@name='%s']" % key[len(prefix) :]):
                extra_domains.append(safe_eval(node.get("domain", "[]"), eval_context))
        return AND([domain] + extra_domains)
