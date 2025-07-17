import json
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.conf import settings
from rest_framework import generics, viewsets, status
from .serializers import ExtendedUserSerializer, UserSerializer, TeamMemberDetailSerializer
from rest_framework.permissions import AllowAny, IsAuthenticated
from .models import Cargo, EmailVerification, Truck, BookingRequest, TeamCompany, TeamMember
from .serializers import CargoSerializer, UserSerializer, TruckSerializer, ProfileSerializer, BookingRequestSerializer, TeamCompanySerializer, TeamMemberSerializer
from .forms import CargoForm
import random
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.decorators import permission_classes
import requests
from django.utils.translation import gettext as _
import logging

from rest_framework import generics
from rest_framework.exceptions import PermissionDenied

from django.db import models

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from .models import Notification

from .serializers import NotificationSerializer

from rest_framework.generics import ListAPIView

from .utils import get_user_company_and_role

from api.models import Profile, TeamMember, RegisteredCompany

import pyotp
import qrcode
import io
import base64

from rest_framework import viewsets, permissions

from .serializers import ReviewSerializer

from .models import Review

import os
from django.views.generic import View
from django.http import FileResponse

class FrontendAppView(View):
    def get(self, request):
        file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '../frontend/dist/index.html')
        return FileResponse(open(file_path, 'rb'))


logger = logging.getLogger(__name__)

class CreateUserView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = ExtendedUserSerializer
    permission_classes = [AllowAny]

    def perform_create(self, serializer):
        try:
            user = serializer.save()
            code = str(random.randint(100000, 999999))
            print("[DEBUG] Received request:")
            print(json.dumps(self.request.data, indent=4, ensure_ascii=False))
            EmailVerification.objects.create(user=user, code=code)
            self.send_verification_email(user, code)
        except Exception as e:
            print(f"[ERROR] Error creating a user: {e}")

    def send_verification_email(self, user, code):
        subject = _('Код підтвердження реєстрації')
        message = _('Привіт, {username}! Ваш код підтвердження: {code}').format(username=user.username, code=code)
        from_email = settings.DEFAULT_FROM_EMAIL
        recipient_list = [user.email]

        try:
            send_mail(subject, message, from_email, recipient_list, fail_silently=False)
            print("[DEBUG] Email was sent successfully.")
        except Exception as e:
            print(f"[ERROR] Error sending an email: {e}")

from django.db.models import Q

class CargoViewSet(viewsets.ModelViewSet):
    queryset = Cargo.objects.all()  # 👈 ОБЯЗАТЕЛЬНО
    serializer_class = CargoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Cargo.objects.filter(user=self.request.user)  # 👈 Логика фильтрации

    def get_serializer_context(self):
        return {'request': self.request}

    def perform_create(self, serializer):
        serializer.save(
            user=self.request.user,
            show_on_main=False,
            show_in_available_cargo=False  # ❗️Отключаем
        )





def add_cargo_view(request):
    if request.method == 'POST':
        form = CargoForm(request.POST)
        if form.is_valid():
            cargo = form.save(commit=False)  # НЕ сохраняем сразу
            cargo.user = request.user        # Проставляем пользователя
            cargo.save()                     # Теперь сохраняем
            return redirect('cargo-success')
    else:
        form = CargoForm()

    return render(request, 'api/add_cargo.html', {'form': form})


class UserProfileAPIView(generics.RetrieveUpdateAPIView):
    serializer_class = ExtendedUserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        user = self.get_object()
        profile_data = request.data.pop('profile', {})

        serializer = self.get_serializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        profile_serializer = ProfileSerializer(user.profile, data=profile_data, partial=True)
        profile_serializer.is_valid(raise_exception=True)
        profile_serializer.save()

        return Response(serializer.data, status=status.HTTP_200_OK)

class VerifyEmailCodeView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        code = request.data.get('code')

        if not email or not code:
            return Response({'error': _('Email и код обязательны')}, status=400)

        try:
            user = User.objects.get(email=email)
            verification = EmailVerification.objects.get(user=user)

            if verification.code == code:
                user.is_active = True
                user.save()
                verification.delete()
                refresh = RefreshToken.for_user(user)
                return Response({
                    'message': _('Аккаунт успешно подтверждён!'),
                    'token': str(refresh.access_token),
                }, status=200)
            else:
                return Response({'error': _('Неверный код')}, status=400)

        except User.DoesNotExist:
            return Response({'error': _('Пользователь не найден')}, status=404)
        except EmailVerification.DoesNotExist:
            return Response({'error': _('Код не найден')}, status=404)

