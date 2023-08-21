# -*- coding: utf-8 -*-
# Copyright 2018 The Open Source Company ((www.tosc.nl).)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, _, SUPERUSER_ID
from datetime import datetime, time, timedelta
from odoo.exceptions import UserError, ValidationError
from dateutil.rrule import MONTHLY, WEEKLY
from dateutil.relativedelta import relativedelta, SU
from odoo.tools import float_compare
import babel.dates

import babel.dates
import logging
import re
from collections import namedtuple

# from odoo.addons.queue_job.job import job, related_action


_logger = logging.getLogger(__name__)

empty_name = "/"

class HrTimesheetSheet(models.Model):
	_inherit = "hr_timesheet.sheet"
	_order = "week_id desc"


	def get_week_to_submit(self):
		dt = datetime.now()
		emp_obj = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
		emp_id = emp_obj.id if emp_obj else False
		timesheets = self.env['hr_timesheet.sheet'].search([('employee_id', '=', emp_id)])
		logged_weeks = timesheets.mapped('week_id').ids if timesheets else []
		date_range = self.env['date.range']
		date_range_type_cw_id = self.env.ref(
			'ps_date_range_week.date_range_calender_week').id
		employment_date = emp_obj.official_date_of_employment
		employment_week = date_range.search(
			[('type_id', '=', date_range_type_cw_id), ('date_start', '<=', employment_date),
			 ('date_end', '>=', employment_date)])
		past_week_domain = [('type_id', '=', date_range_type_cw_id),
							('date_end', '<', dt - timedelta(days=dt.weekday()))]
		if employment_week:
			past_week_domain += [('date_start', '>=', employment_week.date_start)]

		if logged_weeks:
			past_week_domain += [('id', 'not in', logged_weeks)]
		past_weeks = date_range.search(past_week_domain, limit=1, order='date_start')
		week = date_range.search([('type_id', '=', date_range_type_cw_id), ('date_start', '=', dt - timedelta(days=dt.weekday()))], limit=1)

		if week or past_weeks:
			if past_weeks and past_weeks.id not in logged_weeks:
				return past_weeks
			elif week and week.id not in logged_weeks:
				return week
			else:
				upcoming_week = date_range.search([
					('id', 'not in', logged_weeks),
					('type_id','=',date_range_type_cw_id),
					('date_start', '>', dt-timedelta(days=dt.weekday()))
				], order='date_start', limit=1)
				if upcoming_week:
					return upcoming_week
				else:
					return False
		return False

	@api.model
	def default_get(self, fields):
		rec = super().default_get(fields)
		week = self.get_week_to_submit()
		if week:
			rec.update({'week_id': week.id})
		else:
			if self._uid == SUPERUSER_ID:
				raise UserError(_
				('Please generate Date Ranges.\n Menu: Settings > Technical > Date Ranges > Generate Date Ranges.'))
			else:
				raise UserError(_
				('Please contact administrator.'))
		return rec

	def _get_week_domain(self):
		emp_id = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
		emp_id = emp_id.id if emp_id else False
		timesheets = self.env['hr_timesheet.sheet'].search([('employee_id', '=', emp_id)])
		logged_weeks = timesheets.mapped('week_id').ids if timesheets else []
		date_range_type_cw_id = self.env.ref(
			'ps_date_range_week.date_range_calender_week').id
		return [('type_id','=', date_range_type_cw_id), ('active','=',True), ('id', 'not in', logged_weeks)]

	def _default_employee(self):
		emp_ids = self.env['hr.employee'].search([('user_id', '=', self.env.uid)])
		return emp_ids and emp_ids[0] or False

	def _get_employee_domain(self):
		emp_id = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
		domain = [('id', '=', emp_id.id)] if emp_id else [('id', '=', False)]
		return domain

	def _get_vehicle(self):
		vehicle = False
		if self.employee_id:
			user = self.employee_id.user_id or False
			if user:
				dtt_vehicle = self.env['data.time.tracker'].sudo().search([
					('model','=','fleet.vehicle'),
					('relation_model','=','res.partner'),
					('relation_ref', '=', user.partner_id.id),
					('date_from', '<', self.date_start),
					('date_to', '>=', self.date_end)],limit=1)
				if dtt_vehicle:
					vehicle = self.env['fleet.vehicle'].sudo().search([
						('id', '=', dtt_vehicle.model_ref)], limit=1)
				else:
					vehicle = self.env['fleet.vehicle'].sudo().search([
					('driver_id', '=', user.partner_id.id)], limit=1)
		return vehicle

	def _get_latest_mileage(self):
		vehicle = self._get_vehicle()
		odoo_meter_sudo = self.env['fleet.vehicle.odometer'].sudo()
		if vehicle and self.week_id:
			latest_mileage = odoo_meter_sudo.sudo().search([('vehicle_id', '=', vehicle.id), ('date', '<', self.week_id.date_start)], order='date desc', limit=1).value
		elif vehicle:
			latest_mileage = odoo_meter_sudo.sudo().search([('vehicle_id', '=', vehicle.id)], order='date desc', limit=1).value
		else:
			latest_mileage = self.sudo().starting_mileage_editable
		return latest_mileage

	@api.depends('employee_id','week_id')
	def _get_starting_mileage(self):
		for sheet in self:
			sheet.vehicle = True if sheet._get_vehicle() else False
			sheet.starting_mileage = sheet._get_latest_mileage()

	@api.depends('timesheet_ids.kilometers')
	def _get_business_mileage(self):
		for sheet in self:
			sheet.business_mileage = sum(sheet.sudo().timesheet_ids.mapped('kilometers')) if sheet.timesheet_ids else 0

	@api.depends('end_mileage','business_mileage','starting_mileage')
	def _get_private_mileage(self):
		for sheet in self:
			m = sheet.end_mileage - sheet.business_mileage - sheet.starting_mileage
			sheet.private_mileage = m if m > 0 else 0

	@api.depends('timesheet_ids')
	def _get_overtime_hours(self):
		ptl_incl_ott = self.timesheet_ids.filtered(lambda a: not a.task_id.standby)
		ptl_ott = self.timesheet_ids.filtered('project_id.overtime')
		working_hrs_incl_ott = sum(ptl_incl_ott.mapped('unit_amount'))
		ott = sum(ptl_ott.mapped('unit_amount'))
		self.overtime_hours = working_hrs_incl_ott - 40
		self.overtime_hours_delta = working_hrs_incl_ott - ott - 40

	## Override for ps_time_line
	timesheet_ids = fields.One2many(
		comodel_name="ps.time.line",
		inverse_name="sheet_id",
		string="PS Time Lines",
		readonly=True,
		states={"new": [("readonly", False)], "draft": [("readonly", False)]},
	)
	## End override
	validator_user_ids = fields.Many2many(
		'res.users',
		string='Validators'
	)
	week_id = fields.Many2one(
		'date.range',
		domain=_get_week_domain,
		string="Timesheet Week",
		required=True
	)
	employee_id = fields.Many2one(
		'hr.employee',
		string='Employee',
		default=_default_employee,
		required=True,
		domain=_get_employee_domain
	)
	starting_mileage = fields.Integer(
		compute='_get_starting_mileage',
		string='Starting Mileage',
		store=False
	)
	starting_mileage_editable = fields.Integer(
		string='Starting Mileage'
	)
	vehicle = fields.Boolean(
		compute='_get_starting_mileage',
		string='Vehicle',
		store=False
	)
	business_mileage = fields.Integer(
		compute='_get_business_mileage',
		string='Business Mileage',
		store=True
	)
	private_mileage = fields.Integer(
		compute='_get_private_mileage',
		string='Private Mileage',
		store=True
	)
	end_mileage = fields.Integer(
		'End Mileage'
	)
	overtime_hours = fields.Float(
		compute="_get_overtime_hours",
		string='Overtime Hours',
		store=True
	)
	overtime_hours_delta = fields.Float(
		compute="_get_overtime_hours",
		string='Change in Overtime Hours',
		store=True
	)
	odo_log_id = fields.Many2one(
		'fleet.vehicle.odometer',
		string="Odo Log ID"
	)
	overtime_line_id = fields.Many2one(
		'ps.time.line',
		string="Overtime Entry"
	)
	date_start = fields.Date(
		string='Date From',
		related='week_id.date_start',
		required=True,
		index=True,
		readonly=True,
		states={'new': [('readonly', False)]},
	)
	date_end = fields.Date(
		string='Date To',
		related='week_id.date_end',
		required=True,
		index=True,
		readonly=True,
		states={'new': [('readonly', False)]},
	)

	state = fields.Selection([
		('new', 'New'),
		('draft', 'Open'),
		('confirm', 'Waiting Approval'),
		('done', 'Approved')], default='new', track_visibility='onchange',
		string='Status', required=True, readonly=True, index=True,
		help=' * The \'Open\' status is used when a user is encoding a new and unconfirmed timesheet. '
			 '\n* The \'Waiting Approval\' status is used to confirm the timesheet by user. '
			 '\n* The \'Approved\' status is used when the users timesheet is accepted by his/her senior.')

