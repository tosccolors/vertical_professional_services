# Copyright 2018 Eficent Business and IT Consulting Services, S.L.
# Copyright 2018-2020 Brainbean Apps (https://brainbeanapps.com)
# Copyright 2018-2019 Onestein (<https://www.onestein.eu>)
# Copyright 2023 The Open Source Company BV (<https://www.tosc.nl>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import babel.dates
import logging
import re
from collections import namedtuple
from datetime import datetime, time
from dateutil.relativedelta import relativedelta, SU
from dateutil.rrule import MONTHLY, WEEKLY
import json
from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.tools.translate import _
from odoo.tools.sql import drop_view_if_exists
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

empty_name = '/'


class PSPlanningSheet(models.Model):
	_name = 'ps.planning.sheet'
	_inherit = "hr_timesheet.sheet"
	_description = 'Professional Services Planning Sheet'
	_order = 'id desc'
	_rec_name = "complete_name"

	def _default_date_start(self):
		return (datetime.today() + relativedelta(weekday=0, days=-6)).strftime('%Y-%m-%d')
		# return self._get_period_start(
		#     self.env.user.company_id,
		#     fields.Date.context_today(self)
		# )

	def _default_date_end(self):
		return (datetime.today() + relativedelta(weekday=6)).strftime('%Y-%m-%d')
		# return self._get_period_end(
		#     self.env.user.company_id,
		#     fields.Date.context_today(self)
		# )

	## we use hr_timesheet_sheet method, OK?
	# def _default_employee(self):
	# 	company = self.env['res.company']._company_default_get()
	# 	return self.env['hr.employee'].search([
	# 		('user_id', '=', self.env.uid),
	# 		('company_id', 'in', [company.id, False]),
	# 	], limit=1, order="company_id ASC")

	## we use hr_timesheet_sheet method, OK?
	# def _default_department_id(self):
	# 	return self._default_employee().department_id

	def fetch_weeks_from_planning_quarter(self, planning_quarter):
		start_date = planning_quarter.date_start
		end_date = planning_quarter.date_end
		date_range_type_cw = self.env.ref('ps_date_range_week.date_range_calender_week')
		date_range = self.env['date.range']
		domain = [('type_id', '=', date_range_type_cw.id)]
		week_from = date_range.search(domain + [('date_start', '<=', start_date), ('date_end', '>=', start_date)],
										   limit=1).id
		week_to = date_range.search(domain + [('date_start', '<=', end_date), ('date_end', '>=', end_date)],
										 limit=1).id
		return week_from, week_to

	@api.onchange('planning_quarter')
	def onchange_planning_quarter(self):
		self.employee_id = self._default_employee()
		if not self.week_to or not self.week_from:
			self.week_from, self.week_to = self.fetch_weeks_from_planning_quarter(self.planning_quarter)

	def remove_planning_from_managers(self, empIds):
		# delete employee lines from manager's planning, which no longer belongs to manager
		if not empIds:
			return
		op = '!='
		if not isinstance(empIds, (int)) and len(empIds) > 1:
			op = 'NOT IN'

		line_query = ("""
			DELETE FROM ps_planning_line_rel 
				WHERE planning_sheet_id = {0} AND ps_planning_line_ps_time_line_id IN (
					SELECT id FROM ps_time_line WHERE id IN 
					(SELECT ps_time_line_id FROM ps_planning_ps_time_line_rel WHERE planning_sheet_id = {0}) 
						AND employee_id {1} {2}
					)
			""".format(
			self.id,
			op,
			empIds
		))
		# 
		self.env.cr.execute(line_query)

	def get_employee_child_ids(self):
		# get department's manager list
		self.env.cr.execute("""
			WITH RECURSIVE
				subordinates AS(
					SELECT id, parent_id, manager_id FROM hr_department WHERE id = %s
					UNION
					SELECT h.id, h.parent_id, h.manager_id FROM hr_department h
					INNER JOIN subordinates s ON s.id = h.parent_id)
				SELECT  *  FROM subordinates"""
				% (self.employee_id.department_id.id))
		dept_mgr_ids = [x[2] for x in self.env.cr.fetchall() if x[2]]

		# get employees list
		self.env.cr.execute("""
			WITH RECURSIVE
				subordinates AS(
					SELECT id, parent_id  FROM hr_employee WHERE id = %s
					UNION
					SELECT hr.id, hr.parent_id FROM hr_employee hr
					INNER JOIN subordinates s ON s.id = hr.parent_id)
				SELECT  *  FROM subordinates"""
				% (self.employee_id.id))

		employee_ids = [x[0] for x in self.env.cr.fetchall() if x[0]]

		child_ids = list(set(dept_mgr_ids+employee_ids))
		return child_ids
		
	def get_planning_from_managers(self):
		line_query = ("""
						INSERT INTO
						   ps_planning_ps_time_line_rel
						   (planning_sheet_id, ps_time_line_id)
							SELECT
								mp.id as planning_sheet_id,
								ptl.id as ps_time_line_id
							FROM 
								ps_time_line ptl
								JOIN ps_planning mp ON ptl.employee_id = mp.employee_id
								JOIN ps_planning_ps_time_line_rel rel ON rel.ps_time_line_id = ptl.id
								WHERE ptl.week_id >= {0} AND ptl.week_id <= {1}
								AND mp.id = {2} 
						  EXCEPT
							SELECT
							  planning_sheet_id, ps_time_line_id
							  FROM ps_planning_ps_time_line_rel
				""".format(
			self.week_from.id,
			self.week_to.id,
			self.id))
		print("---------line query",line_query)

		self.env.cr.execute(line_query)

	def get_planning_from_employees(self):
		if not self.env.context.get('self_planning', False):
			child_emp_ids = tuple(set(self.get_employee_child_ids()) - set([self.employee_id.id]))
			op, child_emp_ids = ('IN', child_emp_ids) if len(child_emp_ids) > 1 else ('=', child_emp_ids and child_emp_ids[0] or False)
		else:
			op, child_emp_ids = '=', self.employee_id.id

		print("------child emp ids",child_emp_ids)

		self.remove_planning_from_managers(child_emp_ids)

		if child_emp_ids:
			print("--------executing query")
			line_query = ("""
					INSERT INTO
					   ps_planning_ps_time_line_rel
					   (planning_sheet_id, ps_time_line_id)
						SELECT 
							{0}, ptl.id 
						  FROM ps_time_line ptl 
						  WHERE 
							ptl.week_id >= {1} AND ptl.week_id <= {2}
							AND ptl.id IN (
								SELECT ps_time_line_id FROM ps_planning_ps_time_line_rel WHERE planning_sheet_id IN 
								(SELECT id FROM ps_planning WHERE employee_id {3} {4}))
						EXCEPT
							SELECT
							  planning_sheet_id, ps_time_line_id
							  FROM ps_planning_ps_time_line_rel
					""".format(
						self.id,
						self.week_from.id,
						self.week_to.id,
						op,
						child_emp_ids
						))
			print("-fetch from employee query",line_query)
			self.env.cr.execute(line_query)

	def _compute_planning_lines(self):
		self_planning = self.env.context.get('self_planning', False)
		if self_planning:
			self.get_planning_from_managers()
		elif self.employee_id.user_id.has_group("ps_timesheet_invoicing.group_ps_planning_officer") or self.employee_id.user_id.has_group("hr.group_hr_user") or self.employee_id.user_id.has_group("hr.group_hr_manager"):
			self.get_planning_from_employees()
		else:
			self.get_planning_from_managers()

	def compute_planning_lines(self):
		self._compute_planning_lines()

	@api.onchange('add_line_project_id')
	def compute_employee_domain(self):
		print("----all context",self.env.context)
		my_planning = self.env.context.get('default_self_planning')
		user = self.employee_id.user_id
		print("------user id",user)
		print("------My Planning",my_planning)
		domain = [('user_id', '=', user.id)]
		# employee_id = self.env['hr.employee'].search([('user_id','=',user.id)])

		if not my_planning:
			print("---------not my planning")
			domain = ['|', '|', ('department_id.manager_id.user_id', '=', user.id),
					  ('department_id.parent_id.manager_id.user_id', '=', user.id),
					  ('parent_id.user_id', '=', user.id)]
		print("-----domainsssss",domain)
		emp_list = self.env['hr.employee'].search(domain).ids
		print("------employeeee",emp_list)
		res = {
			'domain': {
				'add_line_emp_id': [('id', 'in', emp_list)],
			},
			'value': {
				'add_line_emp_id':emp_list[0]
			}
		}
		return res

	week_to = fields.Many2one(
		'date.range',
		string="Week Start"
	)
	week_from = fields.Many2one(
		'date.range',
		string="Week End"
	)
	date_start = fields.Date(related='planning_quarter.date_start')
	date_end = fields.Date(related='planning_quarter.date_end')
	planning_quarter = fields.Many2one(
		'date.range',
		string='Select Quarter',
		required=True,
		index=True
	)
	planning_line_ids = fields.One2many(
		comodel_name='ps.planning.line',
		inverse_name="planning_sheet_id",
		string='Planning lines',
		readonly=True,
		states={"new": [("readonly", False)], "draft": [("readonly", False)]},
		copy=False
	)
	line_ids = fields.One2many(
		comodel_name='ps.planning.sheet.line',
		compute='_compute_line_ids',
		string='Planning Sheet Lines',
		readonly=True,
		states={"new": [("readonly", False)], "draft": [("readonly", False)]},
	)
	new_line_ids = fields.One2many(
		comodel_name='ps.planning.new.line',
		inverse_name='planning_sheet_id',
		string='Temporary Planning Lines',
		readonly=True,
		states={"new": [("readonly", False)], "draft": [("readonly", False)]},
	)
	add_line_emp_id = fields.Many2one(
		comodel_name='hr.employee',
		string='Select Employee',
	)
	is_planning_officer = fields.Boolean(
		'Is Planning Officer'
	)
	self_planning = fields.Boolean(
		'Self Planning'
	)

	@api.depends('week_from', 'week_to')
	def _compute_name(self):
		locale = self.env.context.get('lang') or self.env.user.lang or 'en_US'
		for sheet in self:
			if sheet.planning_quarter.date_start:
				if sheet.planning_quarter.date_start == sheet.planning_quarter.date_end:
					sheet.name = babel.dates.format_skeleton(
						skeleton='MMMEd',
						datetime=datetime.combine(sheet.planning_quarter.date_start, time.min),
						locale=locale,
					)
					continue

				period_start = sheet.planning_quarter.date_start.strftime(
					'%V, %Y'
				)
				period_end = sheet.planning_quarter.date_end.strftime(
					'%V, %Y'
				)

				if sheet.planning_quarter.date_end <= sheet.planning_quarter.date_start + relativedelta(weekday=SU):
					sheet.name = _('Week %s') % (
						period_end,
					)
				else:
					sheet.name = _('Weeks %s - %s') % (
						period_start,
						period_end,
					)

	@api.depends('planning_line_ids.unit_amount')
	def _compute_total_time(self):
		# need to add logic for ps.planning.line as well
		for sheet in self:
			sheet.total_time = sum(sheet.mapped('planning_line_ids.unit_amount'))

	def _get_overlapping_sheet_domain(self):
		self.ensure_one()
		return [
			('id', '!=', self.id),
			('planning_quarter', '=', self.planning_quarter.id),
			('employee_id', '=', self.employee_id.id),
			('company_id', '=', self._get_planning_sheet_company().id),
		]

	def _get_planning_sheet_company(self):
		self.ensure_one()
		employee = self.employee_id
		company = employee.company_id or employee.department_id.company_id
		if not company:
			company = employee.user_id.company_id
		return company

	@api.onchange('employee_id')
	def onchange_employee_id(self):
		vals, data = {}, {}
		# ctx = self.env.context
		# default_planning_quarter = ctx.get('default_planning_quarter', False)
		# if default_planning_quarter:
		# 	data = {'planning_quarter': [('id', '=', default_planning_quarter)]}
		# else:
		company = self._get_planning_sheet_company()
		vals['company_id'] = company.id
		vals['department_id'] = self.employee_id.department_id.id
		date = datetime.now().date()
        # ('type_id.fiscal_year', '=', False)
		period = self.env['date.range'].search(
			[('type_id.calender_week', '=', False),
			 ('type_id.fiscal_month', '=', False), ('date_start', '<=', date), ('date_end', '>=', date)])
		vals['planning_quarter'] = period.ids[0]
		data = {'planning_quarter': [('id', 'in', period.ids)]}
		return {'value': vals, 'domain': data}

	def _get_planning_sheet_lines_domain(self):
		self.ensure_one()
		return [
			('date', '<=', self.week_to.date_end),
			('date', '>=', self.week_from.date_start),
			('employee_id', '=', self.employee_id.id),
			('company_id', '=', self._get_planning_sheet_company().id),
			('project_id', '!=', False),
		]

	# @api.depends('date_start', 'date_end')
	@api.depends('week_from', 'week_to')
	def _compute_line_ids(self):
		SheetLine = self.env['ps.planning.sheet.line']
		for sheet in self:
			if not all([sheet.week_from.date_start, sheet.week_to.date_end]):
				continue
			matrix = sheet._get_data_matrix()
			vals_list = []
			for key in sorted(matrix,key=lambda key: self._get_matrix_sortby(key)):
				vals_list.append(sheet._get_default_sheet_line(matrix, key))
				## todo: not necessary?
				if sheet.state in ["new", "draft"]:
					sheet.clean_timelines(matrix[key])
			sheet.line_ids = SheetLine.create(vals_list)

	@api.model
	def _matrix_key_attributes(self):
		""" Hook for extensions """
		return ['date', 'project_id','employee_id','week_id']


	@api.model
	def _get_matrix_key_values_for_line(self, ppl):
		""" Hook for extensions """
		week_id = self.env['date.range'].search([('date_start','=',ppl.date),('type_id.calender_week','=',True)])
		# print("-----------emp id",ppl.employee_id.name)
		# print("-----------alll",ppl)
		return {
			# 'date': ppl.date,
			'date': week_id.date_start,
			'week_id':week_id,
			'project_id': ppl.project_id,
			# 'task_id': ppl.task_id,
			'employee_id': ppl.employee_id,
		}
	## we use the inherited method, which is identical
	# @api.model
	# def _get_matrix_sortby(self, key):
	# 	res = []
	# 	for attribute in key:
	# 		value = None
	# 		if hasattr(attribute, 'name_get'):
	# 			name = attribute.name_get()
	# 			value = name[0][1] if name else ''
	# 		else:
	# 			value = attribute
	# 		res.append(value)
	# 	return res

	def _get_data_matrix(self):
		self.ensure_one()
		MatrixKey = self._matrix_key()
		matrix = {}
		# empty_line = self.env['ps.time.line']
		empty_line = self.env['ps.planning.line']
		# print("--------- line ids",self.planning_line_ids)
		for line in self.planning_line_ids:
			key = MatrixKey(**self._get_matrix_key_values_for_line(line))
			# print("--------------key",key)
			if key not in matrix:
				matrix[key] = empty_line
			matrix[key] += line
		for date in self._get_dates():
			week_id = self.env['date.range'].search([('date_start','=',date),('type_id.calender_week','=',True)])
			for key in matrix.copy():
				key = MatrixKey(**{
					**key._asdict(),
					'date': date,
					'week_id':week_id
				})
				if key not in matrix:
					matrix[key] = empty_line
		return matrix

	def _compute_planning_line_ids(self):
		ps_planning_lines = self.env['ps.planning.line']
		for sheet in self:
			domain = sheet._get_planning_sheet_lines_domain()
			# check this
			planning_lines = ps_planning_lines.search(domain)
			# sheet.link_timesheets_to_sheet(timesheets)
			sheet.planning_line_ids = [(6, 0, planning_lines.ids)]

	# @api.onchange('date_start', 'date_end', 'employee_id')
	@api.onchange('week_from', 'week_to', 'employee_id')
	def _onchange_scope(self):
		self._compute_planning_line_ids()


	@api.onchange('planning_line_ids')
	def _onchange_planning_lines(self):
		self._compute_line_ids()

	
	@api.model
	def _check_employee_user_link(self, vals):
		if 'employee_id' in vals:
			employee = self.env['hr.employee'].browse(vals['employee_id'])
			if not employee.user_id:
				raise UserError(_(
					'In order to create a sheet for this employee, you must'
					' link him/her to an user: %s'
				) % (
					employee.name,
				))
			return employee.user_id.id
		return False

	@api.model
	def create(self, vals):
		self._check_employee_user_link(vals)
		vals.setdefault('state', 'draft')
		res = super().create(vals)
		return res

	def _sheet_write(self, field, recs):
		self.with_context(sheet_write=True).write({field: [(6, 0, recs.ids)]})

	def write(self, vals):
		self._check_employee_user_link(vals)
		return super().write(vals)

	def _get_informables(self):
		""" Hook for extensions """
		self.ensure_one()
		return self.employee_id.parent_id.user_id.partner_id

	# 
	# def action_timesheet_draft(self):
	#     if self.filtered(lambda sheet: sheet.state != 'done'):
	#         raise UserError(_('Cannot revert to draft a non-approved sheet.'))
	#     # self._check_can_review()
	#     self.write({
	#         'state': 'draft',
	#         # 'reviewer_id': False,
	#     })

	# 
	# def action_timesheet_confirm(self):
	#     self.reset_add_line()
	#     self.write({'state': 'confirm'})

	# 
	# def action_timesheet_done(self):
	#     if self.filtered(lambda sheet: sheet.state != 'confirm'):
	#         raise UserError(_('Cannot approve a non-submitted sheet.'))
	#     self.write({
	#         'state': 'done',
	#     })
	#
	# 
	# def action_timesheet_refuse(self):
	#     if self.filtered(lambda sheet: sheet.state != 'confirm'):
	#         raise UserError(_('Cannot reject a non-submitted sheet.'))
	#     self.write({
	#         'state': 'draft',
	#     })

	@api.model
	def _get_current_reviewer(self):
		reviewer = self.env['hr.employee'].search(
			[('user_id', '=', self.env.uid)],
			limit=1
		)
		if not reviewer:
			raise UserError(_(
				'In order to review a planning sheet, your user needs to be'
				' linked to an employee.'
			))
		return reviewer

	def button_add_line(self):
		for rec in self:
			# if rec.state in ['new', 'draft']:
			rec.add_line()
			rec.reset_add_line()

	def reset_add_line(self):
		self.write({
			'add_line_project_id': False,
			'add_line_emp_id': False,
		})

	def _get_date_name(self, date):
		# name = babel.dates.format_skeleton(
		#     skeleton='MMMEd',
		#     datetime=datetime.combine(date, time.min),
		#     locale=(
		#         self.env.context.get('lang') or self.env.user.lang or 'en_US'
		#     ),
		# )
		# name = re.sub(r'(\s*[^\w\d\s])\s+', r'\1\n', name)
		# name = re.sub(r'([\w\d])\s([\w\d])', u'\\1\u00A0\\2', name)
		name = date
		return name

	def _get_line_name(self, project_id, employee_id=None, **kwargs):
		self.ensure_one()
		if employee_id:
			return '%s - %s' % (
				project_id.name_get()[0][1],
				employee_id.name
			)
		return project_id.name_get()[0][1]

	def _get_new_line_unique_id(self):
		""" Hook for extensions """
		self.ensure_one()
		return {
			'project_id': self.add_line_project_id,
			'employee_id': self.add_line_emp_id,
		}

	def _get_default_sheet_line(self, matrix, key):
		self.ensure_one()
		week_date = self._get_date_name(key.week_id)
		week_id = self.env['date.range'].search([('id','=',week_date.id),('type_id.calender_week','=',True)])
		# print("-------week id ",week_id.id)
		values = {
			# 'value_x': self._get_date_name(key.date),
			'value_x':week_id.name,
			'value_y': self._get_line_name(**key._asdict()),
			'date': key.date,
			'week_id':week_id.id,
			'project_id': key.project_id.id,
			# 'task_id': key.task_id.id,
			'unit_amount': sum(t.unit_amount for t in matrix[key]),
			'employee_id': key.employee_id.id,
			'company_id': self.company_id.id,
		}
		if self.id:
			values.update({'planning_sheet_id': self.id})
		return values

	@api.model
	def _prepare_empty_planning_line(self):
		# this function is
		return {
			'name': empty_name,
			# 'employee_id': self.employee_id.id,
			'date': self.week_from.date_start,
			'project_id': self.add_line_project_id.id,
			# 'task_id': self.add_line_task_id.id,
			'employee_id': self.add_line_emp_id.id,
			'planning_sheet_id': self.id,
			'unit_amount': 0.0,
			'company_id': self.company_id.id,
		}

	def add_line(self):
		# print("---------------add line triggered")
		if not self.add_line_project_id:
			return
		values = self._prepare_empty_planning_line()
		print("----------values form empty planning line",values)
		new_line_unique_id = self._get_new_line_unique_id()
		existing_unique_ids = list(set(
			[frozenset(line.get_unique_id().items()) for line in self.line_ids]
		))
		if existing_unique_ids:
			self.delete_empty_lines(False)
		if frozenset(new_line_unique_id.items()) not in existing_unique_ids:
			print("------------values",values)
			print(" add line context print",self.env.context)
			# self.ps_planning_ids |= \
			#     self.env['ps.time.line']._planning_create(values)
			self.planning_line_ids |= \
				self.env['ps.planning.line']._planning_create(values)


	def clean_timelines(self, timelines):
		repeated = timelines.filtered(lambda t: t.name == empty_name)
		if len(repeated) > 1 and self.id:
			return repeated.merge_timelines()
		return timelines

	def _is_add_line(self, row):
		""" Hook for extensions """
		self.ensure_one()
		# return self.add_line_project_id == row.project_id \
		#     and self.add_line_task_id == row.task_id
		return self.add_line_project_id == row.project_id \
			and self.add_line_emp_id == row.employee_id

	@api.model
	def _is_line_of_row(self, ptl, row):
		""" Hook for extensions """
		# return ptl.project_id.id == row.project_id.id \
		#     and ptl.task_id.id == row.task_id.id
		return ptl.project_id.id == row.project_id.id \
			and ptl.employee_id.id == row.employee_id.id

	def delete_empty_lines(self, delete_empty_rows=False):
		self.ensure_one()
		for name in list(set(self.line_ids.mapped('value_y'))):
			rows = self.line_ids.filtered(lambda l: l.value_y == name)
			if not rows:
				continue
			row = fields.first(rows)
			if delete_empty_rows and self._is_add_line(row):
				check = any([l.unit_amount for l in rows])
			else:
				check = not all([l.unit_amount for l in rows])
			if not check:
				continue
			row_lines = self.planning_line_ids.filtered(
				lambda ptl: self._is_line_of_row(ptl, row)
			)
			row_lines.filtered(
				lambda t: t.name == empty_name and not t.unit_amount
			).unlink()
			if self.planning_line_ids != self.planning_line_ids.exists():
				self._sheet_write(
					'planning_line_ids', self.planning_line_ids.exists())

	def _update_time_lines_from_new_lines(self, vals):
		self.ensure_one()
		new_line_ids_list = []
		for line in vals.get('line_ids', []):
			# Every time we change a value in the grid a new line in line_ids
			# is created with the proposed changes, even though the line_ids
			# is a computed field. We capture the value of 'new_line_ids'
			# in the proposed dict before it disappears.
			# This field holds the ids of the transient records
			# of model 'ps.planning.new.line.line'.
			if line[0] == 1 and line[2] and line[2].get('new_line_id'):
				new_line_ids_list += [line[2].get('new_line_id')]
		for new_line in self.new_line_ids.exists():
			if new_line.id in new_line_ids_list:
				new_line._update_time_lines()

	@api.model
	def _prepare_new_line(self, line):
		# print("-----line",line.employee_id.name)
		""" Hook for extensions """
		# week_from.date_start, sheet.week_to.date_end
		
		return {
			'date': line.date,
			'project_id': line.project_id.id,
			'employee_id': line.employee_id.id,
			# 'week_id':week_id.id,
			# 'task_id': line.task_id.id,
			'unit_amount': line.unit_amount,
			'company_id': line.company_id.id,
			'employee_id': line.employee_id.id,
		}

	def _is_compatible_new_line(self, line_a, line_b):
		""" Hook for extensions """
		self.ensure_one()
		return line_a.project_id.id == line_b.project_id.id \
			and line_a.employee_id.id == line_b.employee_id.id \
			and line_a.date == line_b.date
			# and line_a.task_id.id == line_b.task_id.id \

	def add_new_line(self, line):
		self.ensure_one()
		new_line_model = self.env['ps.planning.new.line']
		new_line = self.new_line_ids.filtered(
			lambda l: self._is_compatible_new_line(l, line)
		)
		if new_line:
			new_line.write({'unit_amount': line.unit_amount})
		else:
			vals = self._prepare_new_line(line)
			new_line = new_line_model.create(vals)
		self._sheet_write('new_line_ids', self.new_line_ids | new_line)
		line.new_line_id = new_line.id


