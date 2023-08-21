# -*- coding: utf-8 -*-
# Copyright 2018 The Open Source Company ((www.tosc.nl).)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    type = fields.Selection(selection_add=[('wip', 'WIP')], ondelete={'wip': 'cascade'})


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.depends('invoice_line_ids')
    def _compute_month_id(self):
        ps_invoice_id = self.invoice_line_ids.mapped('ps_invoice_id')
        self.month_id = ps_invoice_id and ps_invoice_id[0].month_id.id or False

    target_invoice_amount = fields.Monetary(
        'Target Invoice Amount'
    )
    month_id = fields.Many2one(
        'date.range',
        compute='_compute_month_id',
        string="Invoicing Period"
    )
    wip_move_id = fields.Many2one(
        'account.move',
        string='WIP Journal Entry',
        readonly=True,
        index=True,
        ondelete='restrict',
        copy=False
    )


    def compute_target_invoice_amount(self):
        try:
            if self.amount_untaxed != self.target_invoice_amount:
                self.reset_target_invoice_amount()
                factor = self.target_invoice_amount / self.amount_untaxed
                discount = (1.0 - factor) * 100
                for line in self.invoice_line_ids:
                    line.discount = discount
                taxes_grouped = self.get_taxes_values()
                tax_lines = self.tax_line_ids.filtered('manual')
                for tax in taxes_grouped.values():
                    tax_lines += tax_lines.new(tax)
                self.tax_line_ids = tax_lines
        except ZeroDivisionError:
            raise UserError(_('You cannot set a target amount if the invoice line amount is 0'))


    def reset_target_invoice_amount(self):
        for line in self.invoice_line_ids:
            line.discount = 0.0

    @api.model
    def invoice_line_move_line_get(self):
        """Copy user_id from invoice line to move lines"""
        res = super(AccountMove, self).invoice_line_move_line_get()
        ailo = self.env['account.move.line']
        for move_line_dict in res:
            iline = ailo.browse(move_line_dict['invl_id'])
            if iline.user_id:
                move_line_dict['user_id'] = iline.user_id.id
        return res

    @api.model
    def line_get_convert(self, line, part):
        res = super(AccountMove, self).line_get_convert(line, part)
        res['user_id'] = line.get('user_id', False)
        return res

    def inv_line_characteristic_hashcode(self, invoice_line):
        """Overridable hashcode generation for invoice lines. Lines having the same hashcode
        will be grouped together if the journal has the 'group line' option. Of course a module
        can add fields to invoice lines that would need to be tested too before merging lines
        or not."""
        res = super(AccountMove, self).inv_line_characteristic_hashcode(invoice_line)
        return res + "%s" % (
            invoice_line['user_id']
        )

    def _get_timesheet_by_group(self):
        self.ensure_one()
        ptl_ids = []
        ps_invoice_ids = self.invoice_line_ids.mapped('ps_invoice_id')
        for ps_invoice in ps_invoice_ids:
            for grp_line in ps_invoice.user_total_ids:
                ptl_ids += grp_line.detail_ids
        userProject = {}
        for ptl in ptl_ids:
            project_id, user_id = ptl.project_id if ptl.project_id else ptl.task_id.project_id , ptl.user_id
            if project_id.correction_charge and project_id.specs_invoice_report:
                if (project_id, user_id) in userProject:
                    userProject[(project_id, user_id)] = userProject[(project_id, user_id)] + [ptl]
                else:
                    userProject[(project_id, user_id)] = [ptl]
        return userProject


    def action_invoice_open(self):
        to_process_invoices = self.filtered(lambda inv: inv.type in ('out_invoice', 'out_refund'))
        supplier_invoices = self - to_process_invoices
        if to_process_invoices:
            to_process_invoices.action_create_ic_lines()
        if supplier_invoices:
            supplier_invoices.fill_trading_partner_code_supplier_invoice()
        res = super(AccountMove, self).action_invoice_open()
        for invoice in to_process_invoices:
            ps_invoice_id = invoice.invoice_line_ids.mapped('ps_invoice_id')
            if ps_invoice_id and invoice.type != 'out_refund':
                # if invoicing period doesn't lie in same month
                period_date = datetime.strptime(str(ps_invoice_id.month_id.date_start), "%Y-%m-%d").strftime('%Y-%m')
                cur_date = datetime.now().date().strftime("%Y-%m")
                invoice_date = invoice.date or invoice.date_invoice
                inv_date = datetime.strptime(str(invoice_date), "%Y-%m-%d").strftime('%Y-%m') if invoice_date else cur_date
                if inv_date != period_date and invoice.move_id:
                    invoice.action_wip_move_create()
        return res



    def set_move_to_draft(self):
        if self.move_id.state == 'posted':
            if not self.move_id.journal_id.update_posted:
                raise UserError(_('Please allow to cancel entries from this journal.'))
            self.move_id.state = 'draft'
            return 'posted'
        return 'draft'

    @api.model
    def get_wip_default_account(self):
        if self.type in ('out_invoice', 'in_refund'):
            return self.journal_id.default_credit_account_id.id
        return self.journal_id.default_debit_account_id.id

    def action_wip_move_create(self):
        """ Creates invoice related analytics and financial move lines """
        for inv in self:
            # wip_journal = self.env.ref('ps_timesheet_invoicing.wip_journal')
            # if not wip_journal.sequence_id:
            #     raise UserError(_('Please define sequence on the type WIP journal.'))
            if not inv.company_id.wip_journal_id:
                raise UserError(_('Please define WIP journal on company.'))
            if not inv.company_id.wip_journal_id.sequence_id:
                raise UserError(_('Please define sequence on the type WIP journal.'))
            wip_journal = inv.company_id.wip_journal_id
            sequence = wip_journal.sequence_id
            if inv.type in ['out_refund', 'in_invoice','in_refund'] or inv.wip_move_id:
                continue
            date_end = inv.month_id.date_end
            new_name = sequence.with_context(ir_sequence_date=date_end).next_by_id()
            if inv.move_id:
                wip_move = inv.move_id.wip_move_create( wip_journal, new_name, inv.account_id.id, inv.number)
            wip_move.post()
            # make the invoice point to that wip move
            inv.wip_move_id = wip_move.id
            #wip reverse posting
            reverse_date = datetime.strptime(str(wip_move.date), "%Y-%m-%d") + timedelta(days=1)
            ##########updated reversal code####
            # line_amt = sum(ml.credit + ml.debit for ml in wip_move.line_ids)
            # reconcile = False
            # if line_amt > 0:
            #     reconcile = True
            # reverse_wip_move = wip_move.create_reversals(
            #     date=reverse_date,
            #     journal=wip_journal,
            #     move_prefix='WIP Invoicing Reverse',
            #     line_prefix='WIP Invoicing Reverse',
            #     reconcile=reconcile
            # )
            ########################################
            reverse_wip_ids = wip_move.reverse_moves(date=reverse_date, journal_id=wip_journal, auto=False)
            if len(reverse_wip_ids) == 1:
                reverse_wip_move = wip_move.browse(reverse_wip_ids)
                wip_nxt_seq = sequence.with_context(ir_sequence_date=reverse_wip_move.date).next_by_id()
                reverse_wip_move.write({'name':wip_nxt_seq})
        return True

    def action_cancel(self):
        res = super(AccountMove, self).action_cancel()
        wip_moves = self.env['account.move']
        for inv in self:
            if inv.wip_move_id:
                wip_moves += inv.wip_move_id

        # First, set the invoices as cancelled and detach the move ids
        self.write({'wip_move_id': False})
        if wip_moves:
            # second, invalidate the move(s)
            wip_moves.button_cancel()
            # delete the move this invoice was pointing to
            # Note that the corresponding move_lines and move_reconciles
            # will be automatically deleted too
            wip_moves.unlink()
        return res

    def post(self, invoice=False):
        for move in self:
            if not move.company_id.ou_is_self_balanced or not move.name:
                continue
            for line in move.line_ids:
                if line.name == 'OU-Balancing':
                    line.with_context(wip=True).unlink()
        res = super(AccountMove, self).post(invoice=invoice)
        return res

    def wip_move_create(self, wip_journal, name, ar_account_id, ref=None):
        self.ensure_one()
        move_date = datetime.strptime(str(self.date), "%Y-%m-%d")
        last_day_month_before = datetime.strptime(str(move_date - timedelta(days=move_date.day)), "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d")
        default = {
            'name': name,
            'ref':  ref if ref else 'WIP Invoicing Posting',
            'journal_id': wip_journal.id,
            'date': last_day_month_before,
            'narration': 'WIP Invoicing Posting',
            'to_be_reversed': True,
        }
        wip_move = self.copy(default)
        mls = wip_move.line_ids
        ## we filter all BS lines out of all move lines. And also all "null" lines because of reconcile problem
        # All filtered out lines are unlinked. All will be kept unchanged and copied with reversing debit/credit
        # and replace P/L account by wip-account.
        ids = []
        ids.append(self.env.ref('account.data_account_type_other_income').id)
        ids.append(self.env.ref('account.data_account_type_revenue').id)
        ids.append(self.env.ref('account.data_account_type_depreciation').id)
        ids.append(self.env.ref('account.data_account_type_expenses').id)
        ids.append(self.env.ref('account.data_account_type_direct_costs').id)
        # Balance Sheet lines
        bs_move_lines = mls.filtered(lambda r: r.account_id.user_type_id.id not in ids)
        # lines with both debit and credit equals 0
        null_lines = mls.filtered(lambda r: r.credit + r.debit == 0.0)
        # leaving only not-null Profit and Loss lines
        pl_move_lines = mls - bs_move_lines - null_lines
        bs_move_lines.unlink()
        null_lines.unlink()
        default = {
            'account_id': wip_journal.default_credit_account_id.id
        }
        for line in pl_move_lines:
            wip_line = line.copy(default)
            if line.credit != 0:
                wip_line.credit = line.debit
                wip_line.debit = line.credit
            else:
                wip_line.debit = line.credit
                wip_line.credit = line.debit
        return wip_move



