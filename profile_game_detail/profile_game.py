# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2004-2008 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# $Id$
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
import pooler
import time
from mx import DateTime
import datetime
# develop following dashboard
#Financial Manager (Fabien Pinckaers, put here the name of the financial manager user)
#-----------------

#Expenses Forecast: _________
#Current Treasory: _________

#Loans : [ button : Ask for a Loan ]
#* Total to Reimburse : ______
#* To Reimburse this Year : _____

#Directeur RH (Marc Dupont)
#--------------------------

#HR Budget : ________
#Budget Spread of the Year: (one2many on a account.budget)
#    Budget     | Amount

#Sales Manager (Stephane Dubois)
#-------------------------------

#Sales Y-1 : _______
#Sales Forecast : _______
#Margin Forecast : ________

#Logistic Manager (Marc Andre)
#-----------------------------

#Average Stock Y-1  : ______
#Average Stock Forecast : ____
#Costs of Purchases Forecast : _______

#Objectives Achievement (colspan=4)
#----------------------

#Turnover Y-1 : _____ | Total Benefits : _____ | # of Products Sold : __
#Turnover Growth : __ | Benefits Growth: _____ | Growth Products : _____
#Selected Objective: Maximise Turnover         | Current Note : 12/20, B


#Total Expenses, Total Treasury, Total Expenses Y-1; are computed functions that
#compute the balance of accounts of a particular type for the year defined in
#the context (fiscalyear). If no year is defined in the context, it's the
#current fiscal year. When I say Y-1, it means, current fiscalyear minus 1 year.


