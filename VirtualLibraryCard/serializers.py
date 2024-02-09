from rest_framework import serializers

from .models import CustomUser, Library, LibraryCard


class LibrarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Library
        fields = "__all__"


class CustomUserSerializer(serializers.ModelSerializer):
    library = serializers.StringRelatedField(many=False)

    class Meta:
        model = CustomUser
        fields = "__all__"


class LibraryCardSerializer(serializers.ModelSerializer):
    user = CustomUserSerializer(many=False)
    library = LibrarySerializer(many=False)

    class Meta:
        model = LibraryCard
        fields = "__all__"
