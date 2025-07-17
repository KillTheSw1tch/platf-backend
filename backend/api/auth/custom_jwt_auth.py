from rest_framework_simplejwt.authentication import JWTAuthentication

class CustomJWTAuthentication(JWTAuthentication):
    def get_header(self, request):
        """
        Этот метод изменяет заголовок с 'Token <...>' на 'Bearer <...>',
        чтобы JWT-аутентификатор понял его.
        """
        header = super().get_header(request)
        if header is None:
            return None

        if header.startswith(b'Token '):
            return b'Bearer ' + header[6:]  # удаляем "Token ", вставляем "Bearer "
        return header
