from rest_framework import serializers
from rest_framework.relations import ManyRelatedField

from authentication.models import Profile
from .models import AssignedProject, Project,Task


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = "__all__"
        read_only_fields = ["active_status"]


class NameManyRelatedField(ManyRelatedField):
    @property
    def child(self):
        return self.child_relation


class NameRelatedField(serializers.PrimaryKeyRelatedField):
    def get_attribute(self, instance):
        return getattr(instance, self.source_attrs[0])

    @classmethod
    def many_init(cls, *args, **kwargs):
        return NameManyRelatedField(child_relation=cls(*args, **kwargs))


class ProjectField(NameRelatedField):
    def to_representation(self, value):
        return value.title


class ProfileField(NameRelatedField):
    def to_representation(self, value):
        return value.first_name


class AssignedProjectSerializer(serializers.ModelSerializer):
    project = ProjectField(queryset=Project.objects.all())
    coordinator = ProfileField(queryset=Profile.objects.filter(role="Project Coordinator"))
    developers = ProfileField(
        queryset=Profile.objects.filter(role="Developer"),
        many=True,
    )

    def validate_project(self, project):
        assignments = AssignedProject.objects.filter(project=project)
        if self.instance is not None:
            assignments = assignments.exclude(pk=self.instance.pk)
        if assignments.exists():
            raise serializers.ValidationError(
                "This project has already been assigned."
            )
        return project

    class Meta:
        model = AssignedProject
        fields = "__all__"
        read_only_fields = ["active_status"]


class AssignedProjectField(serializers.PrimaryKeyRelatedField):    
          def get_attribute(self, instance):         
             return getattr(instance,self.source_attrs[0])      
             def to_representation(self, value):       
                 return ProjectSerializer(value).data       
             
class TaskSerializer(serializers.ModelSerializer):
            
    queryset = AssignedProject.objects.all().select_related('project','coordinator').prefetch_related('developers')

    assigned_to = ProfileField(queryset=Profile.objects.filter(role='Developer'))

    class Meta :

            model = Task

            fields = "__all__"

            read_only_fields = ["active_status"]




