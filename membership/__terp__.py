{
	"name" : "Membership",
	"version" : "0.1",
	"author" : "Tiny",
	"category" : "Generic Modules/Association",
	"depends" : [
		"base", "product", "account", "sale"
		],
	"demo_xml" : [
		#"demo_data.xml",
		#"membership_demo.xml"
		],
	"init_xml" : [
		"membership_data.xml",
		],
	"update_xml" : [
		"membership_view.xml","membership_wizard.xml"
		],
	"active" : False,
	"installable" : True,
}
