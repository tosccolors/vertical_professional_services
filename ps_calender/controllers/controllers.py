# -*- coding: utf-8 -*-
from odoo import http

# class PSCalender(http.Controller):
#     @http.route('/ps_calender/ps_calender/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/ps_calender/ps_calender/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('ps_calender.listing', {
#             'root': '/ps_calender/ps_calender',
#             'objects': http.request.env['ps_calender.magnus_calender'].search([]),
#         })

#     @http.route('/magnus_calender/magnus_calender/objects/<model("magnus_calender.magnus_calender"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('magnus_calender.object', {
#             'object': obj
#         })