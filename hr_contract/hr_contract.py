# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
import time

from osv import fields, osv

class hr_employee(osv.osv):
    _name = "hr.employee"
    _description = "Employee"
    _inherit = "hr.employee"
    _columns = {
        'manager': fields.boolean('Is a Manager'),
        'medic_exam': fields.date('Medical Examination Date'),
        'place_of_birth': fields.char('Place of Birth', size=30),
        'children': fields.integer('Number of Children'),
        'vehicle': fields.char('Company Vehicle', size=64),
        'vehicle_distance': fields.integer('Home-Work Distance', help="In kilometers"),
        'contract_ids': fields.one2many('hr.contract', 'employee_id', 'Contracts'),
        }
hr_employee()

#Contract wage type period name
class hr_contract_wage_type_period(osv.osv):
    _name='hr.contract.wage.type.period'
    _description='Wage Period'
    _columns = {
        'name': fields.char('Period Name', size=50, required=True, select=True),
        'factor_days': fields.float('Hours in the period', digits=(12,4), required=True, help='This field is used by the timesheet system to compute the price of an hour of work wased on the contract of the employee')
        }
    _defaults = {
        'factor_days': 168.0
        }
hr_contract_wage_type_period()

#Contract wage type (hourly, daily, monthly, ...)
class hr_contract_wage_type(osv.osv):
    _name = 'hr.contract.wage.type'
    _description = 'Wage Type'
    _columns = {
        'name': fields.char('Wage Type Name', size=50, required=True, select=True),
        'period_id': fields.many2one('hr.contract.wage.type.period', 'Wage Period', required=True),
        'type': fields.selection([('gross','Gross'), ('net','Net')], 'Type', required=True),
        'factor_type': fields.float('Factor for hour cost', digits=(12,4), required=True, help='This field is used by the timesheet system to compute the price of an hour of work wased on the contract of the employee')
        }
    _defaults = {
        'type': 'gross',
        'factor_type': 1.8
        }
hr_contract_wage_type()


class hr_contract_type(osv.osv):
    _name = 'hr.contract.type'
    _description = 'Contract Type'
    _columns = {
        'name': fields.char('Contract Type', size=32, required=True),
    }
hr_contract_type()

class hr_contract(osv.osv):
    _name = 'hr.contract'
    _description = 'Contract'
    _columns = {
        'name': fields.char('Contract Reference', size=32, required=True),
        'employee_id': fields.many2one('hr.employee', "Employee", required=True),
        'department_id': fields.related('employee_id','department_id', string="Department", readonly=True),
        'type_id': fields.many2one('hr.contract.type', "Contract Type"),
        'job_id': fields.many2one('hr.job', 'Job Title'),
        'date_start': fields.date('Start Date', required=True),
        'date_end': fields.date('End Date'),
        'working_hours': fields.many2one('resource.calendar','Working Schedule'),
        'wage_type_id': fields.many2one('hr.contract.wage.type', 'Wage Type', required=True),
        'wage': fields.float('Wage', digits=(16,2), required=True),
        'advantages': fields.text('Advantages'),
        'advantages_net': fields.float('Net Advantages Value', digits=(16,2)),
        'advantages_gross': fields.float('Gross Advantages Value', digits=(16,2)),
        'notes': fields.text('Notes'),
        }
    _defaults = {
        'date_start': time.strftime("%Y-%m-%d"),
        }

hr_contract()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
