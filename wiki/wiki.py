# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2004-2006 TINY SPRL. (http://axelor.com) All Rights Reserved.
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

from osv import fields, osv
from tools.translate import _
import difflib

class Wiki(osv.osv):
    """ wiki """
    _name = "wiki.wiki"

Wiki()

class WikiGroup(osv.osv):
    """ Wiki Groups """

    _name = "wiki.groups"
    _description = "Wiki Groups"
    _order = 'name'

    _columns = {
       'name':fields.char('Wiki Group', size=256, select=True, required=True),
       'page_ids':fields.one2many('wiki.wiki', 'group_id', 'Pages'),
       'notes':fields.text("Description"),
       'create_date':fields.datetime("Created Date", select=True),
       'template': fields.text('Wiki Template'),
       'section': fields.boolean("Make Section ?"),
       'method':fields.selection([('list', 'List'), ('page', 'Home Page'), \
                                   ('tree', 'Tree')], 'Display Method'),
       'home':fields.many2one('wiki.wiki', 'Home Page'),
    }

    _defaults = {
        'method': lambda *a: 'page',
    }

WikiGroup()


class GroupLink(osv.osv):
    """ Apply Group Link """

    _name = "wiki.groups.link"
    _description = "Wiki Groups Links"
    _rec_name = 'action_id'

    _columns = {
       'group_id': fields.many2one('wiki.groups', 'Parent Group', ondelete='set null'),
       'action_id': fields.many2one('ir.ui.menu', 'Menu')
    }

GroupLink()


class Wiki2(osv.osv):
    """ Wiki Page """

    _inherit = "wiki.wiki"
    _description = "Wiki Page"
    _order = 'section,create_date desc'

    _columns = {
        'name': fields.char('Title', size=256, select=True, required=True),
        'write_uid': fields.many2one('res.users', "Last Contributor", select=True),
        'text_area': fields.text("Content"),
        'create_uid': fields.many2one('res.users', 'Author', select=True),
        'create_date': fields.datetime("Created on", select=True),
        'write_date': fields.datetime("Modification Date", select=True),
        'tags': fields.char('Tags', size=1024, select=True),
        'history_id': fields.one2many('wiki.wiki.history', 'wiki_id', 'History Lines'),
        'minor_edit': fields.boolean('Minor edit', select=True),
        'summary': fields.char('Summary', size=256),
        'section': fields.char('Section', size=32, help="Use page section code like 1.2.1", select=True),
        'group_id': fields.many2one('wiki.groups', 'Wiki Group', select=1, ondelete='set null', 
            help="Topic, also called Wiki Group"),
        'toc': fields.boolean('Table of Contents', 
            help="Indicates that this pages is a table of contents (linking to other pages)"),
        'review': fields.boolean('Needs Review', select=True, 
            help="Indicates that this page should be reviewed, raising the attention of other contributors"),
        'parent_id': fields.many2one('wiki.wiki', 'Parent Page'),
        'child_ids': fields.one2many('wiki.wiki', 'parent_id', 'Child Pages'),
    }

    def onchange_group_id(self, cr, uid, ids, group_id, content, context={}):

        """ @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param ids: List of wiki page’s IDs
            @return: dictionay of open wiki page on give page section  """

        if (not group_id) or content:
            return {}
        grp = self.pool.get('wiki.groups').browse(cr, uid, group_id)
        section = '0'
        for page in grp.page_ids:
            if page.section: section = page.section
        s = section.split('.')
        template = grp.template
        try:
            s[-1] = str(int(s[-1])+1)
        except:
            pass
        section = '.'.join(s)
        return {
            'value':{
                'text_area': template,
                'section': section
            }
        }

    def copy_data(self, cr, uid, id, default=None, context=None):

        """ @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param id: Give wiki page's ID """

        return super(Wiki, self).copy_data(cr, uid, id, {'wiki_id': False}, context)

    def create(self, cr, uid, vals, context=None):

        """ @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks, """

        id = super(Wiki, self).create(cr, uid, vals, context)
        history = self.pool.get('wiki.wiki.history')
        if vals.get('text_area'):
            res = {
                'minor_edit': vals.get('minor_edit', True),
                'text_area': vals.get('text_area', ''),
                'write_uid': uid,
                'wiki_id': id,
                'summary':vals.get('summary', '')
            }
            history.create(cr, uid, res)
        return id

    def write(self, cr, uid, ids, vals, context=None):

        """ @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks, """

        result = super(Wiki, self).write(cr, uid, ids, vals, context)
        history = self.pool.get('wiki.wiki.history')
        if vals.get('text_area'):
            for id in ids:
                res = {
                    'minor_edit': vals.get('minor_edit', True),
                    'text_area': vals.get('text_area', ''),
                    'write_uid': uid,
                    'wiki_id': id,
                    'summary': vals.get('summary', '')
                }
                history.create(cr, uid, res)
        return result

Wiki2()


class History(osv.osv):
    """ Wiki History """

    _name = "wiki.wiki.history"
    _description = "Wiki History"
    _rec_name = "date_time"
    _order = 'id DESC'

    _columns = {
              'create_date': fields.datetime("Date", select=True),
              'text_area': fields.text("Text area"),
              'minor_edit': fields.boolean('This is a major edit ?', select=True),
              'summary': fields.char('Summary', size=256, select=True),
              'write_uid': fields.many2one('res.users', "Modify By", select=True),
              'wiki_id': fields.many2one('wiki.wiki', 'Wiki Id', select=True)
            }

    _defaults = {
        'write_uid': lambda obj, cr, uid, context: uid,
    }

    def getDiff(self, cr, uid, v1, v2, context={}):

        """ @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks, """

        history_pool = self.pool.get('wiki.wiki.history')
        text1 = history_pool.read(cr, uid, [v1], ['text_area'])[0]['text_area']
        text2 = history_pool.read(cr, uid, [v2], ['text_area'])[0]['text_area']
        line1 = text1.splitlines(1)
        line2 = text2.splitlines(1)
        diff = difflib.HtmlDiff()
        return diff.make_file(line1, line2, "Revision-%s" % (v1), "Revision-%s" % (v2), context=False)

History()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