class PSAbstractPlanningLine(models.AbstractModel):
	_name = 'ps.planning.line.abstract'
	_description = 'Abstract Planning Line'

	planning_sheet_id = fields.Many2one(
		comodel_name='ps.planning.sheet',
		ondelete='cascade',
	)
	date = fields.Date()
	project_id = fields.Many2one(
		comodel_name='project.project',
		string='Project',
	)
	# task_id = fields.Many2one(
	#     comodel_name='project.task',
	#     string='Task',
	# )
	unit_amount = fields.Float(
		string="Quantity",
		default=0.0,
	)
	company_id = fields.Many2one(
		comodel_name='res.company',
		string='Company',
	)
	employee_id = fields.Many2one(
		comodel_name='hr.employee',
		string='Employee',
	)

	def get_unique_id(self):
		""" Hook for extensions """
		self.ensure_one()
		return {
			'project_id': self.project_id,
			'employee_id': self.employee_id,
			# 'task_id': self.task_id,
		}


class PSPlanningSheetLine(models.TransientModel):
	_name = 'ps.planning.sheet.line'
	_inherit = 'ps.planning.line.abstract'
	_description = 'PS Planning Line'

	value_x = fields.Char(
		string='Date Name',
	)
	value_y = fields.Char(
		string='Project Name',
	)
	new_line_id = fields.Integer(
		default=0,
	)
	# can remove if not required
	week_id = fields.Many2one('date.range',string="Week")

	@api.onchange('unit_amount')
	def onchange_unit_amount(self):
		""" This method is called when filling a cell of the matrix. """
		self.ensure_one()
		sheet = self._get_sheet()
		if not sheet:
			return {'warning': {
				'title': _("Warning"),
				'message': _("Save the planning Sheet first."),
			}}
		# in planning line itself current employee id is being showed. Track this and save employee id for each line
		sheet.add_new_line(self)

	@api.model
	def _get_sheet(self):
		sheet = self.planning_sheet_id
		if not sheet:
			model = self.env.context.get('params', {}).get('model', '')
			obj_id = self.env.context.get('params', {}).get('id')
			if model == 'ps.planning' and isinstance(obj_id, int):
				sheet = self.env['ps.planning'].browse(obj_id)
		return sheet