class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    ps_invoice_id = fields.Many2one(
        'ps.invoice',
        string='Invoice Reference',
        ondelete='cascade',
        index=True
    )
    user_id = fields.Many2one(
        'res.users',
        'Timesheet User',
        index = True
    )
    user_task_total_line_id = fields.Many2one(
        'ps.time.line.user.total',
        string='Grouped PS Time line',
        ondelete='cascade',
        index=True
    )
    user_id = fields.Many2one(
        'res.users',
        string='Timesheet User'
    )
    # wip_percentage=fields.Float("WIP percentage")


    @api.constrains('operating_unit_id', 'analytic_account_id','user_id')
    def _check_analytic_operating_unit(self):
        for rec in self.filtered('user_id'):
            if not rec.operating_unit_id == \
                                    rec.user_id._get_operating_unit_id():
                raise UserError(_('The Operating Unit in the'
                                  ' Move Line must be the '
                                  'Operating Unit in the department'
                                  ' of the user/employee'))
        super(AccountMoveLine, self - self.filtered('user_id'))._check_analytic_operating_unit()

    @api.onchange('analytic_account_id', 'user_id')
    def onchange_operating_unit(self):
        super(AccountMoveLine, self).onchange_operating_unit()
        if self.user_id:
            self.operating_unit_id = \
                self.user_id._get_operating_unit_id()

    @api.depends('account_analytic_id', 'user_id', 'move_id.operating_unit_id')
    def _compute_operating_unit(self):
        super(AccountMoveLine, self)._compute_operating_unit()
        for line in self.filtered('user_id'):
            line.operating_unit_id = line.user_id._get_operating_unit_id()

    # 
    # def write(self, vals):
    #     res = super(AccountInvoiceLine, self).write(vals)
    #     self.filtered('ps_invoice_id').mapped('invoice_id').compute_taxes() #Issue: Vat creation double after invoice date change
    #     return res

    @api.model
    def default_get(self, fields):
        res = super(AccountMoveLine, self).default_get(fields)
        ctx = self.env.context.copy()
        if 'default_invoice_id' in ctx:
            invoice_obj = self.env['account.move'].browse(ctx['default_invoice_id'])
            ps_invoice_id = invoice_obj.invoice_line_ids.mapped('ps_invoice_id')
            if ps_invoice_id:
                res['ps_invoice_id'] = ps_invoice_id.id
        return res

    @api.onchange('user_task_total_line_id.fee_rate')
    def _onchange_fee_rate(self):
        if self.user_task_total_line_id.fee_rate:
            self.price_unit = self.user_task_total_line_id.fee_rate


#    @api.onchange('product_id')
#    def _onchange_product_id(self):
#        if self.ps_invoice_id:
#            self.invoice_id = self.env['account.invoice'].browse(self.ps_invoice_id.invoice_ids.id)
#        return super(AccountInvoiceLine, self)._onchange_product_id()


