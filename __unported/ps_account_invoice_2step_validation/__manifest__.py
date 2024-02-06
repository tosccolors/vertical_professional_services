# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright 2013 - 2023 The Open Source Company ((www.tosc.nl).)
#
#
##############################################################################

{
    'name' : 'ps_account_invoice_2step_validation',
    'version' : '0.9',
    'category': 'accounts',
    'description': """
This module adds authorization steps in workflow in professional services supplier invoices version 10.0. and 12.0.
 >= 14.0: this module deprecated. base_tier_validation and helper mods.
=============================================================================

Enchanced to add
* Authorization
* Verification status on the Invoice

    """,
    'author'  : 'TOSC - Willem Hulshof',
    'website' : 'http://www.tosc.nl',
    'depends' : ['account_invoice_2step_validation',
    ],
    'data' : [
        "views/account_move_view.xml",
    ],
    'demo' : [],
    'installable': False
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

