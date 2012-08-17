from openerp.osv import osv, fields

class auth_oauth_providers(osv.osv):
    """Class defining the configuration values of an OAuth2 provider"""

    _name = 'auth.oauth.provider'
    _description = 'OAuth2 provider'
    _order = 'name'

    _columns = {
        'name' : fields.char('Provider name', required=True),               # Name of the OAuth2 entity, Google, LinkedIn, etc
        'client_id' : fields.char('Client ID', required=True),              # Our identifier
        'auth_endpoint' : fields.char('Authentication URL', required=True), # OAuth provider URL to authenticate users
        'scope' : fields.char('Scope'),                                     # OAUth user data desired to access
        'validation_endpoint' : fields.char('Validation URL'),              # OAuth provider URL to validate tokens
        'data_endpoint' : fields.char('Data URL'),
        'css_class' : fields.char('CSS class'),
        'body' : fields.char('Body'),
        'active' : fields.boolean('Active'),
        'sequence' : fields.integer(),
    }