class SheetNewPlanningLine(models.TransientModel):
	_name = 'ps.planning.new.line'
	_inherit = 'ps.planning.line.abstract'
	_description = 'New PS Planning Line'

	@api.model
	def _is_similar_planning_line(self, ppl):
		""" Hook for extensions """
		return ppl.date == self.date \
			and ppl.project_id.id == self.project_id.id \
			and ppl.employee_id.id == self.employee_id.id

	@api.model
	def _update_planning_lines(self):
		sheet = self.planning_sheet_id
		planning_lines = sheet.planning_line_ids.filtered(
			lambda ppl: self._is_similar_planning_line(ppl)
		)
		new_ts = planning_lines.filtered(lambda t: t.name == empty_name)
		amount = sum(t.unit_amount for t in planning_lines)
		diff_amount = self.unit_amount - amount
		# print("-------diff amount",diff_amount)
		if len(new_ts) > 1:
			print("---entered update if")
			new_ts = new_ts.merge_timelines()
			sheet._sheet_write('planning_line_ids', sheet.planning_line_ids.exists())
		if not diff_amount:
			return
		if new_ts:
			unit_amount = new_ts.unit_amount + diff_amount
			# print("-----unit amount",unit_amount)
			if unit_amount:
				new_ts.write({'unit_amount': unit_amount})
			else:
				new_ts.unlink()
				sheet._sheet_write(
					'planning_line_ids', sheet.planning_line_ids.exists())
		else:
			# print("---------sheet employee id",sheet.employee_id.name)
			# print("---------sheet employee id self",self.employee_id.name)
			new_ts_values = sheet._prepare_new_line(self)
			new_ts_values.update({
				'name': empty_name,
				'unit_amount': diff_amount,
			})
			# self.env['ps.time.line']._planning_create(new_ts_values)
			print('-----------new ts values',new_ts_values)
			planning_line_ids = self.env['ps.planning.line']._planning_create(new_ts_values)
			planning_line_ids |= sheet.planning_line_ids
			sheet._sheet_write(
				'planning_line_ids', planning_line_ids.exists())

	@api.model
	def _update_analytic_lines(self):
		"""No need for any updates here"""
		pass
			
	def unlink(self):
		"""No need for any updates here"""
		return super().unlink()
	
