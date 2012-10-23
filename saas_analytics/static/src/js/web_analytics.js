
var _gaq = _gaq || [];  // asynchronous stack used by google analytics

openerp.web_analytics = function(instance) {

    /** The Google Analytics Module inserts the Google Analytics JS Snippet
     *  at the top of the page, and sends to google a virtual url each time the
     *  openerp url is changed. Google needs a virtual url because it cannot 
     *  handle sharps in the url. At this time the virtual url only handles the
     *  model and view parameters and is of the form /web_analytics/redirect/MODEL/VIEW
     *
     *  The pushes of the virtual urls is made by adding a callback to the 
     *  web_client.do_push_state() method which is responsible of changing the openerp current url
     */

    

    if (instance.webclient) {
        //_gaq.push(['_setAccount', 'UA-25293939-2']);  // fva@openerp.com localhost
        _gaq.push(['_setAccount', 'UA-28648768-1']);    // fva@openerp.com runbot
        //_gaq.push(['_setAccount', 'UA-28648768-1']);  // fva@openerp.com
        //_gaq.push(['_setAccount', 'UA-7333765-1']);   // fp@openerp.com
        //_gaq.push(['_setAccount', 'UA-7333765-1']);   // fp@openerp.com
        _gaq.push(['_setDomainName', '.openerp.com']);
        _gaq.push(['_trackPageview']);

        var connection = this.sessions.session0.connection;
        _gaq.push(['_setCustomVar',1,'Paying User',String(connection.openerp_entreprise),1]);
        _gaq.push(['_setCustomVar',2,'Admin User',String(connection.uid == 1),1]);

        // Google Analytics Code snippet
        (function() {
            var ga   = document.createElement('script');
            ga.type  = 'text/javascript';
            ga.async = true
            ga.src   = ('https:' == document.location.protocol ? 'https://ssl' : 'http://www') + '.google-analytics.com/ga.js';
            var s = document.getElementsByTagName('script')[0];
            s.parentNode.insertBefore(ga,s);
        }) ();

        instance.webclient.do_push_state.add(function(state) {
            var model     = state["model"]  || "no_model";
            var view_type = state["view_type"] || "default";
            var vurl = "web_analytics/redirect/"+ model + "/" + view_type
            console.log(vurl);
            _gaq.push(['_trackPageview',vurl]);
        });
    }
};