class TruckViewSet(viewsets.ModelViewSet):
    serializer_class = TruckSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Truck.objects.filter(user=self.request.user)

    def get_serializer_context(self):
        return {'request': self.request}

    def perform_create(self, serializer):
        serializer.save(
            user=self.request.user,
            show_on_main=False,
            show_in_available_vehicles=False
        )




class TruckListCreateView(generics.ListCreateAPIView):
    serializer_class = TruckSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # ✅ Только свои транспортные средства
        return Truck.objects.filter(user=self.request.user)


from rest_framework.decorators import api_view
from .models import RegisteredCompany, SuspiciousAttempt

def normalize_code(code):
    print(f"[DEBUG] Raw input code: '{code}'")
    normalized = ''.join(filter(str.isalnum, code)).upper()
    print(f"[DEBUG] Normalized code: '{normalized}'")
    return normalized

@api_view(['POST'])
@permission_classes([AllowAny])
def validate_company_code(request):
    country = request.data.get('country')
    code = request.data.get('code')
    ip_address = request.META.get('REMOTE_ADDR')

    print("🔍 Проверка кода:", country, code)

    normalized_code = normalize_code(code)

    if RegisteredCompany.objects.filter(code__iexact=normalized_code).exists():
        SuspiciousAttempt.objects.create(
            country=country,
            code=normalized_code,
            ip_address=ip_address
        )
        return Response({
            "valid": False,
            "message": _("🚫 Компанія з таким кодом вже зареєстрована. Якщо ви вважаєте це помилкою — зв'яжіться з підтримкою.")
        })

    if country == "switzerland" and normalized_code.startswith("CHE") and len(normalized_code) == 12:
        return Response({"valid": True})

    if country == "ukraine" and normalized_code.isdigit() and len(normalized_code) == 8:
        return Response({"valid": True})

    return Response({"valid": False, "message": _("❌ Код не знайдено або недійсний.")})

from rest_framework.parsers import MultiPartParser, FormParser
from .models import CompanyDocument
from .serializers import CompanyDocumentSerializer

class CompanyDocumentUploadView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, *args, **kwargs):
        files = request.FILES.getlist('files')
        documents = []

        for file in files:
            doc = CompanyDocument.objects.create(user=request.user, file=file)
            documents.append(doc)

        serializer = CompanyDocumentSerializer(documents, many=True)
        return Response(serializer.data, status=201)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_documents_approval(request):
    user = request.user
    documents = CompanyDocument.objects.filter(user=user)

    approved = documents.filter(is_approved=True).exists()
    rejected = documents.filter(is_rejected=True).exists()

    profile = getattr(user, "profile", None)
    company_data = {}
    is_owner = False
    is_member = False

    registered_company = None
    team_member = TeamMember.objects.select_related('company__registered_company', 'user').filter(user=user).first()

    if team_member:
        team_company = team_member.company
        registered_company = team_company.registered_company
        is_member = True

        print("[DEBUG] is_member:", is_member)
        print("[DEBUG] profile:", profile)
        print("[DEBUG] registered_company:", registered_company)

        if profile and registered_company:
            company_data = {
                "name": team_company.name,
                "address": profile.address or "",
                "email": user.email,
                "phone": profile.phone or "",
                "fullName": user.username,
                "country": registered_company.country,
                "code": registered_company.code,
                "registrationDate": registered_company.created_at.strftime('%Y-%m-%d'),
                "isVerified": approved,
                "totalOrders": 0,
                "activeOrders": 0,
                "totalCargo": 0,
                "totalVehicles": 0,
                "interest": _("Міжнародний транспорт"),
                "activity": _("Замовник перевезення")
            }


    # 2. Если не сотрудник — может, владелец
    if not is_member:
        registered_company = RegisteredCompany.objects.filter(registered_by=user).first()
        is_owner = True if registered_company else False

        if profile and registered_company:
            company_data = {
                "name": profile.company or "",
                "address": profile.address or "",
                "email": user.email,
                "phone": profile.phone or "",
                "fullName": user.username,
                "country": registered_company.country,
                "code": registered_company.code,
                "registrationDate": registered_company.created_at.strftime('%Y-%m-%d'),
                "isVerified": approved,
                "totalOrders": 0,
                "activeOrders": 0,
                "totalCargo": 0,
                "totalVehicles": 0,
                "interest": _("Міжнародний транспорт"),
                "activity": _("Замовник перевезення")
            }

    print("[DEBUG] company_data:", company_data)

    role = None
    if is_owner:
        role = "owner"
    elif is_member and team_member:
        role = team_member.role

    return Response({
        "approved": approved,
        "rejected": rejected,
        "is_owner": is_owner,
        "is_member": is_member,
        "role": role, 
        "company_data": company_data if company_data else None,
    })



