# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError

class ChangeChargecode(models.TransientModel):
    _name = "change.chargecode"
    _description = "Change Chargecode"

    project_id = fields.Many2one('project.project', 'Project')
    task_id = fields.Many2one('project.task', 'Task')

    @api.onchange('project_id')
    def onchange_project(self):
        res, domain = {}, {}
        if self.project_id:
            tasks = self.project_id.task_ids
            domain['task_id'] = [('id', 'in', tasks.ids)]
            if len(tasks) == 1:
                res['task_id'] = tasks.id
        return {'value': res, 'domain': domain}

    # TODO: aal with km's?
    # TODO: Reverse of correction?
    
    def post(self):
        context = self.env.context.copy()
        line_ids = context.get('active_ids', [])
        time_lines = self.env['ps.time.line'].search([
            ('id', 'in', line_ids),
            ('state', 'in', ['invoiceable','open'])])
        project_id = self.project_id.id
        task_id = self.task_id.id
        for tl in time_lines:
            if tl.task_id.id == task_id:
                continue
            unit_amount = tl.unit_amount
            amount = tl.amount
            tl.write({'state': 'change-chargecode'})
            tl.with_context(analytic_check_state=True).copy(
                default={'sheet_id': False,
                         'ts_line': False,
                         'unit_amount': -unit_amount,
                         'amount': -amount,
                         'state': 'change-chargecode'
                        }
            )
            tl.with_context(analytic_check_state=True).copy(
                default={'sheet_id': False,
                         'ts_line': False,
                         'amount': tl.get_fee_rate_amount(
                             task_id,
                             tl.user_id.id
                         ) if self.project_id.chargeable else 0.0,
                         'project_id': project_id,
                         'task_id': task_id,
                         'state':'open'
                         })
        return True
