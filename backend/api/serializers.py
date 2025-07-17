
from django.contrib.auth.models import User
from rest_framework import serializers
from .models import Cargo, Profile, Truck, CompanyDocument

from .models import BookingRequest

from django.db import IntegrityError
from rest_framework.exceptions import ValidationError

from .models import Notification

from .models import TeamCompany, TeamMember



class UserSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(
        required=True,
        allow_blank=False,
        label="Email",
        error_messages={
            "unique": "Пользователь с таким email уже существует.",
        }
    )

    class Meta:
        model = User
        fields = ["id", "username", "password", "email"]
        extra_kwargs = {
            "password": {"write_only": True},
        }

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Этот email уже используется.")
        return value

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)
        

class CargoSerializer(serializers.ModelSerializer):
    company_name = serializers.SerializerMethodField()
    contact_name = serializers.SerializerMethodField()
    company_logo_url = serializers.SerializerMethodField()  # 👈

    class Meta:
        model = Cargo
        fields = '__all__'

    def get_company_name(self, obj):
        if obj.user and hasattr(obj.user, 'profile') and obj.user.profile and obj.user.profile.company:
            return obj.user.profile.company
        return None

    def get_contact_name(self, obj):
        if obj.user and hasattr(obj.user, 'profile'):
            return obj.user.profile.full_name or obj.user.username
        return None

    def get_company_logo_url(self, obj):  # 👈
        request = self.context.get('request')
        if obj.user and hasattr(obj.user, 'profile') and obj.user.profile.company_photo:
            return request.build_absolute_uri(obj.user.profile.company_photo.url) if request else obj.user.profile.company_photo.url
        return None

    status = serializers.SerializerMethodField()  # 👈 ДОБАВЬ ЭТУ СТРОКУ

    def get_status(self, obj):
        user = self.context.get('request').user
        if not user or user.is_anonymous:
            return None

        # Если пользователь — ВЛАДЕЛЕЦ груза
        if obj.user == user:
            # Проверяем все заявки на этот груз
            bookings = BookingRequest.objects.filter(cargo=obj).exclude(status__in=["Cancelled", "Rejected"])
            for booking in bookings:
                if booking.status == "Finished":
                    return "Finished"
                elif booking.status == "Accepted":
                    return "In Process"
            return None

        # Если пользователь — ОТПРАВИТЕЛЬ заявки
        booking = BookingRequest.objects.filter(cargo=obj, sender=user).exclude(status="Cancelled").first()
        if booking:
            if booking.status == "Waiting":
                return "Booked"
            elif booking.status == "Accepted":
                return "In Process"
            elif booking.status == "Rejected":
                return "Rejected"
            elif booking.status == "Finished":
                return "Finished"

        return None



class TruckSerializer(serializers.ModelSerializer):
    company_name = serializers.SerializerMethodField()
    contact_name = serializers.SerializerMethodField()
    company_logo_url = serializers.SerializerMethodField()  # 👈

    class Meta:
        model = Truck
        fields = '__all__'

    def get_company_name(self, obj):
        if obj.user and hasattr(obj.user, 'profile') and obj.user.profile and obj.user.profile.company:
            return obj.user.profile.company
        return None

    def get_contact_name(self, obj):
        if obj.user:
            return obj.user.username
        return None

    def get_company_logo_url(self, obj):  # 👈
        request = self.context.get('request')
        if obj.user and hasattr(obj.user, 'profile') and obj.user.profile.company_photo:
            return request.build_absolute_uri(obj.user.profile.company_photo.url) if request else obj.user.profile.company_photo.url
        return None

    status = serializers.SerializerMethodField()

    def get_status(self, obj):
        user = self.context.get('request').user
        if not user or user.is_anonymous:
            return None

        # Если пользователь — ВЛАДЕЛЕЦ транспорта
        if obj.user == user:
            bookings = BookingRequest.objects.filter(truck=obj).exclude(status__in=["Cancelled", "Rejected"])
            for booking in bookings:
                if booking.status == "Finished":
                    return "Finished"
                elif booking.status == "Accepted":
                    return "In Process"
            return None

        # Если пользователь — ОТПРАВИТЕЛЬ заявки
        booking = BookingRequest.objects.filter(truck=obj, sender=user).exclude(status="Cancelled").first()
        if booking:
            if booking.status == "Waiting":
                return "Booked"
            elif booking.status == "Accepted":
                return "In Process"
            elif booking.status == "Rejected":
                return "Rejected"
            elif booking.status == "Finished":
                return "Finished"

        return None


      
