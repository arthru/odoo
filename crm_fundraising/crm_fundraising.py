#-*- coding: utf-8 -*-
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

from osv import fields, osv, orm
from crm import crm

class crm_fundraising(osv.osv, crm.crm_case):
    """ Fund Raising Cases """

    _name = "crm.fundraising"
    _description = "Fund Raising Cases"
    _order = "id desc"
    _inherits = {'mailgate.thread': 'thread_id'}
    

    _columns = {
            'thread_id': fields.many2one('mailgate.thread', 'Thread', required=False), 
            'id': fields.integer('ID'), 
            'name': fields.char('Name', size=128, required=True),
            'active': fields.boolean('Active', required=False), 
            'date_action_last': fields.datetime('Last Action', readonly=1),
            'date_action_next': fields.datetime('Next Action', readonly=1), 
            'description': fields.text('Description'), 
            'create_date': fields.datetime('Creation Date' , readonly=True), 
            'write_date': fields.datetime('Update Date' , readonly=True), 
            'date_deadline': fields.date('Deadline'), 
            'user_id': fields.many2one('res.users', 'Responsible'), 
            'section_id': fields.many2one('crm.case.section', 'Sales Team', \
                            select=True, help='Sales team to which Case belongs to. Define Responsible user and Email account for mail gateway.'), 
            'company_id': fields.many2one('res.company', 'Company'), 
            'partner_id': fields.many2one('res.partner', 'Partner'), 
            'partner_address_id': fields.many2one('res.partner.address', 'Partner Contact', \
                                 domain="[('partner_id','=',partner_id)]"), 
            'email_cc': fields.text('Watchers Emails', size=252 , help="These people will receive a copy of the future communication between partner and users by email"), 
            'email_from': fields.char('Email', size=128, help="These people will receive email."), 
            'date_closed': fields.datetime('Closed', readonly=True), 
            'date': fields.datetime('Date'), 
            'priority': fields.selection(crm.AVAILABLE_PRIORITIES, 'Priority'), 
            'categ_id': fields.many2one('crm.case.categ', 'Category', \
                                domain="[('section_id','=',section_id),\
                                ('object_id.model', '=', 'crm.fundraising')]"), 
            'planned_revenue': fields.float('Planned Revenue'), 
            'planned_cost': fields.float('Planned Costs'), 
            'probability': fields.float('Probability (%)'), 
            'partner_name': fields.char("Employee's Name", size=64), 
            'partner_name2': fields.char('Employee Email', size=64), 
            'partner_phone': fields.char('Phone', size=32), 
            'partner_mobile': fields.char('Mobile', size=32), 
            'stage_id': fields.many2one ('crm.case.stage', 'Stage', \
                             domain="[('section_id','=',section_id),\
                            ('object_id.model', '=', 'crm.fundraising')]"), 
            'type_id': fields.many2one('crm.case.resource.type', 'Fundraising Type', \
                             domain="[('section_id','=',section_id),\
                             ('object_id.model', '=', 'crm.fundraising')]"), 
            'duration': fields.float('Duration'), 
            'ref': fields.reference('Reference', selection=crm._links_get, size=128), 
            'ref2': fields.reference('Reference 2', selection=crm._links_get, size=128), 
            'canal_id': fields.many2one('res.partner.canal', 'Channel', \
                        help="The channels represent the different communication "\
                        "modes available with the customer." \
                       " With each commercial opportunity, you can indicate\
                     the canall which is this opportunity source."), 
            'som': fields.many2one('res.partner.som', 'State of Mind', \
                         help="The minds states allow to define a value scale which represents" \
                              "the partner mentality in relation to our services.The scale has" \
                            "to be created with a factor for each level from 0 \
                             (Very dissatisfied) to 10 (Extremely satisfied)."), 
            'state': fields.selection(crm.AVAILABLE_STATES, 'State', size=16, readonly=True, 
                                  help='The state is set to \'Draft\', when a case is created.\
                                  \nIf the case is in progress the state is set to \'Open\'.\
                                  \nWhen the case is over, the state is set to \'Done\'.\
                                  \nIf the case needs to be reviewed then the state is set to \'Pending\'.'), 
        }

    _defaults = {
            'active': lambda *a: 1, 
            'user_id': crm.crm_case._get_default_user, 
            'partner_id': crm.crm_case._get_default_partner, 
            'partner_address_id': crm.crm_case._get_default_partner_address, 
            'email_from': crm.crm_case. _get_default_email, 
            'state': lambda *a: 'draft', 
            'section_id': crm.crm_case. _get_section, 
            'company_id': lambda s, cr, uid, c: s.pool.get('res.company')._company_default_get(cr, uid, 'crm.case', context=c), 
            'priority': lambda *a: crm.AVAILABLE_PRIORITIES[2][0], 
            'probability': lambda *a:0.0, 
            'planned_cost': lambda *a:0.0, 
            'planned_revenue': lambda *a:0.0, 
            }

crm_fundraising()
