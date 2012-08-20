# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2010-Today OpenERP SA (<http://www.openerp.com>)
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
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#
##############################################################################

import ast
import re

import tools
from osv import osv
from osv import fields
from tools.safe_eval import safe_eval as eval
from tools.translate import _

# FP Note: refactor in tools ?
def mail_tools_to_email(text):
    """Return a list of the email addresses found in ``text``"""
    if not text: return []
    return re.findall(r'([^ ,<@]+@[^> ,]+)', text)

# main mako-like expression pattern
EXPRESSION_PATTERN = re.compile('(\$\{.+?\})')

class mail_compose_message(osv.TransientModel):
    """Generic Email composition wizard. This wizard is meant to be inherited
       at model and view level to provide specific wizard features.

       The behavior of the wizard can be modified through the use of context
       parameters, among which are:

         * mail.compose.message.mode: if set to 'reply', the wizard is in 
            reply to a previous message mode and pre-populated with the original
            quote. If set to 'comment', it means you are writing a new message to
            be attached to a document. If set to 'mass_mail', the wizard is in
            mass mailing where the mail details can contain template placeholders
            that will be merged with actual data before being sent to each
            recipient.
         * active_model: model name of the document to which the mail being
                        composed is related
         * active_id: id of the document to which the mail being composed is
                      related, or id of the message to which user is replying,
                      in case ``mail.compose.message.mode == 'reply'``
         * active_ids: ids of the documents to which the mail being composed is
                      related, in case ``mail.compose.message.mode == 'mass_mail'``.
    """
    _name = 'mail.compose.message'
    _inherit = 'mail.message'
    _description = 'Email composition wizard'

    def default_get(self, cr, uid, fields, context=None):
        """ Overridden to provide specific defaults depending on the context
            parameters.

            Composition mode
            - comment: default mode; active_model, active_id = model and ID of a
            document we are commenting,
            - reply: active_id = ID of a mail.message to which we are replying.
            From this message we can find the related model and res_id,
            - mass_mailing mode: active_model, active_id  = model and ID of a
            document we are commenting,

           :param dict context: several context values will modify the behavior
                                of the wizard, cfr. the class description.
        """
        if context is None:
            context = {}
        compose_mode = context.get('mail.compose.message.mode', 'comment')
        active_model = context.get('active_model')
        active_id = context.get('active_id')
        result = super(mail_compose_message, self).default_get(cr, uid, fields, context=context)

        # get default values according to the composition mode
        vals = {}
        if compose_mode in ['reply']:
            vals = self.get_message_data(cr, uid, int(context['active_id']), context=context)
        elif compose_mode in ['comment', 'mass_mail'] and active_model and active_id:
            vals = self.get_value(cr, uid, active_model, active_id, context)
        for field in vals:
            if field in fields:
                result[field] = vals[field]

        # link to model and record if not done yet
        if not result.get('model') and active_model:
            result['model'] = active_model
        if not result.get('res_id') and active_id:
            result['res_id'] = active_id
        return result

    _columns = {
        'dest_partner_ids': fields.many2many('res.partner',
            'email_message_send_partner_rel',
            'wizard_id', 'partner_id', 'Destination partners',
            help="When sending emails through the social network composition wizard"\
                 "you may choose to send a copy of the mail to partners."),
        'attachment_ids': fields.many2many('ir.attachment','email_message_send_attachment_rel', 'wizard_id', 'attachment_id', 'Attachments'),
        'auto_delete': fields.boolean('Auto Delete', help="Permanently delete emails after sending"),
        'filter_id': fields.many2one('ir.filters', 'Filters'),
        'body_html': fields.html('HTML Editor Body'),
        'content_subtype': fields.char('Message content subtype', size=32,
            oldname="subtype", readonly=1,
            help="Type of message, usually 'html' or 'plain', used to select "\
                  "plain-text or rich-text contents accordingly"),
    }
    _defaults = {
        'content_subtype': lambda self,cr, uid, context={}: 'plain',
        'body_html': lambda self,cr, uid, context={}: '',
        'body': lambda self,cr, uid, context={}: ''
    }


    def get_value(self, cr, uid, model, res_id, context=None):
        """ Returns a defaults-like dict with initial values for the composition
            wizard when sending an email related to the document record
            identified by ``model`` and ``res_id``.

            The default implementation returns an empty dictionary, and is meant
            to be overridden by subclasses.

            :param str model: model name of the document record this mail is
                related to.
            :param int res_id: id of the document record this mail is related to.
            :param dict context: several context values will modify the behavior
                of the wizard, cfr. the class description.
        """
        result = {}
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        result.update({
            'model': model,
            'res_id': res_id,
            'email_from': user.email or tools.config.get('email_from', False),
            'body': False,
            'subject': False,
            'dest_partner_ids': [],
        })
        return result

    def onchange_email_mode(self, cr, uid, ids, value, model, res_id, context=None):
        """ email_mode (values: True or False). This onchange on the email mode
            allows to have some specific behavior when going in email mode, or
            when going out of email mode.
            Basically, dest_partner_ids is reset when going out of email
            mode.
            This method can be overridden for models that want to have their
            specific behavior.
            Note that currently, this onchange is used in mail.js and called
            manually on the form instantiated in the Chatter.
        """
        if not value:
            return {'value': {'dest_partner_ids': []}}
        return {'value': {}}

    def onchange_formatting(self, cr, uid, ids, value, model, res_id, context=None):
        """ onchange_formatting (values: True or False). This onchange on the
            formatting allows to have some specific behavior when going in 
            formatting mode, or when going out of formatting.
            Basically, subject is reset when going out of formatting mode.
            This method can be overridden for models that want to have their
            specific behavior.
            Note that currently, this onchange is used in mail.js and called
            manually on the form instantiated in the Chatter.
        """
        if not value:
            return {'value': {'subject': False}}
        return {'value': {}}

    def get_message_data(self, cr, uid, message_id, context=None):
        """ Returns a defaults-like dict with initial values for the composition
            wizard when replying to the given message (e.g. including the quote
            of the initial message, and the correct recipient). It should not be
            called unless ``context['mail.compose.message.mode'] == 'reply'``.

            :param int message_id: id of the mail.message to which the user
                is replying.
            :param dict context: several context values will modify the behavior
                of the wizard, cfr. the class description.
        """
        if context is None:
            context = {}
        result = {}
        if not message_id:
            return result

        current_user = self.pool.get('res.users').browse(cr, uid, uid, context)
        message_data = self.pool.get('mail.message').browse(cr, uid, message_id, context)
        # Form the subject
        re_prefix = _("Re:")
        reply_subject = tools.ustr(message_data.subject or '')
        if not (reply_subject.startswith('Re:') or reply_subject.startswith(re_prefix)):
            reply_subject = "%s %s" % (re_prefix, reply_subject)

        # Form the bodies (text and html). We use the plain text version of the
        # original mail, by default, as it is easier to quote than the HTML
        # version. TODO: make it possible to switch to HTML on the fly

        sent_date = _('On %(date)s, ') % {'date': message_data.date} if message_data.date else ''
        sender = _('%(sender_name)s wrote:') % {'sender_name': tools.ustr(message_data.email_from or _('You'))}

        body = message_data.body or ''
        quoted_body = '<blockquote>%s</blockquote>' % (tools.ustr(body)),
        reply_body = '<br /><br />%s%s<br />%s<br />%s' % (sent_date, sender, quoted_body, current_user.signature)

        # form dest_partner_ids
        dest_partner_ids = [partner.id for partner in message_data.partner_ids]

        # update the result
        result.update({
            'body': reply_body,
            'subject': reply_subject,
            'dest_partner_ids': dest_partner_ids,
            'model': message_data.model or False,
            'res_id': message_data.res_id or False,
        })
        return result

    def send_mail(self, cr, uid, ids, context=None):
        '''Process the wizard contents and proceed with sending the corresponding
           email(s), rendering any template patterns on the fly if needed.
           If the wizard is in mass-mail mode (context['mail.compose.message.mode'] is
           set to ``'mass_mail'``), the resulting email(s) are scheduled for being
           sent the next time the mail.message scheduler runs, or the next time
           ``mail.message.process_email_queue`` is called.
           Otherwise the new message is sent immediately.

           :param dict context: several context values will modify the behavior
                                of the wizard, cfr. the class description.
        '''
        if context is None:
            context = {}

        email_mode = context.get('email_mode')
        formatting = context.get('formatting')
        mass_mail_mode = context.get('mail.compose.message.mode') == 'mass_mail'

        mail_message_obj = self.pool.get('mail.message')
        for mail_wiz in self.browse(cr, uid, ids, context=context):
            attachment = {}
            for attach in mail_wiz.attachment_ids:
                attachment[attach.datas_fname] = attach.datas and attach.datas or False

            # default values, according to the wizard options
            subject = mail_wiz.subject if formatting else False
            partner_ids = [partner.id for partner in mail_wiz.dest_partner_ids]
            body = mail_wiz.body_html if mail_wiz.content_subtype == 'html' else mail_wiz.body

            active_model_pool = self.pool.get('mail.thread')
            active_id = context.get('default_res_id', False)
            if context.get('mail.compose.message.mode') == 'mass_mail' and context.get('default_model', False) and context.get('default_res_id', False):
                active_model = context.get('default_model', False)
                active_model_pool = self.pool.get(active_model)
                subject = self.render_template(cr, uid, subject, active_model, active_id)
                body = self.render_template(cr, uid, mail_wiz.body_html, active_model, active_id)
            active_model_pool.message_post(cr, uid, active_id, body, subject, 'comment', 
                attachments=attachment, context=context)

        return {'type': 'ir.actions.act_window_close'}

    def render_template(self, cr, uid, template, model, res_id, context=None):
        """Render the given template text, replace mako-like expressions ``${expr}``
           with the result of evaluating these expressions with an evaluation context
           containing:

                * ``user``: browse_record of the current user
                * ``object``: browse_record of the document record this mail is
                              related to
                * ``context``: the context passed to the mail composition wizard

           :param str template: the template text to render
           :param str model: model name of the document record this mail is related to.
           :param int res_id: id of the document record this mail is related to.
        """
        if context is None:
            context = {}
        def merge(match):
            exp = str(match.group()[2:-1]).strip()
            result = eval(exp,
                          {
                            'user' : self.pool.get('res.users').browse(cr, uid, uid, context=context),
                            'object' : self.pool.get(model).browse(cr, uid, res_id, context=context),
                            'context': dict(context), # copy context to prevent side-effects of eval
                          })
            if result in (None, False):
                return ""
            return tools.ustr(result)
        return template and EXPRESSION_PATTERN.sub(merge, template)