class profile_game_retail(osv.osv):
    _name="profile.game.retail"
    def _calculate_detail(self, cr, uid, ids, field_names, arg, context):
        res = {}
        fiscal_obj = self.pool.get('account.fiscalyear')
        account_obj = self.pool.get('account.account')
        account_type_obj = self.pool.get('account.account.type')
        for val in self.browse(cr, uid, ids,context=context):
            res[val.id] = {}
            fiscalyear_id=context.get('fiscalyear_id', False)
            if not fiscalyear_id:
                fiscalyear_id=fiscal_obj.find(cr,uid)
            fiscalyear=fiscal_obj.browse(cr,uid,fiscalyear_id)
            # calculate finace detail
            if 'expenses_forecast' in field_names or 'total_refund' in field_names or 'total_current_refund' in field_names:
                mapping={
                    'expenses_forecast' : 'in_invoice',
                    'total_refund' : 'out_refund',
                    'total_current_refund' : 'in_refund',
                }
                for field in mapping:
                    sql="""
                    select
                    	sum(invoice.amount_total) as total,
                    from account_invoice invoice
                    where invoice.type in ('%s') and date_invoice>='%s' and date_invoice<='%s'
                    """%(mapping[field],fiscalyear.date_start,fiscalyear.date_stop)
                    cr.execute(sql)
                    result=cr.fetchall()[0]
                    res[val.id][field]=result[0] and result[0] or 0.0
            if 'current_treasury' in field_names:
                type_ids=account_type_obj.search(cr,uid,[('code','=','cash')])
                cash_account_ids=account_obj.search(cr,uid,[('user_type','in',type_ids)])
                total_balance=0
                for cash_account in account_obj.browse(cr,uid,cash_account_ids):
                    total_balance+=cash_account.balance
                res[val.id]['current_treasury']=total_balance

            # calculate hr detail

           # calculate logistic detail

            if 'last_avg_stock' in field_names or 'avg_stock_forcast' in field_names or 'cost_purchase_forcast' in field_names:
                for field in field_names:
                   if field =='last_avg_stock':
                        start_date=prev_fy_datestart
                        stop_date=prev_fy_datestop
                   else:
                        start_date=fiscalyear.date_start
                        stop_date=fiscalyear.date_stop

                   if field =='last_avg_stock' or field =='avg_stock_forcast':
                       sql="""
                                select
                                    avg(invoice_line.quantity) as avg_qty
                                from account_invoice_line invoice_line
                                where invoice_line.invoice_id in (select id from account_invoice invoice
                                where invoice.type ='out_invoice' and date_invoice>='%s' and date_invoice<='%s')
                                """%(start_date,stop_date)
                       cr.execute(sql)
                       result=cr.fetchall()[0]
                       res[val.id][field]=result[0] or 0.0
                   else:
                        inv_type=['in_invoice','out_refund']
                        sql="""
                            select
                                sum(invoice.amount_total) as total
                            from account_invoice invoice
                            where invoice.type in ('%s') and date_invoice>='%s' and date_invoice<='%s'
                            """%("','".join(inv_type),start_date,stop_date)
                        cr.execute(sql)
                        result=cr.fetchall()[0]
                        res[val.id][field]=result[0] or 0.0

            # calculate sales detail

            if 'last_total_sale' in field_names or 'sale_forcast' in field_names or 'margin_forcast' in field_names:
                for field in field_names:
                   if field =='last_total_sale':
                        start_date=prev_fy_datestart
                        stop_date=prev_fy_datestop
                   else:
                        start_date=fiscalyear.date_start
                        stop_date=fiscalyear.date_stop

                   if field =='last_total_sale' or field =='sale_forcast':
                        sql="""
                            select
                                sum(invoice.amount_total) as total
                            from account_invoice invoice
                            where invoice.type ='out_invoice' and date_invoice>='%s' and date_invoice<='%s'
                            """%(start_date,stop_date)
                        cr.execute(sql)
                        result=cr.fetchall()[0]
                        res[val.id][field]=result[0] or 0.0
                   else:
                         invoice_types=['in_invoice','out_invoice']
                         sql="""
                            select
                                sum(l.quantity * l.price_unit) as total,
                                sum(l.quantity * product.standard_price) as normal_cost
                            from account_invoice_line l
                            left join account_invoice i on (l.invoice_id = i.id)
                            left join product_template product on (product.id=l.product_id)
                            where i.type in ('%s') and i.date_invoice>='%s' and i.date_invoice<='%s'
                            """%("','".join(invoice_types),start_date,stop_date)
                         cr.execute(sql)
                         result=cr.fetchall()[0]
                         res[val.id][field]=result[0] or 0.0 - result[1] or 0.0

            # calculate Objectives Achievement
            if 'last_turnover' in field_names or 'total_benefit' in field_names or 'total_sold_products' in field_names \
                or 'turnover_growth' in field_names or 'benefits_growth' in field_names or 'products_growth' in field_names:
                for field in field_names:
                    if field =='last_turnover':
                        start_date=prev_fy_datestart
                        stop_date=prev_fy_datestop
                        sql="""
                        select
                            sum(l.quantity * l.price_unit) as total
                        from account_invoice_line l
                        left join account_invoice i on (l.invoice_id = i.id)
                        left join product_template product on (product.id=l.product_id)
                        where i.type ='out_invoice' and i.date_invoice>='%s' and i.date_invoice<='%s'
                        """%(start_date,stop_date)
                        cr.execute(sql)
                        result=cr.fetchall()[0]
                        res[val.id][field]=result[0] or 0.0

                    elif field =='total_benefit':
                        start_date=fiscalyear.date_start
                        stop_date=fiscalyear.date_stop
                        sql1="""
                        select
                            sum(l.quantity * l.price_unit) as total,
                            sum(l.quantity * product.list_price) as sale_expected,
                            sum(l.quantity * product.standard_price) as normal_cost
                        from account_invoice_line l
                        left join account_invoice i on (l.invoice_id = i.id)
                        left join product_template product on (product.id=l.product_id)
                        where i.type ='out_invoice' and i.date_invoice>='%s' and i.date_invoice<='%s'
                        """%(start_date,stop_date)
                        cr.execute(sql1)
                        result1=cr.fetchall()[0]

                        sql2="""
                        select
                            sum(l.quantity * l.price_unit) as total
                        from account_invoice_line l
                        left join account_invoice i on (l.invoice_id = i.id)
                        left join product_template product on (product.id=l.product_id)
                        where i.type ='in_invoice' and i.date_invoice>='%s' and i.date_invoice<='%s'
                        """%(start_date,stop_date)
                        cr.execute(sql2)
                        result2=cr.fetchall()[0]
                        res[val.id][field]=((result1[1] or 0.0) -(result1[0] or 0.0))-((result1[2] or 0.0) -(result2[0] or 0.0))

                    elif field =='total_sold_products':
                        start_date=fiscalyear.date_start
                        stop_date=fiscalyear.date_stop
                        sql="""
                                select
                                    sum(invoice_line.quantity) as total
                                from account_invoice_line invoice_line
                                where invoice_line.invoice_id in (select id from account_invoice invoice
                                where invoice.type ='out_invoice' and date_invoice>='%s' and date_invoice<='%s')
                                """%(start_date,stop_date)
                        cr.execute(sql)
                        result=cr.fetchall()[0]
                        res[val.id][field]=result[0] or 0.0

                    elif field =='turnover_growth':
                        start_date=prev_fy_datestart
                        stop_date=prev_fy_datestop
                        sql="""
                            select
                                sum(l.quantity * l.price_unit) as total
                            from account_invoice_line l
                            left join account_invoice i on (l.invoice_id = i.id)
                            left join product_template product on (product.id=l.product_id)
                            where i.type ='out_invoice' and i.date_invoice>='%s' and i.date_invoice<='%s'
                            """%(start_date,stop_date)
                        cr.execute(sql)
                        result=cr.fetchall()[0]

                        start_date=fiscalyear.date_start
                        stop_date=fiscalyear.date_stop
                        turnover_cur=0.0
                        sql1="""
                        select
                            sum(l.quantity * l.price_unit) as total,
                            sum(l.quantity * product.list_price) as sale_expected,
                            sum(l.quantity * product.standard_price) as normal_cost
                        from account_invoice_line l
                        left join account_invoice i on (l.invoice_id = i.id)
                        left join product_template product on (product.id=l.product_id)
                        where i.type ='out_invoice' and i.date_invoice>='%s' and i.date_invoice<='%s'
                        """%(start_date,stop_date)
                        cr.execute(sql1)
                        result1=cr.fetchall()[0]
                        turnover_cur=result1[0] or 0.0
                        if result[0] or 0.0  == 0.0:
                            res[val.id][field]=0.0
                        else:
                            res[val.id][field]=((turnover_cur - result[0] or 0.0)*100)/ result[0] or 0.0

                    elif field =='benefits_growth':
                        start_date=prev_fy_datestart
                        stop_date=prev_fy_datestop
                        sql1="""
                            select
                                sum(l.quantity * l.price_unit) as total,
                                sum(l.quantity * product.list_price) as sale_expected,
                                sum(l.quantity * product.standard_price) as normal_cost
                            from account_invoice_line l
                            left join account_invoice i on (l.invoice_id = i.id)
                            left join product_template product on (product.id=l.product_id)
                            where i.type ='out_invoice' and i.date_invoice>='%s' and i.date_invoice<='%s'
                            """%(start_date,stop_date)
                        cr.execute(sql1)
                        result1=cr.fetchall()[0]

                        sql2="""
                            select
                                sum(l.quantity * l.price_unit) as total
                            from account_invoice_line l
                            left join account_invoice i on (l.invoice_id = i.id)
                            left join product_template product on (product.id=l.product_id)
                            where i.type ='in_invoice' and i.date_invoice>='%s' and i.date_invoice<='%s'
                            """%(start_date,stop_date)
                        cr.execute(sql2)
                        result2=cr.fetchall()[0]
                        benefit_prev=((result1[1] or 0.0) -(result1[0] or 0.0))-((result1[2] or 0.0) -(result2[0] or 0.0))


                        start_date=fiscalyear.date_start
                        stop_date=fiscalyear.date_stop

                        sql1="""
                        select
                            sum(l.quantity * l.price_unit) as total,
                            sum(l.quantity * product.list_price) as sale_expected,
                            sum(l.quantity * product.standard_price) as normal_cost
                        from account_invoice_line l
                        left join account_invoice i on (l.invoice_id = i.id)
                        left join product_template product on (product.id=l.product_id)
                        where i.type ='out_invoice' and i.date_invoice>='%s' and i.date_invoice<='%s'
                        """%(start_date,stop_date)
                        cr.execute(sql1)
                        result1=cr.fetchall()[0]

                        sql2="""
                        select
                            sum(l.quantity * l.price_unit) as total
                        from account_invoice_line l
                        left join account_invoice i on (l.invoice_id = i.id)
                        left join product_template product on (product.id=l.product_id)
                        where i.type ='in_invoice' and i.date_invoice>='%s' and i.date_invoice<='%s'
                        """%(start_date,stop_date)
                        cr.execute(sql2)
                        result2=cr.fetchall()[0]
                        benefit_cur=((result1[1] or 0.0) -(result1[0] or 0.0))-((result1[2] or 0.0) -(result2[0] or 0.0))

                        if benefit_prev == 0.0:
                            res[val.id][field]=0.0
                        else:
                            res[val.id][field]=((benefit_cur-benefit_prev)*100)/benefit_prev

                    elif field =='products_growth':
                        start_date=prev_fy_datestart
                        stop_date=prev_fy_datestop
                        sql="""
                                select
                                    sum(invoice_line.quantity) as total
                                from account_invoice_line invoice_line
                                where invoice_line.invoice_id in (select id from account_invoice invoice
                                where invoice.type ='out_invoice' and date_invoice>='%s' and date_invoice<='%s')
                                """%(start_date,stop_date)
                        cr.execute(sql)
                        result=cr.fetchall()[0]
                        prod_sold_prev=result[0] or 0.0

                        start_date=fiscalyear.date_start
                        stop_date=fiscalyear.date_stop
                        sql="""
                                select
                                    sum(invoice_line.quantity) as total
                                from account_invoice_line invoice_line
                                where invoice_line.invoice_id in (select id from account_invoice invoice
                                where invoice.type ='out_invoice' and date_invoice>='%s' and date_invoice<='%s')
                                """%(start_date,stop_date)
                        cr.execute(sql)
                        result=cr.fetchall()[0]
                        prod_sold_cur=result[0] or 0.0

                        if prod_sold_prev == 0.0:
                            res[val.id][field]=0.0
                        else:
                            res[val.id][field]=((prod_sold_cur -prod_sold_prev)*100)/prod_sold_prev


        return res
    _columns = {
        'name':fields.char('Name',size=64),
        'players':fields.selection([('3','3'),('4','4')],'Number of Players'),
        'objectives':fields.selection([
            ('on_max_turnover','Maximise Turnover of Last Year'),
            ('on_max_cumulative','Maximise Cumulative Benefit'),
            ('on_max_products_sold','Maximise Number of Products Sold')],'Objectives'),
        'years':fields.selection([
            ('3','3 Years (40 minutes)'),
            ('5','5 Years (1 hour)'),
            ('7','7 Years (1 hours and 20 minutes)')],'Number of Turns'),
        'difficulty':fields.selection([
            ('easy','Easy'),
            ('medium','Medium'),
            ('hard','Hard')],'Difficulty'),
        'expenses_forecast' : fields.function(_calculate_detail, method=True, type='float', string='Expenses Forecast', multi='finance',help="Sum of all budgets of the year"),
        'current_treasury' : fields.function(_calculate_detail, method=True, type='float', string='Current treasury', multi='finance',help="Balance of all Cash Accounts"),
        'total_refund' : fields.function(_calculate_detail, method=True, type='float', string='Total to Reimburse', multi='finance',help="Total to Reimburse"),
        'total_current_refund' : fields.function(_calculate_detail, method=True, type='float', string='To Reimburse this Year', multi='finance',help="To Reimburse this Year"),

        'hr_budget' : fields.function(_calculate_detail, method=True, type='float', string='HR Budget', multi='hr',help="HR Budget"),

        'last_total_sale' : fields.function(_calculate_detail, method=True, type='float', string='Total Sales in Last Year', multi='sale',help="Total Sales in Last Year"),
        'sale_forcast' : fields.function(_calculate_detail, method=True, type='float', string='Sales Forcast', multi='sale',help="Sales Forcast"),
        'margin_forcast' : fields.function(_calculate_detail, method=True, type='float', string='Margin Forcast', multi='sale',help="Margin Forcast"),

        'last_avg_stock' : fields.function(_calculate_detail, method=True, type='float', string='Avg. stock in Last year', multi='logistic',help="Avg. stock in Last year"),
        'avg_stock_forcast' : fields.function(_calculate_detail, method=True, type='float', string='Avg. Stock Forcast', multi='logistic',help="Avg. Stock Forcast"),
        'cost_purchase_forcast' : fields.function(_calculate_detail, method=True, type='float', string='Costs of Purchases Forecast', multi='logistic',help="Costs of Purchases Forecast"),

        'last_turnover' : fields.function(_calculate_detail, method=True, type='float', string='Turnover in last year', multi='objectives',help="Turnover in last year"),
        'total_benefit' : fields.function(_calculate_detail, method=True, type='float', string='Total Benefits', multi='objectives',help="Total Benefits"),
        'total_sold_products' : fields.function(_calculate_detail, method=True, type='float', string='# of Products Sold', multi='objectives',help="# of Products Sold"),
        'turnover_growth' : fields.function(_calculate_detail, method=True, type='float', string='Turnover Growth', multi='objectives',help="Turnover Growth"),
        'benefits_growth' : fields.function(_calculate_detail, method=True, type='float', string='Benefits Growth', multi='objectives',help="Benefits Growth"),
        'products_growth' : fields.function(_calculate_detail, method=True, type='float', string='Growth Products', multi='objectives',help="Growth Products"),
        'note':fields.text('Notes'),
    }

