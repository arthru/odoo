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

from caldav import common
from osv import fields, osv
import datetime
import base64
import re
import time
import tools
from tools.translate import _
from dateutil import parser

class crm_meeting(osv.osv):
    _name = 'crm.meeting'
    _description = "Meeting Cases"
    _order = "id desc"
    _inherits = {'crm.case': "inherit_case_id"}
    __attribute__ = {
        'class': {'field': 'class', 'type': 'selection'},
        'created': {'field': 'create_date', 'type': 'datetime'}, # keep none for now
        'description': {'field': 'description', 'type': 'text'},
        'dtstart': {'field': 'date', 'type': 'datetime'},
        'location': {'field': 'location', 'type': 'text'},
        #'organizer': {'field': 'partner_id', 'sub-field': 'name', 'type': 'many2one'},
        'priority': {'field': 'priority', 'type': 'int'},
        'dtstamp' : {'field': 'date', 'type': 'datetime'},
        'seq': None,
        'status': {'field': 'state', 'type': 'selection', 'mapping': {'tentative': 'draft', \
                                                  'confirmed': 'open' , 'cancelled': 'cancel'}},
        'summary': {'field': 'name', 'type': 'text'},
        'transp': {'field': 'transparent', 'type': 'text'},
        'uid': {'field': 'id', 'type': 'text'},
        'url': {'field': 'caldav_url', 'type': 'text'},
        'recurid': None,
#        'attach': {'field': 'attachment_ids', 'sub-field': 'datas', 'type': 'list'},
        'attendee': {'field': 'attendees', 'type': 'text'},
#        'categories': {'field': 'categ_id', 'sub-field': 'name'},
        'categories': {'field': 'categ_id', 'type': 'many2one', 'object': 'crm.case.categ'},
        'comment': None,
        'contact': None,
        'exdate' : {'field': 'exdate', 'type': 'datetime'},
        'exrule' : {'field': 'exrule', 'type': 'text'},
        'rstatus': None,
        'related': None,
        'resources': None,
        'rdate': None,
        'rrule': {'field': 'rrule', 'type': 'text'},
        'x-openobject-model': {'value': _name, 'type': 'text'},
#        'duration': {'field': 'duration'},
        'dtend': {'field': 'date_deadline', 'type': 'datetime'}, 
        'valarm': {'field': 'alarms', 'type': 'text'}, 

    }
    
    def _get_data(self, cr, uid, ids, name, arg, context):        
        result = {}
        attendee_obj = self.pool.get('calendar.attendee')
        alarm_obj = self.pool.get('calendar.alarm')
        model_obj = self.pool.get('ir.model')
        model_id = model_obj.search(cr, uid, [('model','=',self._name)])[0]
        for meeting_id in ids:
            result[meeting_id] = {}            
            if "attendees" in name:
                attendee_ids = attendee_obj.search(cr, uid, [('ref','=','%s,%d'%(self._name, meeting_id))])
                result[meeting_id]["attendees"] = attendee_obj.export_cal(cr, uid, attendee_ids)
            if "alarms" in name:                
                alarm_ids = alarm_obj.search(cr, uid, [('model_id','=',model_id), ('res_id','=',meeting_id)])
                result[meeting_id]["alarms"] = alarm_obj.export_cal(cr, uid, alarm_ids)         
        return result

    def _set_data(self, cr, uid, meeting_id, name, value, arg, context):
        if not value:
            return         
        attendee_obj = self.pool.get('calendar.attendee')
        model_obj = self.pool.get('ir.model')
        alarm_obj = self.pool.get('calendar.alarm')
        eventdata = self.read(cr, uid, meeting_id, [name], context=context)
        if name == "attendees":
            attendee_ids = attendee_obj.import_cal(cr, uid, eventdata['attendees'])
            vals = {
                'ref':'%s,%d'%('crm.meeting', meeting_id)
            }
            attendee_obj.write(cr, uid, attendee_ids, vals)
        if name == "alarms": 
            model_id = model_obj.search(cr, uid, [('model','=',self._name)])[0]
            alarm_ids = alarm_obj.import_cal(cr, uid, eventdata['alarms'])
            vals = {
                'res_id' : meeting.id,                    
                'model_id' : model_id,
            }
            alarm_obj.write(cr, uid, alarm_ids, vals)
            alarm = alarm_obj.browse(cr, uid, alarm_ids)[0]
            self.write(cr, uid, [meeting_id], {'alarm_id':alarm.alarm_id})
        return True

    _columns = {
        'inherit_case_id': fields.many2one('crm.case', 'Case', ondelete='cascade'),
        'class': fields.selection([('public', 'Public'), ('private', 'Private'), \
                 ('confidential', 'Confidential')], 'Privacy'),
        'location': fields.char('Location', size=264, help="Gives Location of Meeting"),
        'freebusy': fields.text('FreeBusy'),
        'show_as': fields.selection([('free', 'Free'), \
                                  ('busy', 'Busy')],
                                   'show_as'),
        'caldav_url': fields.char('Caldav URL', size=264),
        'exdate': fields.text('Exception Date/Times', help="This property defines the list\
                 of date/time exceptions for arecurring calendar component."),
        'exrule': fields.char('Exception Rule', size=352, help="defines a rule or repeating pattern\
                                 for anexception to a recurrence set"),
        'rrule': fields.char('Recurrent Rule', size=352, invisible="True"),
        'rrule_type' : fields.selection([('none', 'None'), ('daily', 'Daily'), \
                 ('weekly', 'Weekly'), ('monthly', 'Monthly'), ('yearly', 'Yearly'), ('custom','Custom')], 'Recurrency'), 
        'attendees': fields.function(_get_data, method=True,\
                fnct_inv=_set_data, string='Attendees', type="text", multi='attendees'), 
        'alarms': fields.function(_get_data, method=True,\
                fnct_inv=_set_data, string='Attendees', type="text", multi='alarms'),
        'alarm_id': fields.many2one('res.alarm', 'Alarm'),
    }

    _defaults = {
         'class': lambda *a: 'public',
         'show_as' : lambda *a : 'busy',          
    }

    def do_alarm_create(self, cr, uid, ids, context={}):
        alarm_obj = self.pool.get('calendar.alarm')
        model_obj = self.pool.get('ir.model')
        attendee_obj = self.pool.get('calendar.attendee')
        model_id = model_obj.search(cr, uid, [('model','=',self._name)])[0]

        for meeting in self.browse(cr, uid, ids):
            self.do_alarm_unlink(cr, uid, [meeting.id])
            attendee_ids = attendee_obj.search(cr, uid, [('ref','=','%s,%d'%(self._name, meeting.id))])
            basic_alarm = meeting.alarm_id
            if basic_alarm:
                vals = {
                    'action': 'display', 
                    'description': meeting.description, 
                    'name': meeting.name, 
                    'attendee_ids': [(6,0, attendee_ids)],
                    'trigger_related': basic_alarm.trigger_related, 
                    'trigger_duration': basic_alarm.trigger_duration, 
                    'trigger_occurs': basic_alarm.trigger_occurs, 
                    'trigger_interval': basic_alarm.trigger_interval, 
                    'duration': basic_alarm.duration, 
                    'repeat': basic_alarm.repeat, 
                    'state' : 'run',
                    'event_date' : meeting.date,
                    'event_end_date' : meeting.date_deadline, 
                    'res_id' : meeting.id,                    
                    'model_id' : model_id,
                    'user_id' : uid              
                 }       
                alarm_id = alarm_obj.create(cr, uid, vals)
        cr.commit()
        return True

    def do_alarm_unlink(self, cr, uid, ids, context={}):
        alarm_obj = self.pool.get('calendar.alarm')
        model_obj = self.pool.get('ir.model')
        model_id = model_obj.search(cr, uid, [('model','=',self._name)])[0]
        for meeting in self.browse(cr, uid, ids):
            alarm_ids = alarm_obj.search(cr, uid, [('model_id','=',model_id), ('res_id','=',meeting.id)])
            if alarm_ids and len(alarm_ids):
                alarm_obj.unlink(cr, uid, alarm_ids)                
        cr.commit()
        return True

    def on_change_duration(self, cr, uid, id, date, duration):
        if not date:
            return {}
        start_date = datetime.datetime.strptime(date, "%Y-%m-%d %H:%M:%S")
        if duration >= 0 :
            end = start_date + datetime.timedelta(hours=duration)
        if duration < 0:
            raise osv.except_osv(_('Warning !'),
                    _('You can not set negative Duration.'))
        res = {'value' : {'date_deadline' : end.strftime('%Y-%m-%d %H:%M:%S')}}
        return res

    def export_cal(self, cr, uid, ids, context={}):
        crm_data = self.read(cr, uid, ids)
        event_obj = self.pool.get('basic.calendar.event')
        event_obj.__attribute__.update(self.__attribute__)

        ical = event_obj.export_ical(cr, uid, crm_data, {'model': self._name})
        cal_val = ical.serialize()
        cal_val = cal_val.replace('"', '').strip()
        return cal_val

    def import_cal(self, cr, uid, data, context={}):
        file_content = base64.decodestring(data)
        event_obj = self.pool.get('basic.calendar.event')
        event_obj.__attribute__.update(self.__attribute__)        
        
        vals = event_obj.import_ical(cr, uid, file_content)
        ids = []
        for val in vals:
            is_exists = common.uid2openobjectid(cr, val['id'], self._name)
            if val.has_key('create_date'): val.pop('create_date')
            val['caldav_url'] = context.get('url') or ''
            val.pop('id')
            if is_exists:                
                self.write(cr, uid, [is_exists], val)
                ids.append(is_exists)
            else:
                case_id = self.create(cr, uid, val)   
                ids.append(case_id)             
        return ids

    def get_recurrent_ids(self, cr, uid, ids, start_date, until_date, limit=100):
        if not limit:
            limit = 100
        if ids and (start_date or until_date):
            cr.execute("select m.id, m.rrule, c.date, m.exdate from crm_meeting m\
                         join crm_case c on (c.id=m.inherit_case_id) \
                         where m.id in ("+ ','.join(map(lambda x: str(x), ids))+")")
            result = []
            count = 0            
            start_date = start_date and datetime.datetime.strptime(start_date, "%Y-%m-%d") or False
            until_date = until_date and datetime.datetime.strptime(until_date, "%Y-%m-%d") or False            
            for data in cr.dictfetchall():                
                if count > limit:
                    break
                event_date = datetime.datetime.strptime(data['date'], "%Y-%m-%d %H:%M:%S")
                if start_date and start_date <= event_date:
                    start_date = event_date
                if not data['rrule']:
                    idval = common.real_id2caldav_id(data['id'], data['date'])
                    result.append(idval)
                    count += 1
                else:
                    exdate = data['exdate'] and data['exdate'].split(',') or []
                    event_obj = self.pool.get('basic.calendar.event')
                    rrule_str = data['rrule']
                    new_rrule_str = []
                    rrule_until_date = False
                    is_until = False
                    for rule in rrule_str.split(';'):
                        name, value = rule.split('=')
                        if name == "UNTIL":
                            is_until = True
                            value = parser.parse(value)
                            rrule_until_date = parser.parse(value.strftime("%Y-%m-%d"))
                            if until_date and until_date >= rrule_until_date:
                                until_date = rrule_until_date
                            if until_date:
                                value = until_date.strftime("%Y%m%d%H%M%S")                                
                        new_rule = '%s=%s' % (name, value)
                        new_rrule_str.append(new_rule)
                    if not is_until and until_date:                        
                        value = until_date.strftime("%Y%m%d%H%M%S")                        
                        name = "UNTIL"
                        new_rule = '%s=%s' % (name, value)
                        new_rrule_str.append(new_rule)
                    new_rrule_str = ';'.join(new_rrule_str)
                    start_date = datetime.datetime.strptime(data['date'], "%Y-%m-%d %H:%M:%S")
                    rdates = event_obj.get_recurrent_dates(str(new_rrule_str), exdate, start_date)
                    for rdate in rdates:
                        idval = common.real_id2caldav_id(data['id'], rdate)
                        result.append(idval)
                        count += 1
            ids = result
        return ids

    def search(self, cr, uid, args, offset=0, limit=100, order=None,
            context=None, count=False):
        args_without_date = []
        start_date = False
        until_date = False
        for arg in args:
            if arg[0] not in ('date', unicode('date')):
                args_without_date.append(arg)
            else:
                if arg[1] in ('>', '>='):
                    start_date = arg[2]
                elif arg[1] in ('<', '<='):
                    until_date = arg[2]

        res = super(crm_meeting, self).search(cr, uid, args_without_date, offset,
                limit, order, context, count)
        return self.get_recurrent_ids(cr, uid, res, start_date, until_date, limit)


    def write(self, cr, uid, ids, vals, context=None, check=True, update_check=True):
        if isinstance(ids, (str, int, long)):
            select = [ids]
        else:
            select = ids
        new_ids = []
        for id in select:
            id = common.caldav_id2real_id(id)
            if not id in new_ids:
                new_ids.append(id)
        if 'case_id' in vals:
            vals['case_id'] = common.caldav_id2real_id(vals['case_id'])
        res = super(crm_meeting, self).write(cr, uid, new_ids, vals, context=context)
        self.do_alarm_create(cr, uid, new_ids)
        return res

    def browse(self, cr, uid, ids, context=None, list_class=None, fields_process={}):
        if isinstance(ids, (str, int, long)):
            select = [ids]
        else:
            select = ids
        select = map(lambda x: common.caldav_id2real_id(x), select)
        res = super(crm_meeting, self).browse(cr, uid, select, context, list_class, fields_process)
        if isinstance(ids, (str, int, long)):
            return res and res[0] or False
        return res

    def read(self, cr, uid, ids, fields=None, context={}, load='_classic_read'):
        if isinstance(ids, (str, int, long)):
            select = [ids]
        else:
            select = ids
        select = map(lambda x: (x, common.caldav_id2real_id(x)), select)
        result = []
        if fields and 'date' not in fields:
            fields.append('date')
        for caldav_id, real_id in select:
            res = super(crm_meeting, self).read(cr, uid, real_id, fields=fields, context=context, \
                                              load=load)
            ls = common.caldav_id2real_id(caldav_id, with_date=True)
            if not isinstance(ls, (str, int, long)) and len(ls) >= 2:
                res['date'] = ls[1]
            res['id'] = caldav_id

            result.append(res)
        if isinstance(ids, (str, int, long)):
            return result and result[0] or False
        return result

    def copy(self, cr, uid, id, default=None, context={}):
        res = super(crm_meeting, self).copy(cr, uid, common.caldav_id2real_id(id), \
                                                          default, context)
        self.do_alarm_create(cr, uid, [res])
        return res

    def unlink(self, cr, uid, ids, context=None):
        res = False
        for id in ids:
            ls = common.caldav_id2real_id(id)
            if not isinstance(ls, (str, int, long)) and len(ls) >= 2:
                date_new = ls[1]
                for record in self.read(cr, uid, [common.caldav_id2real_id(id)], \
                                            ['date', 'rrule', 'exdate']):
                    if record['rrule']:
                        exdate = (record['exdate'] and (record['exdate'] + ',')  or '') + \
                                    ''.join((re.compile('\d')).findall(date_new)) + 'Z'
                        if record['date'] == date_new:
                            res = self.write(cr, uid, [common.caldav_id2real_id(id)], {'exdate': exdate})
                    else:
                        ids = map(lambda x: common.caldav_id2real_id(x), ids)
                        res = super(crm_meeting, self).unlink(cr, uid, common.caldav_id2real_id(ids))
                        self.do_alarm_unlink(cr, uid, ids)
            else:
                res = super(crm_meeting, self).unlink(cr, uid, ids)
                self.do_alarm_unlink(cr, uid, ids)
        return res

    def create(self, cr, uid, vals, context={}):
        if 'case_id' in vals:
            vals['case_id'] = common.caldav_id2real_id(vals['case_id'])
        res = super(crm_meeting, self).create(cr, uid, vals, context)
        self.do_alarm_create(cr, uid, [res])
        return res


    def _map_ids(self, method, cr, uid, ids, *args, **argv):
        if isinstance(ids, (str, int, long)):
            select = [ids]
        else:
            select = ids
        case_data = self.browse(cr, uid, select)
        new_ids = []
        for case in case_data:
            if case.inherit_case_id:
                new_ids.append(case.inherit_case_id.id)
        res = getattr(self.pool.get('crm.case'), method)(cr, uid, new_ids, *args, **argv)
        if isinstance(ids, (str, int, long)) and isinstance(res, list):
            return res and res[0] or False
        return res

    def onchange_rrule_type(self, cr, uid, ids, type, *args, **argv):
        if type == 'none':
            return {'value': {'rrule': ''}}
        if type == 'custom':
            return {}
        rrule = self.pool.get('caldav.set.rrule')
        rrulestr = rrule.compute_rule_string(cr, uid, {'freq': type.upper(),\
                 'interval': 1})
        return {'value': {'rrule': rrulestr}}


    def onchange_case_id(self, cr, uid, ids, *args, **argv):
        return self._map_ids('onchange_case_id', cr, uid, ids, *args, **argv)
    def onchange_partner_id(self, cr, uid, ids, *args, **argv):
        return self._map_ids('onchange_partner_id', cr, uid, ids, *args, **argv)
    def onchange_partner_address_id(self, cr, uid, ids, *args, **argv):
        return self._map_ids('onchange_partner_address_id', cr, uid, ids, *args, **argv)
    def onchange_categ_id(self, cr, uid, ids, *args, **argv):
        return self._map_ids('onchange_categ_id', cr, uid, ids, *args, **argv)
    def case_close(self, cr, uid, ids, *args, **argv):
        return self._map_ids('case_close', cr, uid, ids, *args, **argv)
    def case_open(self, cr, uid, ids, *args, **argv):
        return self._map_ids('case_open', cr, uid, ids, *args, **argv)
    def case_cancel(self, cr, uid, ids, *args, **argv):
        return self._map_ids('case_cancel', cr, uid, ids, *args, **argv)
    def case_reset(self, cr, uid, ids, *args, **argv):
        return self._map_ids('case_reset', cr, uid, ids, *args, **argv)

    def msg_new(self, cr, uid, msg):
        mailgate_obj = self.pool.get('mail.gateway')
        msg_body = mailgate_obj.msg_body_get(msg)
        data = {
            'name': msg['Subject'],
            'email_from': msg['From'],
            'email_cc': msg['Cc'],
            'user_id': False,
            'description': msg_body['body'],
            'history_line': [(0, 0, {'description': msg_body['body'], 'email': msg['From'] })],
        }
        res = mailgate_obj.partner_get(cr, uid, msg['From'])
        if res:
            data.update(res)
        res = self.create(cr, uid, data)
        return res

    def msg_update(self, cr, uid, ids, *args, **argv):
        return self._map_ids('msg_update', cr, uid, ids, *args, **argv)
    def emails_get(self, cr, uid, ids, *args, **argv):
        return self._map_ids('emails_get', cr, uid, ids, *args, **argv)
    def msg_send(self, cr, uid, ids, *args, **argv):
        return self._map_ids('msg_send', cr, uid, ids, *args, **argv)