class mail_compose_message_extended(osv.TransientModel):
    """ Extension of 'mail.compose.message' to support default field values related
        to CRM-like models that follow the following conventions:

        1. The model object must have an attribute '_mail_compose_message' equal to True.

        2. The model should define the following fields:
            - 'name' as subject of the message (required);
            - 'email_from' as destination email address (required);
            - 'email_cc' as cc email addresses (required);
            - 'section_id.reply_to' as reply-to address (optional).
    """
    _inherit = 'mail.compose.message'

    def get_value(self, cr, uid, model, res_id, context=None):
        return {}

    def onchange_email_mode(self, cr, uid, ids, value, model, res_id, context=None):
        """ Overrides the default implementation to provide default values for
            dest_partner_ids. This method checks that a partner maching the
            ``email_from`` of the record exists. It it does not exist, it
            creates a new partner. The found or created partner is then added
            in dest_partner_ids.
            Partner check/creation valid inly if the value is True, and if 
            the model has the ``_mail_compose_message`` attribute.
        """
        result = super(mail_compose_message_extended, self).onchange_email_mode(cr, uid, ids, value, model, res_id, context=context)
        model_obj = self.pool.get(model)
        if not value or not (getattr(model_obj, '_mail_compose_message', False) and res_id):
            return result
        data = model_obj.browse(cr, uid , res_id, context=context)
        partner_obj = self.pool.get('res.partner')
        partner_ids = partner_obj.search(cr, uid, [('email', '=', data.email_from)], context=context)
        if partner_ids:
            partner_id = partner_ids[0]
        else:
            partner_id = partner_obj.name_create(cr, uid, data.email_from, context=context)[0]
        result['value'].update({
            'dest_partner_ids': [partner_id],
            'email_cc': tools.ustr(data.email_cc or ''),
        })
        if hasattr(data, 'section_id'):
            result['value']['reply_to'] = data.section_id and data.section_id.reply_to or False
        return result

    def onchange_formatting(self, cr, uid, ids, value, model, res_id, context=None):
        """ Overrides the default implementation to provide default values for
            the subject.
            Subject re-creation valid only if the value is True, and if the
            model has the ``_mail_compose_message`` attribute.
        """
        result = super(mail_compose_message_extended, self).onchange_formatting(cr, uid, ids, value, model, res_id, context=context)
        model_obj = self.pool.get(model)
        if not value or not (getattr(model_obj, '_mail_compose_message', False) and res_id):
            return result
        data = model_obj.browse(cr, uid , res_id, context=context)
        result['value'].update({
            'subject': data.name or False,
        })
        return result

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
