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
from tools.translate import _
from tools import email_send as email

class project_task_close(osv.osv_memory):
    """
    Close Task
    """
    _name = "project.task.close"
    _description = "Project Close Task"
    _columns = {
        'manager_warn': fields.boolean("Warn Manager", help="Warn Manager by Email"),
        'partner_warn': fields.boolean("Warn Customer", help="Warn Customer by Email"),
        'manager_email': fields.char('Manager Email', size=128, help="Email Address of Project's Manager"),
        'partner_email': fields.char('Customer Email', size=128, help="Email Address of Customer"),
        'description': fields.text('Description'),
    }

    def default_get(self, cr, uid, fields, context=None):
        """
        This function gets default values
        """
        if context is None:
            context = {}
        record_id = context and context.get('active_id', False) or False
        task_pool = self.pool.get('project.task')
        project_pool = self.pool.get('project.project')
                
        res = super(project_task_close, self).default_get(cr, uid, fields, context=context)
        task = task_pool.browse(cr, uid, record_id, context=context)
        project = task.project_id
        manager = project.user_id or False
        partner = task.partner_id or task.project_id.partner_id
        
        if 'description' in fields:
            res.update({'description': task.description})
        if 'manager_warn' in fields:
            res.update({'manager_warn': project.warn_manager})
        if 'partner_warn' in fields:
            res.update({'partner_warn': project.warn_customer})
        if 'manager_email' in fields:
            res.update({'manager_email': manager and manager.user_email or False})
        if partner and len(partner.address) and 'partner_email' in fields:
            res.update({'partner_email': partner.address[0].email})
        return res

    def done(self, cr, uid, ids, context=None):
        task_pool = self.pool.get('project.task')
        task_id = context.get('active_id', False)
        res = task_pool.do_close(cr, uid, [task_id], context=context)
        return res

    def confirm(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        
        task_pool = self.pool.get('project.task')
        task_id = context.get('active_id', False)
        if not task_id:
            return {}
        task = task_pool.browse(cr, uid, task_id, context=context)
        for data in self.browse(cr, uid, ids, context=context):
            res = task_pool.do_close(cr, uid, [task.id], context=context)
            if res:
                # Send Warn Message by Email to Manager and Customer
                if data.manager_warn and not data.manager_email:
                    raise osv.except_osv(_('Error'), _("Please specify the email address of Project Manager."))

                elif data.partner_warn and not data.partner_email:
                    raise osv.except_osv(_('Error'), _("Please specify the email address of Customer."))

                elif data.manager_warn or data.partner_warn:
                    project = task.project_id
                    subject = _("Task '%s' Closed") % task.name
                    if task.user_id and task.user_id.address_id and task.user_id.address_id.email:
                        from_adr = task.user_id.address_id.email
                        signature = task.user_id.signature
                    else:
                        raise osv.except_osv(_('Error'), _("Couldn't send mail because your email address is not configured!"))
                    val = {
                            'name': task.name,
                            'user_id': task.user_id.name,
                            'task_id': "%d/%d" % (project.id, task.id),
                            'date_start': task.date_start,
                            'date_end': task.date_end,
                            'state': task.state
                    }

                    header = (project.warn_header or '') % val
                    footer = (project.warn_footer or '') % val
                    body = u'%s\n%s\n%s\n\n-- \n%s' % (header, description, footer, signature)
                    if data.manager_warn and data.manager_email:
                        to_adr.append(data.manager_email)
                    if data.partner_warn and data.partner_email:
                        to_adr.append(data.partner_email)
                    mail_id = email(from_adr, to_adr, subject, tools.ustr(body), email_bcc=[from_adr])
                    if not mail_id:
                        raise osv.except_osv(_('Error'), _("Couldn't send mail! Check the email ids and smtp configuration settings"))
        return {}

project_task_close()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
