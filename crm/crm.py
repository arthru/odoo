# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-today OpenERP SA (<http://www.openerp.com>)
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
import base64
import tools

from osv import fields
from osv import osv
from tools.translate import _

MAX_LEVEL = 15
AVAILABLE_STATES = [
    ('draft', 'New'),
    ('cancel', 'Cancelled'),
    ('open', 'In Progress'),
    ('pending', 'Pending'),
    ('done', 'Closed')
]

AVAILABLE_PRIORITIES = [
    ('1', 'Highest'),
    ('2', 'High'),
    ('3', 'Normal'),
    ('4', 'Low'),
    ('5', 'Lowest'),
]

class crm_case_channel(osv.osv):
    _name = "crm.case.channel"
    _description = "Channels"
    _order = 'name'
    _columns = {
        'name': fields.char('Channel Name', size=64, required=True),
        'active': fields.boolean('Active'),
    }
    _defaults = {
        'active': lambda *a: 1,
    }

class crm_case_stage(osv.osv):
    """ Model for case stages. This models the main stages of a document
        management flow. Main CRM objects (leads, opportunities, project 
        issues, ...) will now use only stages, instead of state and stages.
        Stages are for example used to display the kanban view of records.
    """
    _name = "crm.case.stage"
    _description = "Stage of case"
    _rec_name = 'name'
    _order = "sequence"

    _columns = {
        'name': fields.char('Stage Name', size=64, required=True, translate=True),
        'sequence': fields.integer('Sequence', help="Used to order stages. Lower is better."),
        'probability': fields.float('Probability (%)', required=True, help="This percentage depicts the default/average probability of the Case for this stage to be a success"),
        'on_change': fields.boolean('Change Probability Automatically', help="Setting this stage will change the probability automatically on the opportunity."),
        'requirements': fields.text('Requirements'),
        'section_ids':fields.many2many('crm.case.section', 'section_stage_rel', 'stage_id', 'section_id', string='Sections',
                        help="Link between stages and sales teams. When set, this limitate the current stage to the selected sales teams."),
        'state': fields.selection(AVAILABLE_STATES, 'State', required=True, help="The related state for the stage. The state of your document will automatically change regarding the selected stage. For example, if a stage is related to the state 'Close', when your document reaches this stage, it will be automatically have the 'closed' state."),
        'case_default': fields.boolean('Common to All Teams', help="If you check this field, this stage will be proposed by default on each sales team. It will not assign this stage to existing teams."),
        'fold': fields.boolean('Hide in Views when Empty', help="This stage is not visible, for example in status bar or kanban view, when there are no records in that stage to display."),
    }

    _defaults = {
        'sequence': lambda *args: 1,
        'probability': lambda *args: 0.0,
        'state': 'draft',
        'fold': False,
    }

