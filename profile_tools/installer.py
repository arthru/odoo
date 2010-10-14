# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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
from osv import fields, osv

class misc_tools_installer(osv.osv_memory):
    _name = 'misc_tools.installer'
    _inherit = 'res.config.installer'

    _columns = {
        'lunch':fields.boolean('Lunch',help='A simple module to help you to manage Lunch orders.'),
        'subscription':fields.boolean('Recurring Documents',help='Helps to generate automatically recurring documents.'),
        'survey':fields.boolean('Survey',help='Allows you to organize surveys.'),
        'idea':fields.boolean('Ideas Box',help='Promote ideas of the employees, votes and discussion on best ideas.'),
    }
    _defaults = {
        'lunch': True,
    }
misc_tools_installer()

