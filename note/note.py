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

from openerp.osv import osv, fields
from tools.translate import _
import re

class note_stage(osv.osv):
    """ Category of Note """
    _name = "note.stage"
    _description = "Note Stage"
    _columns = {
        'name': fields.char('Stage Name', required=True),
        'sequence': fields.integer('Sequence', help="Used to order the note stages"),
        'user_id': fields.many2one('res.users', 'Owner', help="Owner of the note stage.", required=True),
        'fold': fields.boolean('Folded by Default'),
    }
    _order = 'sequence asc'
    _defaults = {
        'fold': 0,
        'user_id': lambda self, cr, uid, ctx: uid,
        'sequence' : 1,
    }

class note_tag(osv.osv):
    _name = "note.tag"
    _description = "Note Tag"
    _columns = {
        'name' : fields.char('Tag Name', required=True),
    }

class note_note(osv.osv):
    """ Note """
    _name = 'note.note'
    _inherit = ['mail.thread']
    _description = "Note"

    #writing method (no modification of values)
    def name_create(self, cr, uid, name, context=None):
        rec_id = self.create(cr, uid, {'memo': name}, context=context)
        return self.name_get(cr, uid, [rec_id], context)[0]

    #read the first line (convert hml into text)
    def _get_note_first_line(self, cr, uid, ids, name="", args={}, context=None):
        res = {}
        for note in self.browse(cr, uid, ids, context=context):
            text_note = (note.memo or '').strip().split('\n')[0]
            text_note = re.sub(r'(\S?)(<br[ /]*>|<[/]?p>|<[/]?div>|<table>)[\s\S]*',r'\1',text_note)
            text_note = re.sub(r'<[^>]+>','',text_note)
            res[note.id] = text_note
        return res

    #unactivate a sticky note and record the date
    def onclick_note_is_done(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, { 'active' : False, 'date_done' : fields.date.today() })
        self.message_post(cr, uid, ids[0], body='Note is done.', subject=False, 
            type='notification', parent_id=False, attachments=None, context=context)
        return False

    #activate a note
    def onclick_note_not_done(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'active' : True})
        self.message_post(cr, uid, ids[0], body='Note has been activated.', subject=False, 
            type='notification', parent_id=False, attachments=None, context=context)
        return False

    #used for undisplay the follower if it's the current user
    def _get_my_current_partner(self, cr, uid, ids, name, args, context=None):
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        pid = user.partner_id and user.partner_id.id or False
        return dict.fromkeys(ids, pid)

    #return the default stage for the uid user
    def _get_default_stage_id(self,cr,uid,context=None):
        ids = self.pool.get('note.stage').search(cr,uid,[('user_id','=',uid)], context=context)
        return ids and ids[0] or False

    def _set_stage_per_user(self, cr, uid, id, name, value, args=None, context=None):
        note = self.browse(cr, uid, id, context=context)
        if not value: return False
        return self.write(cr, uid, [id], {'stage_ids': [(4, value)]}, context=context)

    def _get_stage_per_user(self, cr, uid, ids, name, args, context=None):
        result = dict.fromkeys(ids, False)
        for record in self.browse(cr, uid, ids, context=context):
            for stage in record.stage_ids:
                if stage.user_id.id == uid:
                    result[record.id] = stage.id
        return result


    _columns = {
        'name': fields.function(_get_note_first_line, 
            string='Note Summary', 
            type='text', store=True),
        'memo': fields.html('Note Content'),
        'sequence': fields.integer('Sequence'),
        'stage_id': fields.function(_get_stage_per_user, 
            fnct_inv=_set_stage_per_user, 
            string='Stage', 
            type='many2one', 
            relation='note.stage'),
        'stage_ids': fields.many2many('note.stage','note_stage_rel','note_id','stage_id','Stages of Users'),
        'active': fields.boolean('Active'),
        'date_done': fields.date('Date done'),
        'color': fields.integer('Color Index'),
        'tag_ids' : fields.many2many('note.tag','note_tags_rel','note_id','tag_id','Tags'),
        'current_partner_id' : fields.function(_get_my_current_partner),
    }
    _defaults = {
        'active' : 1,
        'stage_id' : _get_default_stage_id,
    }
    _order = 'sequence'

    def read_group(self, cr, uid, domain, fields, groupby, offset=0, limit=None, context=None, orderby=False):
        if groupby and groupby[0]=="stage_id":

            #search all stages
            current_stage_ids = self.pool.get('note.stage').search(cr,uid,[('user_id','=',uid)], context=context)

            if current_stage_ids: #if the user have some stages

                #dict of stages: map les ids sur les noms
                stage_name = dict(self.pool.get('note.stage').name_get(cr, uid, current_stage_ids, context=context))

                result = [{ #notes by stage for stages user
                        '__context': {'group_by': groupby[1:]},
                        '__domain': domain + [('stage_ids.id', '=', current_stage_id)],
                        'stage_id': (current_stage_id, stage_name[current_stage_id]),
                        'stage_id_count': self.search(cr,uid, domain+[('stage_ids', '=', current_stage_id)], context=context, count=True)
                    } for current_stage_id in current_stage_ids]

                #note without user's stage
                nb_notes_ws = self.search(cr,uid, domain+[('stage_ids', 'not in', current_stage_ids)], context=context, count=True)
                if nb_notes_ws:
                    result += [{ #notes for unknown stage and if stage_ids is not empty
                        '__context': {'group_by': groupby[1:]},
                        '__domain': domain + [('stage_ids', 'not in', current_stage_ids)],
                        'stage_id': (0, 'Unknown'),
                        'stage_id_count':nb_notes_ws
                    }]

            else: # if stage_ids is empty

                #note without user's stage
                nb_notes_ws = self.search(cr,uid, domain, context=context, count=True)
                if nb_notes_ws:
                    result = [{ #notes for unknown stage
                        '__context': {'group_by': groupby[1:]},
                        '__domain': domain,
                        'stage_id': (0, 'Unknown'),
                        'stage_id_count':nb_notes_ws
                    }]
                else:
                    result = []
            return result

        else:
            return super(note_note, self).read_group(self, cr, uid, domain, fields, groupby, 
                offset=offset, limit=limit, context=context, orderby=orderby)


#upgrade config setting page to configure pad, fancy and tags mode
class note_base_config_settings(osv.osv_memory):
    _inherit = 'base.config.settings'
    _columns = {
        'module_note_pad': fields.boolean('Use collaborative pads (etherpad)'),
        'group_note_fancy': fields.boolean('Use fancy layouts for notes', implied_group='note.group_note_fancy'),
        'group_note_tags': fields.boolean('Allow setting tags on notes', implied_group='note.group_note_tags'),
    }
