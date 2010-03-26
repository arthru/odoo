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

from osv import fields, osv
import crm
from datetime import datetime, timedelta
from datetime import datetime, timedelta
from tools.translate import _
from base_calendar import base_calendar

class crm_opportunity(osv.osv):
    _name = 'crm.opportunity'
crm_opportunity()


class crm_phonecall(osv.osv):
    """ CRM Phonecall """

    _name = 'crm.phonecall'

crm_phonecall()


class crm_meeting(osv.osv):
    """ CRM Meeting Cases """

    _name = 'crm.meeting'
    _description = "Meeting Cases"
    _order = "id desc"
    _inherit = ["crm.case", "calendar.event"]

    _columns = {
        'categ_id': fields.many2one('crm.case.categ', 'Meeting Type', \
                        domain="[('object_id.model', '=', 'crm.meeting')]", \
            ),
        'phonecall_id': fields.many2one ('crm.phonecall', 'Phonecall'),
        'opportunity_id': fields.many2one ('crm.opportunity', 'Opportunity'),
        'attendee_ids': fields.many2many('calendar.attendee', 'event_attendee_rel',\
                                 'event_id', 'attendee_id', 'Attendees'),
        'date_closed': fields.datetime('Closed', readonly=True),
        'date_deadline': fields.datetime('Deadline'),
        'state': fields.selection([('open', 'Confirmed'),
                                    ('draft', 'Unconfirmed'),
                                    ('cancel', 'Cancelled'),
                                    ('done', 'Done')], 'State', \
                                    size=16, readonly=True)
    }

    _defaults = {
        'state': lambda *a: 'draft',
    }
    
    def open_meeting(self, cr, uid, ids, context=None):
        """
        Open Crm Meeting Form for Crm Meeting.
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of crm meeting’s IDs
        @param context: A standard dictionary for contextual values
        @return: Dictionary value which open Crm Meeting form.
        """
        if not context:
            context = {}
            
        data_obj = self.pool.get('ir.model.data')
        
        value = {}
        
        id2 = data_obj._get_id(cr, uid, 'crm', 'crm_case_form_view_meet')
        id3 = data_obj._get_id(cr, uid, 'crm', 'crm_case_tree_view_meet')
        id4 = data_obj._get_id(cr, uid, 'crm', 'crm_case_calendar_view_meet')
        if id2:
            id2 = data_obj.browse(cr, uid, id2, context=context).res_id
        if id3:
            id3 = data_obj.browse(cr, uid, id3, context=context).res_id
        if id4:
            id4 = data_obj.browse(cr, uid, id4, context=context).res_id
        for id in ids:
            value = {
                    'name': _('Meeting'), 
                    'view_type': 'form', 
                    'view_mode': 'form,tree', 
                    'res_model': 'crm.meeting', 
                    'view_id': False, 
                    'views': [(id2, 'form'), (id3, 'tree'), (id4, 'calendar')],
                    'type': 'ir.actions.act_window', 
                    'res_id': base_calendar.base_calendar_id2real_id(id), 
                    'nodestroy': True
                    }
        
        return value

crm_meeting()

class calendar_attendee(osv.osv):
    """ Calendar Attendee """

    _inherit = 'calendar.attendee'
    _description = 'Calendar Attendee'

    def _compute_data(self, cr, uid, ids, name, arg, context):

       """
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of compute data’s IDs
        @param context: A standard dictionary for contextual values

        """

       name = name[0]
       result = super(calendar_attendee, self)._compute_data(cr, uid, ids, name, arg, context)

       for attdata in self.browse(cr, uid, ids, context=context):
            id = attdata.id
            result[id] = {}
            if name == 'categ_id':
                if attdata.ref:
                    result[id][name] = (attdata.ref.categ_id.id, attdata.ref.categ_id.name,)
                else:
                    result[id][name] = False
       return result

    _columns = {
        'categ_id': fields.function(_compute_data, method=True, \
                        string='Event Type', type="many2one", \
                        relation="crm.case.categ", multi='categ_id'),
    }

calendar_attendee()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
