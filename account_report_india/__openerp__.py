# -*- encoding: utf-8 -*-
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
    "name" : "Accounting Reports",
    "version" : "1.0",
    "depends" : [
        "account"
    ],
    "author" : "Tiny ERP",
    "description": """Accounting Reports 
Modules gives the 2 most Important Reports for the Accounting
* Profit and Loss Account
* Balance Sheet
    """,
    "website" : "http://tinyerp.com/module_account.html",
    "category" : "Generic Modules/Accounting",
    "init_xml" : [
    ],
    "demo_xml" : [
                   
    ],
    "update_xml" : [
        "wizard/account_pl_report_view.xml",
        "wizard/account_bs_report_view.xml"
    ],
    "active": False,
    "installable": True
}
