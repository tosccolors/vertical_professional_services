# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright 2014-2023 The Open Source Company (www.tosc.nl).
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs.
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company like Veritos.
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
#
##############################################################################

{
    'name' : 'ps_account',
    'version' : '1.0',
    'category': 'accounts',
    'description': """
This module enhances accounts & Invoice in OpenERP.
=============================================================================

* Report: Invoice Layout enhancements


    """,
    'author'  : 'TOSC - Willem Hulshof',
    'website' : 'http://www.tosc.nl',
    'depends' : [
                'account',
                'account_invoice_supplier_ref_unique',
                'report_qweb_operating_unit',
                'account_operating_unit',
                'operating_unit_report_layout',
                'ps_timesheet_invoicing',
    ],
    'data' : [
        "report/report_layout.xml",
        "report/report_invoice.xml",
        "views/account_invoice_view.xml",
        "views/project_view.xml",
        "views/account_invoice_report.xml",
    ],
    'demo' : [],
    'installable': True,
    'external_dependencies': {
        'python': [
            'PyPDF2',
        ],
    },
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

