# -*- coding: utf-8 -*-

{
    'name': 'Professional Services - Co Manager for Departments',
    'version': '1.0',
    'author'  : 'TOSC - Hayo Bos',
    'website' : 'http://www.tosc.nl',
    'category': 'Human Resources',
    'description': """Adds a co-manager field to a department""",
    'depends': ['ps_expense', 'ps_timesheet_invoicing'],
    'summary': 'Employee,Department',
    'data': [
        'security/ir_rule.xml',
        'views/hr_views.xml',
    ],

    'installable': False,
    'application': True,
}
