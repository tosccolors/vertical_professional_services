# Copyright 2018 The Open Source Company ((www.tosc.nl).)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json

from odoo import api, fields, models


class HREmployeeWizard(models.TransientModel):
    _name = "hr.employee.wizard"
    _description = "Employee creation wizard"

    def _get_ou_domain(self):
        ou = self.env["operating.unit"].search(
            [("company_id", "=", self.env.user.company_id.id)]
        )
        domain = [("id", "in", ou.ids)] if ou else [("id", "=", False)]
        return domain

    firstname = fields.Char("Firstname")
    lastname = fields.Char("Lastname")
    email = fields.Char("Email")
    mobile = fields.Char("Mobile")
    gender = fields.Selection(
        [("male", "Male"), ("female", "Female"), ("other", "Other")], string="Gender"
    )
    birthday = fields.Date("Date of Birth")
    place_of_birth = fields.Char("Place of Birth")
    acc_number = fields.Char("Account number")
    bank_name_id = fields.Many2one("res.bank", "Bank")
    login = fields.Char("Login")
    ref = fields.Char("Internal Reference")
    # Field to store the parent department based on the operating unit selected
    parent_department_id = fields.Many2one("hr.department", "Parent Department")
    # Based on the parent department the child department along with parent will
    # be displayed in the below field
    department_id = fields.Many2one("hr.department", "Department")
    department_id_domain = fields.Text(compute="_compute_department_id_domain")
    default_operating_unit_id = fields.Many2one(
        "operating.unit", "Default operating unit", domain=_get_ou_domain
    )
    operating_unit_ids = fields.Many2many(
        "operating.unit", string="Allowed Operating units", domain=_get_ou_domain
    )
    #     allocated_leaves = fields.Integer("Allocated Leaves")
    # Address
    street = fields.Char("Street")
    zip = fields.Char("Zip")
    city = fields.Char("City")
    country_id = fields.Many2one(
        "res.country", "Country", default=lambda self: self.env.company.country_id
    )
    lang = fields.Selection(
        selection=lambda self: self.env["res.lang"].get_installed(),
        string="Language",
        default=lambda self: self.env.lang,
        required=True,
    )

    account_id = fields.Many2one("account.account", "Account")
    initial_employment_date = fields.Date("Initial date of employment")
    official_date_of_employment = fields.Date("Official date of employment")
    temporary_contract = fields.Date("Temporary contract")
    category_ids = fields.Many2many("hr.employee.category", string="Category")
    external = fields.Boolean("External")

    role_line_ids = fields.One2many("users.role.wizard", "user_role_id", "Roles")

    parent_id = fields.Many2one("hr.employee", "Manager")

    leave_hours = fields.Float(string="Leave Hours")

    @api.depends("parent_department_id", "default_operating_unit_id")
    def _compute_department_id_domain(self):
        for this in self:
            this.department_id_domain = json.dumps(
                [("id", "child_of", self.parent_department_id.id)]
                if self.parent_department_id
                else [("operating_unit_id", "=", self.default_operating_unit_id.id)]
            )

    @api.onchange("default_operating_unit_id")
    def onchange_operating_unit(self):
        # In order to display the child ids, we need to get the parent id first
        if self.default_operating_unit_id:
            department_id = self.env["hr.department"].search(
                [("operating_unit_id", "=", self.default_operating_unit_id.id)]
            )
            if department_id:
                for line in department_id:
                    self.parent_department_id = line.id
        else:
            self.parent_department_id = False

    @api.model
    def default_get(self, field_list):
        company = self.env.user.company_id.id
        res = super(HREmployeeWizard, self).default_get(field_list)
        operating_unit_ids = self.env["operating.unit"].search(
            [("company_id", "=", company)]
        )
        res.update({"operating_unit_ids": operating_unit_ids.ids})
        return res

    def create_partner(self):
        """partner creation"""
        firstname = self.firstname
        lastname = self.lastname
        account_payment_term_id = self.env["account.payment.term"].search(
            [("name", "=", "Immediate Payment")], limit=1
        )
        account_payment_mode_id = self.env["account.payment.mode"].search(
            [("name", "=", "SEPA Credit Transfer (Outbound)")], limit=1
        )
        partner = {
            "name": firstname + " " + lastname if firstname and lastname else "",
            "lastname": lastname,
            "firstname": firstname,
            "street": self.street,
            "zip": self.zip,
            "city": self.city,
            "country_id": self.country_id and self.country_id.id,
            "email": self.email,
            "mobile": self.mobile,
            "ref": self.ref,
            "property_supplier_payment_term_id": account_payment_term_id
            and account_payment_term_id.id,
            "supplier_payment_mode_id": account_payment_mode_id
            and account_payment_mode_id.id,
            "lang": self.lang,
        }
        partner_id = self.env["res.partner"].create(partner)
        return partner_id

    # @api.multi
    def create_user(self, partner_id):
        list_role = [(5, False, False)]
        for role_line in self.role_line_ids:
            data = {
                "role_id": role_line.role_id.id,
                "date_from": role_line.from_date or False,
                "date_to": role_line.to_date or False,
            }
            list_role.append((0, 0, data))
        user = {
            "lastname": self.lastname,
            "firstname": self.firstname,
            "login": self.login,
            "partner_id": partner_id.id,
            "default_operating_unit_id": self.default_operating_unit_id.id,
            "operating_unit_ids": [(6, 0, self.operating_unit_ids.ids)],
            "role_line_ids": list_role,
            "notification_type": "inbox",
        }
        user_id = self.env["res.users"].create(user)
        return user_id

    # @api.multi
    def create_res_partner_bank(self, partner_id):
        res_partner_bank_id = self.env["res.partner.bank"].search(
            [("acc_number", "=", self.acc_number)], limit=1
        )
        if res_partner_bank_id:
            res_partner_bank_id = res_partner_bank_id
        else:
            if self.acc_number:
                res_partner_bank_id = self.env["res.partner.bank"].create(
                    {
                        "acc_number": self.acc_number,
                        "bank_id": self.bank_name_id and self.bank_name_id.id,
                        "partner_id": partner_id and partner_id.id,
                    }
                )
        return res_partner_bank_id

    def create_employee(self, user_id, res_partner_bank_id):
        firstname = self.firstname
        lastname = self.lastname
        employee = {
            "name": firstname + " " + lastname if firstname and lastname else "",
            "firstname": firstname,
            "lastname": lastname,
            "work_email": self.email,
            "gender": self.gender,
            "mobile_phone": self.mobile,
            "birthday": self.birthday,
            "place_of_birth": self.place_of_birth,
            "address_home_id": user_id.partner_id.id,
            "user_id": user_id.id,
            "bank_account_id": res_partner_bank_id.id,
            "department_id": self.department_id.id,
            # TODO: which account_id is this about? missing dependency?
            # 'account_id': self.account_id.id,
            "service_hire_date": self.initial_employment_date,
            "official_date_of_employment": self.official_date_of_employment,
            "temporary_contract": self.temporary_contract,
            "category_ids": [(6, 0, self.category_ids.ids)],
            "external": self.external,
            "parent_id": self.parent_id.id,
        }
        return self.env["hr.employee"].create(employee)

    def create_all(self):
        """Partner, user, bank, holiday and Employee creation"""
        partner_id = self.create_partner()
        user_id = self.create_user(partner_id)
        res_partner_bank_id = self.create_res_partner_bank(partner_id)
        employee_id = self.create_employee(user_id, res_partner_bank_id)
        result_dict = self.env["ir.actions.actions"]._for_xml_id(
            "hr.open_view_employee_list_my"
        )
        result_dict.update(views=[(False, "form")], res_id=employee_id.id)
        return result_dict


class UsersRoleWizard(models.TransientModel):
    _name = "users.role.wizard"
    _description = "Employee role"

    user_role_id = fields.Many2one("hr.employee.wizard", "Role")
    role_id = fields.Many2one("res.users.role", "Role")
    from_date = fields.Date("From")
    to_date = fields.Date("To")
    is_enable = fields.Boolean("Enabled")
