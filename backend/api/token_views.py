from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth.models import User
from rest_framework import serializers
from django.contrib.auth import authenticate

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
import pyotp
from rest_framework_simplejwt.tokens import RefreshToken


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'] = serializers.EmailField(write_only=True)
        self.fields['password'] = serializers.CharField(write_only=True)
        self.fields['username'] = serializers.CharField(write_only=True, required=False)

    def validate(self, attrs):
        email = attrs.get("email")
        password = attrs.get("password")

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError("Пользователь с таким email не найден.")

        user = authenticate(username=user.username, password=password)

        if not user:
            raise serializers.ValidationError("Неверный email или пароль.")
        if not user.is_active:
            raise serializers.ValidationError("Пользователь не активирован.")

        # ✅ Проверяем 2FA
        if hasattr(user, "profile") and user.profile.is_2fa_enabled:
            # ❗️ НЕ выдаём токен, только флаг для фронта
            raise serializers.ValidationError({"2fa_required": True})

        self.user = user
        return super().validate({"username": user.username, "password": password})

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["email"] = self.user.email

        profile = getattr(self.user, "profile", None)
        if profile and profile.is_2fa_enabled:
            data["2fa_required"] = True

        return data


class EmailTokenObtainPairView(TokenObtainPairView):
    serializer_class = EmailTokenObtainPairSerializer


class Verify2FALoginView(APIView):
    def post(self, request):
        email = request.data.get("email")
        code = request.data.get("code")

        if not email or not code:
            return Response({"error": "Missing email or code"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"error": "Пользователь не найден"}, status=status.HTTP_404_NOT_FOUND)

        profile = getattr(user, "profile", None)
        if not profile or not profile.two_fa_secret:
            return Response({"error": "2FA не активирована"}, status=status.HTTP_400_BAD_REQUEST)

        totp = pyotp.TOTP(profile.two_fa_secret)
        if not totp.verify(code):
            return Response({"error": "Неверный код"}, status=status.HTTP_400_BAD_REQUEST)

        # Всё ок — выдаём токен
        refresh = RefreshToken.for_user(user)
        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        })