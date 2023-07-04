# -*- coding: utf-8 -*-
from odoo import http

# class PSExpense(http.Controller):
#     @http.route('/ps_expense/ps_expense/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/ps_expense/ps_expense/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('ps_expense.listing', {
#             'root': '/ps_expense/ps_expense',
#             'objects': http.request.env['ps_expense.ps_expense'].search([]),
#         })

#     @http.route('/ps_expense/ps_expense/objects/<model("ps_expense.ps_expense"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('ps_expense.object', {
#             'object': obj
#         })