@api_view(['POST'])
@permission_classes([IsAuthenticated])
def register_company(request):
    user = request.user
    country = request.data.get('country')
    code = request.data.get('code')

    if not country or not code:
        return Response({"error": _("Missing country or code")}, status=400)

    normalized_code = normalize_code(code)

    if RegisteredCompany.objects.filter(code__iexact=normalized_code).exists():
        return Response({"error": _("Company already registered")}, status=409)

    # 1. Регистрируем компанию
    registered_company = RegisteredCompany.objects.create(
        country=country,
        code=normalized_code,
        registered_by=user
    )

    # 2. Автоматически создаём TeamCompany
    TeamCompany.objects.create(
        name=request.user.profile.company or "Unnamed company",
        created_by=user,
        registered_company=registered_company
    )

    return Response({"message": _("Company registered successfully")})


from api.models import Profile
from rest_framework import serializers

# backend/api/views.py

from api.models import Profile, RegisteredCompany, Cargo, Truck

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from api.models import Profile, RegisteredCompany, Cargo, Truck
from django.utils.translation import gettext as _

class CompanyProfileByNameView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, name):
        profile = Profile.objects.select_related('user').filter(company__iexact=name).first()
        
        if not profile:
            return Response({"error": "Компанія не знайдена"}, status=404)

        user = profile.user
        registered_company = RegisteredCompany.objects.filter(registered_by=user).first()
        total_cargo = Cargo.objects.filter(user=user).count()
        total_vehicles = Truck.objects.filter(user=user).count()

        data = {
            "company_name": profile.company or '',
            "address": profile.address or '',
            "registration_date": registered_company.created_at.strftime('%Y-%m-%d') if registered_company and registered_company.created_at else '',
            "is_verified": registered_company is not None,
            "email": user.email or '',
            "phone": profile.phone or '',
            "full_name": profile.full_name or user.username or '',
            "total_orders": 0,
            "active_orders": 0,
            "total_cargo": total_cargo,
            "total_vehicles": total_vehicles,
            "interest": _("Міжнародний транспорт"),
            "activity": profile.client_type or '',
            "country": registered_company.country if registered_company else '',
            "company_photo_url": request.build_absolute_uri(profile.company_photo.url) if profile.company_photo else None,
            "city": profile.city or '',
            "canton": profile.canton or '',
            "viber_whatsapp": profile.viber_whatsapp_number or '',
        }

        return Response(data, status=200)



# Грузы для главной страницы
class MainPageCargoView(generics.ListAPIView):
    serializer_class = CargoSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        finished_cargo_ids = BookingRequest.objects.filter(
            status__in=["Finished", "Cancelled", "Rejected"]
        ).values_list('cargo_id', flat=True)

        return Cargo.objects.filter(
            show_on_main=True
        ).exclude(id__in=finished_cargo_ids)


# Грузы для "Available Cargo"
class AvailableCargoView(generics.ListAPIView):
    serializer_class = CargoSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        # Все занятые грузы
        finished_cargo_ids = BookingRequest.objects.filter(
            status__in=["Finished", "Cancelled", "Accepted"],
            cargo__isnull=False
        ).values_list('cargo_id', flat=True)

        return Cargo.objects.filter(
            show_in_available_cargo=True
        ).exclude(id__in=finished_cargo_ids)




# Машины для главной страницы
class MainPageTruckView(generics.ListAPIView):
    serializer_class = TruckSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        finished_truck_ids = BookingRequest.objects.filter(
            status__in=["Finished", "Cancelled", "Rejected"]
        ).values_list('truck_id', flat=True)

        return Truck.objects.filter(
            show_on_main=True
        ).exclude(id__in=finished_truck_ids)

# Машины для "Available Vehicles"
class AvailableTruckView(generics.ListAPIView):
    serializer_class = TruckSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        # Все занятые машины
        finished_truck_ids = BookingRequest.objects.filter(
            status__in=["Finished", "Cancelled", "Accepted"],
            truck__isnull=False
        ).values_list('truck_id', flat=True)

        return Truck.objects.filter(
            show_in_available_vehicles=True
        ).exclude(id__in=finished_truck_ids)



