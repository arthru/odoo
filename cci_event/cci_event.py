# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2007 TINY SPRL. (http://tiny.be) All Rights Reserved.
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

from osv import fields,osv
from osv import orm
import netsvc
import pooler

class event_meeting_table(osv.osv):
    _name="event.meeting.table"
    _description="event.meeting.table"
    _columns={
        'partner_id1':fields.many2one('res.partner','First Partner',required=True),
        'partner_id2':fields.many2one('res.partner','Second Partner', required=True),
        'event_id':fields.many2one('event.event','Related Event', required=True),
        'contact_id1':fields.many2one('res.partner.contact','First Contact',required=True),
        'contact_id2':fields.many2one('res.partner.contact','Second Contact', required=True),
        'service':fields.integer('Service', required=True),
        'table':fields.char('Table',size=10,required=True),
        }
event_meeting_table()


class event_check_type(osv.osv):
    _name="event.check.type"
    _description="event.check.type"
    _columns={
        'name':fields.char('Name',size=20,required=True),
        }
event_check_type()

class event(osv.osv):

    def cci_event_fixed(self, cr, uid, ids, *args):
        self.write(cr, uid, ids, {'state':'fixed',})
        return True

    def cci_event_open(self, cr, uid, ids, *args):
        self.write(cr, uid, ids, {'state':'open',})
        return True

    def cci_event_confirm(self, cr, uid, ids, *args):
        self.write(cr, uid, ids, {'state':'confirm',})
        return True

    def cci_event_running(self, cr, uid, ids, *args):
        self.write(cr, uid, ids, {'state':'running',})
        return True

    def cci_event_done(self, cr, uid, ids, *args):
        self.write(cr, uid, ids, {'state':'done',})
        return True

    def cci_event_closed(self, cr, uid, ids, *args):
        self.write(cr, uid, ids, {'state':'closed',})
        return True

    def cci_event_cancel(self, cr, uid, ids, *args):
        self.write(cr, uid, ids, {'state':'cancel',})
        return True

    def onchange_check_type(self, cr, uid, id, type):
        if not type:
            return {}
        tmp=self.pool.get('event.type').browse(cr, uid, type)
        return {'value':{'check_type' : tmp.check_type.id}}

    def _group_names(self, cr, uid, ids):
        cr.execute('''
        SELECT distinct name
        FROM event_group
        ''')
        res = cr.fetchall()
        temp=[]
        for r in res:
            temp.append((r[0],r[0]))
        return temp

    _inherit="event.event"
    _description="event.event"
    _columns={
            'state': fields.selection([('draft','Draft'),('fixed','Fixed'),('open','Open'),('confirm','Confirmed'),('running','Running'),('done','Done'),('cancel','Canceled'),('closed','Closed')], 'State', readonly=True, required=True),
            'agreement_nbr':fields.char('Agreement Nbr',size=16),
            'note':fields.text('Note'),
            'fse_code':fields.char('FSE code',size=64),
            'fse_hours':fields.integer('FSE Hours'),
            'signet_type':fields.selection(_group_names, 'Signet type'),
            'localisation':fields.char('Localisation',size=20),
            'account_analytic_id':fields.many2one('account.analytic.account','Analytic Account'),
            'check_type': fields.many2one('event.check.type','Check Type'),
            }
event()

class event_check(osv.osv):
    _name="event.check"
    _description="event.check"

    def cci_event_check_block(self, cr, uid, ids, *args):
        self.write(cr, uid, ids, {'state':'block',})
        return True

    def cci_event_check_confirm(self, cr, uid, ids, *args):
        self.write(cr, uid, ids, {'state':'confirm',})
        return True

    def cci_event_check_cancel(self, cr, uid, ids, *args):
        self.write(cr, uid, ids, {'state':'cancel',})
        return True

    _columns={
        "name": fields.char('Name', size=128, required=True),
        "code": fields.char('Code', size=64),
        "reg_id": fields.many2one('event.registration','Inscriptions',required=True),
        "state": fields.selection([('draft','Draft'),('block','Blocked'),('confirm','Confirm'),('cancel','Cancel'),('asked','Asked')], 'State', readonly=True),#should be check (previous states :('open','Open'),('block','Blocked'),('paid','Paid'),('refused','Refused'),('asked','Asked')])
        "unit_nbr": fields.float('Value'),
        "type_id":fields.many2one('event.check.type','Type'),
        "date_reception":fields.date("Reception Date"),
        "date_limit":fields.date('Limit Date'),
        "date_submission":fields.date("Submission Date"),
        }
    _defaults = {
        'state': lambda *args: 'draft',
        'name': lambda *args: 'cheque',
    }

event_check()

class event_type(osv.osv):
    _inherit = 'event.type'
    _description= 'Event type'
    _columns = {
        'check_type': fields.many2one('event.check.type','Default Check Type'),
    }
event_type()

class event_group(osv.osv):
    _name= 'event.group'
    _description = 'event.group'
    _columns = {
        "name":fields.char('Group Name',size=20,required=True),
        "bookmark_name":fields.char('Value',size=128),
        "picture":fields.binary('Picture'),
        "type":fields.selection([('image','Image'),('text','Text')], 'Type',required=True)
        }
    _defaults = {
        'type': lambda *args: 'text',
    }

event_group()