class crm_case_section(osv.osv):
    """ Model for sales teams. """
    _name = "crm.case.section"
    _description = "Sales Teams"
    _order = "complete_name"

    def get_full_name(self, cr, uid, ids, field_name, arg, context=None):
        return  dict(self.name_get(cr, uid, ids, context=context))

    _columns = {
        'name': fields.char('Sales Team', size=64, required=True, translate=True),
        'complete_name': fields.function(get_full_name, type='char', size=256, readonly=True, store=True),
        'code': fields.char('Code', size=8),
        'active': fields.boolean('Active', help="If the active field is set to "\
                        "true, it will allow you to hide the sales team without removing it."),
        'allow_unlink': fields.boolean('Allow Delete', help="Allows to delete non draft cases"),
        'change_responsible': fields.boolean('Reassign Escalated', help="When escalating to this team override the saleman with the team leader."),
        'user_id': fields.many2one('res.users', 'Team Leader'),
        'member_ids':fields.many2many('res.users', 'sale_member_rel', 'section_id', 'member_id', 'Team Members'),
        'reply_to': fields.char('Reply-To', size=64, help="The email address put in the 'Reply-To' of all emails sent by OpenERP about cases in this sales team"),
        'parent_id': fields.many2one('crm.case.section', 'Parent Team'),
        'child_ids': fields.one2many('crm.case.section', 'parent_id', 'Child Teams'),
        'resource_calendar_id': fields.many2one('resource.calendar', "Working Time", help="Used to compute open days"),
        'note': fields.text('Description'),
        'working_hours': fields.float('Working Hours', digits=(16,2 )),
        'stage_ids': fields.many2many('crm.case.stage', 'section_stage_rel', 'section_id', 'stage_id', 'Stages'),
    }
    
    def _get_stage_common(self, cr, uid, context):
        ids = self.pool.get('crm.case.stage').search(cr, uid, [('case_default','=',1)], context=context)
        return ids

    _defaults = {
        'active': lambda *a: 1,
        'allow_unlink': lambda *a: 1,
        'stage_ids': _get_stage_common
    }

    _sql_constraints = [
        ('code_uniq', 'unique (code)', 'The code of the sales team must be unique !')
    ]

    _constraints = [
        (osv.osv._check_recursion, 'Error ! You cannot create recursive Sales team.', ['parent_id'])
    ]

    def name_get(self, cr, uid, ids, context=None):
        """Overrides orm name_get method"""
        if not isinstance(ids, list) :
            ids = [ids]
        res = []
        if not ids:
            return res
        reads = self.read(cr, uid, ids, ['name', 'parent_id'], context)

        for record in reads:
            name = record['name']
            if record['parent_id']:
                name = record['parent_id'][1] + ' / ' + name
            res.append((record['id'], name))
        return res

class crm_case_categ(osv.osv):
    """ Category of Case """
    _name = "crm.case.categ"
    _description = "Category of Case"
    _columns = {
        'name': fields.char('Name', size=64, required=True, translate=True),
        'section_id': fields.many2one('crm.case.section', 'Sales Team'),
        'object_id': fields.many2one('ir.model', 'Object Name'),
    }

    def _find_object_id(self, cr, uid, context=None):
        """Finds id for case object"""
        object_id = context and context.get('object_id', False) or False
        ids = self.pool.get('ir.model').search(cr, uid, [('id', '=', object_id)])
        return ids and ids[0] or False

    _defaults = {
        'object_id' : _find_object_id
    }

class crm_case_resource_type(osv.osv):
    """ Resource Type of case """
    _name = "crm.case.resource.type"
    _description = "Campaign"
    _rec_name = "name"
    _columns = {
        'name': fields.char('Campaign Name', size=64, required=True, translate=True),
        'section_id': fields.many2one('crm.case.section', 'Sales Team'),
    }

