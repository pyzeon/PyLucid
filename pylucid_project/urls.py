# coding: utf-8

"""
    global url patterns
    ~~~~~~~~~~~~~~~~~~~

    :copyleft: 2009-2011 by the PyLucid team, see AUTHORS for more details.
    :license: GNU GPL v3 or above, see LICENSE for more details.
"""

from django.conf import settings
from django.conf.urls.defaults import patterns, url, include
from django.contrib import admin
from django.http import HttpResponse
from django.views.defaults import server_error, page_not_found


# TODO: Use own error views?
handler500 = server_error
handler404 = page_not_found


admin.autodiscover()


urlpatterns = patterns('',
    #_____________________________________
    # PYLUCID UPDATE SECTION
    url('^%s/update/' % settings.ADMIN_URL_PREFIX, include('pylucid_update.urls')),

    #_____________________________________
    # PYLUCID ADMIN
    url(r'^%s/' % settings.PYLUCID_ADMIN_URL_PREFIX, include('pylucid_admin.urls')),

    # move it somewhere?
    url(r'^comments/', include('django.contrib.comments.urls')),

    #_____________________________________
    # DJANGO ADMIN PANEL
    url(r'^%s/' % settings.ADMIN_URL_PREFIX, include(admin.site.urls)),
)

# Return a robots.txt that disallows all spiders when DEBUG is True.
if settings.DEBUG:
    urlpatterns += patterns("",
        url(
            "^robots.txt$",
            lambda r: HttpResponse("User-agent: *\nDisallow: /", mimetype="text/plain")
        ),
    )

# serve static files
if settings.SERVE_STATIC_FILES:
    # Should only enabled, if the django development server used.
    print "Serve static file from MEDIA_ROOT:", settings.MEDIA_ROOT
    urlpatterns += patterns('',
        url('^%s/(?P<path>.*)$' % settings.MEDIA_URL.strip("/"), 'django.views.static.serve',
            {'document_root': settings.MEDIA_ROOT, 'show_indexes': True}),
    )

urlpatterns += patterns('',
    url('^', include('pylucid.urls')),
)

#_____________________________________________________________________________
# use the undocumented django function to add the "lucidTag" to the tag library.
# 
from django.template import add_to_builtins
add_to_builtins('pylucid_project.apps.pylucid.defaulttags')