crm_meeting()


class crm_meeting_generic_wizard(osv.osv_memory):
    _name = 'crm.meeting.generic_wizard'

    _columns = {
        'section_id': fields.many2one('crm.case.section', 'Section', required=False),
        'user_id': fields.many2one('res.users', 'Responsible'),
    }

    def _get_default_section(self, cr, uid, context):
        case_id = context.get('active_id', False)
        if not case_id:
            return False
        case_obj = self.pool.get('crm.meeting')
        case = case_obj.read(cr, uid, case_id, ['state', 'section_id'])
        if case['state'] in ('done'):
            raise osv.except_osv(_('Error !'), _('You can not assign Closed Case.'))
        return case['section_id']


    _defaults = {
        'section_id': _get_default_section
    }
    def action_create(self, cr, uid, ids, context=None):
        case_obj = self.pool.get('crm.meeting')
        case_id = context.get('active_id', [])
        res = self.read(cr, uid, ids)[0]
        case = case_obj.browse(cr, uid, case_id)
        if case.state in ('done'):
            raise osv.except_osv(_('Error !'), _('You can not assign Closed Case.'))
        new_case_id = case_obj.copy(cr, uid, case_id, default=
                                            {
                                                'section_id': res.get('section_id', False),
                                                'user_id': res.get('user_id', False),
                                                'case_id': case.inherit_case_id.id
                                            }, context=context)
        case_obj.case_close(cr, uid, [case_id])
        data_obj = self.pool.get('ir.model.data')
        result = data_obj._get_id(cr, uid, 'crm', 'view_crm_case_meetings_filter')
        search_view = data_obj.read(cr, uid, result, ['res_id'])
        new_case = case_obj.read(cr, uid, new_case_id, ['id'])
        value = {
            'name': _('Meetings'),
            'view_type': 'form',
            'view_mode': 'calendar, tree, form',
            'res_model': 'crm.meeting',
            'type': 'ir.actions.act_window',
            'search_view_id': search_view['res_id']
        }
        return value

crm_meeting_generic_wizard()

class res_users(osv.osv):
    _inherit = 'res.users'
    def _get_user_avail(self, cr, uid, ids, context=None):
        current_datetime = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        res = super(res_users, self)._get_user_avail(cr, uid, ids, context)
        cr.execute("SELECT crm_case.user_id, 'busy' as status \
                    FROM crm_meeting meeting, crm_case \
                    WHERE meeting.inherit_case_id = crm_case.id \
                    and crm_case.date <= %s and crm_case.date_deadline >= %s and crm_case.user_id = ANY(%s) and meeting.show_as = %s", 
                                (current_datetime, current_datetime , ids, 'busy'))
        result = cr.dictfetchall()
        for user_data in result:
            user_id = user_data['user_id']
            status = user_data['status']
            res.update({user_id:status})        
        return res
res_users()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
