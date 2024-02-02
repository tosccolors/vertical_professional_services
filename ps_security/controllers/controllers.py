# -*- coding: utf-8 -*-
from odoo import http

# class PSSecurity(http.Controller):
#     @http.route('/ps_security/ps_security/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/ps_security/ps_security/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('ps_security.listing', {
#             'root': '/ps_security/ps_security',
#             'objects': http.request.env['ps_security.ps_security'].search([]),
#         })

#     @http.route('/ps_security/ps_security/objects/<model("ps_security.ps_security"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('ps_security.object', {
#             'object': obj
#         })