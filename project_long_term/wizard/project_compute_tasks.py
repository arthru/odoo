# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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
import datetime
from resource.faces import *
from new import classobj
import operator

from tools.translate import _
from osv import osv, fields

import working_calendar as wkcal

class project_compute_tasks(osv.osv_memory):
    _name = 'project.compute.tasks'
    _description = 'Project Compute Tasks'
    _columns = {
        'project_id': fields.many2one('project.project', 'Project', required=True)
                }

    def compute_date(self, cr, uid, ids, context=None):
        """
        Schedule the tasks according to resource available and priority.
        """
        project_obj = self.pool.get('project.project')
        task_pool = self.pool.get('project.task')
        resource_obj = self.pool.get('resource.resource')
        user_obj = self.pool.get('res.users')

        if context is None:
            context = {}

        data = self.read(cr, uid, ids, [])[0]
        project_id = data['project_id']
        project = project_obj.browse(cr, uid, project_id, context=context)
        task_ids = task_pool.search(cr, uid, [('project_id', '=', project_id),
                                              ('state', 'in', ['draft', 'open', 'pending'])
                                              ])
        if task_ids:
            task_ids.sort()
            tasks = task_pool.browse(cr, uid, task_ids, context=context)
            calendar_id = project.resource_calendar_id and project.resource_calendar_id.id or False
            start_date = project.date_start
            if not project.date_start:
                start_date = datetime.datetime.now().strftime("%Y-%m-%d")
            date_start = datetime.datetime.strftime(datetime.datetime.strptime(start_date, "%Y-%m-%d"), "%Y-%m-%d %H:%M")
            # Create Resource Class objects which are the Project Members
            resources = []
            for user in project.members:
                leaves = []
                time_efficiency = 1.0
                resource_id = resource_obj.search(cr, uid, [('user_id', '=', user.id)], context=context)
                if resource_id:
#                    resource = resource_obj.browse(cr, uid, resource_id, context=context)[0]
                    resource = resource_obj.read(cr, uid, resource_id, ['calendar_id','time_efficiency'], context=context)[0]
                    if resource.get('calendar_id', False):
                       leaves = wkcal.compute_leaves(cr, uid, calendar_id , resource_id[0], resource['calendar_id'] and resource['calendar_id'][0] or False)
                    time_efficiency = resource.get('time_efficiency')
                resources.append(classobj((user.name.encode('utf8')), (Resource,), {'__doc__': user.name,
                                                                        '__name__': user.name,
                                                                        'vacation': tuple(leaves),
                                                                        'efficiency': time_efficiency
                                                                        }))
            priority_dict = {'0': 1000, '1': 800, '2': 500, '3': 300,'4': 100}
            # Create dynamic no of tasks with the resource specified
            def create_tasks(j, eff, priorty=500, obj=None):
                def task():
                    """
                    task is a dynamic method!
                    """
                    effort = eff
                    if obj:
                        resource = obj
                    priority = priorty
                task.__doc__ = "TaskNO%d" %j
                task.__name__ = "task%d" %j
                return task

            # Create a 'Faces' project with all the tasks and resources
            def Project():
                title = project.name
                start = date_start
                try:
                    resource = reduce(operator.or_, resources)
                except:
                    raise osv.except_osv(_('Error'), _('Project must have members assigned !'))
                minimum_time_unit = 1
                if calendar_id:        # If project has calendar
                    working_days = wkcal.compute_working_calendar(cr, uid, calendar_id)
                    vacation = tuple(wkcal.compute_leaves(cr, uid, calendar_id))
                # Dynamic Creation of tasks
                i = 0
                for each_task in tasks:
                    hours = str(each_task.planned_hours )+ 'H'
                    if each_task.priority in priority_dict.keys():
                        priorty = priority_dict[each_task.priority]
                    if each_task.user_id:
                       for resource in resources:
                            if resource.__name__ == each_task.user_id.name: # check me!!
                               task = create_tasks(i, hours, priorty, resource)
                    else:
                        task = create_tasks(i, hours, priorty)
                    i += 1

            project = BalancedProject(Project)
            loop_no = 0
            # Write back the computed dates
            for t in project:
                s_date = t.start.to_datetime()
                e_date = t.end.to_datetime()
                if loop_no == 0:
                    project_obj.write(cr, uid, [project_id], {'date' : e_date}, context=context)
                else:
                    ctx = context.copy()
                    ctx.update({'scheduler': True})
                    user_id = user_obj.search(cr, uid, [('name', '=', t.booked_resource[0].__name__)])
                    task_pool.write(cr, uid, [tasks[loop_no-1].id], {'date_start': s_date.strftime('%Y-%m-%d %H:%M:%S'),
                                                                         'date_end': e_date.strftime('%Y-%m-%d %H:%M:%S'),
                                                                         'user_id': user_id[0]},
                                                                         context=ctx)
                loop_no +=1
        return {}

project_compute_tasks()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
