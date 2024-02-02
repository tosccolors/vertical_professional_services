# -*- coding: utf-8 -*-
# Copyright 2018 The Open Source Company ((www.tosc.nl).)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta





class AccountMove(models.Model):
    _inherit = "account.move"

    ic_lines = fields.Boolean(
        string='IC lines generated',
        default=False
    )

    ## todo: bcs no account_invoice anymore, this has to change
    # @api.model
    # def invoice_line_move_line_get(self):
    #     """Copy user_id and trading_partner_code from invoice line to move lines"""
    #     res = super(AccountMove, self).invoice_line_move_line_get()
    #     ailo = self.env['account.move.line']
    #     for move_line_dict in res:
    #         iline = ailo.browse(move_line_dict['invl_id'])
            # if iline.trading_partner_code:
            #     move_line_dict['trading_partner_code'] = iline.trading_partner_code
        # return res

    ## todo: bcs no account_invoice anymore, this has to change
    # @api.model
    # def line_get_convert(self, line, part):
    #     res = super(AccountMove, self).line_get_convert(line, part)
    #     res['trading_partner_code'] = line.get('trading_partner_code', False)
    #     if self.partner_id.trading_partner_code \
    #             and self.operating_unit_id.partner_id.trading_partner_code \
    #             and line.get('type', False) == 'dest':
    #         res['trading_partner_code'] = self.partner_id.trading_partner_code
    #     return res



    @api.onchange('product_id')
    def _onchange_product_id(self):
        res = super(AccountMoveLine, self)._onchange_product_id()
        if self.move_id.move_type == 'out_invoice' \
                and self.operating_unit_id != self.move_id.operating_unit_id \
                and self.account_id.user_type_id in (
                                            self.env.ref('account.data_account_type_other_income'),
                                            self.env.ref('account.data_account_type_revenue')
                                            ):
           account = self.account_id
           trading_partners = self.operating_unit_id.partner_id.trading_partner_code \
                              and self.move_id.operating_unit_id.partner_id.trading_partner_code
           self.account_id = self.env['inter.ou.account.mapping']._get_mapping_dict(
                                                                self.company_id, trading_partners,'product_to_inter'
                                                                )[account.id]
        return res

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    ## todo: bcs no account_invoice anymore, this has to change
    @api.depends('full_reconcile_id','invoice_line_id','invoice_id')
    def _compute_trading_partner_code(self):
        invoice_lines = self.filtered('invoice_line_id')
        ar_ap_lines = self.filtered(lambda line:
                                (line.invoice_id.partner_id.trading_partner_code or
                                 line.invoice_id.partner_id.parent_id.trading_partner_code) and
                                line.invoice_id.operating_unit_id.partner_id.trading_partner_code and
                                line.account_id.internal_type in ('receivable', 'payable'))
        reconciled_arap_lines = ar_ap_lines.filtered('full_reconcile_id')
        fr_ids = reconciled_arap_lines.mapped('full_reconcile_id')
        reconciled_payment_lines = self.filtered(lambda line: line.full_reconcile_id in fr_ids) - ar_ap_lines
        for il in invoice_lines:
            il.trading_partner_code = il.invoice_line_id.trading_partner_code
        for aal in ar_ap_lines:
            aal.trading_partner_code = aal.invoice_id.partner_id.trading_partner_code or \
                                       aal.invoice_id.partner_id.parent_id.trading_partner_code
        for pl in reconciled_payment_lines:
            pl.trading_partner_code = self.search([
                ('full_reconcile_id','=', pl.full_reconcile_id.id),
                ('invoice_id' ,'!=', False)
                 ])[0].trading_partner_code

    ic_line = fields.Boolean(
        string='IC line',
        default=False
    )
    revenue_line = fields.Boolean(
        string='Revenue line',
        default=False
    )
    trading_partner_code = fields.Char(
        'Trading Partner Code',
        compute=_compute_trading_partner_code,
        # inverse=_inverse_trading_partner_code,
        store= True,
        help="Specify code of Trading Partner"
    )
    invoice_line_id = fields.Many2one(
        'account.invoice.line',
        string='Originating Invoice Line'
    )

    def action_create_ic_lines(self):
        mapping_tp = self.env['inter.ou.account.mapping']._get_mapping_dict(self.company_id, trading_partners=True, maptype='inter_to_regular')
        mapping_notp = self.env['inter.ou.account.mapping']._get_mapping_dict(self.company_id, trading_partners=False, maptype='inter_to_regular')
        mapping2_tp = self.env['inter.ou.account.mapping']._get_mapping_dict(self.company_id, trading_partners=True, maptype='inter_to_cost')
        mapping2_notp = self.env['inter.ou.account.mapping']._get_mapping_dict(self.company_id, trading_partners=False, maptype='inter_to_cost')
        for invoice in self:
            if invoice.ic_lines:
                continue
            all_lines = invoice.invoice_line_ids
            timesheet_user = all_lines.mapped('user_id')
            ou_trading_partner = invoice.operating_unit_id.partner_id.trading_partner_code
            if not timesheet_user and ou_trading_partner:
                all_lines.write({'revenue_line':True,
                                 'trading_partner_code': invoice.partner_id.trading_partner_code or
                                                         invoice.partner_id.parent_id.trading_partner_code})
            elif not timesheet_user:
                all_lines.write({'revenue_line': True})
                continue
            intercompany_revenue_lines = invoice.invoice_line_ids.filtered(
                lambda l: l.operating_unit_id != invoice.operating_unit_id and
                          l.account_id.user_type_id in (
                              self.env.ref('account.data_account_type_other_income'),
                              self.env.ref('account.data_account_type_revenue')))
            regular_lines = all_lines - intercompany_revenue_lines if intercompany_revenue_lines else all_lines
            regular_lines.write({'revenue_line': True,
                                 'trading_partner_code': invoice.partner_id.trading_partner_code or
                                                         invoice.partner_id.parent_id.trading_partner_code
                                 if ou_trading_partner else False})
            if intercompany_revenue_lines:
                invoice_tpc = invoice.operating_unit_id.partner_id.trading_partner_code
                for line in intercompany_revenue_lines:
                    line_tpc = line.operating_unit_id.partner_id.trading_partner_code
                    trading_partners = invoice_tpc and line_tpc and invoice_tpc != line_tpc
                    if trading_partners:
                        mapping = mapping_tp
                        mapping2 = mapping2_tp
                    else:
                        mapping = mapping_notp
                        mapping2 = mapping2_notp
                    if line.account_id.id in mapping and line.account_id.id in mapping2:
                        ## revenue line
                        revenue_line = line.copy({
                            'account_id': mapping[line.account_id.id],
                            'operating_unit_id': invoice.operating_unit_id.id,
                            'user_id': False,
                            'name': line.user_id.firstname + " " + line.user_id.lastname + " " + line.name,
                            'ic_line': True,
                            'revenue_line': True,
                            'trading_partner_code': invoice.partner_id.trading_partner_code or
                                                    invoice.partner_id.parent_id.trading_partner_code
                                                        if ou_trading_partner else False})
                        revenue_line.price_unit = line.price_unit if not line.user_task_total_line_id else \
                            line.user_task_total_line_id.fee_rate
                        ## intercompany cost of sales line
                        cost_line = line.copy({
                            'account_id': mapping2[line.account_id.id],
                            'product_id': False,
                            'operating_unit_id': invoice.operating_unit_id.id,
                            'price_unit': - line.price_unit,
                            'user_id': False,
                            'name': line.user_id.firstname + " " + line.user_id.lastname + " " + line.name,
                            'ic_line': True,
                            'trading_partner_code': line_tpc if trading_partners else False
                        })
                        cost_line.tax_ids = [(6, 0, [])]
                        line.tax_ids = [(6, 0, [])]
                        line.trading_partner_code = invoice_tpc if trading_partners else False
                    else:
                        raise UserError(
                            _('The mapping from account "%s" does not exist or is incomplete.') % (
                                line.account_id.name))
                invoice.ic_lines = True
            if any(line.tax_ids for line in invoice.invoice_line_ids):
                invoice.compute_taxes()

    def action_delete_ic_lines(self):
        for invoice in self.filtered('ic_lines'):
            invoice.invoice_line_ids.filtered('ic_line').unlink()
            for line in invoice.invoice_line_ids:
                price_unit = line.price_unit
                line._set_taxes()
                line.price_unit = price_unit
                # if any(line.invoice_line_tax_ids for line in invoice.invoice_line_ids):
                invoice.compute_taxes()
            invoice.ic_lines = False

    def fill_trading_partner_code_supplier_invoice(self):
        for invoice in self:
            if not (invoice.partner_id.trading_partner_code or invoice.partner_id.parent_id.trading_partner_code):
                intercompany_lines = invoice.invoice_line_ids.filtered(
                    lambda l: l.operating_unit_id != invoice.operating_unit_id)
                if intercompany_lines:
                    invoice_tpc = invoice.operating_unit_id.partner_id.trading_partner_code
                    for line in intercompany_lines:
                        line_tpc = line.operating_unit_id.partner_id.trading_partner_code
                        trading_partners = invoice_tpc and line_tpc and invoice_tpc != line_tpc
                        line.trading_partner_code = invoice_tpc if trading_partners else False
            elif invoice.operating_unit_id.partner_id.trading_partner_code:
                invoice.invoice_line_ids.write({'trading_partner_code': invoice.partner_id.trading_partner_code  or
                                                         invoice.partner_id.parent_id.trading_partner_code})