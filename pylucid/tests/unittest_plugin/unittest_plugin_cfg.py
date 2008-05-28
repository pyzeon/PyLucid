#!/usr/bin/python
# -*- coding: UTF-8 -*-

#_____________________________________________________________________________
# meta information
__author__              = "Jens Diemer"
__url__                 = "http://www.PyLucid.org"
__description__         = "unittest plugin (only for unittest!)"
__long_description__ = """
PyLucid important comonent is the plugin system. Many features realised as a
plugin. So we need a way for testing the plugin API. This special plugin are
used in the unittest ./tests/test_plugin_api.py

It should never be installed/activated in a productive environment!
"""

#_____________________________________________________________________________
# preferences

from django import newforms as forms
from django.utils.translation import ugettext as _

class PreferencesForm(forms.Form):
    print_last_page = forms.BooleanField(
        initial = True,
        help_text = _(
            "If checked the actual page will be the last page in the bar."
            " Otherwise the parentpage."
        ),
    )
    print_index = forms.BooleanField(
        initial = False,
        help_text = _('If checked every back link bar starts with a link to "index_url"'),
    )
    index_url = forms.CharField(
        initial = "/",
        help_text = _("The url used for print_index. Note: not verify if the url exists."),
    )
    index = forms.CharField(
        initial = _("Index"),
        help_text = _('the name that is printed for the indexpage'),
    )

#_____________________________________________________________________________
# plugin administration data

global_rights = {
    "must_login"    : False,
    "must_admin"    : False,
}

plugin_manager_data = {
    "lucidTag" : global_rights,
    "hello_world": global_rights,
    "test_attributes" : global_rights,
}