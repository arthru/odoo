 #-*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2008 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
import time
import netsvc
from osv import fields, osv

from tools.misc import currency

import pooler
import mx.DateTime
from mx.DateTime import RelativeDateTime, now, DateTime, localtime


class document_rule(osv.osv):
    _name = "document.rule"
    _description = "Document Rule"
    _columns = {
                'name': fields.char('Name', size=64, required=True),
                'author':fields.many2one('res.users','Author'),
                'partner_id':fields.many2one('res.partner', 'Partner', select=1),
                'directory_id': fields.many2one('document.directory', 'Directory'),
                'date_type':  fields.selection([('none','None'),
                                                    ('create','Creation Date'),], 'Trigger Date', size=16),
                'server_act':fields.many2one('ir.actions.server', 'Action'),
                'filename':fields.many2one('ir.attachment','File'),
                'resource_object':fields.char('Resource Name',size=64),
                'active': fields.boolean('Active'),
                'sequence': fields.integer('Sequence'),
                'act_copy_directory_id':fields.many2one('document.directory', 'Copy to'),
                'act_move_directory_id':fields.many2one('document.directory', 'Move to'),
                'act_assign_user_id': fields.many2one('res.users', 'Assign to User'),
                'act_assign_partner_id': fields.many2one('res.partner', 'Assign to Partner'),
                }
    _defaults = {
        'active': lambda *a: 1,
        }

document_rule()


