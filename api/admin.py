from django.contrib import admin
from .models import Cargo, EmailVerification, Truck, Profile, TeamCompany, TeamMember, BookingRequest, CargoAdmin as CargoHistory, TruckAdmin as TruckHistory

@admin.register(Cargo)
class CargoAdmin(admin.ModelAdmin):
    list_display = (
        'loading_city_primary', 'unloading_city_primary', 'date_from', 'cargo_type', 'hidden',
        'show_on_main', 'show_in_available_cargo'
    )
    search_fields = ('loading_city_primary', 'unloading_city_primary', 'cargo_type')
    list_filter = ('cargo_type', 'transport_type', 'humanitarian_aid', 'hidden', 'show_on_main', 'show_in_available_cargo')
    list_editable = ('hidden', 'show_on_main', 'show_in_available_cargo')


@admin.register(EmailVerification)
class EmailVerificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'code', 'created_at')
    search_fields = ('user__username', 'code')

@admin.register(Truck)
class TruckAdmin(admin.ModelAdmin):
    list_display = (
        'loading_city', 'unloading_city', 'vehicle_type', 'loading_date_from',
        'show_on_main', 'show_in_available_vehicles'
    )
    search_fields = ('loading_city', 'unloading_city', 'vehicle_type')
    list_filter = ('vehicle_type', 'has_gps', 'show_on_main', 'show_in_available_vehicles')
    list_editable = ('show_on_main', 'show_in_available_vehicles')


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone', 'company', 'preferred_language')
    search_fields = ('user__username', 'company')

    
from .models import CompanyDocument  # если еще не импортировано выше

@admin.register(CompanyDocument)
class CompanyDocumentAdmin(admin.ModelAdmin):
    list_display = ('user', 'file', 'uploaded_at', 'is_approved', 'is_rejected')
    list_filter = ('is_approved', 'is_rejected', 'uploaded_at')
    list_editable = ('is_approved', 'is_rejected')
    search_fields = ('user__username',)

from .models import RegisteredCompany

@admin.register(RegisteredCompany)
class RegisteredCompanyAdmin(admin.ModelAdmin):
    list_display = ('country', 'code', 'created_at', 'registered_by')
    search_fields = ('code', 'country', 'registered_by__username')
    list_filter = ('country', 'created_at')

@admin.register(TeamCompany)
class TeamCompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_by', 'created_at')
    search_fields = ('name', 'created_by__username')

@admin.register(TeamMember)
class TeamMemberAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'email', 'phone', 'role', 'company')
    search_fields = ('full_name', 'email', 'company__name')
    list_filter = ('role', 'company')

@admin.register(BookingRequest)
class BookingRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'sender', 'receiver', 'status', 'cargo', 'truck', 'created_at')
    list_filter = ('status',)
    search_fields = ('sender__username', 'receiver__username')

@admin.register(CargoHistory)
class CargoHistoryAdmin(admin.ModelAdmin):
    list_display = (
        'order_number',
        'get_sender',
        'get_receiver',
        'loading_city_primary',
        'unloading_city_primary',
        'created_at',
        'get_sent_at',
        'get_accepted_at',
        'get_finished_at',
        'get_finished_by',
        'get_archived_at',
        'get_status',
        'is_archived',
        'get_online_status',
    )


    readonly_fields = (
        'get_sender',
        'get_receiver',
        'get_updated_at',
        'get_status',
        'get_sent_at',
        'get_accepted_at',
        'get_finished_at',
        'get_finished_by',
        'get_archived_at',
        'is_archived',
        'get_online_status',
    )

    fieldsets = (
        (None, {
            'fields': (
                'original',
                'user',
                'order_number',
                'loading_city_primary',
                'unloading_city_primary',
            )
        }),
        ('Информация о бронировании', {
            'fields': (
                'get_sender',
                'get_receiver',
                'get_updated_at',
                'get_status',
                'get_sent_at',
                'get_accepted_at',
                'get_finished_at',
                'get_finished_by',
                'get_archived_at',
                'is_archived',
                'get_online_status',
            )
        }),
    )

    def is_archived(self, obj):
        return obj.original is None

    search_fields = ('order_number', 'user__username', 'loading_city_primary', 'unloading_city_primary')
    list_filter = ('created_at',)

    def get_sender(self, obj):
        return obj.sender.username if obj.sender else '—'


    def get_receiver(self, obj):
        return obj.receiver.username if obj.receiver else '—'


    def get_updated_at(self, obj):
        if not obj.original:
            return '—'
        request = obj.original.booking_requests.order_by('-updated_at').first()
        return request.updated_at if request else '—'

    def get_status(self, obj):
        return obj.status or '—'


    def get_online_status(self, obj):
        if obj.status == 'Accepted':
            return '🟢 Активен'
        elif obj.status == 'Waiting':
            return '🟡 Ожидание'
        elif obj.status in ['Finished', 'Cancelled']:
            return '⚫ Завершён'
        elif obj.status == 'Rejected':
            return '🔴 Отклонён'
        return '❌ Нет данных'


    def get_sent_at(self, obj):
        return obj.sent_at.strftime('%Y-%m-%d %H:%M') if obj.sent_at else '—'


    def get_accepted_at(self, obj):
        return obj.accepted_at.strftime('%Y-%m-%d %H:%M') if obj.accepted_at else '—'


    def get_finished_at(self, obj):
        return obj.finished_at.strftime('%Y-%m-%d %H:%M') if obj.finished_at else '—'


    def get_finished_by(self, obj):
        return obj.finished_by.username if obj.finished_by else '—'


    def get_archived_at(self, obj):
        return obj.archived_at.strftime('%Y-%m-%d %H:%M') if obj.archived_at else '—'



    get_online_status.short_description = "Онлайн статус"


