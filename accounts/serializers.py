from rest_framework import serializers


class EnrollStudentsInBatchSerializer(serializers.Serializer):
    batch_id = serializers.IntegerField(write_only=True)
    student_ids = serializers.ListField(write_only=True)
