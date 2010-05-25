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
{
    "name" : "Purchase - Purchase Requisition",
    "version" : "0.1",
    "author" : "Tiny",
    "category" : "Generic Modules/Sales & Purchases",
    "website" : "http://www.openerp.com",
    "description": """
    This module allows you to manage your Purchase Requisition.
    When a purchase order is created, you now have the opportunity to save the related requisition.
    This new object will regroup and will allow you to easily keep track and order all your purchase orders.
""",
    "depends" : ["purchase","mrp"],
    "init_xml" : [],
    "demo_xml" : [],
    "update_xml" : ["wizard/purchase_requisition_partner_view.xml",
                    "purchase_requisition_view.xml",
                    "security/ir.model.access.csv","purchase_requisition_sequence.xml"],
    "active": False,
    "test":[
#            'test/purchase_requisition.yml','test/purchase_requisition_exclusive.yml'
            ],
    "installable": True
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

