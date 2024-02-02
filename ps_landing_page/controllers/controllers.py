# -*- coding: utf-8 -*-
from odoo import http

# class PSLandingPage(http.Controller):
#     @http.route('/ps_landing_page/ps_landing_page/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/ps_landing_page/ps_landing_page/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('ps_landing_page.listing', {
#             'root': '/ps_landing_page/ps_landing_page',
#             'objects': http.request.env['ps_landing_page.ps_landing_page'].search([]),
#         })

#     @http.route('/ps_landing_page/ps_landing_page/objects/<model("ps_landing_page.ps_landing_page"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('ps_landing_page.object', {
#             'object': obj
#         })