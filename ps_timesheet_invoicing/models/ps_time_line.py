# -*- coding: utf-8 -*-
# Copyright 2018 The Open Source Company ((www.tosc.nl).)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, _
from datetime import datetime, timedelta
from odoo.exceptions import UserError, ValidationError
import calendar

class TimeLine(models.Model):
    _name = 'ps.time.line'
    _description = 'Professional Services Time Line'
    _order = 'date desc'
    _check_company_auto = True

    # ## Todo: check/correct
    # def _compute_sheet(self):
    #     """Links the timesheet line to the corresponding sheet"""
    #     uom_hrs = self.env.ref("uom.product_uom_hour").id
    #     for timesheet in self.filtered(lambda line: line.task_id and line.product_uom_id.id == uom_hrs):
    #         sheet = timesheet._determine_sheet()
    #         if timesheet.sheet_id != sheet:
    #             timesheet.sheet_id = sheet

    @api.depends('project_id.chargeable',
                 'project_id.correction_charge',
                 'project_id.user_id',
                 'project_id.invoice_properties.expenses',
                 'project_id.standard_task_id.task_user_ids',
                 'account_id',
                 'unit_amount',
                 'planned',
                 'date',
                 'task_id',
                 'user_id',
                 'task_id.task_user_ids',
                 'task_user_id.from_date',
                 'task_user_id.product_id',
                 'task_user_id.fee_rate',
                 )
    def _compute_time_line(self):
        self.filtered(lambda i: isinstance(i.id, (int, long))).read(
            ['task_user_id', 'line_fee_rate', 'product_id', 'amount'])
        uom_hrs = self.env.ref("product.product_uom_hour").id
        for line in self.filtered(lambda line: line.task_id and line.product_uom_id.id == uom_hrs):
            # all analytic lines need a project_operating_unit_id and
            # for all analytic lines day_name, week_id and month_id are computed
            date = line.date
            line.project_operating_unit_id = \
                line.account_id.operating_unit_ids \
                and line.account_id.operating_unit_ids[0] or False
            line.day_name = str(datetime.strptime(date, '%Y-%m-%d').
                                strftime("%m/%d/%Y")) + \
                            ' (' + datetime.strptime(date, '%Y-%m-%d'). \
                                strftime('%a') + ')'
            line.week_id = line.find_daterange_week(date)
            line.month_id = var_month_id = line.find_daterange_month(date)
            # only when project_id these fields are computed
            if line.project_id:
                line.chargeable = line.project_id.chargeable
                line.correction_charge = line.project_id.correction_charge
                line.project_mgr = line.project_id.user_id or False
                if line.project_id.invoice_properties:
                    line.expenses = line.project_id.invoice_properties.expenses
            else:
                line.project_mgr = line.account_id.project_ids.user_id or False
            task = line.task_id
            user = line.user_id
            date = line.date
            # only if task_id the remaining fields are computed
            if task and user:
                uou = user._get_operating_unit_id()
                if uou:
                    line.operating_unit_id = uou
                    if line.planned:
                        line.planned_qty = line.unit_amount
                        line.actual_qty = 0.0
                    else:
                        if line.month_of_last_wip:
                            line.wip_month_id = line.month_of_last_wip
                        else:
                            line.wip_month_id = var_month_id
                        if line.product_uom_id.id == uom_hrs:
                            if date and line.state in ['new',
                                                       'draft',
                                                       'open',
                                                       'delayed',
                                                       'invoiceable',
                                                       'progress',
                                                       're_confirmed', ]:
                                task_user = self.env['task.user'].get_task_user_obj(task.id, user.id, date)[:1]
                                if task_user:
                                    line.task_user_id = task_user
                                # check standard task for fee earners
                                else:
                                    # project_id = self.env['project.task'].browse(task.id).project_id
                                    if line.project_id:
                                        standard_task = line.project_id.standard_task_id
                                    if len(standard_task) == 1:
                                        line.task_user_id = self.env['task.user'].get_task_user_obj(standard_task.id,
                                                                                                    user.id,
                                                                                                    date) or False
                                line.line_fee_rate = line.get_fee_rate()[0]
                                line.amount = line.get_fee_rate_amount()
                                line.product_id = line.get_task_user_product()
                        line.actual_qty = line.unit_amount
                        line.planned_qty = 0.0

    @api.model
    def _default_user(self):
        return self.env.context.get('user_id', self.env.user.id)

    def find_daterange_week(self, date):
        """
        try to find a date range with type 'week'
        with @param:date contained in its date_start/date_end interval
        """
        date_range_type_cw_id = self.env.ref(
            'ps_date_range_week.date_range_calender_week').id
        s_args = [
            ('type_id', '=', date_range_type_cw_id),
            ('date_start', '<=', date),
            ('date_end', '>=', date),
            '|',
            ('company_id', '=', self.company_id.id),
            ('company_id', '=', False),
        ]
        date_range = self.env['date.range'].search(s_args,
                                                   limit=1,
                                                   order='company_id asc')
        return date_range

    def find_daterange_month(self, date):
        """
        try to find a date range with type 'month'
        with @param:date contained in its date_start/date_end interval
        """
        date_range_type_fm_id = self.env.ref(
            'account_fiscal_month.date_range_fiscal_month').id

        s_args = [
            ('type_id', '=', date_range_type_fm_id),
            ('date_start', '<=', date),
            ('date_end', '>=', date),
            '|',
            ('company_id', '=', self.company_id.id),
            ('company_id', '=', False),
        ]
        date_range = self.env['date.range'].search(
            s_args,
            limit=1,
            order='company_id asc'
        )
        return date_range

    @api.model
    def default_get(self, fields):
        context = self._context
        res = super(TimeLine, self).default_get(fields)
        if 'planning_lines' in context:
            project = self.env['project.project']
            project_id = context.get('default_project_id', project)
            task_id = context.get('default_task_id', False)
            project = project.browse(project_id)
            account_id = project.analytic_account_id
            operating_unit_id = account_id.operating_unit_ids and account_id.operating_unit_ids[0] or False
            res.update({'operating_unit_id': operating_unit_id, 'name': '/', 'task_id': task_id})
        if 'timesheet_date_start' in context:
            date = context.get('timesheet_date_start')
            res.update({'date': date})
        return res

    sheet_id = fields.Many2one(
        comodel_name="hr_timesheet.sheet",
        string="Sheet"
    )
    sheet_state = fields.Selection(
        string="Sheet State",
        related="sheet_id.state"
    )
    name = fields.Char(
        'Description',
        required=True
    )
    date = fields.Date(
        'Date',
        required=True,
        index=True,
        default=fields.Date.context_today
    )
    amount = fields.Monetary(
        'Amount',
        required=True,
        default=0.0
    )
    unit_amount = fields.Float(
        'Quantity',
        default=0.0
    )
    product_uom_id = fields.Many2one(
        'uom.uom',
        string='Unit of Measure',
        domain="[('category_id', '=', product_uom_category_id)]"
    )
    account_id = fields.Many2one(
        'account.analytic.account',
        'Analytic Account',
        required=True,
        ondelete='restrict',
        index=True,
        check_company=True
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Partner',
        check_company=True
    )
    user_id = fields.Many2one(
        'res.users',
        string='User',
        default=_default_user
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        readonly=True,
        default=lambda self: self.env.company
    )
    currency_id = fields.Many2one(
        related="company_id.currency_id",
        string="Currency",
        readonly=True,
        store=True,
        compute_sudo=True
    )
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        check_company=True
    )
    task_id = fields.Many2one(
        'project.task',
        'Task',
        compute='_compute_task_id',
        store=True,
        readonly=False,
        index=True,
        domain="[('company_id', '=', company_id), ('project_id.allow_timesheets', '=', True), ('project_id', '=?', project_id)]"
    )
    project_id = fields.Many2one(
        'project.project',
        'Project',
        compute='_compute_project_id',
        store=True,
        readonly=False,
        domain=_domain_project_id
    )
    user_id = fields.Many2one(
        compute='_compute_user_id',
        store=True,
        readonly=False
    )
    employee_id = fields.Many2one(
        'hr.employee',
        "Employee",
    )
    department_id = fields.Many2one(
        'hr.department',
        "Department",
        store=True,
        compute_sudo=True
    )
    ## todo: are we using this?
    # encoding_uom_id = fields.Many2one(
    #     'uom.uom',
    #     compute='_compute_encoding_uom_id'
    # )
    kilometers = fields.Integer(
        'Kilometers'
    )
    non_invoiceable_mileage = fields.Boolean(
        string='Invoice Mileage',
        store=True
    )
    ref_id = fields.Many2one(
        'account.analytic.line',
        string='Reference'
    )
    week_id = fields.Many2one(
        'date.range',
        compute=_compute_time_line,
        string='Week',
        store=True,
    )
    month_id = fields.Many2one(
        'date.range',
        compute=_compute_time_line,
        string='Month',
        store=True,
    )
    wip_month_id = fields.Many2one(
        'date.range',
        compute=_compute_time_line,
        store=True,
        string="Month of Analytic Line or last Wip Posting"
    )
    month_of_last_wip = fields.Many2one(
        "date.range",
        "Month Of Next Reconfirmation"
    )
    operating_unit_id = fields.Many2one(
        'operating.unit',
        compute=_compute_time_line,
        string='Operating Unit',
        store=True
    )
    project_operating_unit_id = fields.Many2one(
        'operating.unit',
        compute=_compute_time_line,
        string='Project Operating Unit',
        store=True
    )
    task_id = fields.Many2one(
        'project.task', 'Task',
        ondelete='restrict'
    )
    planned = fields.Boolean(
        string='Planned'
    )
    actual_qty = fields.Float(
        string='Actual Qty',
        compute=_compute_time_line,
        store=True
    )
    planned_qty = fields.Float(
        string='Planned Qty',
        compute=_compute_time_line,
        store=True
    )
    day_name = fields.Char(
        string="Day",
        compute=_compute_time_line,
        store=True,
    )
    # ts_line = fields.Boolean(
    #     compute=_compute_analytic_line,
    #     string='Timesheet line',
    #     store=True,
    # )
    correction_charge = fields.Boolean(
        compute=_compute_time_line,
        string='Correction Chargeability',
        store=True,
    )
    chargeable = fields.Boolean(
        compute=_compute_time_line,
        string='Chargeable',
        store=True,
    )
    expenses = fields.Boolean(
        compute=_compute_time_line,
        string='Expenses',
        store=True,
    )
    project_mgr = fields.Many2one(
        comodel_name='res.users',
        compute=_compute_time_line,
        store=True
    )
    ot = fields.Boolean(
        string='Overtime',
    )
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee'
    )
    line_fee_rate = fields.Float(
        compute=_compute_time_line,
        string='Fee Rate',
        store=True,
    )
    project_rate = fields.Float(
        compute=_compute_time_line,
        string='Project Rate',
        store=True,
    )
    project_amount = fields.Float(
        compute=_compute_time_line,
        string='Project Amount',
        store=True,
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('open', 'Confirmed'),
        ('delayed', 'Delayed'),
        ('invoiceable', 'To be Invoiced'),
        ('progress', 'In Progress'),
        ('invoice_created', 'Invoice Created'),
        ('invoiced', 'Invoiced'),
        ('write-off', 'Write-Off'),
        ('change-chargecode', 'Change-Chargecode'),
        ('re_confirmed', 'Re-Confirmed'),
        ('invoiced-by-fixed', 'Invoiced by Fixed'),
        ('expense-invoiced', 'Expense Invoiced')
    ],
        string='Status',
        readonly=True,
        copy=False,
        index=True,
        track_visibility='onchange',
        default='draft'
    )
    user_total_id = fields.Many2one(
        'analytic.user.total',
        string='Summary Reference',
    )
    date_of_last_wip = fields.Date(
        "Date Of Last WIP"
    )
    date_of_next_reconfirmation = fields.Date(
        "Date Of Next Reconfirmation"
    )

    @api.constrains('company_id', 'account_id')
    def _check_company_id(self):
        for line in self:
            if line.account_id.company_id and line.company_id.id != line.account_id.company_id.id:
                raise ValidationError(
                    _('The selected account belongs to another company than the one you\'re trying to create an analytic item for'))