from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from rest_framework.response import Response

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def sent_requests_view(request):
    user = request.user
    user_id = request.query_params.get("user_id")

    # Если user_id не передан — вернём заявки текущего юзера
    if not user_id:
        qs = BookingRequest.objects.filter(sender=user)
        serializer = BookingRequestSerializer(qs, many=True, context={'request': request})
        return Response(serializer.data)

    # Проверяем, что текущий пользователь — владелец или менеджер
    from .utils import get_user_company_and_role
    company, role = get_user_company_and_role(user)

    if role not in ['owner', 'manager']:
        return Response({"error": "Access denied"}, status=403)

    # Проверим, что указанный user_id — это сотрудник этой компании
    try:
        TeamMember.objects.get(company=company, user_id=user_id)
    except TeamMember.DoesNotExist:
        return Response({"error": "User not in your team"}, status=403)

    # Всё ок — возвращаем заявки выбранного сотрудника
    qs = BookingRequest.objects.filter(sender_id=user_id)
    serializer = BookingRequestSerializer(qs, many=True, context={'request': request})
    return Response(serializer.data)



@api_view(['GET'])
@permission_classes([IsAuthenticated])
def received_requests_view(request):
    user = request.user
    user_id = request.query_params.get("user_id")

    if not user_id:
        qs = BookingRequest.objects.filter(receiver=user, status="Waiting")
        serializer = BookingRequestSerializer(qs, many=True, context={'request': request})
        return Response(serializer.data)

    company, role = get_user_company_and_role(user)
    if role not in ['owner', 'manager']:
        return Response({"error": "Access denied"}, status=403)

    try:
        TeamMember.objects.get(company=company, user_id=user_id)
    except TeamMember.DoesNotExist:
        return Response({"error": "User not in your team"}, status=403)

    qs = BookingRequest.objects.filter(receiver_id=user_id, status="Waiting")
    serializer = BookingRequestSerializer(qs, many=True, context={'request': request})
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def active_requests_view(request):
    user = request.user
    user_id = request.query_params.get("user_id")

    if not user_id:
        qs = BookingRequest.objects.filter(
            status="Accepted"
        ).filter(models.Q(sender=user) | models.Q(receiver=user))
        serializer = BookingRequestSerializer(qs, many=True, context={'request': request})
        return Response(serializer.data)

    company, role = get_user_company_and_role(user)
    if role not in ['owner', 'manager']:
        return Response({"error": "Access denied"}, status=403)

    try:
        TeamMember.objects.get(company=company, user_id=user_id)
    except TeamMember.DoesNotExist:
        return Response({"error": "User not in your team"}, status=403)

    qs = BookingRequest.objects.filter(
        status="Accepted"
    ).filter(models.Q(sender_id=user_id) | models.Q(receiver_id=user_id))

    serializer = BookingRequestSerializer(qs, many=True, context={'request': request})
    return Response(serializer.data)




@api_view(['GET'])
@permission_classes([IsAuthenticated])
def archived_requests_view(request):
    user = request.user
    user_id = request.query_params.get("user_id")

    if not user_id:
        qs = BookingRequest.objects.filter(
            status="Finished"
        ).filter(
            (models.Q(sender=user) & models.Q(sender_deleted=False)) |
            (models.Q(receiver=user) & models.Q(receiver_deleted=False))
        )
        serializer = BookingRequestSerializer(qs, many=True, context={'request': request})
        return Response(serializer.data)

    company, role = get_user_company_and_role(user)
    if role not in ['owner', 'manager']:
        return Response({"error": "Access denied"}, status=403)

    try:
        TeamMember.objects.get(company=company, user_id=user_id)
    except TeamMember.DoesNotExist:
        return Response({"error": "User not in your team"}, status=403)

    qs = BookingRequest.objects.filter(
        status="Finished"
    ).filter(
        (models.Q(sender_id=user_id) & models.Q(sender_deleted=False)) |
        (models.Q(receiver_id=user_id) & models.Q(receiver_deleted=False))
    )

    serializer = BookingRequestSerializer(qs, many=True, context={'request': request})
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def soft_delete_booking_for_user(request, booking_id):
    user = request.user
    try:
        booking = BookingRequest.objects.get(id=booking_id)
    except BookingRequest.DoesNotExist:
        return Response({'error': 'Заявка не найдена'}, status=404)

    if booking.sender == user:
        booking.sender_deleted = True
    elif booking.receiver == user:
        booking.receiver_deleted = True
    else:
        return Response({'error': 'Нет доступа'}, status=403)

    booking.save()
    return Response({'message': 'Заявка скрыта для текущего пользователя'}, status=200)


