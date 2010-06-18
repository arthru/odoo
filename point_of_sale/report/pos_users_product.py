# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
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
from report import report_sxw


class pos_user_product(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        super(pos_user_product, self).__init__(cr, uid, name, context)
        self.total = 0.0
        self.localcontext.update({
                'time': time,
                'get_data':self._get_data,
                'get_user':self._get_user,
                'get_total':self._get_total,

                })
    def _get_data(self,o):
        data={}
        sql1=""" SELECT distinct(o.id) from account_bank_statement s, account_bank_statement_line l,pos_order o,pos_order_line i where  i.order_id=o.id and o.state='paid' and l.statement_id=s.id and l.pos_statement_id=o.id and s.id=%d"""%(o.id)
        self.cr.execute(sql1)
        data = self.cr.dictfetchall()
        a_l=[]
        for r in data:
            a_l.append(r['id'])
        if len(a):
            sql2="""SELECT sum(qty) as qty,l.price_unit*sum(l.qty) as amt,t.name as name from product_product p, product_template t, pos_order_line l where order_id IN %s and p.product_tmpl_id=t.id and l.product_id=p.id group by t.name, l.price_unit""",(tuple(a_l),)
            self.cr.execute(sql2)
            data = self.cr.dictfetchall()
        for d in data:
            self.total += d['amt']
        return data

    def _get_user(self,object):
        for o in object :
            sql = """select ru.name from account_bank_statement as abs,res_users ru
                                    where abs.user_id = ru.id
                                    and abs.id = %d"""%(o.id)
            self.cr.execute(sql)
            data = self.cr.fetchone()
            return data[0]
    def _get_total(self):
        return self.total

report_sxw.report_sxw('report.pos.user.product', 'account.bank.statement', 'addons/statement/report/pos_users_product.rml', parser=pos_user_product)
