# -*- coding: utf-8 -*-
# Copyright 2023 The Open Source Company (www.tosc.nl)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'Professional Services External Consolidation',
    'summary': """
        This module creates inter-operating-unit revenue lines in invoices and adds trading_partner_code 
        for external systems to consolidate""",
    'version': '14.0.1.0.0',
    'license': 'AGPL-3',
    'author': 'TOSC, Odoo Community Association (OCA)',
    'website': 'https://www.tosc.nl',
    'depends': [
        'consolidation_external_system',
    ],
    'data': [
        'views/fleet_view.xml',
    ],
    'installable': False,
}
