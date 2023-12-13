odoo.define('ps_hr.employee_wizard', function (require) {
"use strict";

    var FormController = require('web.FormController');
    var KanbanController = require('web.KanbanController');
    var ListController = require('web.ListController');
    var core = require('web.core');
    var _t = core._t;

    KanbanController.include({
        _onButtonNew: function () {
            if (this.modelName == 'hr.employee' ) {
                return this.do_action({
                    type: 'ir.actions.act_window',
                    name: _('Create Employee'),
                    res_model: 'hr.employee.wizard',
                    view_type: 'form',
                    view_mode: 'form',
                    target: 'new',
                    views: [[false, 'form']],
                });
            }
            return this._super()
        }
    });
    ListController.include({
        _onCreateRecord: function () {
            if (this.modelName == 'hr.employee' ) {
                return this.do_action({
                    type: 'ir.actions.act_window',
                    name: _('Create Employee'),
                    res_model: 'hr.employee.wizard',
                    view_type: 'form',
                    view_mode: 'form',
                    target: 'new',
                    views: [[false, 'form']],
                });
            }
            return this._super()
        }
    });
    FormController.include({
        _onCreate: function () {
            if (this.modelName == 'hr.employee' ) {
                return this.do_action({
                    type: 'ir.actions.act_window',
                    name: _('Create Employee'),
                    res_model: 'hr.employee.wizard',
                    view_type: 'form',
                    view_mode: 'form',
                    target: 'new',
                    views: [[false, 'form']],
                });
            }
            return this._super()
        }
    });
});

