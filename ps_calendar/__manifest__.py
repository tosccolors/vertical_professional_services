{
    "name": "Professional Services Calendar",
    "summary": """
        Professional Services Calendar""",
    "license": "AGPL-3",
    "author": "The Open Source Company",
    "website": "http://www.tosc.nl",
    "category": "Uncategorized",
    "version": "16.0.1.0.0",
    "depends": ["account_fiscal_month", "account_fiscal_year", "ps_date_range_week"],
    "data": [
        "views/date_range_views.xml",
    ],
    "post_init_hook": "post_init_hook",
}
