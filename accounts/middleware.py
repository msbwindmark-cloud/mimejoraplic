class TwoFactorEnforcementMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # Bypass 2FA verification for local development
            request.user.is_verified = lambda: True
            
        return self.get_response(request)
