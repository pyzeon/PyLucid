# -*- coding: utf-8 -*-

"""
    PyLucid blog plugin
    ~~~~~~~~~~~~~~~~~~~

    A simple blog system.

    Last commit info:
    ~~~~~~~~~
    $LastChangedDate:$
    $Rev:$
    $Author: JensDiemer $

    :copyleft: 2008 by the PyLucid team, see AUTHORS for more details.
    :license: GNU GPL v2 or above, see LICENSE for more details
"""

__version__= "$Rev:$ Alpha"

import datetime

from django.db import models
from django.conf import settings
from django import newforms as forms
from django.core.mail import send_mail
from django.contrib.auth.models import User
from django.utils.safestring import mark_safe
from django.utils.encoding import force_unicode
from django.utils.translation import ugettext as _

from PyLucid.system.BasePlugin import PyLucidBasePlugin
from PyLucid.tools.content_processors import apply_markup
from PyLucid.tools.utils import escape_django_tags
from PyLucid.models.Page import MARKUPS

# Don't send mails, display them only.
#MAIL_DEBUG = True
MAIL_DEBUG = False

#______________________________________________________________________________


class BlogComment(models.Model):
    """
    comment from non-registered users
    """
    blog_entry = models.ForeignKey("BlogEntry")

    ip_address = models.IPAddressField(_('ip address'),)
    person_name = models.CharField(
        _("person's name"), max_length=50
    )
    email = models.EmailField(
        _('e-mail address'),
        help_text=_("Only for internal use."),
    )
    homepage = models.URLField(
        _("homepage"), help_text = _("Your homepage (optional)"),
        verify_exists = False, max_length = 200,
        null=True, blank=True
    )

    content = models.TextField(_('content'), max_length=3000)

    is_public = models.BooleanField(_('is public'))

    createtime = models.DateTimeField(
        auto_now_add=True, help_text="Create time",
    )
    lastupdatetime = models.DateTimeField(
        auto_now=True, help_text="Time of the last change.",
    )
    createby = models.ForeignKey(
        User, editable=False,
        help_text="User how create the current comment.",
        null=True, blank=True
    )
    lastupdateby = models.ForeignKey(
        User, editable=False,
        help_text="User as last edit the current comment.",
        null=True, blank=True
    )

    class Admin:
        pass

    class Meta:
        app_label = 'PyLucidPlugins'


class BlogCommentForm(forms.ModelForm):
    """
    Add a comment.
    """
    person_name = forms.CharField(
        min_length=4, max_length=50,
        help_text=_("Your name."),
    )
    content = forms.CharField(
        label = _('content'), min_length=5, max_length=3000,
        help_text=_("Your comment to this blog entry."),
        widget=forms.Textarea(attrs={'rows': '15'}),
    )

    class Meta:
        model = BlogComment
        # Using a subset of fields on the form
        fields = ('person_name', 'email', "homepage", "comment")


#______________________________________________________________________________


class BlogTagManager(models.Manager):
    """
    Manager for BlogTag model.
    """
    def get_or_creates(self, tags_string):
        """
        split the given tags_string and create not existing tags.
        returns a list of all tag model objects and a list of all created tags.
        """
        tag_objects = []
        new_tags = []
        for tag_name in tags_string.split(" "):
            tag_name = tag_name.strip().lower()
            try:
                tag_obj = self.get(name = tag_name)
            except self.model.DoesNotExist:
                new_tags.append(tag_name)
                tag_obj = self.create(name = tag_name, slug = tag_name)

            tag_objects.append(tag_obj)

        return tag_objects, new_tags


class BlogTag(models.Model):

    objects = BlogTagManager()

    name = models.CharField(max_length=255, core=True, unique=True)
    slug = models.SlugField(
        unique=True, prepopulate_from=('tag',), max_length=120
    )

    def __unicode__(self):
        return self.name

    class Admin:
        pass

    class Meta:
        app_label = 'PyLucidPlugins'