class ProfileSerializer(serializers.ModelSerializer):
    company_photo_url = serializers.SerializerMethodField()
    is_2fa_enabled = serializers.BooleanField(read_only=True)

    class Meta:
        model = Profile
        fields = [
            'company', 'address', 'canton', 'zip_code', 'city',
            'phone', 'mobile', 'preferred_language', 'viber_whatsapp_number',
            'client_type', 'company_photo_url', 'full_name',
            'is_2fa_enabled',  # 👈 ДОБАВЬ СЮДА
        ]

    def get_company_photo_url(self, obj):
        request = self.context.get('request')
        if obj.company_photo:
            return request.build_absolute_uri(obj.company_photo.url) if request else obj.company_photo.url
        return None



class ExtendedUserSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer()

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password', 'profile']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        profile_data = validated_data.pop('profile', {})
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password']
        )

        # Профиль уже создан сигналом — обновляем поля
        for attr, value in profile_data.items():
            setattr(user.profile, attr, value)
        user.profile.save()

        return user

    def update(self, instance, validated_data):
        profile_data = validated_data.pop('profile', {})
        profile, created = Profile.objects.get_or_create(user=instance)

        instance.username = validated_data.get('username', instance.username)
        instance.email = validated_data.get('email', instance.email)

        if 'password' in validated_data:
            instance.set_password(validated_data['password'])
        instance.save()

        for attr, value in profile_data.items():
            setattr(profile, attr, value)
        profile.save()

        return instance
    
from .models import CompanyDocument

class CompanyDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyDocument
        fields = ['id', 'user', 'file', 'uploaded_at']
        read_only_fields = ['id', 'uploaded_at']

class BookingRequestSerializer(serializers.ModelSerializer):
    sender_username = serializers.CharField(source='sender.username', read_only=True)
    sender_company = serializers.SerializerMethodField()
    receiver_username = serializers.CharField(source='receiver.username', read_only=True)
    receiver_company = serializers.SerializerMethodField()

    cargo_data = CargoSerializer(source='cargo', read_only=True)
    truck_data = TruckSerializer(source='truck', read_only=True)

    cargo = serializers.PrimaryKeyRelatedField(queryset=Cargo.objects.all(), required=False, allow_null=True)
    truck = serializers.PrimaryKeyRelatedField(queryset=Truck.objects.all(), required=False, allow_null=True)

    counterpart_user_id = serializers.SerializerMethodField()

    def get_counterpart_user_id(self, obj):
        request = self.context.get('request')
        if not request:
            return None
        current_user = request.user
        if obj.sender == current_user:
            return obj.receiver.id
        elif obj.receiver == current_user:
            return obj.sender.id
        return None


    class Meta:
        model = BookingRequest
        fields = [
            'id',
            'sender',
            'sender_username',
            'sender_company',
            'receiver',
            'receiver_username',
            'receiver_company',
            'cargo',
            'truck',
            'cargo_data',
            'truck_data',
            'status',
            'message',
            'created_at',
            'updated_at',
            'counterpart_user_id',  # ✅ ДОБАВИЛИ
        ]
        read_only_fields = ['sender', 'receiver', 'created_at', 'updated_at']

    def get_sender_company(self, obj):
        profile = getattr(obj.sender, 'profile', None)
        return profile.company if profile else None

    def get_receiver_company(self, obj):
        profile = getattr(obj.receiver, 'profile', None)
        return profile.company if profile else None

    def get_counterpart_user_id(self, obj):  # ✅ ДОБАВИЛИ
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None

        user = request.user

        if obj.sender == user:
            return obj.receiver.id if obj.receiver else None
        elif obj.receiver == user:
            return obj.sender.id if obj.sender else None

        return None

    def validate(self, data):
        sender = self.context['request'].user
        cargo = data.get("cargo")
        truck = data.get("truck")

        if not cargo and not truck:
            raise serializers.ValidationError("Нужно указать хотя бы груз или транспорт.")

        if cargo:
            active = BookingRequest.objects.filter(sender=sender, cargo=cargo, status='Waiting')
            if active.exists():
                raise serializers.ValidationError("⏳ Вы уже отправили заявку на этот груз и она ожидает обработки.")

        if truck:
            active = BookingRequest.objects.filter(sender=sender, truck=truck, status='Waiting')
            if active.exists():
                raise serializers.ValidationError("⏳ Вы уже отправили заявку на этот транспорт и она ожидает обработки.")

        return data

    def create(self, validated_data):
        request = self.context.get("request")
        sender = request.user
        cargo = validated_data.get("cargo")
        truck = validated_data.get("truck")
        message = validated_data.get("message")

        receiver = cargo.user if cargo else truck.user if truck else None
        if not receiver:
            raise serializers.ValidationError("Нужно указать либо груз, либо транспорт.")

        try:
            return BookingRequest.objects.create(
                sender=sender,
                receiver=receiver,
                cargo=cargo,
                truck=truck,
                message=message
            )
        except IntegrityError:
            raise ValidationError("Вы уже отправляли заявку на этот груз или транспорт.")

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'message', 'is_read', 'created_at']

class TeamCompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = TeamCompany
        fields = ['id', 'name', 'created_by', 'created_at']
        read_only_fields = ['id', 'created_by', 'created_at']

    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['created_by'] = user
        return super().create(validated_data)


class TeamMemberSerializer(serializers.ModelSerializer):
    username = serializers.CharField(write_only=True)
    password = serializers.CharField(write_only=True)
    viber_whatsapp_number = serializers.CharField(write_only=True, required=False, allow_blank=True)

    address = serializers.CharField(write_only=True, required=False, allow_blank=True)
    zip_code = serializers.CharField(write_only=True, required=False, allow_blank=True)
    city = serializers.CharField(write_only=True, required=False, allow_blank=True)
    canton = serializers.CharField(write_only=True, required=False, allow_blank=True)


    class Meta:
        model = TeamMember
        fields = [
            'id', 'company', 'user',
            'role', 'phone', 'email',
            'full_name', 'username', 'password', 'viber_whatsapp_number',
            'address', 'zip_code', 'city', 'canton',
        ]

        read_only_fields = ['id', 'user', 'company']

    def create(self, validated_data):
        username = validated_data.pop('username')
        password = validated_data.pop('password')
        viber = validated_data.pop('viber_whatsapp_number', '')

        email = validated_data.get('email')
        full_name = validated_data.get('full_name', '')
        phone = validated_data.get('phone', '')

        # 🔴 НОВОЕ: получаем доп. поля
        address = validated_data.get('address', '')
        zip_code = validated_data.get('zip_code', '')
        city = validated_data.get('city', '')
        canton = validated_data.get('canton', '')

        if User.objects.filter(username=username).exists():
            raise serializers.ValidationError("Пользователь с таким логином уже существует.")
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError("Пользователь с таким email уже существует.")

        user = User.objects.create_user(username=username, password=password, email=email)

        company = self.context.get('company')
        if not company:
            raise serializers.ValidationError({'company': 'Компания не найдена.'})

        team_member = TeamMember.objects.create(
            company=company,
            user=user,
            role=validated_data.get('role', 'worker'),
            phone=phone,
            email=email,
            full_name=full_name,
        )

        # 🔴 НОВОЕ: обновим профиль сотрудника
        profile = user.profile
        profile.phone = phone
        profile.full_name = full_name
        profile.viber_whatsapp_number = viber
        profile.company = company.name


        # 🔴 Дополним профиль
                # 🔴 Дополним профиль
        # ✅ Подтягиваем с владельца, если пусто
        owner = company.created_by
        owner_profile = getattr(owner, 'profile', None)

        if hasattr(owner_profile, 'company_photo') and owner_profile.company_photo:
            profile.company_photo = owner_profile.company_photo

        if not address:
            address = owner_profile.address
        if not zip_code:
            zip_code = owner_profile.zip_code
        if not city:
            city = owner_profile.city
        if not canton:
            canton = owner_profile.canton

        profile.address = address
        profile.zip_code = zip_code
        profile.city = city
        profile.canton = canton


        profile.save()

        return team_member

class TeamMemberDetailSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    profile_full_name = serializers.CharField(source="user.profile.full_name", read_only=True)
    profile_phone = serializers.CharField(source="user.profile.phone", read_only=True)

    class Meta:
        model = TeamMember
        fields = [
            'id',
            'email',
            'phone',
            'full_name',
            'role',
            'username',
            'profile_full_name',
            'profile_phone',
        ]

from .models import Review

class ReviewSerializer(serializers.ModelSerializer):
    author_username = serializers.CharField(source='author.username', read_only=True)
    target_username = serializers.CharField(source='target_user.username', read_only=True)

    class Meta:
        model = Review
        fields = [
            'id',
            'author',
            'author_username',
            'target_user',
            'target_username',
            'booking',
            'rating',
            'comment',
            'created_at',
            'is_visible',
        ]
        read_only_fields = [
            'id', 'created_at', 'author', 'author_username', 'target_username', 'is_visible'
        ]

    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['author'] = request.user
        return super().create(validated_data)