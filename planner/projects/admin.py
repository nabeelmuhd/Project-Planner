from django import forms
from django.contrib import admin
from django.db.models import Q

from .models import AssignedProject, Project, Task


admin.site.register(Task)


class AssignedProjectAdminForm(forms.ModelForm):
    class Meta:
        model = AssignedProject
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        project_filter = Q(assignedproject__isnull=True)
        if self.instance.pk:
            project_filter |= Q(pk=self.instance.project_id)
        self.fields["project"].queryset = Project.objects.filter(project_filter)


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    def _has_project_admin_role(self, request):
        user = request.user
        return bool(
            user.is_authenticated
            and user.is_staff
            and (user.is_superuser or user.role == "Admin")
        )

    def has_module_permission(self, request):
        return super().has_module_permission(request) or self._has_project_admin_role(request)

    def has_view_permission(self, request, obj=None):
        return super().has_view_permission(request, obj) or self._has_project_admin_role(request)

    def has_add_permission(self, request):
        return super().has_add_permission(request) or self._has_project_admin_role(request)

    def has_change_permission(self, request, obj=None):
        return super().has_change_permission(request, obj) or self._has_project_admin_role(request)

    def has_delete_permission(self, request, obj=None):
        return super().has_delete_permission(request, obj) or self._has_project_admin_role(request)


@admin.register(AssignedProject)
class AssignedProjectAdmin(ProjectAdmin):
    form = AssignedProjectAdminForm
    list_display = (
        "project",
        "coordinator",
        "duration",
        "start_date",
        "tentative_end_date",
        "project_completed",
    )