class event_registration(osv.osv):

    def cci_event_reg_open(self, cr, uid, ids, *args):
        self.write(cr, uid, ids, {'state':'open',})
        self.pool.get('event.registration').mail_user(cr,uid,ids)
        cases = self.browse(cr, uid, ids)
        self.pool.get('event.registration')._history(cr, uid, cases, 'Open', history=True)
        return True

    def cci_event_reg_done(self, cr, uid, ids, *args):
        self.write(cr, uid, ids, {'state':'done',})
        cases = self.browse(cr, uid, ids)
        self.pool.get('event.registration')._history(cr, uid, cases, 'Done', history=True)
        return True

    def cci_event_reg_cancel(self, cr, uid, ids, *args):
        self.write(cr, uid, ids, {'state':'cancel',})
        cases = self.browse(cr, uid, ids)
        self.pool.get('event.registration')._history(cr, uid, cases, 'Cancel', history=True)
        return True

    def cal_check_amount(self, cr, uid, ids, name, arg, context={}):
        res = {}
        data_reg = self.browse(cr,uid,ids)
        for reg in data_reg:
            total = 0
            for check in reg.check_ids:
                total = total + check.unit_nbr
            res[reg.id] = total
        return res

    _inherit = 'event.registration'
    _description="event.registration"
    _columns={
            "contact_order_id":fields.many2one('res.partner.contact','Contact Order'),
            "group_id": fields.many2one('event.group','Event Group'),
            "cavalier": fields.boolean('Cavalier',help="Check if we should print papers with participant name"),
            "payment_mode":fields.many2one('payment.mode',"Payment Mode"),#should be check (m2o ?)
            "check_mode":fields.boolean('Check Mode'),
            "check_ids":fields.one2many('event.check','reg_id',"Check ids"),
            "payment_ids":fields.many2many("account.move.line","move_line_registration", "reg_id", "move_line_id","Payment", readonly=True),
            "training_authorization":fields.char('Training Auth.',size=12,help='Formation Checks Authorization number',readonly=True),
            "check_amount":fields.function(cal_check_amount,method=True,type='float', string='Check Amount')
    }
    _defaults = {
        'name': lambda *a: 'Registration',
    }

    def write(self, cr, uid, *args, **argv):
        if 'partner_invoice_id' in args[1] and args[1]['partner_invoice_id']:
            data_partner = self.pool.get('res.partner').browse(cr,uid,args[1]['partner_invoice_id'])
            if data_partner:
                args[1]['training_authorization'] = data_partner.training_authorization
        return super(event_registration, self).write(cr, uid, *args, **argv)

    def onchange_partner_id(self, cr, uid, ids, part, event_id, email=False):#override function for partner name.
        if part:
            data_partner = self.pool.get('res.partner').browse(cr,uid,part)
            if data_partner.alert_events:
                raise osv.except_osv('Error!',data_partner.alert_explanation or 'Partner is not valid')
        return super(event_registration,self).onchange_partner_id(cr, uid, ids, part, event_id, email)

    def onchange_partner_invoice_id(self, cr, uid, ids, event_id, partner_invoice_id):
        data={}
        context={}
        data['training_authorization']=data['unit_price']=False
        if partner_invoice_id:
            data_partner = self.pool.get('res.partner').browse(cr,uid,partner_invoice_id)
            data['training_authorization']=data_partner.training_authorization
        if not event_id:
            return {'value':data}
        data_event =  self.pool.get('event.event').browse(cr,uid,event_id)

        if data_event.product_id:
            if not partner_invoice_id:
                data['training_authorization']=False
                data['unit_price']=self.pool.get('product.product').price_get(cr, uid, [data_event.product_id.id],context=context)[data_event.product_id.id]
                return {'value':data}
            data_partner = self.pool.get('res.partner').browse(cr,uid,partner_invoice_id)
            context.update({'partner_id':data_partner})
            data['unit_price']=self.pool.get('product.product').price_get(cr, uid, [data_event.product_id.id],context=context)[data_event.product_id.id]
            return {'value':data}
        return {'value':data}

#   def pay_and_recon(self,cr,uid,reg,inv_obj,inv_id,context={}):
#
#       if reg.check_ids:
#           total = 0
#           writeoff_account_id = False # should be check
#           writeoff_journal_id = False # should be check
#           data_inv = inv_obj.browse(cr,uid,inv_id)
#           journal_obj = self.pool.get('account.journal')
#           wf_service = netsvc.LocalService('workflow')
#
#           for check in reg.check_ids:
#               total = total + check.unit_nbr

#           ids = self.pool.get('account.period').find(cr, uid, context=context)
#           period_id = False
#           if len(ids):
#               period_id = ids[0]
#
#           cash_id = journal_obj.search(cr, uid, [('type', '=', 'cash')])
#           acc_id = journal_obj.browse(cr, uid, cash_id[0], context).default_credit_account_id.id
#           wf_service.trg_validate(uid, 'account.invoice', inv_id, 'invoice_open', cr)
#           inv_obj.pay_and_reconcile(cr,uid,[inv_id],total, acc_id, period_id, cash_id[0], writeoff_account_id, period_id, writeoff_journal_id, context)


event_registration()


class account_move_line(osv.osv):
    _inherit = 'account.move.line'
    _columns={
        "case_id" : fields.many2many("event.registration","move_line_registration", "move_line_id", "reg_id","Registration"),
    }
account_move_line()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

