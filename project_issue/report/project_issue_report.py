from osv import fields,osv
import tools
from crm import crm

class project_issue_report(osv.osv):
    _name = "project.issue.report"
    _auto = False
    _inherit = "crm.case.report"
    _columns = {
        'categ_id': fields.many2one('crm.case.categ', 'Category', domain="[('section_id','=',section_id),('object_id.model', '=', 'project.issue.report')]"),
        'stage_id': fields.many2one ('crm.case.stage', 'Stage', domain="[('object_id.model', '=', 'project.issue.report')]"),
        'nbr': fields.integer('# of Issues', reaadonly=True),
        'delay_close': fields.char('Delay to close', size=20, readonly=True),
        'company_id' : fields.many2one('res.company', 'Company'),
        'priority': fields.selection(crm.AVAILABLE_PRIORITIES, 'Priority'),
        'project_id':fields.many2one('project.project', 'Project'),
        'type_id': fields.many2one('crm.case.resource.type', 'Bug Type', domain="[('object_id.model', '=', 'project.issue')]"),
        'date_closed': fields.datetime('Close Date', readonly=True),
    }
    def init(self, cr):
        tools.drop_view_if_exists(cr, 'project_issue_report')
        cr.execute("""
            create or replace view project_issue_report as (
                select
                    min(c.id) as id,
                    to_char(c.create_date, 'YYYY') as name,
                    to_char(c.create_date, 'MM') as month,
                    c.state,
                    c.user_id,
                    c.section_id,
                    c.categ_id,
                    c.stage_id,
                    to_char(c.date_closed, 'YYYY/mm/dd') as date_closed,
                    u.company_id as company_id,
                    c.priority as priority,
                    c.project_id as project_id,
                    c.type_id as type_id,
                    count(*) as nbr,
                    to_char(avg(date_closed-c.create_date), 'DD"d" HH24:MI:SS') as delay_close
                from
                    project_issue c
                left join
                    res_users u on (c.id = u.id)
                group by to_char(c.create_date, 'YYYY'), to_char(c.create_date, 'MM'), c.state, c.user_id,c.section_id,c.categ_id,c.stage_id
                ,c.date_closed,u.company_id,c.priority,c.project_id,c.type_id
            )""")


project_issue_report()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
