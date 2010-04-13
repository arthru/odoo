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


{
    'name': 'Attendances Of Employees',
    'version': '1.1',
    'category': 'Generic Modules/Human Resources',
    'description': """
    This module aims to manage employee's attendances.

    Keeps account of the attendances of the employees on the basis of the
    actions(Sign in/Sign out) performed by them.
       """,
    'author': 'Tiny',
    'depends': ['base', 'hr'],
    'update_xml': [
        'security/hr_security.xml',
        'hr_attendance_view.xml',
        'hr_attendance_wizard.xml',
        'hr_attendance_report.xml',
        'security/ir.model.access.csv',
        'wizard/hr_attendance_bymonth_view.xml',
    ],
    'demo_xml': ['hr_attendance_demo.xml'],
    'installable': True,
    'active': False,
    'certificate': '0063495605613',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
