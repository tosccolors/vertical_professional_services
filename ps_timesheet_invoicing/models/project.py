# Copyright 2018 The Open Source Company ((www.tosc.nl).)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, _, SUPERUSER_ID
from odoo.exceptions import UserError, ValidationError
from datetime import datetime


class Task(models.Model):
    _inherit = "project.task"

    @api.constrains('project_id', 'standard')
    def _check_project_standard(self):
        task = self.env['project.task'].search([('project_id', '=', self.project_id.id), ('standard', '=', True)])
        if len(task) > 1 and self.standard:
            raise ValidationError(_('You can have only one task with the standard as true per project!'))

    standard = fields.Boolean(
        string='Standard'
    )
    task_user_ids = fields.One2many(
        'task.user',
        'task_id',
        string='Can register time',
        tracking=True,
    )

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        recs = self.browse()
        if name:
            recs = self.search([('name', '=', name)] + args, limit=limit)
        if not recs:
            domain = [('name', operator, name)]
            # if 'jira_compound_key' in self._fields:
            #     domain = ['|'] + domain + [('jira_compound_key', operator, name)]
            recs = self.search(domain + args, limit=limit)
        return recs.name_get()


class Project(models.Model):
    _inherit = "project.project"

    @api.depends('task_ids.standard')
    def _compute_standard(self):
        if self.task_ids:
            self.standard_task_id = self.env['project.task'].search(
                [('standard', '=', True), ('id', 'in', self.task_ids.ids)])

    overtime = fields.Boolean(
        string='Overtime Taken'
    )
    overtime_hrs = fields.Boolean(
        string='Overtime Hours'
    )
    invoice_principle = fields.Selection(
        [
        ('ff', 'Fixed Fee'),
        ('tm', 'Time and Material'),
        ('ctm', 'Capped Time and Material')
    ], )
    invoice_schedule_ids = fields.One2many(
        'invoice.schedule.lines',
        'project_id',
        string='Invoice Schedule'
    )
    standard_task_id = fields.Many2one(
        'project.task',
        compute=_compute_standard,
        string='Standard Task',
        store=True
    )

    @api.constrains('overtime', 'overtime_hrs')
    def _check_project_overtime(self):
        company_id = self.company_id.id if self.company_id else False

        overtime_taken_project = self.search([('company_id', '=', company_id), ('overtime', '=', True)])
        if len(overtime_taken_project) > 1:
            raise ValidationError(_("You can have only one project with 'Overtime Taken' per company!"))

        overtime_project = self.search([('company_id', '=', company_id), ('overtime_hrs', '=', True)])
        if len(overtime_project) > 1:
            raise ValidationError(_("You can have only one project with 'Overtime Hours' per company!"))

    def action_view_invoice(self):
        invoice_lines = self.env['account.move.line']
        invoices = invoice_lines.search([('account_analytic_id', '=', self.analytic_account_id.id)]).mapped('invoice_id')
        action = self.env.ref('account.action_invoice_tree1').read()[0]
        if len(invoices) > 1:
            action['domain'] = [('id', 'in', invoices.ids)]
        elif len(invoices) == 1:
            action['views'] = [(self.env.ref('account.view_move_form').id, 'form')]
            action['res_id'] = invoices.ids[0]
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action

class InvoiceScheduleLine(models.Model):
    _name = 'invoice.schedule.lines'

    project_id = fields.Many2one(
        'project.project',
    )


class ProjectInvoicingProperties(models.Model):
    _inherit = "project.invoicing.properties"

    invoice_mileage = fields.Boolean(
        'Invoice Mileage'
    )
    group_invoice = fields.Boolean(
        'Group Invoice'
    )
    group_by_fee_rate = fields.Boolean(
        'Group By Fee Rate'
    )
    group_by_month = fields.Boolean(
        'Group By Month'
    )

    @api.onchange('invoice_mileage')
    def onchange_invoice_mileage(self):
        try:
            id = self._origin.id
        except:
            id = self.id
        project = self.env['project.project'].search([('invoice_properties', '=', id)])
        if project:
            ps_time_lines = self.env['ps.time.line'].search([
                ('project_id', 'in', project.ids),
                ('product_uom_id', '=', self.env.ref('uom.product_uom_km').id)
            ])
            if ps_time_lines:
                non_invoiceable_mileage = False if self.invoice_mileage else True
                cond = '='
                rec = ps_time_lines.ids[0]
                if len(ps_time_lines) > 1:
                    cond = 'IN'
                    rec = tuple(ps_time_lines.ids)
                self.env.cr.execute("""
                    UPDATE ps_time_line SET product_uom_id = %s, non_invoiceable_mileage = %s WHERE id %s %s
                """ % (self.env.ref('uom.product_uom_km').id, non_invoiceable_mileage, cond, rec))