# 	## with override of date fields as related of week_id not necessary anymore
# 	# @api.onchange('week_id', 'date_from', 'date_to')
# 	# def onchange_week(self):
# 	#     self.date_from = self.week_id.date_start
# 	#     self.date_to = self.week_id.date_end
#
# 	#  @api.onchange('starting_mileage', 'business_mileage')
# 	#  def onchange_private_mileage(self):
# 	#      if self.private_mileage == 0:
# 	#          self.end_mileage = self.starting_mileage + self.business_mileage
#
#
	## start override methods from hr_timesheet and hr_timesheet_sheet
	def _get_data_matrix(self):
		self.ensure_one()
		MatrixKey = self._matrix_key()
		matrix = {}
		empty_line = self.env["ps.time.line"]
		for line in self.timesheet_ids:
			key = MatrixKey(**self._get_matrix_key_values_for_line(line))
			if key not in matrix:
				matrix[key] = empty_line
			matrix[key] += line
		for date in self._get_dates():
			for key in matrix.copy():
				key = MatrixKey(**{**key._asdict(), "date": date})
				if key not in matrix:
					matrix[key] = empty_line
		return matrix

	def _compute_timeline_ids(self):
		PSTimeLines = self.env["ps.time.line"]
		for sheet in self:
			domain = sheet._get_timesheet_sheet_lines_domain()
			time_lines = PSTimeLines.search(domain)
			sheet.link_timelines_to_sheet(time_lines)
			sheet.timesheet_ids = [(6, 0, time_lines.ids)]

	def add_line(self):
		if not self.add_line_project_id:
			return
		values = self._prepare_empty_time_line()
		new_line_unique_id = self._get_new_line_unique_id()
		existing_unique_ids = list(
			{frozenset(line.get_unique_id().items()) for line in self.line_ids}
		)
		if existing_unique_ids:
			self.delete_empty_lines(False)
		if frozenset(new_line_unique_id.items()) not in existing_unique_ids:
			self.timesheet_ids |= self.env["ps.time.line"]._sheet_create(
				values
			)

	def link_timelines_to_sheet(self, timelines):
		self.ensure_one()
		if self.id and self.state in ["new", "draft"]:
			for ptl in timelines.filtered(lambda a: not a.sheet_id):
				ptl.write({"sheet_id": self.id})
	## end overrides


	@api.depends('date_start', 'date_end')
	def _compute_name(self):
		locale = self.env.context.get('lang') or self.env.user.lang or 'en_US'
		for sheet in self:
			if sheet.week_id:
				if sheet.date_start == sheet.date_end:
					sheet.name = babel.dates.format_skeleton(
						skeleton='MMMEd',
						datetime=datetime.combine(sheet.date_start, time.min),
						locale=locale,
					)
					continue
				period_start = sheet.date_start.strftime(
					'%V, %Y'
				)
				period_end = sheet.date_end.strftime(
					'%V, %Y'
				)
				if sheet.date_end <= sheet.date_start + relativedelta(weekday=SU):
					sheet.name = _('Week %s') % (
						period_end,
					)
				else:
					sheet.name = _('Weeks %s - %s') % (
						period_start,
						period_end,
					)

	@api.constrains('week_id', 'employee_id')
	def _check_sheet_date(self, forced_user_id=False):
		for sheet in self:
			new_user_id = forced_user_id or sheet.user_id and sheet.user_id.id
			if new_user_id:
				self.env.cr.execute('''
						SELECT id
						FROM hr_timesheet_sheet
						WHERE week_id=%s
						AND user_id=%s''',
						(sheet.week_id.id, new_user_id)
				)
				if self.env.cr.rowcount > 1:
					raise ValidationError(_(
						'You cannot have 2 timesheets with the same week_id!\nPlease use the menu \'My Current Timesheet\' to avoid this problem.'))