@api_view(['GET', 'POST', 'DELETE'])
@permission_classes([IsAuthenticated])
def company_photo_view(request):
    profile = request.user.profile

    if request.method == 'GET':
        if profile.company_photo:
            return Response({"photo_url": request.build_absolute_uri(profile.company_photo.url)})
        return Response({"photo_url": "/static/images/no-photo-placeholder.png"})

    elif request.method == 'POST':
        photo = request.FILES.get('company_photo')
        if not photo:
            return Response({"error": "No photo provided"}, status=400)

        profile.company_photo = photo
        profile.save()
        return Response({"photo_url": request.build_absolute_uri(profile.company_photo.url)}, status=201)

    elif request.method == 'DELETE':
        if profile.company_photo:
            profile.company_photo.delete(save=False)  # удаляет файл физически
            profile.company_photo = None              # очищает ссылку в базе
            profile.save()
            return Response({"message": "Photo deleted successfully."}, status=204)
        return Response({"error": "No photo to delete."}, status=404)


class BookingRequestListCreateView(generics.ListCreateAPIView):
    queryset = BookingRequest.objects.all()
    serializer_class = BookingRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Показывать только заявки, отправленные текущим пользователем
        return BookingRequest.objects.filter(sender=self.request.user)

    def perform_create(self, serializer):
        sender = self.request.user
        data = self.request.data

        cargo_id = data.get("cargo")
        truck_id = data.get("truck")

        receiver = None

        if cargo_id:
            try:
                cargo = Cargo.objects.get(id=cargo_id)
                receiver = cargo.user
            except Cargo.DoesNotExist:
                raise serializers.ValidationError("Груз не найден")
        elif truck_id:
            try:
                truck = Truck.objects.get(id=truck_id)
                receiver = truck.user
            except Truck.DoesNotExist:
                raise serializers.ValidationError("Транспорт не найден")
        else:
            raise serializers.ValidationError("Нужно указать cargo или truck")

        serializer.save(sender=sender, receiver=receiver)
        # 🔔 Уведомление получателю
        if receiver:
            send_notification_to_user(receiver.id, f"Вам поступил новый запрос от {sender.username}")

class BookingRequestDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = BookingRequest.objects.all()
    serializer_class = BookingRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        obj = super().get_object()
        if obj.receiver != self.request.user and obj.sender != self.request.user:
            raise PermissionDenied("Вы не можете изменить эту заявку.")
        return obj

    def patch(self, request, *args, **kwargs):
        instance = self.get_object()
        new_status = request.data.get("status")

        print(f"🔄 PATCH booking ID {instance.id} — {instance.status} → {new_status}")
        print(f"👤 Запрос от пользователя: {request.user.username} (ID: {request.user.id})")

        if new_status not in ["Accepted", "Rejected", "Finished", "Cancelled"]:
            return Response({"error": "Неверный статус."}, status=400)

        instance.status = new_status
        instance.save()

        # 🔔 Отправка уведомлений обеим сторонам
        if new_status == "Accepted":
            send_notification_to_user(instance.sender.id, f"Ваш запрос был принят {instance.receiver.username}")
            send_notification_to_user(instance.receiver.id, f"Вы приняли запрос от {instance.sender.username}")

        elif new_status == "Rejected":
            send_notification_to_user(instance.sender.id, f"Ваш запрос был отклонён {instance.receiver.username}")

        elif new_status == "Finished":
            send_notification_to_user(instance.sender.id, f"Ваш заказ завершён {instance.receiver.username}")
            send_notification_to_user(instance.receiver.id, f"Вы завершили заказ с {instance.sender.username}")

        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def perform_destroy(self, instance):
        user = self.request.user

        if instance.sender == user:
            instance.sender_deleted = True
        elif instance.receiver == user:
            instance.receiver_deleted = True
        else:
            raise PermissionDenied("Вы не имеете доступа к этой заявке.")

        if instance.sender_deleted and instance.receiver_deleted:
            # Если оба удалили — тогда удаляем полностью
            print(f"🗑️ Оба пользователя удалили → удаляем полностью: {instance.id}")
            if instance.cargo:
                instance.cargo.delete()
            if instance.truck:
                instance.truck.delete()
            instance.delete()
        else:
            print(f"❕ Только один удалил → сохраняем заявку (ID: {instance.id})")
            instance.save()