#______________________________________________________________________________



class BlogEntry(models.Model):
    """
    A blog entry
    """
    headline = models.CharField(_('Headline'),
        help_text=_("The blog entry headline"), max_length=255
    )
    content = models.TextField(_('Content'))
    markup = models.IntegerField(
        max_length=1, choices=MARKUPS,
        help_text="the used markup language for this entry",
    )

    tags = models.ManyToManyField(BlogTag, blank=True)

    is_public = models.BooleanField(
        default=True, help_text="Is post public viewable?"
    )

    createtime = models.DateTimeField(auto_now_add=True)
    lastupdatetime = models.DateTimeField(auto_now=True)
    createby = models.ForeignKey(User,
        editable = False,
    )
    lastupdateby = models.ForeignKey(
        User,
        editable = False,
        null=True, blank=True
    )

    def html_content(self, context):
        """
        returns the generatet html code from the content applyed the markup.
        """
        return apply_markup(
            content = self.content,
            context = context,
            markup_no = self.markup
        )

    def get_tag_string(self):
        """
        Returns all tags as a joined string
        """
        tags = self.tags.all()
        tags_names = [i.name for i in tags]
        return " ".join(tags_names)

    def __unicode__(self):
        return self.headline

    class Admin:
        pass

    class Meta:
        app_label = 'PyLucidPlugins'
        ordering = ('-createtime', '-lastupdatetime')


class BlogEntryForm(forms.ModelForm):
    """
    Form for create/edit a blog entry.
    """
    content = forms.CharField(
        widget=forms.Textarea(attrs={'rows': '15'}),
    )

    tags = forms.CharField(
        max_length=255, required=False,
        help_text=_("Tags for this entry (separated by spaces.)"),
        widget=forms.TextInput(attrs={'class':'bigger'}),
    )
    class Meta:
        model = BlogEntry


#______________________________________________________________________________


PLUGIN_MODELS = (BlogComment, BlogTag, BlogEntry,)




