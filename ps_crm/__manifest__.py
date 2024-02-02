# Copyright 2018 Willem Hulshof The Open Source Company (www.tosc.nl).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    'name': "Professional Services CRM",

    'summary': "Opportunities - Extended",

    'description': """
This module creates monthly revenue forecast lines.
===================================================

For each calendar month between the start date and end date, a month-revenue is generated.
Go to Reports>Monthly Revenue to see the overview of the expected revenue per month derived from all the opportunities.

Steps to generate monthly expected revenue:
--------------------------------------------------
* Expected revenue should be filled. Once set the monthly expected revenue fields will be visible.
* Then you can fill start date and end date to get splitted revenues per month.
    """,

    'author': "TOSC",
    'website': "http://www.tosc.nl",

    'category': 'Sales',
    'version': '14.0.1.0.0',

    'depends': ['base','uom', 'crm', 'crm_industry', 'project', 'operating_unit', 'hr', 'utm', 'date_range','web_notify','sale'],

    # always loaded
    'data': [
        'security/crm_security.xml',
        'security/ir.model.access.csv',
        'views/crm_lead_views.xml',
    ],
    'installable': True,
}
