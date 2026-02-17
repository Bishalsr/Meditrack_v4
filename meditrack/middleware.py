import time
from importlib import import_module

from django.conf import settings
from django.contrib.sessions.backends.base import UpdateError
from django.contrib.sessions.exceptions import SessionInterrupted
from django.http import HttpRequest
from django.utils.cache import patch_vary_headers
from django.utils.deprecation import MiddlewareMixin
from django.utils.http import http_date


class SplitSessionMiddleware(MiddlewareMixin):
    """
    Keep admin and app authentication sessions separate.

    /admin/... -> ADMIN_SESSION_COOKIE_NAME
    everything else -> APP_SESSION_COOKIE_NAME
    """

    def __init__(self, get_response):
        super().__init__(get_response)
        engine = import_module(settings.SESSION_ENGINE)
        self.SessionStore = engine.SessionStore

    def _is_admin_request(self, request: HttpRequest) -> bool:
        return request.path.startswith("/admin")

    def _cookie_name(self, request: HttpRequest) -> str:
        if self._is_admin_request(request):
            return getattr(settings, "ADMIN_SESSION_COOKIE_NAME", "admin_sessionid")
        return getattr(settings, "APP_SESSION_COOKIE_NAME", "app_sessionid")

    def _cookie_path(self, request: HttpRequest) -> str:
        if self._is_admin_request(request):
            return getattr(settings, "ADMIN_SESSION_COOKIE_PATH", "/admin/")
        return getattr(settings, "APP_SESSION_COOKIE_PATH", settings.SESSION_COOKIE_PATH)

    def process_request(self, request):
        session_cookie_name = self._cookie_name(request)
        session_key = request.COOKIES.get(session_cookie_name)
        request.session = self.SessionStore(session_key)
        request._session_cookie_name = session_cookie_name
        request._session_cookie_path = self._cookie_path(request)

    def process_response(self, request, response):
        try:
            accessed = request.session.accessed
            modified = request.session.modified
            empty = request.session.is_empty()
        except AttributeError:
            return response

        session_cookie_name = getattr(request, "_session_cookie_name", settings.SESSION_COOKIE_NAME)
        session_cookie_path = getattr(request, "_session_cookie_path", settings.SESSION_COOKIE_PATH)

        if session_cookie_name in request.COOKIES and empty:
            response.delete_cookie(
                session_cookie_name,
                path=session_cookie_path,
                domain=settings.SESSION_COOKIE_DOMAIN,
                samesite=settings.SESSION_COOKIE_SAMESITE,
            )
            patch_vary_headers(response, ("Cookie",))
        else:
            if accessed:
                patch_vary_headers(response, ("Cookie",))
            if (modified or settings.SESSION_SAVE_EVERY_REQUEST) and not empty:
                if request.session.get_expire_at_browser_close():
                    max_age = None
                    expires = None
                else:
                    max_age = request.session.get_expiry_age()
                    expires_time = time.time() + max_age
                    expires = http_date(expires_time)

                if response.status_code < 500:
                    try:
                        request.session.save()
                    except UpdateError:
                        raise SessionInterrupted(
                            "The request's session was deleted before the "
                            "request completed. The user may have logged "
                            "out in a concurrent request, for example."
                        )
                    response.set_cookie(
                        session_cookie_name,
                        request.session.session_key,
                        max_age=max_age,
                        expires=expires,
                        domain=settings.SESSION_COOKIE_DOMAIN,
                        path=session_cookie_path,
                        secure=settings.SESSION_COOKIE_SECURE or None,
                        httponly=settings.SESSION_COOKIE_HTTPONLY or None,
                        samesite=settings.SESSION_COOKIE_SAMESITE,
                    )
        return response