def send_notification_to_user(user_id, message):
    try:
        profile = Profile.objects.get(user_id=user_id)
        if not profile.notifications_enabled:
            print(f"[INFO] Уведомления отключены для user_id={user_id}")
            return  # ⛔ Не отправляем
    except Profile.DoesNotExist:
        print(f"[WARNING] Профиль не найден для user_id={user_id}")
        return

    # 1. Сохраняем в базу
    Notification.objects.create(
        receiver_id=user_id,
        message=message
    )

    # 2. Отправляем по WebSocket
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"user_{user_id}",
        {
            "type": "send_notification",
            "message": message
        }
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_notifications(request):
    notifications = Notification.objects.filter(receiver=request.user).order_by('-created_at')
    serializer = NotificationSerializer(notifications, many=True)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_notification_as_read(request, notification_id):
    try:
        notification = Notification.objects.get(id=notification_id, receiver=request.user)
        notification.is_read = True
        notification.save()
        return Response({'status': 'marked as read'})
    except Notification.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)

class CreateTeamCompanyView(generics.CreateAPIView):
    serializer_class = TeamCompanySerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        registered_company = RegisteredCompany.objects.filter(registered_by=self.request.user).first()

        if not registered_company:
            raise PermissionDenied("Сначала зарегистрируйте компанию.")

        if TeamCompany.objects.filter(registered_company=registered_company).exists():
            raise PermissionDenied("Команда уже была создана для этой компании.")

        serializer.save(
            created_by=self.request.user,
            registered_company=registered_company
        )




class TeamMemberCreateView(generics.CreateAPIView):
    serializer_class = TeamMemberSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        company, _ = get_user_company_and_role(self.request.user)
        context['company'] = company  # 👈 вот это нужно
        return context

    def perform_create(self, serializer):
        company, role = get_user_company_and_role(self.request.user)

        if role not in ['owner', 'manager']:
            raise PermissionDenied("Только владелец или менеджер может добавлять сотрудников.")


        print("[DEBUG] Пришли данные:", self.request.data)
        print("[DEBUG] Привязываем к компании:", company)

        new_member = serializer.save()

        # 👇 Записываем название компании в профиль сотрудника
        if hasattr(new_member.user, 'profile'):
            new_member.user.profile.company = company.name
            new_member.user.profile.save()







# def perform_create(self, serializer):
#     print("[DEBUG] Данные от фронта:", self.request.data)  # 👈 печатаем всё, что пришло

class TeamMemberListView(ListAPIView):
    serializer_class = TeamMemberDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        company, role = get_user_company_and_role(self.request.user)

        if role not in ['owner', 'manager']:
            return TeamMember.objects.none()

        return TeamMember.objects.filter(company=company)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_company_info(request):
    user = request.user
    profile = getattr(user, 'profile', None)

    # 1. Если пользователь — сотрудник (TeamMember)
    team_member = TeamMember.objects.select_related('company__registered_company').filter(user=user).first()
    if team_member:
        company = team_member.company
        registered = company.registered_company
        return Response({
            'name': company.name,
            'zip_code': profile.zip_code if profile else '',
            'city': profile.city if profile else '',
            'address': profile.address if profile else '',
            'canton': profile.canton if profile else ''
        })

    # 2. Если пользователь — владелец (зарегистрировал компанию)
    registered = RegisteredCompany.objects.filter(registered_by=user).first()
    if registered and profile:
        return Response({
            'name': profile.company or '',
            'zip_code': profile.zip_code or '',
            'city': profile.city or '',
            'address': profile.address or '',
            'canton': profile.canton or ''
        })

    return Response({'error': 'Company not found'}, status=404)

class SearchCargoView(generics.ListAPIView):
    serializer_class = CargoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        finished_cargo_ids = BookingRequest.objects.filter(
            status__in=["Finished", "Cancelled"],
            cargo__isnull=False
        ).values_list('cargo_id', flat=True)

        sort_param = self.request.query_params.get('sort', 'createdAt_desc')

        sort_map = {
            'createdAt_desc': '-created_at',
            'createdAt_asc': 'created_at',
            'price_asc': 'price',
            'price_desc': '-price',
            'pickupDate_asc': 'pickup_date',
            'pickupDate_desc': '-pickup_date',
            'weight_asc': 'weight',
            'weight_desc': '-weight'
        }

        ordering = sort_map.get(sort_param, '-created_at')

        return Cargo.objects.exclude(id__in=finished_cargo_ids).order_by(ordering)



