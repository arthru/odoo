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
import crm_report

class crm_phonecall_report(osv.osv):
    """ Phone calls by user and section """

    _name = "crm.phonecall.report"
    _description = "Phone calls by user and section"
    _auto = False
    _inherit = "crm.case.report"

    _columns = {
        'delay_close': fields.float('Delay to close', digits=(16,2),readonly=True, group_operator="avg",help="Number of Days to close the case"),
        'categ_id': fields.many2one('crm.case.categ', 'Category', \
                        domain="[('section_id','=',section_id),\
                        ('object_id.model', '=', 'crm.phonecall')]"),
        'partner_id': fields.many2one('res.partner', 'Partner' , readonly=True),
        'company_id': fields.many2one('res.company', 'Company', readonly=True),
        'priority': fields.selection(crm_report.AVAILABLE_PRIORITIES, 'Priority'),
        'date_closed': fields.datetime('Closed', readonly=True),
        'opportunity_id': fields.many2one ('crm.opportunity', 'Opportunity'),
        'canal_id': fields.many2one('res.partner.canal','Channel',domain="[('section_id','=',section_id),('object_id.model', '=', 'crm.phonecall')]"),
        'duration': fields.float('Duration',readonly=True),
        'date': fields.datetime('Planned Date')
    }

    def init(self, cr):

        """ Phone Calls By User And Section
            @param cr: the current row, from the database cursor,
        """

        tools.drop_view_if_exists(cr, 'crm_phonecall_report')
        cr.execute("""
            create or replace view crm_phonecall_report as (
                select
                    min(c.id) as id,
                    to_char(c.create_date, 'YYYY') as name,
                    to_char(c.create_date, 'MM') as month,
                    to_char(c.create_date, 'YYYY-MM-DD') as day,
                    c.state,
                    c.user_id,
                    c.section_id,
                    c.categ_id,
                    c.partner_id,
                    c.company_id,
                    count(*) as nbr,
                    0 as avg_answers,
                    0.0 as perc_done,
                    0.0 as perc_cancel,
                    c.priority as priority,
                    c.date_closed as date_closed,
                    c.opportunity_id as opportunity_id,
                    c.canal_id as canal_id,
                    c.date as date,
                    sum(c.duration) as duration,
                    date_trunc('day',c.create_date) as create_date,
                    avg(extract('epoch' from (c.date_closed-c.create_date)))/(3600*24) as  delay_close
                from
                    crm_phonecall c
                group by to_char(c.create_date, 'YYYY'), to_char(c.create_date, 'MM'),\
                     c.state, c.user_id,c.section_id, c.categ_id,c.partner_id,c.company_id
                     ,to_char(c.create_date, 'YYYY-MM-DD'),c.create_date
                     ,c.priority,c.date_closed,opportunity_id,canal_id,c.date
            )""")

crm_phonecall_report()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
