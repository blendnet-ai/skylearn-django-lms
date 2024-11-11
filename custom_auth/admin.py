from django.contrib import admin
from django.core.management import call_command
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import path, reverse

from .models import Form, UserProfile

# Register your models here.
admin.site.register(Form)


class WhitelistUsersModelAdmin(admin.ModelAdmin):
    change_list_template = "whitelist_users.html"

    def run_whitelist_users_command(self, request):
        try:
            call_command("whitelist_users")
            self.message_user(
                request, "Management command executed successfully", messages.SUCCESS
            )
        except Exception as e:
            self.message_user(
                request, f"Error executing command: {str(e)}", messages.ERROR
            )

        return HttpResponseRedirect(reverse("admin:custom_auth_userprofile_changelist"))

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "whitelist-users/",
                self.admin_site.admin_view(self.run_whitelist_users_command),
                name="whitelist_users",
            ),
        ]
        return custom_urls + urls

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context["whitelist_users_url"] = "whitelist-users"
        return super().changelist_view(request, extra_context=extra_context)


admin.site.register(UserProfile, WhitelistUsersModelAdmin)