class PSStandbyPlanning(models.Model):
	_name = "ps.standby.planning"
	_description = "Stand-By Planning"
	_rec_name = 'employee_id'

	@api.constrains('date_from', 'date_to')
	def _check_date(self):
		for planning in self:
			domain = [
				('date_from', '<=', planning.date_to),
				('date_to', '>=', planning.date_from),
				('employee_id', '=', planning.employee_id.id),
				('id', '!=', planning.id),
			]
			nplanning = self.search_count(domain)
			if nplanning:
				raise ValidationError(_('%s can not have 2 planning that overlaps on same day!')%(planning.employee_id.name))

	@api.model
	def default_get(self, fields):
		rec = super(PSStandbyPlanning, self).default_get(fields)
		emp_ids = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
		rec.update({'employee_id': emp_ids and emp_ids.id or False})
		return rec

	employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
	user_id = fields.Many2one('res.users', related='employee_id.user_id', string='User', store=True, readonly=True)
	department_id = fields.Many2one('hr.department', related='employee_id.department_id', string='Department',
									readonly=True, store=True)
	date_from = fields.Date(string='Date From', required=True, index=True)
	date_to = fields.Date(string='Date To', required=True, index=True)
	note = fields.Text(string='Note')


class HrEmployee(models.Model):
	_inherit = 'hr.employee'

	def name_get(self):
		res = []
		if self.env.context.get('ps_planning', False):
			pass

		res = super(HrEmployee, self).name_get()
		return res



