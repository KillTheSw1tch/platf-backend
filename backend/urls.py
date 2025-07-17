from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView

from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from api.token_views import EmailTokenObtainPairView
from api.views import (
    CreateUserView, UserProfileAPIView, add_cargo_view,
    TruckViewSet, CargoViewSet,
    VerifyEmailCodeView, TruckListCreateView,
    validate_company_code, CompanyDocumentUploadView,
    check_documents_approval, register_company,
    CompanyProfileByNameView, MainPageCargoView,
    AvailableCargoView, MainPageTruckView, AvailableTruckView,
    company_photo_view, BookingRequestListCreateView,
    BookingRequestDetailView, sent_requests_view, received_requests_view,
    active_requests_view, archived_requests_view, get_user_notifications, 
    mark_notification_as_read, CreateTeamCompanyView, TeamMemberCreateView,
    TeamMemberListView, get_company_info, SearchCargoView, SearchTruckView,
    GetTeamMembersView, GetUserOrdersView, find_order_by_number, soft_delete_booking_for_user,
    generate_2fa_qr, verify_2fa_code, Verify2FAView, Disable2FAView, Verify2FALoginView,
    ChangePasswordView, notifications_toggle_view, ReviewViewSet,
    get_user_rating, get_user_rating_by_email, FrontendAppView,
)

# 📦 Роутер для ViewSet'ов
router = DefaultRouter()
router.register(r'cargo', CargoViewSet)
router.register(r'trucks', TruckViewSet, basename='truck')

router.register(r'reviews', ReviewViewSet, basename='review')


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include(router.urls)),

    # 🧑 Пользователь
    path("api/user/register/", CreateUserView.as_view(), name="register"),
    path("api/user/profile/", UserProfileAPIView.as_view(), name="user-profile"),
    path("api/user/verify/", VerifyEmailCodeView.as_view(), name="verify"),

    path("api/user/generate-2fa/", generate_2fa_qr, name="generate-2fa"),

    path("api/user/verify-2fa/", verify_2fa_code, name="verify-2fa"),

    path("user/verify-2fa/", Verify2FAView.as_view(), name="verify-2fa"),

    path("api/user/disable-2fa/", Disable2FAView.as_view(), name="disable-2fa"),

    path("api/user/change-password/", ChangePasswordView.as_view(), name="change-password"),

    path('api/user/notifications-toggle/', notifications_toggle_view, name='notifications-toggle'),

    path("api/user/<int:user_id>/rating/", get_user_rating, name="user-rating"),

    path('api/user-rating-by-email/', get_user_rating_by_email, name='user-rating-by-email'),




    # 🔐 Аутентификация
    path("api/token/", EmailTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="refresh"),
    path("api-auth/", include("rest_framework.urls")),

    # 🏠 Статические страницы
    path('registration/', TemplateView.as_view(template_name='api/registrationCarrier.html'), name='registration'),
    path('login/', TemplateView.as_view(template_name='api/login.html'), name='login'),

    path("api/verify-2fa-login/", Verify2FALoginView.as_view(), name="verify_2fa_login"),

    path("api/verify-2fa-login/", Verify2FALoginView.as_view()),


    

    # 🚛 Грузы и машины
    path('add-cargo/', add_cargo_view, name='add_cargo'),
    path('trucks/', TruckListCreateView.as_view(), name='truck-list-create'),
    path('api/main-cargo/', MainPageCargoView.as_view(), name='main-cargo'),
    path('api/available-cargo/', AvailableCargoView.as_view(), name='available-cargo'),
    path('api/main-truck/', MainPageTruckView.as_view(), name='main-truck'),
    path('api/available-truck/', AvailableTruckView.as_view(), name='available-truck'),
    path('api/search-cargo/', SearchCargoView.as_view(), name='search-cargo'),
    path('api/search-truck/', SearchTruckView.as_view(), name='search-truck'),
    path('api/find-order/', find_order_by_number, name='find-order'),
    path('api/bookings/<int:booking_id>/soft-delete/', soft_delete_booking_for_user, name='soft-delete-booking'),


    

    # 🏢 Компания
    path("api/validate-company-code/", validate_company_code, name="validate-company-code"),
    path('api/company/upload-documents/', CompanyDocumentUploadView.as_view(), name='upload-documents'),
    path('api/company/check-approval/', check_documents_approval, name='check-documents-approval'),
    path('api/register-company/', register_company, name='register-company'),
    path('api/company-by-name/<str:name>/', CompanyProfileByNameView.as_view(), name='company-by-name'),
    path('api/company/photo/', company_photo_view, name='company-photo'),
    path('api/team/create-company/', CreateTeamCompanyView.as_view(), name='create-team-company'),
    path('api/team/add-member/', TeamMemberCreateView.as_view(), name='add-team-member'),
    path('api/company/info/', get_company_info, name='get_company_info'),
    path('api/team/members/', GetTeamMembersView.as_view(), name='team-members'),
    path("api/team/orders/", GetUserOrdersView.as_view(), name="team-orders"),


    # 🧾 Заявки на бронирование
    path('api/booking-requests/', BookingRequestListCreateView.as_view(), name='booking-request-list'),
    path('api/booking-requests/<int:pk>/', BookingRequestDetailView.as_view(), name='booking-request-detail'),

    path('api/booking-requests/sent/', sent_requests_view, name='sent-requests'),
    path('api/booking-requests/received/', received_requests_view, name='received-requests'),
    path('api/booking-requests/active/', active_requests_view, name='active-requests'),
    path('api/booking-requests/archived/', archived_requests_view, name='archived-requests'),

    path('api/notifications/', get_user_notifications, name='user-notifications'),
    path('api/notifications/<int:notification_id>/read/', mark_notification_as_read, name='mark-notification-read'),
]

# SPA: всі не-API і не-admin шляхи віддають index.html
urlpatterns += [
    re_path(r'^(?!api/|admin/|static/).*$', TemplateView.as_view(template_name="index.html")),
]

# ⚙️ Для отдачи медиафайлов в режиме разработки
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