class crm_base(object):
    """ Base utility mixin class for objects willing to manage their state.
        Object subclassing this class should define the following colums:
        - ``date_open`` (datetime field)
        - ``date_closed`` (datetime field)
        - ``user_id`` (many2one to res.users)
        - ``partner_id`` (many2one to res.partner)
        - ``state`` (selection field)
    """

    def onchange_partner_address_id(self, cr, uid, ids, add, email=False):
        """ This function returns value of partner email based on Partner Address
            :param add: Id of Partner's address
            :param email: Partner's email ID
        """
        data = {'value': {'email_from': False, 'phone':False}}
        if add:
            address = self.pool.get('res.partner').browse(cr, uid, add)
            data['value'] = {'email_from': address and address.email or False ,
                             'phone':  address and address.phone or False}
        if 'phone' not in self._columns:
            del data['value']['phone']
        return data

    def onchange_partner_id(self, cr, uid, ids, part, email=False):
        """ This function returns value of partner address based on partner
            :param part: Partner's id
            :param email: Partner's email ID
        """
        data={}
        if  part:
            addr = self.pool.get('res.partner').address_get(cr, uid, [part], ['contact'])
            data.update(self.onchange_partner_address_id(cr, uid, ids, addr['contact'])['value'])
        return {'value': data}

    def case_open(self, cr, uid, ids, context=None):
        """ Opens case """
        cases = self.browse(cr, uid, ids, context=context)
        for case in cases:
            values = {'active': True}
            if case.state == 'draft':
                values['date_open'] = fields.datetime.now()
            if not case.user_id:
                values['user_id'] = uid
            self.case_set(cr, uid, [case.id], 'open', values, context=context)
            self.case_open_send_note(cr, uid, [case.id], context=context)
        return True

    def case_close(self, cr, uid, ids, context=None):
        """ Closes case """
        self.case_set(cr, uid, ids, 'done', {'date_closed': fields.datetime.now()}, context=context)
        self.case_close_send_note(cr, uid, ids, context=context)
        return True

    def case_cancel(self, cr, uid, ids, context=None):
        """ Cancels case """
        self.case_set(cr, uid, ids, 'cancel', {'active': True}, context=context)
        self.case_cancel_send_note(cr, uid, ids, context=context)
        return True

    def case_pending(self, cr, uid, ids, context=None):
        """ Sets case as pending """
        self.case_set(cr, uid, ids, 'pending', {'active': True}, context=context)
        self.case_pending_send_note(cr, uid, ids, context=context)
        return True

    def case_reset(self, cr, uid, ids, context=None):
        """ Resets case as draft """
        self.case_set(cr, uid, ids, 'draft', {'active': True}, context=context)
        self.case_close_send_note(cr, uid, ids, context=context)
        return True
    
    def case_set(self, cr, uid, ids, state_name, update_values=None, context=None):
        """ Generic method for setting case. This methods wraps the update
            of the record, as well as call to _action and browse record
            case setting.
            
            :params: state_name: the new value of the state, such as 
                     'draft' or 'close'.
            :params: update_values: values that will be added with the state
                     update when writing values to the record.
        """
        cases = self.browse(cr, uid, ids, context=context)
        cases[0].state # fill browse record cache, for _action having old and new values
        if update_values is None:
            update_values = {}
        update_values.update({'state': state_name})
        self.write(cr, uid, ids, update_values, context=context)
        self._action(cr, uid, cases, state_name, context=context)

    def _action(self, cr, uid, cases, state_to, scrit=None, context=None):
        if context is None:
            context = {}
        context['state_to'] = state_to
        rule_obj = self.pool.get('base.action.rule')
        model_obj = self.pool.get('ir.model')
        model_ids = model_obj.search(cr, uid, [('model','=',self._name)])
        rule_ids = rule_obj.search(cr, uid, [('model_id','=',model_ids[0])])
        return rule_obj._action(cr, uid, rule_ids, cases, scrit=scrit, context=context)
    
    # ******************************
    # Notifications
    # ******************************
    
	def case_get_note_msg_prefix(self, cr, uid, id, context=None):
		return ''
	
    def case_open_send_note(self, cr, uid, ids, context=None):
        for id in ids:
            msg = _('%s has been <b>opened</b>.') % (self.case_get_note_msg_prefix(cr, uid, id, context=context))
            self.message_append_note(cr, uid, [id], body=msg, context=context)
        return True

    def case_close_send_note(self, cr, uid, ids, context=None):
        for id in ids:
            msg = _('%s has been <b>closed</b>.') % (self.case_get_note_msg_prefix(cr, uid, id, context=context))
            self.message_append_note(cr, uid, [id], body=msg, context=context)
        return True

    def case_cancel_send_note(self, cr, uid, ids, context=None):
        for id in ids:
            msg = _('%s has been <b>canceled</b>.') % (self.case_get_note_msg_prefix(cr, uid, id, context=context))
            self.message_append_note(cr, uid, [id], body=msg, context=context)
        return True

    def case_pending_send_note(self, cr, uid, ids, context=None):
        for id in ids:
            msg = _('%s is now <b>pending</b>.') % (self.case_get_note_msg_prefix(cr, uid, id, context=context))
            self.message_append_note(cr, uid, [id], body=msg, context=context)
        return True

    def case_reset_send_note(self, cr, uid, ids, context=None):
        for id in ids:
            msg = _('%s has been <b>renewed</b>.') % (self.case_get_note_msg_prefix(cr, uid, id, context=context))
            self.message_append_note(cr, uid, [id], body=msg, context=context)
        return True

