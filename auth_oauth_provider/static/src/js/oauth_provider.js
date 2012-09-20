openerp.auth_oauth_provider = function(instance) {

var QWeb = instance.web.qweb;
var _t = instance.web._t;

instance.web.client_actions.add('oauth2_auth', 'instance.auth_oauth_provider.ProviderAction');
instance.auth_oauth_provider.ProviderAction = instance.web.Widget.extend({
    template: "auth_oauth_provider",
    start: function (parent) {
        var self = this;
        this._super.apply(this, arguments);
        var params = $.deparam($.param.querystring());
        if (params.response_type !== 'token') {
            this.error(_t("Unsupported 'response_type' parameter"));
        }
        if (!params.redirect_uri) {
            this.error(_t("No 'redirect_uri' parameter given"));
        }
        // params.approval_prompt TODO
        if (!this._error) {
            instance.session.rpc('/oauth2/get_token', {
                client_id: params.client_id || '',
                scope: params.scope || '',
            }).then(function(result) {
                self.redirect(result);
            }).fail(function() {
                self.error(_t("An error occured while contacting the OpenERP server."));
            });
        }
    },
    redirect: function(result) {
        var params = $.deparam($.param.querystring());
        var a = document.createElement('a');
        a.href = params.redirect_uri;
        var search = (a.search ? '&' : '?') + 'access_token=' + result.access_token;
        if (params.state) {
            search += "&state=" + params.state;
        }
        if (params.expires_in) {
            search += "&expires_in=" + expires_in;
        }
        search += '&token_type=Bearer';
        var redirect = a.protocol + '//' + a.host + a.pathname + search + a.hash;
        //window.location = redirect;
        console.log("redirect to", redirect);
    },
    error: function(msg) {
        this._error = true;
        var $msg = $('<li/>').addClass('oe_oauth_provider_error_text').text(msg);
        $msg.appendTo(this.$('.oe_oauth_provider_error').show().find('ul'));
        return false;
    },
});

};
