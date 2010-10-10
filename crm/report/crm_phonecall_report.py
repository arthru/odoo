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

from osv import fields,osv
import tools
from crm import crm

AVAILABLE_STATES = [
    ('draft','Draft'),
    ('open','Open'),
    ('cancel', 'Cancelled'),
    ('done', 'Closed'),
    ('pending','Pending')
]


class crm_phonecall_report(osv.osv):
    """ Phone calls by user and section """

    _name = "crm.phonecall.report"
    _description = "Phone calls by user and section"
    _auto = False
    
    def _get_data(self, cr, uid, ids, field_name, arg, context={}):

        """ @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param ids: List of case and section Data’s IDs
            @param context: A standard dictionary for contextual values """

        res = {}
        state_perc = 0.0
        avg_ans = 0.0

        for case in self.browse(cr, uid, ids, context):
            if field_name != 'avg_answers':
                state = field_name[5:]
                cr.execute("select count(*) from crm_lead where \
                    section_id =%s and state='%s'"%(case.section_id.id, state))
                state_cases = cr.fetchone()[0]
                perc_state = (state_cases / float(case.nbr)) * 100

                res[case.id] = perc_state
            else:
                model_name = self._name.split('report.')
                if len(model_name) < 2:
                    res[case.id] = 0.0
                else:
                    model_name = model_name[1]

                    cr.execute("select count(*) from crm_case_log l, ir_model m \
                         where l.model_id=m.id and m.model = '%s'" , model_name)
                    logs = cr.fetchone()[0]

                    avg_ans = logs / case.nbr
                    res[case.id] = avg_ans

        return res

    _columns = {
        'name': fields.char('Year', size=64, required=False, readonly=True),
        'user_id':fields.many2one('res.users', 'User', readonly=True),
        'section_id':fields.many2one('crm.case.section', 'Section', readonly=True),
        'priority': fields.selection(crm.AVAILABLE_PRIORITIES, 'Priority'),
        'nbr': fields.integer('# of Cases', readonly=True),
        'state': fields.selection(AVAILABLE_STATES, 'State', size=16, readonly=True),
        'avg_answers': fields.function(_get_data, string='Avg. Answers', method=True, type="integer"),
        'perc_done': fields.function(_get_data, string='%Done', method=True, type="float"),
        'perc_cancel': fields.function(_get_data, string='%Cancel', method=True, type="float"),
        'month':fields.selection([('01', 'January'), ('02', 'February'), \
                                  ('03', 'March'), ('04', 'April'),\
                                  ('05', 'May'), ('06', 'June'), \
                                  ('07', 'July'), ('08', 'August'),\
                                  ('09', 'September'), ('10', 'October'),\
                                  ('11', 'November'), ('12', 'December')], 'Month', readonly=True),
        'create_date': fields.datetime('Create Date', readonly=True),
        'day': fields.char('Day', size=128, readonly=True), 
        'delay_close': fields.float('Delay to close', digits=(16,2),readonly=True, group_operator="avg",help="Number of Days to close the case"),
        'duration': fields.float('Duration', digits=(16,2),readonly=True, group_operator="avg"),
        'delay_open': fields.float('Delay to open',digits=(16,2),readonly=True, group_operator="avg",help="Number of Days to open the case"),
        'categ_id': fields.many2one('crm.case.categ', 'Category', \
                        domain="[('section_id','=',section_id),\
                        ('object_id.model', '=', 'crm.phonecall')]"),
        'partner_id': fields.many2one('res.partner', 'Partner' , readonly=True),
        'company_id': fields.many2one('res.company', 'Company', readonly=True),
        'opening_date': fields.date('Opening Date', readonly=True),
        'creation_date': fields.date('Creation Date', readonly=True),
        'date_closed': fields.date('Close Date', readonly=True),
    }

    def init(self, cr):

        """ Phone Calls By User And Section
            @param cr: the current row, from the database cursor,
        """
        tools.drop_view_if_exists(cr, 'crm_phonecall_report')
        cr.execute("""
            create or replace view crm_phonecall_report as (
                select
                    id,
                    to_char(c.date, 'YYYY') as name,
                    to_char(c.date, 'MM') as month,
                    to_char(c.date, 'YYYY-MM-DD') as day,
                    to_char(c.create_date, 'YYYY-MM-DD') as creation_date,
                    to_char(c.date_open, 'YYYY-MM-DD') as opening_date,
                    to_char(c.date_closed, 'YYYY-mm-dd') as date_closed,
                    c.state,
                    c.user_id,
                    c.section_id,
                    c.categ_id,
                    c.partner_id,
                    c.duration,
                    c.company_id,
                    c.priority,
                    1 as nbr,
                    0 as avg_answers,
                    0.0 as perc_done,
                    0.0 as perc_cancel,
                    date_trunc('day',c.create_date) as create_date,
                    extract('epoch' from (c.date_closed-c.create_date))/(3600*24) as  delay_close,
                    extract('epoch' from (c.date_open-c.create_date))/(3600*24) as  delay_open
                from
                    crm_phonecall c
            )""")
crm_phonecall_report()
