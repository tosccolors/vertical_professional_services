# -*- coding: utf-8 -*-
# Copyright 2018 Willem Hulshof The Open Source Company (www.tosc.nl).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    'name': "ps_klippa",

    'summary': "This module creates a cron job to update expenses.",

    'description': """
        This cron job does two things:\n
        1. Submits all expenses in state to be submitted.\n
        2. And fills in the operating unit, based on the linked operating unit in the analytic account.\n
    """,

    'author': "TOSC",
    'website': "http://www.tosc.nl",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['ps_expense'],

    # always loaded
    'data': [
        # 'data/cron_data.xml', commented coz of error on model id
    ],
    # only loaded in demonstration mode
    'demo': [
        # 'demo/demo.xml',
    ],
}