class SearchTruckView(generics.ListAPIView):
    serializer_class = TruckSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        finished_truck_ids = BookingRequest.objects.filter(
            status__in=["Finished", "Cancelled"],
            truck__isnull=False
        ).values_list('truck_id', flat=True)

        sort_param = self.request.query_params.get('sort', 'createdAt_desc')

        sort_map = {
            'createdAt_desc': '-created_at',
            'createdAt_asc': 'created_at',
            'price_asc': 'price',
            'price_desc': '-price',
            'availableDate_asc': 'loading_date_from',
            'availableDate_desc': '-loading_date_from',
            'capacity_asc': 'carrying_capacity',
            'capacity_desc': '-carrying_capacity'
        }

        ordering = sort_map.get(sort_param, '-created_at')

        return Truck.objects.exclude(id__in=finished_truck_ids).order_by(ordering)


class GetTeamMembersView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        company, role = get_user_company_and_role(request.user)

        if role not in ['owner', 'manager']:
            raise PermissionDenied("Нет доступа")

        members = TeamMember.objects.filter(company=company).select_related('user')

        data = [
            {
                "id": m.user.id,
                "name": m.full_name or m.user.username,
                "role": m.role
            }
            for m in members
        ]

        return Response(data)

class GetUserOrdersView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user_id = request.query_params.get("user_id")
        order_type = request.query_params.get("type")

        if not user_id or not order_type:
            return Response({"error": "Missing parameters"}, status=400)

        company, role = get_user_company_and_role(request.user)
        if role not in ['owner', 'manager']:
            raise PermissionDenied("Нет доступа")

        # Убедимся, что сотрудник принадлежит компании
        try:
            member = TeamMember.objects.get(company=company, user_id=user_id)
        except TeamMember.DoesNotExist:
            return Response([], status=404)

        if order_type == "cargo":
            orders = Cargo.objects.filter(user_id=user_id)
            return Response(CargoSerializer(orders, many=True).data)
        elif order_type == "truck":
            orders = Truck.objects.filter(user_id=user_id)
            return Response(TruckSerializer(orders, many=True).data)

        return Response({"error": "Invalid type"}, status=400)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def find_order_by_number(request):
    number = request.query_params.get("number")

    if not number:
        return Response({"error": "Номер не передан"}, status=400)

    if number.startswith("C"):
        try:
            cargo = Cargo.objects.get(order_number=number)
            data = CargoSerializer(cargo, context={'request': request}).data
            return Response({"type": "cargo", "data": data})
        except Cargo.DoesNotExist:
            return Response({"error": "Груз не найден"}, status=404)

    elif number.startswith("V"):
        try:
            truck = Truck.objects.get(order_number=number)
            data = TruckSerializer(truck, context={'request': request}).data
            return Response({"type": "truck", "data": data})
        except Truck.DoesNotExist:
            return Response({"error": "Машина не найдена"}, status=404)

    else:
        return Response({"error": "Неверный формат номера"}, status=400)



