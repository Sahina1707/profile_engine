from rest_framework import serializers

class ProfilerRequestSerializer(serializers.Serializer):
    json_file = serializers.FileField()
    prompt = serializers.CharField(required=False, default="Explain this profile.")