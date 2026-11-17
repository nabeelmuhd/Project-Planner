from django.contrib import admin
from django.test import RequestFactory, SimpleTestCase
from django.urls import resolve
from types import SimpleNamespace
from unittest.mock import patch

from authentication.models import Profile

from .admin import AssignedProjectAdminForm, ProjectAdmin
from .models import AssignedProject, Project
from .serializers import AssignedProjectSerializer, ProfileField, ProjectField
from .views import TaskCreateWithAI
from rest_framework.exceptions import ValidationError


class ProjectAdminPermissionTests(SimpleTestCase):
    def setUp(self):
        self.project_admin = ProjectAdmin(Project, admin.site)
        self.request = RequestFactory().get("/admin/projects/project/")

    def test_staff_user_with_admin_role_can_access_projects(self):
        self.request.user = type(
            "User",
            (),
            {
                "is_authenticated": True,
                "is_staff": True,
                "is_superuser": False,
                "role": "Admin",
                "has_perm": lambda self, permission: False,
                "has_module_perms": lambda self, app_label: False,
            },
        )()

        self.assertTrue(self.project_admin.has_module_permission(self.request))
        self.assertTrue(self.project_admin.has_view_permission(self.request))
        self.assertTrue(self.project_admin.has_add_permission(self.request))
        self.assertTrue(self.project_admin.has_change_permission(self.request))
        self.assertTrue(self.project_admin.has_delete_permission(self.request))

    def test_non_admin_staff_user_still_needs_django_permissions(self):
        self.request.user = type(
            "User",
            (),
            {
                "is_authenticated": True,
                "is_staff": True,
                "is_superuser": False,
                "role": "Developer",
                "has_perm": lambda self, permission: False,
                "has_module_perms": lambda self, app_label: False,
            },
        )()

        self.assertFalse(self.project_admin.has_module_permission(self.request))
        self.assertFalse(self.project_admin.has_view_permission(self.request))


class ProjectDetailRouteTests(SimpleTestCase):
    def test_plural_uuid_route_resolves_to_project_detail_view(self):
        match = resolve("/projects/ae6a645c-ad89-471e-b115-95e6afd7d68f/")

        self.assertEqual(match.func.view_class.__name__, "ProjectRetrieveUpdateDestroyView")

    def test_assigned_projects_route_resolves_to_list_create_view(self):
        match = resolve("/assigned-projects/")

        self.assertEqual(
            match.func.view_class.__name__,
            "AssignedProjectListCreateView",
        )

    def test_assigned_project_detail_route_resolves_to_detail_view(self):
        match = resolve(
            "/assigned-projects/a645e6f2-d391-4eda-a6df-7204a00d60ea/"
        )

        self.assertEqual(
            match.func.view_class.__name__,
            "AssignedProjectRetrieveUpdateDestroyView",
        )


class AssignedProjectSerializerTests(SimpleTestCase):
    def test_related_fields_return_names(self):
        project_field = ProjectField(queryset=Project.objects.none())
        coordinator_field = ProfileField(queryset=Profile.objects.none())
        developer_field = ProfileField(queryset=Profile.objects.none(), many=True)

        self.assertEqual(
            project_field.to_representation(type("Project", (), {"title": "Planner"})()),
            "Planner",
        )
        self.assertEqual(
            coordinator_field.to_representation(
                type("Profile", (), {"first_name": "Amina"})()
            ),
            "Amina",
        )
        self.assertEqual(
            [developer_field.child.to_representation(
                type("Profile", (), {"first_name": "Ethan"})()
            )],
            ["Ethan"],
        )

    @patch("projects.serializers.AssignedProject.objects.filter")
    def test_project_cannot_be_assigned_twice(self, filter_assignments):
        filter_assignments.return_value.exists.return_value = True
        serializer = AssignedProjectSerializer()

        with self.assertRaises(ValidationError) as error:
            serializer.validate_project(Project(pk=2))

        self.assertEqual(
            str(error.exception.detail[0]),
            "This project has already been assigned.",
        )


class TaskCreateWithAITests(SimpleTestCase):
    @patch("projects.views.generate_tasks")
    @patch("projects.views.AssignedProject.objects.get")
    def test_post_uses_assigned_project_uuid(self, get_assigned_project, generate):
        assigned_project = AssignedProject(pk=1)
        get_assigned_project.return_value = assigned_project
        generate.return_value = SimpleNamespace(tasks=[])
        request = RequestFactory().post(
            "/create-task-ai/a645e6f2-d391-4eda-a6df-7204a00d60ea/"
        )

        response = TaskCreateWithAI.as_view()(
            request,
            uuid="a645e6f2-d391-4eda-a6df-7204a00d60ea",
        )

        self.assertEqual(response.status_code, 200)
        get_assigned_project.assert_called_once_with(
            uuid="a645e6f2-d391-4eda-a6df-7204a00d60ea"
        )
        generate.assert_called_once_with(assigned_project)


class AssignedProjectAdminFormTests(SimpleTestCase):
    def test_project_field_only_offers_unassigned_projects(self):
        form = AssignedProjectAdminForm()
        query = str(form.fields["project"].queryset.query).upper()

        self.assertIn("ASSIGNEDPROJECT", query)
        self.assertIn("IS NULL", query)

    def test_edit_form_keeps_its_current_project_available(self):
        with patch("django.forms.models.model_to_dict", return_value={}):
            form = AssignedProjectAdminForm(
                instance=AssignedProject(pk=1, project_id=2),
            )
        query = str(form.fields["project"].queryset.query).upper()

        self.assertIn("IS NULL", query)
        self.assertIn(" OR ", query)