# 	# @api.onchange('employee_id')
# 	# def onchange_employee_id(self):
# 	#     super(HrTimesheetSheet, self).onchange_employee_id()
# 	#     return {'domain': {'week_id': self._get_week_domain()}}
#
# 	# need to work on this function deekshith
	def duplicate_last_week(self):
		if self.week_id and self.employee_id:
			ds = self.week_id.date_start
			date_start = datetime.strptime(str(ds), "%Y-%m-%d").date() - \
														timedelta(days=7)
			date_end = datetime.strptime(str(ds), "%Y-%m-%d").date() - \
														timedelta(days=1)
			date_range_type_cw_id = self.env.ref(
				'ps_date_range_week.date_range_calender_week').id
			last_week = self.env['date.range'].search([
				('type_id','=',date_range_type_cw_id),
				('date_start', '=', date_start),
				('date_end', '=', date_end)
			], limit=1)
			if last_week:
				last_week_timesheet = self.env['hr_timesheet.sheet'].search([
					('employee_id', '=', self.employee_id.id),
					('week_id', '=', last_week.id)
				], limit=1)
				if not last_week_timesheet:
					raise UserError(_(
						"You have no timesheet logged for last week. "
						"Duration: %s to %s"
					) % (datetime.strftime(date_start, "%d-%b-%Y"),
						 datetime.strftime(date_end, "%d-%b-%Y")))
				## todo What if during last week department_id and/or operating_unit_id and/or product_id has changed?
				## todo nothing because when unit_amount is set in the timesheet, _compute_ps_time_line and write() are called

				else:
					self.copy_with_query(last_week_timesheet.id)


	def _check_end_mileage(self):
		total = self.starting_mileage + self.business_mileage
		if self.end_mileage < total:
			raise ValidationError(_('End Mileage cannot be lower than the Starting Mileage + Business Mileage.'))

	def action_timesheet_draft(self):
		"""
		On timesheet reset draft check ps_time shouldn't be in invoiced
		:return: Super
		"""
		if any([ts.state == 'progress' for ts in self.timesheet_ids]):
			# if self.timesheet_ids.filtered('invoiced') or any([ts.state == 'progress' for ts in self.timesheet_ids]):
			raise UserError(_('You cannot modify timesheet entries either Invoiced or belongs to PS Invoiced!'))
		res = super(HrTimesheetSheet, self).action_timesheet_draft()
		if self.timesheet_ids:
			cond = '='
			rec = self.timesheet_ids.ids[0]
			if len(self.timesheet_ids) > 1:
				cond = 'IN'
				rec = tuple(self.timesheet_ids.ids)
			self.env.cr.execute("""
								UPDATE ps_time_line SET state = 'draft' WHERE id %s %s;
								DELETE FROM ps_time_line WHERE ref_id %s %s;
						""" % (cond, rec, cond, rec))
			self.env.cache.invalidate()
		if self.odo_log_id:
			self.env['fleet.vehicle.odometer'].sudo().search([('id', '=', self.odo_log_id.id)]).unlink()
			self.odo_log_id = False
		if self.overtime_line_id:
			self.overtime_line_id.unlink()
		return res


	def action_timesheet_confirm(self):
		self._check_end_mileage()
		vehicle = self._get_vehicle()
		if vehicle:
			self.odo_log_id = self.env['fleet.vehicle.odometer'].create({
				'value_period_update': self.business_mileage + self.private_mileage,
				'date': self.week_id.date_end or fields.Date.context_today(self),
				'vehicle_id': vehicle.id
			})
		date_from = datetime.strptime(str(self.date_start), "%Y-%m-%d").date()
		tot_ot_hrs = 0
		GTM = self.employee_id.user_id.has_group("ps_timesheet_invoicing.group_timesheet_manager")
		no_ott_check = self.employee_id.no_ott_check or self.employee_id.department_id.no_ott_check
		for i in range(7):
			date = datetime.strftime(date_from + timedelta(days=i), "%Y-%m-%d")
			hour = sum(self.env['ps.time.line'].search([('date', '=', date), ('sheet_id', '=', self.id), ('task_id.standby', '=', False)]).mapped('unit_amount'))
			if hour < 0 or hour > 24:
				raise UserError(_('Logged hours should be 0 to 24.'))
			if not self.employee_id.timesheet_no_8_hours_day:
				if i < 5 and float_compare(hour, 8, precision_digits=3, precision_rounding=None) < 0:
					raise UserError(_('Each day from Monday to Friday needs to have at least 8 logged hours.'))
			ot_ptl = self.env['ps.time.line'].search(
				[('date', '=', date), ('sheet_id', '=', self.id), ('project_id.overtime', '=', True)])
			if not GTM and ot_ptl:
				ot_hrs = ot_ptl.unit_amount
				if not no_ott_check and float_compare(ot_hrs, 4, precision_digits=3, precision_rounding=None) > 0:
					raise UserError(_('Each day maximum 4 hours overtime taken allowed from Monday to Friday.'))
				tot_ot_hrs += ot_hrs
		if not GTM and float_compare(tot_ot_hrs, 8, precision_digits=3, precision_rounding=None) > 0:
			raise UserError(_('Maximum 8 hours overtime taken allowed in a week.'))
		return super(HrTimesheetSheet, self).action_timesheet_confirm()


	def create_overtime_entries(self):
		ps_time_line = self.env['ps.time.line']
		if self.overtime_hours > 0 and not self.overtime_line_id:
			company_id = self.company_id.id if self.company_id else self.employee_id.company_id.id
			overtime_project = self.env['project.project'].search([('company_id', '=', company_id), ('overtime_hrs', '=', True)])
			overtime_project_task = self.env['project.task'].search([('project_id', '=', overtime_project.id), ('standard', '=', True)])
			if not overtime_project:
				raise ValidationError(_("Please define project with 'Overtime Hours'!"))

			uom = self.env.ref('uom.product_uom_hour').id
			ps_time_line = ps_time_line.create({
				'name':'Overtime line',
				'account_id':overtime_project.analytic_account_id.id,
				'project_id':overtime_project.id,
				'task_id':overtime_project_task.id,
				'date':self.date_end,
				'unit_amount':self.overtime_hours,
				'product_uom_id':uom,
				'ot':True,
				'user_id':self.user_id.id,
			})
			self.overtime_line_id = ps_time_line.id
		elif self.overtime_line_id:
			if self.overtime_hours > 0:
				self.overtime_line_id.write({'unit_amount':self.overtime_hours})
			else:
				self.overtime_line_id.unlink()
		return self.overtime_line_id


	def action_timesheet_done(self):
		"""
		On timesheet confirmed update ps_time_line state to confirmed
		:return: Super
		"""
		res = super(HrTimesheetSheet, self).action_timesheet_done()
		if self.timesheet_ids:
			cond = '='
			rec = self.timesheet_ids.ids[0]
			if len(self.timesheet_ids) > 1:
				cond = 'IN'
				rec = tuple(self.timesheet_ids.ids)
			self.env.cr.execute("""
									UPDATE ps_time_line SET state = 'open' WHERE id %s %s
							""" % (cond, rec))
		self.create_overtime_entries()
		self.generate_km_lines()
		return res

	# @job(default_channel='root.timesheet')
	def _recompute_timesheet(self, fields):
		"""Recompute this sheet and its lines.
		This function is called asynchronically after create/write"""
		for this in self:
			this.modified(fields)
			if 'timesheet_ids' not in fields:
				continue
			this.mapped('timesheet_ids').modified(
				self.env['ps.time.line']._fields.keys()
			)
		self.recompute()

	def _queue_recompute_timesheet(self, fields):
		"""Queue a recomputation if appropriate"""
		if not fields or not self:
			return
		return self.with_delay(
			description=' '.join([self.employee_id.name, self.display_name, str(self.date_start.month)]),
			identity_key=self._name + ',' + ','.join(map(str, self.ids)) +
			',' + ','.join(fields)
		)._recompute_timesheet(fields)

	@api.model
	def create(self, vals):
		result = super(
			HrTimesheetSheet, self.with_context(_timesheet_write=True)
		).create(vals)
		result._queue_recompute_timesheet(['timesheet_ids'])
		return result

	def write(self, vals):
		result = super(
			HrTimesheetSheet, self.with_context(_timesheet_write=True)
		).write(vals)
		self.env['ps.time.line'].search([
			('sheet_id', '=', self.id),
			'|',
			('unit_amount', '>', 24),
			('unit_amount', '<', 0),
		]).write({'unit_amount': 0})
		if 'timesheet_ids' in vals:
			self._queue_recompute_timesheet(['timesheet_ids'])
		return result

	def action_view_overtime_entry(self):
		self.ensure_one()
		## todo: check action name
		action = self.env.ref('analytic.ps_time_line_action_entries')
		return {
			'name': action.name,
			'help': action.help,
			'type': action.type,
			'view_type': 'form',
			'view_mode': 'form',
			'target': action.target,
			'res_id': self.overtime_line_id.id or False,
			'res_model': action.res_model,
			'domain': [('id', '=', self.overtime_line_id.id)],
		}

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
				month_id,
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
				product_uom_id )
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
				dr.id as month_id,
				%(week_id_ptl)s as week_id,
				ptl.account_department_id as account_department_id,
				ptl.chargeable as chargeable,
				ptl.operating_unit_id as operating_unit_id,
				ptl.project_operating_unit_id as project_operating_unit_id,
				ptl.correction_charge as correction_charge,
				NULL as ref_id,
				0 as actual_qty,
				0 as kilometers,
				'draft' as state,
				CASE
				  WHEN ip.invoice_mileage IS NULL THEN true
				  ELSE ip.invoice_mileage
				END AS non_invoiceable_mileage,
				ptl.product_uom_id as product_uom_id
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
			 ON (dr.type_id = 2 and dr.date_start <= ptl.date +7 and dr.date_end >= ptl.date + 7)
			 LEFT JOIN hr_employee he
			 ON (hss.employee_id = he.id)
			 LEFT JOIN task_user tu
			 ON (tu.task_id = ptl.task_id and tu.user_id = ptl.user_id and ptl.date >= tu.from_date)
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

		self.env.cr.execute(query, {'create': str(fields.Datetime.to_string(fields.datetime.now())),
									'week_id_ptl': self.week_id.id,
									'sheet_select': last_week_timesheet_id,
									'sheet_ptl': self.id,
									}
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
				month_id,
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
				product_uom_id )
		SELECT  ptl.create_uid as create_uid,
				ptl.user_id as user_id,
				ptl.account_id as account_id,
				ptl.company_id as company_id,
				ptl.write_uid as write_uid,
				ptl.amount as amount,
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
				ptl.product_id as product_id,
				-- ptl.amount_currency as amount_currency,
				ptl.project_id as project_id,
				ptl.department_id as department_id,
				ptl.task_id as task_id,
				NULL as sheet_id,
				NULL as ts_line,
				ptl.month_id as month_id,
				ptl.week_id as week_id,
				ptl.account_department_id as account_department_id,
				ptl.chargeable as chargeable,
				ptl.operating_unit_id as operating_unit_id,
				ptl.project_operating_unit_id as project_operating_unit_id,
				ptl.correction_charge as correction_charge,
				ptl.id as ref_id,
				ptl.actual_qty as actual_qty,
				0 as kilometers,
				'open' as state,
				CASE
				  WHEN ip.invoice_mileage IS NULL THEN true
				  ELSE ip.invoice_mileage
				END AS non_invoiceable_mileage,
				%(uom)s as product_uom_id
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
			 ON (dr.type_id = 2 and dr.date_start <= ptl.date +7 and dr.date_end >= ptl.date + 7)
			 LEFT JOIN hr_employee he
			 ON (hss.employee_id = he.id)
			 LEFT JOIN task_user tu
			 ON (tu.task_id = ptl.task_id and tu.user_id = ptl.user_id and ptl.date >= tu.from_date)
		WHERE hss.id = %(sheet_select)s
			 AND ptl.ref_id IS NULL
			 AND ptl.kilometers > 0 ;
		"""
		self.env.cr.execute(query, {'create': str(fields.Datetime.to_string(fields.datetime.now())),
									'week_id_ptl': self.week_id.id,
									'uom': self.env.ref('uom.product_uom_km').id,
									'sheet_select': self.id,
									}
							)
		self.env.cache.invalidate()
		return True


# # class DateRangeGenerator(models.TransientModel):
# # 	_inherit = 'date.range.generator'
# #
# #
# # 	def _compute_date_ranges(self):
# # 		self.ensure_one()
# # 		vals = rrule(freq=self.unit_of_time,
# # 					 interval=self.duration_count,
# # 					 dtstart=fields.Date.from_string(self.date_start),
# # 					 count=self.count+1)
# # 		vals = list(vals)
# # 		date_ranges = []
# # 		# count_digits = len(unicode(self.count))
# # 		count_digits = len(str(self.count))
# # 		for idx, dt_start in enumerate(vals[:-1]):
# # 			date_start = fields.Date.to_string(dt_start.date())
# # 			# always remove 1 day for the date_end since range limits are
# # 			# inclusive
# # 			dt_end = vals[idx+1].date() - relativedelta(days=1)
# # 			date_end = fields.Date.to_string(dt_end)
# # 			# year and week number are updated for name according to ISO 8601 Calendar
# # 			date_ranges.append({
# # 				'name': '%s%d' % (
# # 					str(dt_start.isocalendar()[0])+" "+self.name_prefix, int(dt_start.isocalendar()[1])),
# # 				'date_start': date_start,
# # 				'date_end': date_end,
# # 				'type_id': self.type_id.id,
# # 				'company_id': self.company_id.id})
# # 		return date_ranges
#
class SheetLine(models.TransientModel):
	_inherit = 'hr_timesheet.sheet.line'

	@api.onchange('unit_amount')
	def onchange_unit_amount(self):
		""" This method is called when filling a cell of the matrix. """
		res = super(SheetLine, self).onchange_unit_amount()
		if self.unit_amount > 24:
			self.update({'unit_amount':'0.0'})
			return {'warning': {
				'title': _("Warning"),
				'message': _("Logged hours should be 0 to 24."),
			}}
		return res

class SheetNewAnalyticLine(models.TransientModel):
    _inherit = "hr_timesheet.sheet.new.analytic.line"

	## override for replacing account_analytic_line by ps_time_line
    @api.model
    def _update_time_lines(self):
        sheet = self.sheet_id
        timelines = sheet.timesheet_ids.filtered(
            lambda tl: self._is_similar_time_line(tl) #_is_similar_analytic_line
        )
        new_ts = timelines.filtered(lambda t: t.name == empty_name)
        amount = sum(t.unit_amount for t in timelines)
        diff_amount = self.unit_amount - amount
        if len(new_ts) > 1:
            new_ts = new_ts.merge_timelines()
            sheet._sheet_write("timesheet_ids", sheet.timesheet_ids.exists())
        if not diff_amount:
            return
        if new_ts:
            unit_amount = new_ts.unit_amount + diff_amount
            if unit_amount:
                new_ts.write({"unit_amount": unit_amount})
            else:
                new_ts.unlink()
                sheet._sheet_write("timesheet_ids", sheet.timesheet_ids.exists())
        else:
            new_ts_values = sheet._prepare_new_line(self)
            new_ts_values.update({"name": empty_name, "unit_amount": diff_amount})
            self.env["ps.time.line"]._sheet_create(new_ts_values)