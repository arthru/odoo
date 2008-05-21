import wizard
import pooler
import tools

from osv import fields,osv
import time
import netsvc
from tools.misc import UpdateableStr, UpdateableDict

email_send_form = '''<?xml version="1.0"?>
<form string="Send invoice/s by Email">
    <field name="to"/>
    <newline/>
    <field name="subject"/>
    <newline/>
    <separator colspan="4"/>
    <label string="Message:"/>
    <field name="text" nolabel="1" colspan="4"/>
</form>'''

email_send_fields = {
    'to': {'string':"To", 'type':'char', 'size':512, 'required':True},
    'subject': {'string':'Subject', 'type':'char', 'size':64, 'required':True},
    'text': {'string':'Message', 'type':'text', 'required':True}
}

email_done_form = '''<?xml version="1.0"?>
<form string="Send invoice/s by Email">
    <field name="email_sent"/>
</form>'''

email_done_fields = {
    'email_sent': {'string':'Quantity of Emails sent', 'type':'integer', 'readonly': True},
}


def _get_defaults(self, cr, uid, data, context):
    p = pooler.get_pool(cr.dbname)
    user = p.get('res.users').browse(cr, uid, uid, context)
    subject = user.company_id.name+'. Num.'
    text = '\n--' + user.signature

    invoices = p.get('account.invoice').browse(cr, uid, data['ids'], context)
    adr_ids = []
    partner_id = invoices[0].partner_id.id
    for inv in invoices:
#        if partner_id != inv.partner_id.id:
#            raise osv.except_osv('Warning', 'You have selected documents for different partners.')
#        if inv.number:
#            subject = subject + ' ' + inv.number
#        if inv.name:
#            text = inv.name + '\n' + text
        if inv.address_invoice_id.id not in adr_ids:
            adr_ids.append(inv.address_invoice_id.id)
        if inv.address_contact_id and inv.address_contact_id.id not in adr_ids:
            adr_ids.append(inv.address_contact_id.id)
    addresses = p.get('res.partner.address').browse(cr, uid, adr_ids, context)
    to = ''
    for adr in addresses:
        if adr.email:
            name = adr.name or adr.partner_id.name
            to = to + ',%s <%s>' % (name, adr.email)
    return {'to': to[1:], 'subject': subject, 'text': text}


def _send_mails(self, cr, uid, data, context):
    import re
    p = pooler.get_pool(cr.dbname)

    user = p.get('res.users').browse(cr, uid, uid, context)
    file_name = user.company_id.name.replace(' ','_')+'_invoice'
    account_smtpserver_id = p.get('email.smtpclient').search(cr, uid, [('type','=','account'),('state','=','confirm')], context=False)
    if not account_smtpserver_id:
        default_smtpserver_id = p.get('email.smtpclient').search(cr, uid, [('type','=','default'),('state','=','confirm')], context=False)
    smtpserver_id = account_smtpserver_id or default_smtpserver_id
    if not smtpserver_id:
        raise osv.except_osv('Error', 'No SMTP Server Defined!')
    smtpserver = p.get('email.smtpclient').browse(cr, uid, smtpserver_id, context=False)[0]

    nbr = 0
    for email in data['form']['to'].split(','):
        print email, data['form']['subject'], data['ids'], data['model'], file_name, data['form']['text']
#        state = smtpserver.send_email(cr, uid, smtpserver_id, email, data['form']['subject'], data['ids'], data['model'], file_name, data['form']['text'])
        state = smtpserver.send_email(cr, uid, smtpserver_id, email,data['form']['subject'],data['ids'],data['form']['text'],'account.invoice','Invoice')
        if not state:
            raise osv.except_osv('Error sending email', 'Please check the Server Configuration!')

        # Add a partner event
        #c_id = pooler.get_pool(cr.dbname).get('res.partner.canal').search(cr ,uid, [('name','ilike','EMAIL'),('active','=',True)])
        #c_id = c_id and c_id[0] or False
        #pooler.get_pool(cr.dbname).get('res.partner.event').create(cr, uid,
            #{'name': 'Email sent through mass mailing',
             #'partner_id': adr.partner_id.id,
             #'description': mail,
             #'canal_id': c_id,
             #'user_id': uid, })
        nbr += 1
    return {'email_sent': nbr}


class send_email(wizard.interface):
    states = {
        'init': {
            'actions': [_get_defaults],
            'result': {'type': 'form', 'arch': email_send_form, 'fields': email_send_fields, 'state':[('end','Cancel'), ('send','Send Email')]}
        },
        'send': {
            'actions': [_send_mails],
            'result': {'type': 'form', 'arch': email_done_form, 'fields': email_done_fields, 'state': [('end', 'End')] }
        }
    }
send_email('account.invoice.email_send')