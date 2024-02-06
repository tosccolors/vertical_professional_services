# -*- coding: utf-8 -*-
# © 2016-17 Eficent Business and IT Consulting Services S.L.
# © 2016 Serpent Consulting Services Pvt. Ltd.
# Copyright 2018 - 2023 The Open Source Company ((www.tosc.nl).)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

from odoo.tools.translate import _
from odoo import api, fields, models
from odoo.exceptions import UserError
from datetime import datetime, timedelta


class InteroOUAccountMapping(models.Model):
    _name = 'inter.ou.account.mapping'
    _description = 'Inter Operating Unit Account Mapping'
    _rec_name = 'account_id'

    @api.model
    def _get_revenue_account_domain(self):
        ids = [self.env.ref('account.data_account_type_other_income').id,
               self.env.ref('account.data_account_type_revenue').id]
        return [('deprecated', '=', False), ('user_type_id', 'in', ids)]

    @api.model
    def _get_cost_of_sales_account_domain(self):
        ids = [self.env.ref('account.data_account_type_direct_costs').id]
        return [('deprecated', '=', False), ('user_type_id', 'in', ids)]

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env['res.company']._company_default_get(
            'inter.ou.account.mapping')
    )
    account_id = fields.Many2one(
        'account.account',
        string='Product Revenue Account',
        domain=_get_revenue_account_domain,
        required=True
    )
    inter_ou_account_id = fields.Many2one(
        'account.account',
        string='Inter OU Account',
        domain=_get_revenue_account_domain,
        required=True
    )
    revenue_account_id = fields.Many2one(
        'account.account',
        string='Revenue Account',
        domain=_get_revenue_account_domain,
        required=True
    )
    cost_account_id = fields.Many2one(
        'account.account',
        string='Inter OU Cost of Sales Account',
        domain=_get_cost_of_sales_account_domain,
        required=True
    )
    trading_partners = fields.Boolean(
        string='both operating_units are trading partners',
        default=False
    )

    @api.model
    def _get_mapping_dict(self, company_id, trading_partners, maptype):
        """return a dict with:
        key = ID of account,
        value = ID of mapped_account"""
        mappings = self.search([
            ('company_id', '=', company_id.id),('trading_partners','=', trading_partners)])
        mapping = {}
        if maptype == 'product_to_inter':
            for item in mappings:
                mapping[item.account_id.id] = item.inter_ou_account_id.id
        if maptype == 'inter_to_regular':
            for item in mappings:
                mapping[item.inter_ou_account_id.id] = item.revenue_account_id.id
        if maptype == 'regular_to_cost':
            for item in mappings:
                mapping[item.revenue_account_id.id] = item.cost_account_id.id
        if maptype == 'inter_to_cost':
            for item in mappings:
                mapping[item.inter_ou_account_id.id] = item.cost_account_id.id
        return mapping


