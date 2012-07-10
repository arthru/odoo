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

from ..mail_message import to_email

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
    _inherit = 'mail.message.common'
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
            # if result['model'] == 'mail.message' and not result.get('parent_id'):
            #     result['parent_id'] = context.get('active_id')

        # Try to provide default email_from if not specified yet
        if not result.get('email_from'):
            current_user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
            result['email_from'] = current_user.user_email or False

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
            'email_from': user.user_email or tools.config.get('email_from', False),
            'body_html': '<br />---<br />' + tools.ustr(user.signature or ''),
        })
        return result

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
        body_text = message_data.body_text or ''
        quoted_body_text = '> %s' % tools.ustr(body_text.replace('\n', "\n> ") or '')
        quoted_body_html = '> %s' % tools.ustr(body_text.replace('\n', "<br />&gt; ") or '')
        reply_body_text = '\n%s%s\n%s\n%s' % (sent_date, sender, quoted_body_text, current_user.signature)
        reply_body_html = '\n%s%s\n%s\n%s' % (sent_date, sender, quoted_body_html, current_user.signature)
        # Update header and references
        reply_headers = {}
        reply_references = message_data.references and tools.ustr(message_data.references) or False
        reply_message_id = message_data.message_id or False
        if reply_message_id:
            reply_references = (reply_references or '') + " " + mail_wiz.message_id
            reply_headers['In-Reply-To'] = mail_wiz.message_id
        # update the result
        result.update({
            'body_text': reply_body_text,
            'body_html': quoted_body_html,
            'subject': reply_subject,
            'attachment_ids': [],
            'model': message_data.model or False,
            'res_id': message_data.res_id or False,
            'email_from': current_user.user_email or message_data.email_to or False,
            'email_to': message_data.reply_to or message_data.email_from or False,
            'email_cc': message_data.email_cc or False,
            'user_id': uid,
            # pass msg-id and references of mail we're replying to, to construct the
            # new ones later when sending
            'message_id': reply_message_id,
            'references': reply_references,
            'headers': reply_headers,
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
        mail_message = self.pool.get('mail.message')
        for mail_wiz in self.browse(cr, uid, ids, context=context):
            # attachments
            attachment = {}
            for attach in mail_wiz.attachment_ids:
                attachment[attach.datas_fname] = attach.datas and attach.datas.decode('base64')

            # composition wizard options
            email_mode = context.get('email_mode')
            formatting = context.get('formatting')

            # default message values according to the wizard options
            if formatting:
                content_subtype = 'html'
            else:
                content_subtype = 'text'
                subject = False
            if email_mode:
                type = 'email'
            else:
                type = 'comment'
            references = None
            headers = {}
            body = mail_wiz.body_html if mail_wiz.content_subtype == 'html' else mail_wiz.body_text

            # Get model, and check whether it is OpenChatter enabled, aka inherit from mail.thread
            if context.get('mail.compose.message.mode') == 'mass_mail':
                if context.get('active_ids') and context.get('active_model'):
                    active_ids = context['active_ids']
                    active_model = context['active_model']
                else:
                    active_model = mail_wiz.model
                    active_model_pool = self.pool.get(active_model)
                    active_ids = active_model_pool.search(cr, uid, ast.literal_eval(mail_wiz.filter_id.domain), context=ast.literal_eval(mail_wiz.filter_id.context))
            else:
                active_model = mail_wiz.model
                active_ids = [int(mail_wiz.res_id)]
            active_model_pool = self.pool.get(active_model)
            if hasattr(active_model_pool, '_inherit') and 'mail.thread' in active_model_pool._inherit:
                mail_thread_enabled = True
            else:
                mail_thread_enabled = False

            if context.get('mail.compose.message.mode') == 'mass_mail':
                # Mass mailing: must render the template patterns
                for active_id in active_ids:
                    subject = self.render_template(cr, uid, mail_wiz.subject, active_model, active_id)
                    rendered_body = self.render_template(cr, uid, body, active_model, active_id)
                    email_from = self.render_template(cr, uid, mail_wiz.email_from, active_model, active_id)
                    email_to = self.render_template(cr, uid, mail_wiz.email_to, active_model, active_id)
                    email_cc = self.render_template(cr, uid, mail_wiz.email_cc, active_model, active_id)
                    email_bcc = self.render_template(cr, uid, mail_wiz.email_bcc, active_model, active_id)
                    reply_to = self.render_template(cr, uid, mail_wiz.reply_to, active_model, active_id)
    
                    # in mass-mailing mode we only schedule the mail for sending, it will be 
                    # processed as soon as the mail scheduler runs.
                    if mail_thread_enabled:
                        active_model_pool.message_append(cr, uid, [active_id],
                            subject, body_text=mail_wiz.body_text, body_html=mail_wiz.body_html, content_subtype=mail_wiz.content_subtype, state='outgoing',
                            email_to=email_to, email_from=email_from, email_cc=email_cc, email_bcc=email_bcc,
                            reply_to=reply_to, references=references, attachments=attachment, headers=headers, context=context)
                    else:
                        mail_message.schedule_with_attach(cr, uid, email_from, to_email(email_to), subject, rendered_body,
                            model=mail_wiz.model, email_cc=to_email(email_cc), email_bcc=to_email(email_bcc), reply_to=reply_to,
                            attachments=attachment, references=references, res_id=active_id,
                            content_subtype=mail_wiz.content_subtype, headers=headers, context=context)
            else:
                # normal mode - no mass-mailing
                if mail_thread_enabled:
                    msg_ids = active_model_pool.message_append(cr, uid, active_ids,
                            mail_wiz.subject, body_text=mail_wiz.body_text, body_html=mail_wiz.body_html, content_subtype=content_subtype, state='outgoing',
                            email_to=mail_wiz.email_to, email_from=mail_wiz.email_from, email_cc=mail_wiz.email_cc, email_bcc=mail_wiz.email_bcc,
                            reply_to=mail_wiz.reply_to, references=references, attachments=attachment, headers=headers, context=context,
                            type=type)
                else:
                    msg_ids = [mail_message.schedule_with_attach(cr, uid, mail_wiz.email_from, to_email(mail_wiz.email_to), mail_wiz.subject, body_text,
                        model=mail_wiz.model, email_cc=to_email(mail_wiz.email_cc), email_bcc=to_email(mail_wiz.email_bcc), reply_to=mail_wiz.reply_to,
                        attachments=attachment, references=references, res_id=int(mail_wiz.res_id),
                        content_subtype=mail_wiz.content_subtype, headers=headers, context=context)]
                # in normal mode, we send the email immediately, as the user expects us to (delay should be sufficiently small)
                mail_message.send(cr, uid, msg_ids, context=context)

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
        """ Overrides the default implementation to provide more default field values
            related to the corresponding CRM case.
        """
        result = super(mail_compose_message_extended, self).get_value(cr, uid,  model, res_id, context=context)
        model_obj = self.pool.get(model)
        if getattr(model_obj, '_mail_compose_message', False) and res_id:
            data = model_obj.browse(cr, uid , res_id, context)
            result.update({
                'email_to': data.email_from or False,
                'email_cc': tools.ustr(data.email_cc or ''),
                'subject': data.name or False,
            })
            if hasattr(data, 'section_id'):
                result['reply_to'] = data.section_id and data.section_id.reply_to or False
        return result

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