class crm_case(object):
    """ Base utility mixin class for objects willing to manage their stages.
        Object that inherit from this class should inherit from mailgate.thread
        to have access to the mail gateway, as well as Chatter. Objects 
        subclassing this class should define the following colums:
        - ``date_open`` (datetime field)
        - ``date_closed`` (datetime field)
        - ``user_id`` (many2one to res.users)
        - ``partner_id`` (many2one to res.partner)
        - ``stage_id`` (many2one to a stage definition model)
        - ``state`` (selection field, related to the stage_id.state)
    """

    def _get_default_partner(self, cr, uid, context=None):
        """ Gives id of partner for current user
            :param context: if portal in context is false return false anyway
        """
        if context is None:
            context = {}
        if not context.get('portal', False):
            return False
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        if hasattr(user, 'partner_address_id') and user.partner_address_id:
            return user.partner_address_id
        return user.company_id.partner_id.id

    def _get_default_email(self, cr, uid, context=None):
        """ Gives default email address for current user
            :param context: if portal in context is false return false anyway
        """
        if not context.get('portal', False):
            return False
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        return user.user_email

    def _get_default_user(self, cr, uid, context=None):
        """ Gives current user id
            :param context: if portal in context is false return false anyway
        """
        if context and context.get('portal', False):
            return False
        return uid

    def onchange_partner_address_id(self, cr, uid, ids, add, email=False):
        """ This function returns value of partner email based on Partner Address
            :param add: Id of Partner's address
            :param email: Partner's email ID
        """
        data = {'value': {'email_from': False, 'phone':False}}
        if add:
            address = self.pool.get('res.partner').browse(cr, uid, add)
            data['value'] = {'email_from': address and address.email or False ,
                             'phone':  address and address.phone or False}
        if 'phone' not in self._columns:
            del data['value']['phone']
        return data

    def onchange_partner_id(self, cr, uid, ids, part, email=False):
        """ This function returns value of partner address based on partner
            :param part: Partner's id
            :param email: Partner's email ID
        """
        data={}
        if  part:
            addr = self.pool.get('res.partner').address_get(cr, uid, [part], ['contact'])
            data.update(self.onchange_partner_address_id(cr, uid, ids, addr['contact'])['value'])
        return {'value': data}

    def _get_default_section(self, cr, uid, context=None):
        """ Gives default section by checking if present in the context """
        if context is None:
            context = {}
        if context.get('portal', False):
            return False
        if type(context.get('default_section_id')) in (int, long):
            return context.get('default_section_id')
        if isinstance(context.get('default_section_id'), basestring):
            section_name = context['default_section_id']
            section_ids = self.pool.get('crm.case.section').name_search(cr, uid, name=section_name, context=context)
            if len(section_ids) == 1:
                return section_ids[0][0]
        return False

    def _get_default_stage_id(self, cr, uid, context=None):
        """ Gives default stage_id """
        section_id = self._get_default_section(cr, uid, context=context)
        return self.stage_find(cr, uid, section_id, [('state', '=', 'draft')], context=context)
    
    def stage_find(self, cr, uid, section_id, domain=[], order='sequence', context=None):
        """ Find stage, within a sales team, with a domain on the search,
            ordered by the order parameter. If several stages match the 
            search criterions, the first one will be returned, according
            to the requested search order.
            :param section_id: if set, the search is limited to stages that
                               belongs to the given sales team, or that are
                               global (case_default flag set to True)
            :param domain: a domain on the search of stages
            :param order: order of the search
        """
        domain = list(domain)
        if section_id:
            domain += ['|', ('section_ids', '=', section_id), ('case_default', '=', True)]
        stage_ids = self.pool.get('crm.case.stage').search(cr, uid, domain, order=order, context=context)
        if stage_ids:
            return stage_ids[0]
        return False

    def stage_set_with_state_name(self, cr, uid, cases, state_name, context=None):
        """ Set a new stage, with a state_name instead of a stage_id
            :param cases: browse_record of cases
        """
        if isinstance(cases, (int, long)):
            cases = self.browse(cr, uid, cases, context=context)
        for case in cases:
            section_id = case.section_id.id if case.section_id else None
            stage_id = self.stage_find(cr, uid, section_id, [('state', '=', state_name)], context=context)
            if stage_id:
                self.stage_set(cr, uid, [case.id], stage_id, context=context)
        return True

    def stage_set(self, cr, uid, ids, stage_id, context=None):
        value = {}
        if hasattr(self,'onchange_stage_id'):
            value = self.onchange_stage_id(cr, uid, ids, stage_id)['value']
        value['stage_id'] = stage_id
        return self.write(cr, uid, ids, value, context=context)

    def stage_change(self, cr, uid, ids, op, order, context=None):
        for case in self.browse(cr, uid, ids, context=context):
            seq = 0
            if case.stage_id:
                seq = case.stage_id.sequence
            section_id = None
            if case.section_id:
                section_id = case.section_id.id
            next_stage_id = self.stage_find(cr, uid, section_id, [('sequence',op,seq)],order)
            if next_stage_id:
                return self.stage_set(cr, uid, [case.id], next_stage_id, context=context)
        return False

    def stage_next(self, cr, uid, ids, context=None):
        """ This function computes next stage for case from its current stage
            using available stage for that case type
        """
        return self.stage_change(cr, uid, ids, '>','sequence', context)

    def stage_previous(self, cr, uid, ids, context=None):
        """ This function computes previous stage for case from its current
            stage using available stage for that case type
        """
        return self.stage_change(cr, uid, ids, '<', 'sequence desc', context)

    def copy(self, cr, uid, id, default=None, context=None):
        """ Overrides orm copy method to avoid copying messages,
            as well as date_closed and date_open columns if they
            exist."""
        if default is None:
            default = {}

        if hasattr(self, '_columns'):
            if self._columns.get('date_closed'):
                default.update({ 'date_closed': False, })
            if self._columns.get('date_open'):
                default.update({ 'date_open': False })
        return super(crm_case, self).copy(cr, uid, id, default, context=context)

    def case_escalate(self, cr, uid, ids, context=None):
        """ Escalates case to parent level """
        cases = self.browse(cr, uid, ids, context=context)
        cases[0].state # fill browse record cache, for _action having old and new values
        for case in cases:
            data = {'active': True}
            if case.section_id.parent_id:
                data['section_id'] = case.section_id.parent_id.id
                if case.section_id.parent_id.change_responsible:
                    if case.section_id.parent_id.user_id:
                        data['user_id'] = case.section_id.parent_id.user_id.id
            else:
                raise osv.except_osv(_('Error !'), _('You can not escalate, you are already at the top level regarding your sales-team category.'))
            self.write(cr, uid, [case.id], data)
            case.case_escalate_send_note(case.section_id.parent_id, context=context)
        cases = self.browse(cr, uid, ids, context=context)
        self._action(cr, uid, cases, 'escalate', context=context)
        return True

    def case_open(self, cr, uid, ids, context=None):
        """ Opens case """
        cases = self.browse(cr, uid, ids, context=context)
        for case in cases:
            data = {'active': True}
            if case.stage_id and case.stage_id.state == 'draft':
                 data['date_open'] = fields.datetime.now()
            if not case.user_id:
                data['user_id'] = uid
            self.case_set(cr, uid, [case.id], 'open', data, context=context)
            self.case_open_send_note(cr, uid, [case.id], context=context)
        return True
        
    def case_close(self, cr, uid, ids, context=None):
        """ Closes case """
        self.case_set(cr, uid, ids, 'done', {'active': True, 'date_closed': fields.datetime.now()}, context=context)
        self.case_close_send_note(cr, uid, ids, context=context)
        return True

    def case_cancel(self, cr, uid, ids, context=None):
        """ Cancels case """
        self.case_set(cr, uid, ids, 'cancel', {'active': True}, context=context)
        self.case_cancel_send_note(cr, uid, ids, context=context)
        return True

    def case_pending(self, cr, uid, ids, context=None):
        """ Set case as pending """
        self.case_set(cr, uid, ids, 'pending', {'active': True}, context=context)
        self.case_pending_send_note(cr, uid, ids, context=context)
        return True

    def case_reset(self, cr, uid, ids, context=None):
        """ Resets case as draft """
        self.case_set(cr, uid, ids, 'draft', {'active': True}, context=context)
        self.case_reset_send_note(cr, uid, ids, context=context)
        return True

    def case_set(self, cr, uid, ids, new_state_name=None, values_to_update=None, new_stage_id=None, context=None):
        """ TODO """
        cases = self.browse(cr, uid, ids, context=context)
        cases[0].state # fill browse record cache, for _action having old and new values
        # 1. update the stage
        if new_state_name:
            self.stage_set_with_state_name(cr, uid, cases, new_state_name, context=context)
        elif not (new_stage_id is None):
            self.stage_set(cr, uid, ids, new_stage_id, context=context)
        # 2. update values
        if values_to_update:
            self.write(cr, uid, ids, values_to_update, context=context)
        # 3. call _action for base action rule
        if new_state_name:
            self._action(cr, uid, cases, new_state_name, context=context)
        elif not (new_stage_id is None):
            stage = self.pool.get('crm.case.stage').browse(cr, uid, [new_stage_id], context=context)[0]
            new_state_name = stage.state
            self._action(cr, uid, cases, new_state_name, context=context)
        return True

    def _action(self, cr, uid, cases, state_to, scrit=None, context=None):
        if context is None:
            context = {}
        context['state_to'] = state_to
        rule_obj = self.pool.get('base.action.rule')
        model_obj = self.pool.get('ir.model')
        model_ids = model_obj.search(cr, uid, [('model','=',self._name)])
        rule_ids = rule_obj.search(cr, uid, [('model_id','=',model_ids[0])])
        return rule_obj._action(cr, uid, rule_ids, cases, scrit=scrit, context=context)

    def remind_partner(self, cr, uid, ids, context=None, attach=False):
        return self.remind_user(cr, uid, ids, context, attach,
                destination=False)

    def remind_user(self, cr, uid, ids, context=None, attach=False, destination=True):
        mail_message = self.pool.get('mail.message')
        for case in self.browse(cr, uid, ids, context=context):
            if not destination and not case.email_from:
                return False
            if not case.user_id.user_email:
                return False
            if destination and case.section_id.user_id:
                case_email = case.section_id.user_id.user_email
            else:
                case_email = case.user_id.user_email

            src = case_email
            dest = case.user_id.user_email or ""
            body = case.description or ""
            for message in case.message_ids:
                if message.email_from and message.body_text:
                    body = message.body_text
                    break

            if not destination:
                src, dest = dest, case.email_from
                if body and case.user_id.signature:
                    if body:
                        body += '\n\n%s' % (case.user_id.signature)
                    else:
                        body = '\n\n%s' % (case.user_id.signature)

            body = self.format_body(body)

            attach_to_send = {}

            if attach:
                attach_ids = self.pool.get('ir.attachment').search(cr, uid, [('res_model', '=', self._name), ('res_id', '=', case.id)])
                attach_to_send = self.pool.get('ir.attachment').read(cr, uid, attach_ids, ['datas_fname', 'datas'])
                attach_to_send = dict(map(lambda x: (x['datas_fname'], base64.decodestring(x['datas'])), attach_to_send))

            # Send an email
            subject = "Reminder: [%s] %s" % (str(case.id), case.name, )
            mail_message.schedule_with_attach(cr, uid,
                src,
                [dest],
                subject,
                body,
                model=self._name,
                reply_to=case.section_id.reply_to,
                res_id=case.id,
                attachments=attach_to_send,
                context=context
            )
        return True

    def _check(self, cr, uid, ids=False, context=None):
        """Function called by the scheduler to process cases for date actions
           Only works on not done and cancelled cases
        """
        cr.execute('select * from crm_case \
                where (date_action_last<%s or date_action_last is null) \
                and (date_action_next<=%s or date_action_next is null) \
                and state not in (\'cancel\',\'done\')',
                (time.strftime("%Y-%m-%d %H:%M:%S"),
                    time.strftime('%Y-%m-%d %H:%M:%S')))

        ids2 = map(lambda x: x[0], cr.fetchall() or [])
        cases = self.browse(cr, uid, ids2, context=context)
        return self._action(cr, uid, cases, False, context=context)

    def format_body(self, body):
        return self.pool.get('base.action.rule').format_body(body)

    def format_mail(self, obj, body):
        return self.pool.get('base.action.rule').format_mail(obj, body)

    def message_thread_followers(self, cr, uid, ids, context=None):
        res = {}
        for case in self.browse(cr, uid, ids, context=context):
            l=[]
            if case.email_cc:
                l.append(case.email_cc)
            if case.user_id and case.user_id.user_email:
                l.append(case.user_id.user_email)
            res[case.id] = l
        return res
    
    # ******************************
    # Notifications
    # ******************************
    
	def case_get_note_msg_prefix(self, cr, uid, id, context=None):
		return ''
	
    def case_open_send_note(self, cr, uid, ids, context=None):
        for id in ids:
            msg = _('%s has been <b>opened</b>.') % (self.case_get_note_msg_prefix(cr, uid, id, context=context))
            self.message_append_note(cr, uid, [id], body=msg, context=context)
        return True

    def case_close_send_note(self, cr, uid, ids, context=None):
        for id in ids:
            msg = _('%s has been <b>closed</b>.') % (self.case_get_note_msg_prefix(cr, uid, id, context=context))
            self.message_append_note(cr, uid, [id], body=msg, context=context)
        return True

    def case_cancel_send_note(self, cr, uid, ids, context=None):
        for id in ids:
            msg = _('%s has been <b>canceled</b>.') % (self.case_get_note_msg_prefix(cr, uid, id, context=context))
            self.message_append_note(cr, uid, [id], body=msg, context=context)
        return True

    def case_pending_send_note(self, cr, uid, ids, context=None):
        for id in ids:
            msg = _('%s is now <b>pending</b>.') % (self.case_get_note_msg_prefix(cr, uid, id, context=context))
            self.message_append_note(cr, uid, [id], body=msg, context=context)
        return True

    def case_reset_send_note(self, cr, uid, ids, context=None):
        for id in ids:
            msg = _('%s has been <b>renewed</b>.') % (self.case_get_note_msg_prefix(cr, uid, id, context=context))
            self.message_append_note(cr, uid, [id], body=msg, context=context)
        return True
    
    def case_escalate_send_note(self, cr, uid, ids, new_section=None, context=None):
        for id in ids:
            if new_section:
                msg = '%s has been <b>escalated</b> to <b>%s</b>.' % (self.case_get_note_msg_prefix(cr, uid, id, context=context), new_section.name)
            else:
                msg = '%s has been <b>escalated</b>.' % (self.case_get_note_msg_prefix(cr, uid, id, context=context))
            self.message_append_note(cr, uid, [id], 'System Notification', msg, context=context)
        return True

def _links_get(self, cr, uid, context=None):
    """Gets links value for reference field"""
    obj = self.pool.get('res.request.link')
    ids = obj.search(cr, uid, [])
    res = obj.read(cr, uid, ids, ['object', 'name'], context)
    return [(r['object'], r['name']) for r in res]

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