class blog(PyLucidBasePlugin):

    keyword_cache = {}

    def __init__(self, *args, **kwargs):
        super(blog, self).__init__(*args, **kwargs)

        # Get the default preference entry.
        self.preferences = self.get_preferences()

        # Change the page title.
        self.current_page.title = self.preferences["blog_title"]


    def _add_comment_edit_url(self, comments):
        for comment in comments:
            comment.edit_url = self.URLs.methodLink(
                "edit_comment", comment.id
            )

    def _list_entries(self, entries, context={}, full_comments=False):
        """
        Display the blog.
        As a list of entries and as a detail view (see internal page).
        """
        for entry in entries:
            # add tag_info
            tags = []
            for tag in entry.tags.all():
                tags.append({
                    "name": tag.name,
                    "url": self.URLs.methodLink("tag", tag.slug),
                })
            entry.tag_info = tags

            # add html code from the content (apply markup)
            entry.html = entry.html_content(self.context)

            if full_comments:
                # Display all comments
                comments = entry.blogcomment_set
                if self.request.user.is_staff:
                    comments = comments.all()
                    self._add_comment_edit_url(comments)
                else:
                    comments = comments.filter(is_public = True).all()
                entry.all_comments = comments
            else:
                entry.detail_url = self.URLs.methodLink(
                    "detail", entry.id
                )
                entry.comment_count = entry.blogcomment_set.count()

            if self.request.user.is_staff: # Add admin urls
                entry.edit_url = self.URLs.methodLink("edit", entry.id)
                entry.delete_url = self.URLs.methodLink("delete", entry.id)

        context["entries"] = entries

        if self.request.user.is_staff:
            context["create_url"] = self.URLs.methodLink("add_entry")

        self._render_template("display_blog", context)#, debug=2)

    def _get_max_count(self):
        """
        The maximal numbers of blog entries, displayed together.
        FIXME: Use django pagination:
        http://www.djangoproject.com/documentation/pagination/
        """
        if self.request.user.is_anonymous():
            return self.preferences["max_anonym_count"]
        else:
            return self.preferences["max_user_count"]

    def lucidTag(self):
        """
        display the blog.
        """
        # FIXME: Never cache this page.
        self.request._use_cache = False

        self.current_page.title += " - " + _("all entries")

        entries = BlogEntry.objects
        if self.request.user.is_anonymous():
            entries = entries.filter(is_public = True)

        max = self._get_max_count()
        entries = entries.all()[:max]

        self._list_entries(entries)

    def detail(self, urlargs):
        """
        Display one blog entry with all comments.
        """
        blog_entry = self._get_entry_from_url(urlargs, model=BlogEntry)
        if not blog_entry:
            # Wrong url, page_msg was send to the user
            return

        self.current_page.title += " - " + blog_entry.headline


        if blog_entry.is_public != True:
            # This blog entry is not public. Comments only allowed from logged
            # in users.
            if self.request.user.is_anonymous():
                msg = "Wrong url."
                if self.request.debug:
                    msg += " Blog entry is not public"
                self.page_msg.red(msg)
                return

        if self.request.method == 'POST':
            form = BlogCommentForm(self.request.POST)
            #self.page_msg(self.request.POST)
            if form.is_valid():
                ok = self._save_new_comment(blog_entry, form)
                if ok:
                    return self._list_entries([blog_entry], full_comments=True)
        else:
            if self.request.user.is_anonymous():
                initial = {}
            else:
                initial = {
                    "person_name": self.request.user.username,
                    "email": self.request.user.email,
                    "homepage": self.URLs["hostname"],
                }

            form = BlogCommentForm(initial=initial)

        context = {
            #"blog_entry": blog_entry,
            "add_comment_form": form,
            "back_url": self.URLs.methodLink("lucidTag"),
        }

        self._list_entries([blog_entry], context, full_comments=True)


    def tag(self, urlargs):
        """
        Display all blog entries with the given tag.
        """
        slug = urlargs.strip("/")
        # TODO: Verify tag
        tag_obj = BlogTag.objects.get(slug = slug)

        self.current_page.title += (
            " - " + _("all blog entries tagged with '%s'")
        ) % tag_obj.name

        entries = tag_obj.blogentry_set

        if self.request.user.is_anonymous():
            entries = entries.filter(is_public = True)

        max = self._get_max_count()
        entries = entries.all()[:max]

        context = {
            "back_url": self.URLs.methodLink("lucidTag"),
            "current_tag": tag_obj,
        }

        self._list_entries(entries, context)

    def _create_or_edit(self, blog_obj = None):
        """
        Create a new or edit a existing blog entry.
        """
        context = {
            "url_abort": self.URLs.methodLink("lucidTag")
        }

        if self.request.method == 'POST':
            form = BlogEntryForm(self.request.POST)
            #self.page_msg(self.request.POST)
            if form.is_valid():
                if blog_obj == None:
                    # a new blog entry should be created
                    blog_obj = BlogEntry(
                        headline = form.cleaned_data["headline"],
                        content = form.cleaned_data["content"],
                        markup = form.cleaned_data["markup"],
                        is_public = form.cleaned_data["is_public"],
                        createby = self.request.user,
                    )
                    blog_obj.save()
                    self.page_msg.green("New blog entry created.")
                else:
                    # Update a existing blog entry
                    blog_obj.lastupdateby = self.request.user
                    for k,v in form.cleaned_data.iteritems():
                        setattr(blog_obj, k, v)
                    self.page_msg.green("Update existing blog entry.")

                tags_string = form.cleaned_data["tags"]
                tag_objects, new_tags = BlogTag.objects.get_or_creates(
                    tags_string
                )
                if new_tags:
                    self.page_msg(_("New tags created: %s") % new_tags)

                # Add many-to-many
                for tag in tag_objects:
                    blog_obj.tags.add(tag)

                blog_obj.save()

                return self.lucidTag()
        else:
            if blog_obj == None:
                context["legend"] = _("Create a new blog entry")

                form = BlogEntryForm(
                    initial={
                        "markup": self.preferences["default_markup"],
                    }
                )
            else:
                context["legend"] = _("Edit a existing blog entry")
                form = BlogEntryForm(
                    instance=blog_obj,
                    initial={"tags":blog_obj.get_tag_string()}
                )

        context["form"]= form

        self._render_template("edit_blog_entry", context)#, debug=True)

    def _get_entry_from_url(self, urlargs, model):
        """
        returns the blog model object based on a ID in the url.
        """
        try:
            entry_id = int(urlargs.strip("/"))
            return model.objects.get(id = entry_id)
        except Exception, err:
            msg = "Wrong url"
            if self.request.debug:
                msg += " %s" % err
            self.page_msg.red(msg)
            return

    def delete(self, urlargs):
        """
        Edit a existing blog entry.
        """
        entry = self._get_entry_from_url(urlargs, model=BlogEntry)
        if not entry:
            # Wrong url, page_msg was send to the user
            return

        entry.delete()
        self.page_msg.green("Entry '%s' deleted." % entry)
        return self.lucidTag()

    def edit(self, urlargs):
        """
        Edit a existing blog entry.
        """
        entry = self._get_entry_from_url(urlargs, model=BlogEntry)
        if not entry:
            # Wrong url, page_msg was send to the user
            return

        return self._create_or_edit(entry)

    def add_entry(self):
        """
        Create a new blog entry
        """
        return self._create_or_edit()

    #__________________________________________________________________________
    # COMMENTS

    def _send_notify(self, mail_title, blog_entry, is_spam, comment_entry):
        """
        Send a email noitify for a submited blog comment.
        """
        email_context = {
            "blog_entry": blog_entry,
            "blog_edit_url": self.URLs.make_absolute_url(
                self.URLs.methodLink("edit", blog_entry.id)
            ),
            "is_spam": is_spam,
            "comment_entry": comment_entry,
        }

        if not is_spam:
            # Add edit link into the mail
            email_context["edit_url"] = self.URLs.make_absolute_url(
                self.URLs.methodLink("edit_comment", comment_entry.id)
            )

        raw_recipient_list = self.preferences["notify"]
        recipient_list = raw_recipient_list.splitlines()
        recipient_list = [i.strip() for i in recipient_list if i]

        # Render the internal page
        emailtext = self._get_rendered_template(
            "notify_mailtext", email_context#, debug=2
        )

        send_mail_kwargs = {
            "subject": "%s %s" % (settings.EMAIL_SUBJECT_PREFIX, mail_title),
#                from_email = sender,
            "recipient_list": recipient_list,
            "fail_silently": False,
        }

        if MAIL_DEBUG == True:
            self.page_msg("blog.MAIL_DEBUG is on: No Email was sended!")
            self.page_msg(send_mail_kwargs)
            self.response.write("<fieldset><legend>The email text:</legend>")
            self.response.write("<pre>")
            self.response.write(emailtext)
            self.response.write("</pre></fieldset>")
            return
        else:
            send_mail(message = emailtext,**send_mail_kwargs)

    def _check_spam(self, blog_entry, form_cleaned_data, content_lower):
        """
        Check if the submitted comment is spam.
        Display error messages and handle email notify.
        """
        contains_spam = self._check_wordlist(
            content_lower, pref_key = "spam_keywords"
        )
        if not contains_spam:
            # The submitted content contains no spam keyword
            return False

        self.page_msg.red("Sorry, your comment identify as spam.")

        if not self.preferences["spam_notify"]:
            # Don't send spam notify email
            return True

        # Add ID Adress for notify mail text
        form_cleaned_data["ip_address"] = self.request.META.get('REMOTE_ADDR')
        form_cleaned_data["createtime"] = datetime.datetime.now()

        self._send_notify(
            mail_title = _("blog comment as spam detected."),
            blog_entry = blog_entry, is_spam = True,
            comment_entry = form_cleaned_data
        )
        return True

    def _save_new_comment(self, blog_entry, form):
        """
        Save a valid submited comment form into the database.

        Check if content is spam or if the comment should be moderated.
        returns True if the comment accepted (is not spam).

        Send notify emails.
        """
        content = form.cleaned_data["content"]
        content = content.strip()
        content_lower = content.lower()

        if self.request.user.is_staff:
            # Don't check comments from staff users
            is_public = True
            mail_title = _("new blog comment from page member published.")
        else:
            is_spam = self._check_spam(
                blog_entry, form.cleaned_data, content_lower
            )
            if is_spam != False:
                # Is spam: page_msg and notify was handled by _ckeck_spam()
                return False

            should_moderated = self._check_wordlist(
                content_lower, pref_key = "mod_keywords"
            )
            if should_moderated:
                self.page_msg(_("Your comment must wait for authorization."))
                mail_title = _("new blog comment waits for moderation.")
                is_public = False
            else:
                mail_title = _("blog comment published.")
                is_public = True

        content = escape_django_tags(content)

        new_comment = BlogComment(
            blog_entry = blog_entry,
            ip_address = self.request.META.get('REMOTE_ADDR'),
            person_name = form.cleaned_data["person_name"],
            email = form.cleaned_data["email"],
            homepage = form.cleaned_data["homepage"],
            content = content,
            is_public = is_public,
            createby = self.request.user,
        )
        # We must save the entry got get the id of it for the notify mail
        new_comment.save()

        # Send a notify email
        self._send_notify(
            mail_title, blog_entry, is_spam=False, comment_entry=new_comment
        )

        self.page_msg.green("comment saved.")
        return True

    def _get_wordlist(self, pref_key):
        """
        Chached access to the keywords from the preferences.
        (mod_keywords, spam_keywords)
        """
        if pref_key not in self.keyword_cache:
            raw_keywords = self.preferences[pref_key]
            keywords = raw_keywords.splitlines()
            keywords = [word.strip().lower() for word in keywords if word]
            self.keyword_cache[pref_key] = tuple(keywords)

        return self.keyword_cache[pref_key]

    def _check_wordlist(self, content, pref_key):
        """
        Simple check, if the content contains one keyword.
        """
        keywords = self._get_wordlist(pref_key)
        for keyword in keywords:
            if keyword in content:
                return True
        return False

    def edit_comment(self, urlargs):
        """
        Edit a comment (only for admins)
        """
        comment_entry = self._get_entry_from_url(urlargs, model=BlogComment)
        if not comment_entry:
            # Wrong url, page_msg was send to the user
            return

        CommentForm = forms.form_for_instance(comment_entry)

        blog_entry = comment_entry.blog_entry # ForeignKey("BlogEntry")

        if self.request.method == 'POST':
            form = CommentForm(self.request.POST)
            #self.page_msg(self.request.POST)
            if form.is_valid():
                if "delete" in self.request.POST:
                    comment_entry.delete()
                    self.page_msg.green("Comment deleted.")
                else:
                    form.save()
                    self.page_msg.green("Saved.")
                return self._list_entries([blog_entry], context={}, full_comments=True)
        else:
            form = CommentForm()

        context = {
            "blog_entry": blog_entry,
            "url_abort": self.URLs.methodLink("detail", blog_entry.id),
            "form": form,
        }

        self._render_template("edit_comment", context)#, debug=2)

    def mod_comments(self):
        """
        Build a list of all non public comments
        TODO: make this complete...
        """
        self.page_msg.red("TODO")

        comments = BlogComment.objects.filter(is_public=False)
        self._add_comment_edit_url(comments)
        self.page_msg(comments)

        context = {
            "comments": comments,
        }

        self._render_template("mod_comments", context)#, debug=2)