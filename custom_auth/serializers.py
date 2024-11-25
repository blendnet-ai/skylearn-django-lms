from rest_framework import serializers

from django.contrib.auth import get_user_model


User = get_user_model()


class UserSerializer(serializers.ModelSerializer):

    is_admin = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = (
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'is_active',
            'is_staff',
            'is_admin',
            'is_superuser',
        )

    def get_is_admin(self, obj):
        return obj.is_staff or obj.is_superuser

class FormFetchSerializer(serializers.Serializer):
    form_name = serializers.CharField(required=True)

class FormSubmitSerializer(serializers.Serializer):
    form_name = serializers.CharField(required=True)
    user_data = serializers.DictField(required=True)

class ActivityDataSerializer(serializers.Serializer):
    longest_streak = serializers.IntegerField()
    current_streak = serializers.IntegerField()
    activity_status = serializers.ListField(
        child=serializers.BooleanField()
    )