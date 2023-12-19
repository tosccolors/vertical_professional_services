# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'PS Calender Week',
    'summary': """
        Provide a calender week date range type""",
    'version': '14.0.1.0.0',
    'license': 'AGPL-3',
    'author': 'TOSC',
    'website': 'https://www.tosc.nl',
    'depends': [
        'date_range','account_fiscal_year'
    ],
    'data': [
        'data/date_range_type.xml',
        'views/date_range_type.xml',
    ],
}
