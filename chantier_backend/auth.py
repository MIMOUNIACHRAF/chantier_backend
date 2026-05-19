from rest_framework_simplejwt.authentication import JWTAuthentication


class JWTAuthenticationFlex(JWTAuthentication):
    """
    Fallback to X-Authorization when nginx strips the Authorization header
    (PythonAnywhere known limitation).
    """

    def get_header(self, request):
        header = super().get_header(request)
        if header:
            return header
        alt = request.META.get('HTTP_X_AUTHORIZATION', b'')
        if isinstance(alt, str):
            alt = alt.encode('iso-8859-1')
        return alt or None
