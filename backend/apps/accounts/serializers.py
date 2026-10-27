from django.contrib.auth import authenticate, get_user_model
from rest_framework import serializers
from apps.accounts.tokens import decode_token, generate_tokens_for_user

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Public user serializer."""

    class Meta:
        model = User
        fields = ("id", "email", "username", "full_name", "avatar_url", "created_at")
        read_only_fields = ("id", "created_at")


class RegisterSerializer(serializers.ModelSerializer):
    """Serializer for user registration."""

    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ("id", "email", "username", "full_name", "avatar_url", "password")
        read_only_fields = ("id",)

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value.lower()

    def validate_username(self, value):
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("A user with this username already exists.")
        return value.lower()

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class LoginSerializer(serializers.Serializer):
    """Serializer for user login via email or username."""

    login = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        login_input = attrs.get("login").strip().lower()
        password = attrs.get("password")

        # Support login by email or username
        try:
            if "@" in login_input:
                user = User.objects.get(email__iexact=login_input)
            else:
                user = User.objects.get(username__iexact=login_input)
        except User.DoesNotExist:
            raise serializers.ValidationError("Invalid credentials.")

        if not user.check_password(password):
            raise serializers.ValidationError("Invalid credentials.")

        if not user.is_active:
            raise serializers.ValidationError("User account is inactive.")

        attrs["user"] = user
        return attrs


class RefreshTokenSerializer(serializers.Serializer):
    """Serializer for refreshing access tokens."""

    refresh_token = serializers.CharField()

    def validate(self, attrs):
        token = attrs.get("refresh_token")
        try:
            payload = decode_token(token, expected_type="refresh")
        except Exception as exc:
            raise serializers.ValidationError(f"Invalid refresh token: {str(exc)}")

        user_id = payload.get("user_id")
        try:
            user = User.objects.get(id=user_id, is_active=True)
        except User.DoesNotExist:
            raise serializers.ValidationError("User associated with token not found.")

        attrs["user"] = user
        return attrs