@admin.register(TruckHistory)
class TruckHistoryAdmin(admin.ModelAdmin):
    list_display = (
        'order_number',
        'get_sender',
        'get_receiver',
        'loading_city',
        'unloading_city',
        'created_at',
        'get_sent_at',
        'get_accepted_at',
        'get_finished_at',
        'get_finished_by',
        'get_archived_at',
        'get_status',
        'is_archived',
        'get_online_status',
    )

    readonly_fields = (
        'get_sender',
        'get_receiver',
        'get_updated_at',
        'get_status',
        'get_sent_at',
        'get_accepted_at',
        'get_finished_at',
        'get_finished_by',
        'get_archived_at',
        'is_archived',
        'get_online_status',
    )

    fieldsets = (
        (None, {
            'fields': (
                'original',
                'user',
                'order_number',
                'loading_city',
                'unloading_city',
            )
        }),
        ('Информация о бронировании', {
            'fields': (
                'get_sender',
                'get_receiver',
                'get_updated_at',
                'get_status',
                'get_sent_at',
                'get_accepted_at',
                'get_finished_at',
                'get_finished_by',
                'get_archived_at',
                'is_archived',
                'get_online_status',
            )
        }),
    )

    def is_archived(self, obj):
        return obj.original is None

    def get_sender(self, obj):
        return obj.sender.username if obj.sender else '—'


    def get_receiver(self, obj):
        return obj.receiver.username if obj.receiver else '—'


    def get_updated_at(self, obj):
        if not obj.original:
            return '—'
        request = obj.original.booking_requests.order_by('-updated_at').first()
        return request.updated_at if request else '—'

    def get_status(self, obj):
        return obj.status or '—'


    def get_online_status(self, obj):
        if obj.status == 'Accepted':
            return '🟢 Активен'
        elif obj.status == 'Waiting':
            return '🟡 Ожидание'
        elif obj.status in ['Finished', 'Cancelled']:
            return '⚫ Завершён'
        elif obj.status == 'Rejected':
            return '🔴 Отклонён'
        return '❌ Нет данных'


    def get_sent_at(self, obj):
        return obj.sent_at.strftime('%Y-%m-%d %H:%M') if obj.sent_at else '—'


    def get_accepted_at(self, obj):
        return obj.accepted_at.strftime('%Y-%m-%d %H:%M') if obj.accepted_at else '—'


    def get_finished_at(self, obj):
        return obj.finished_at.strftime('%Y-%m-%d %H:%M') if obj.finished_at else '—'


    def get_finished_by(self, obj):
        return obj.finished_by.username if obj.finished_by else '—'


    def get_archived_at(self, obj):
        return obj.archived_at.strftime('%Y-%m-%d %H:%M') if obj.archived_at else '—'


    get_online_status.short_description = "Онлайн статус" 

from django.contrib import admin
from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = (
        'get_author_email',
        'get_target_email',
        'get_booking_id',
        'rating',
        'is_visible',
        'created_at',

        # ➕ Дополнительно отображаем:
        'cargo_order_number',
        'cargo_loading_city',
        'cargo_unloading_city',
        # 'cargo_type',
        # 'cargo_price',

        'truck_order_number',
        'truck_loading_city',
        'truck_unloading_city',
        # 'truck_type',
        # 'truck_price',
    )

    list_filter = ('is_visible', 'rating', 'created_at')
    search_fields = (
        'author__email', 'target_user__email', 'comment',
        'cargo_order_number', 'truck_order_number'
    )

    readonly_fields = (
        'booking',
        'cargo_order_number', 'cargo_loading_city', 'cargo_unloading_city', 
        'truck_order_number', 'truck_loading_city', 'truck_unloading_city', 
    )

    def get_author_email(self, obj):
        return obj.author.email
    get_author_email.short_description = 'Author'

    def get_target_email(self, obj):
        return obj.target_user.email
    get_target_email.short_description = 'Target'

    def get_booking_id(self, obj):
        return f"#{obj.booking.id}" if obj.booking else "-"
    get_booking_id.short_description = 'Booking'