@api_view(['GET'])
@permission_classes([IsAuthenticated])
def generate_2fa_qr(request):
    user_profile = request.user.profile

    # Генерируем секрет (если его ещё нет)
    if not user_profile.two_factor_secret:
        secret = pyotp.random_base32()
        user_profile.two_factor_secret = secret
        user_profile.save()
    else:
        secret = user_profile.two_factor_secret

    # Формируем otpauth URI
    otp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
        name=request.user.email,
        issuer_name="Platforma"
    )

    # Генерация QR-кода → base64
    qr = qrcode.make(otp_uri)
    buffer = io.BytesIO()
    qr.save(buffer, format="PNG")
    qr_b64 = base64.b64encode(buffer.getvalue()).decode()

    return Response({
        "qr_code_base64": f"data:image/png;base64,{qr_b64}",
        "secret": secret
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_2fa_code(request):
    user_profile = request.user.profile
    code = request.data.get("code")

    if not user_profile.two_factor_secret:
        return Response({"error": "2FA не настроена"}, status=400)

    if not code:
        return Response({"error": "Код обязателен"}, status=400)

    totp = pyotp.TOTP(user_profile.two_factor_secret)

    if totp.verify(code, valid_window=1):
        user_profile.is_2fa_enabled = True

        user_profile.save()
        print("✅ 2FA подтверждена и сохранена!")  # ← это выведется в терминал
        print("[DEBUG] is_2fa_enabled:", user_profile.is_2fa_enabled)
        return Response({"success": "2FA включена"})
    else:
        return Response({"error": "Неверный код"}, status=400)


class Generate2FAView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        # 1. Генерируем секрет
        secret = pyotp.random_base32()
        user.profile.two_factor_secret = secret
        user.profile.save()

        # 2. Генерируем URL для Google Authenticator
        otp_uri = pyotp.totp.TOTP(secret).provisioning_uri(name=user.email, issuer_name="Platforma")

        # 3. Генерируем QR-код
        qr = qrcode.make(otp_uri)
        buffer = io.BytesIO()
        qr.save(buffer, format="PNG")
        qr_code_base64 = base64.b64encode(buffer.getvalue()).decode()

        return Response({
            "secret": secret,
            "qr_code_base64": f"data:image/png;base64,{qr_code_base64}"
        })

class Verify2FAView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        code = request.data.get("code")
        user = request.user

        if not user.profile.two_factor_secret:
            return Response({"detail": "2FA не сгенерирована"}, status=status.HTTP_400_BAD_REQUEST)

        totp = pyotp.TOTP(user.profile.two_factor_secret)
        if totp.verify(code):
            user.profile.is_two_factor_enabled = True
            user.profile.save()
            return Response({"detail": "2FA включена!"})
        else:
            return Response({"detail": "Неверный код"}, status=status.HTTP_400_BAD_REQUEST)

class Disable2FAView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        user = request.user
        profile = user.profile

        profile.is_2fa_enabled = False  # ← правильное поле
        profile.two_factor_secret = ''
        profile.save()

        return Response({"detail": "2FA отключена!"}, status=status.HTTP_200_OK)

class Verify2FALoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        code = request.data.get("code")

        if not email or not code:
            return Response({"error": "Email и код обязательны"}, status=400)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"error": "Пользователь не найден"}, status=404)

        profile = getattr(user, "profile", None)
        if not profile or not profile.two_factor_secret:
            return Response({"error": "2FA не настроена"}, status=400)

        totp = pyotp.TOTP(profile.two_factor_secret)
        if not totp.verify(code, valid_window=1):
            return Response({"error": "Неверный код"}, status=400)

        # ✅ Если код верный — выдаём токен
        refresh = RefreshToken.for_user(user)
        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh)
        })

class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        old_password = request.data.get("old_password")
        new_password = request.data.get("new_password")

        if not old_password or not new_password:
            return Response({"error": "Старый и новый пароль обязательны"}, status=400)

        if not user.check_password(old_password):
            return Response({"error": "Неверный старый пароль"}, status=400)

        user.set_password(new_password)
        user.save()
        return Response({"message": "Пароль успешно изменён"})


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def notifications_toggle_view(request):
    profile = request.user.profile

    if request.method == 'GET':
        return Response({'notifications_enabled': profile.notifications_enabled})

    if request.method == 'POST':
        new_value = request.data.get('notifications_enabled')
        if new_value is not None:
            profile.notifications_enabled = new_value in ['true', 'True', True, 1, '1']
            profile.save()
            return Response({'notifications_enabled': profile.notifications_enabled})
        else:
            return Response({'error': 'Missing notifications_enabled'}, status=400) 

class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        queryset = Review.objects.all()
        booking_id = self.request.query_params.get('booking')
        target_id = self.request.query_params.get('target_user')
        author_id = self.request.query_params.get('author')

        if booking_id:
            queryset = queryset.filter(booking_id=booking_id)
        if target_id:
            queryset = queryset.filter(target_user_id=target_id)
        if author_id:
            queryset = queryset.filter(author_id=author_id)

        return queryset

    def perform_create(self, serializer):
        author = self.request.user
        target_user = self.request.data.get('target_user')
        booking = self.request.data.get('booking')

        if Review.objects.filter(author=author, target_user_id=target_user, booking_id=booking).exists():
            raise PermissionDenied("Вы уже оставили отзыв для этого пользователя по этому заказу.")

        serializer.save()

from .utils import get_user_rating_data  # ⬅️ подключаем функцию из utils

@api_view(['GET'])
@permission_classes([AllowAny])  # можно смотреть всем
def get_user_rating(request, user_id):
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({"error": "Пользователь не найден"}, status=404)

    average, total = get_user_rating_data(user)
    return Response({
        "rating": average,
        "reviews": total
    })

from django.http import JsonResponse
from django.contrib.auth import get_user_model

User = get_user_model()

@api_view(['GET'])
def get_user_rating_by_email(request):
    email = request.GET.get('email')
    if not email:
        return JsonResponse({'error': 'Email is required'}, status=400)

    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)

    average, count = get_user_rating_data(user)
    return JsonResponse({'rating': average, 'reviews': count}) 