#    _defaults={
#               'total_refund' : lambda *a: 0.20,
#               'cost_purchase_forcast' : lambda *a: 0.20,
#               'total_sold_products' : lambda *a: 0.20
#               }

profile_game_retail()

class profile_game_config_wizard(osv.osv_memory):
    _name='profile.game.config.wizard'
    _columns = {
        'players':fields.selection([('3','3'),('4','4')],'Number of Players',required=True),
        'finance_name':fields.char('Name of Financial Manager',size='64'),
        'finance_email':fields.char('Email of Financial Manager',size='64'),
        'hr_name':fields.char('Name of Hurman Ressources Manager',size='64'),
        'hr_email':fields.char('Email of Hurman Ressources Manager',size='64'),
        'logistic_name':fields.char('Name of Logistic Manager',size='64'),
        'logistic_email':fields.char('Email of Logistic Manager',size='64'),
        'sales_name':fields.char('Name of Sales Manager',size='64'),
        'sales_email':fields.char('Email of Sales Manager',size='64'),
        'objectives':fields.selection([
            ('on_max_turnover','Maximise Turnover of Last Year'),
            ('on_max_cumulative','Maximise Cumulative Benefit'),
            ('on_max_products_sold','Maximise Number of Products Sold')],'Objectives',required=True),
        'years':fields.selection([
            ('3','3 Years (40 minutes)'),
            ('5','5 Years (1 hour)'),
            ('7','7 Years (1 hours and 20 minutes)')],'Number of Turns',required=True),
        'difficulty':fields.selection([
            ('easy','Easy'),
            ('medium','Medium'),
            ('hard','Hard')],'Difficulty',required=True),
    }
    def action_cancel(self,cr,uid,ids,conect=None):
        return {
                'view_type': 'form',
                "view_mode": 'form',
                'res_model': 'ir.actions.configuration.wizard',
                'type': 'ir.actions.act_window',
                'target':'new',
         }


    def action_run(self, cr, uid, ids, context=None):
        game_obj=self.pool.get('profile.game.retail')
        fiscal_obj = self.pool.get('account.fiscalyear')
        user_obj=self.pool.get('res.users')
        emp_obj=self.pool.get('hr.employee')
        for res in self.read(cr,uid,ids,context=context):
            if res.get('id',False):
                del res['id']
            game_vals={
                'players':res['players'],
                'objectives':res['objectives'],
                'years':res['years'],
                'difficulty':res['difficulty'],
            }
            game_obj.create(cr,uid,game_vals,context=context)
            lower=-2
            years=int(res['years'])
            players=int(res['players'])
            start_date=DateTime.strptime(time.strftime('%Y-01-01'),'%Y-%m-%d')
            stop_date=DateTime.strptime(time.strftime('%Y-12-31'),'%Y-%m-%d')
            while lower<=years:
                new_start_date=datetime.date(start_date.year+lower,1,1)
                new_stop_date=datetime.date(stop_date.year+lower,12,31)
                name=new_start_date.strftime('%Y')
                vals={
                    'name':name,
                    'code':name,
                    'date_start':new_start_date,
                    'date_stop':new_stop_date,
                }
                new_id=fiscal_obj.create(cr, uid, vals, context=context)
                fiscal_obj.create_period3(cr,uid,[new_id])
                lower+=1
            for user_name in ['finance','sales','logistic','hr']:
                if user_name=='hr' and players<4:
                    continue
                user_ids=user_obj.name_search(cr,uid,user_name)
                user_id=len(user_ids) and user_ids[0][0] or False
                name=res.get(user_name+'_name','')
                if name:
                    email=res.get(user_name+'_email','')
                    emp_ids=emp_obj.search(cr,uid,[('user_id','=',user_id)])
                    if not len(emp_ids):
                        emp_obj.create(cr,uid,{
                                'name':name.strip(),
                                'work_email':email
                        })
                    else:
                        emp_obj.write(cr,uid,emp_ids,{
                                'name':name.strip(),
                                'work_email':email
                        })
                    user_obj.write(cr,uid,[user_id],{'name':name.strip()})
        return {
                'view_type': 'form',
                "view_mode": 'form',
                'res_model': 'ir.actions.configuration.wizard',
                'type': 'ir.actions.act_window',
                'target':'new',
            }


profile_game_config_wizard()

