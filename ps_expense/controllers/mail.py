from odoo import http

from odoo.addons.mail.controllers import main


class MailController(main.MailController):
    @http.route("/mail/thread/data", methods=["POST"], type="json", auth="user")
    def mail_thread_data(self, thread_model, thread_id, request_list, **kwargs):
        result = super().mail_thread_data(
            thread_model, thread_id, request_list, **kwargs
        )
        if thread_model == "hr.expense.sheet" and "attachments" in request_list:
            sheet = http.request.env[thread_model].browse(thread_id)
            result["attachments"] += (
                sheet.env["ir.attachment"]
                .search(
                    [
                        ("res_id", "in", sheet.mapped("expense_line_ids").ids),
                        ("res_model", "=", "hr.expense"),
                    ],
                    order="id desc",
                )
                ._attachment_format(commands=True)
            )
        return result
