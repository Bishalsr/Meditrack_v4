import logging

from allauth.socialaccount.adapter import DefaultSocialAccountAdapter


logger = logging.getLogger(__name__)


class MeditrackSocialAccountAdapter(DefaultSocialAccountAdapter):
    def on_authentication_error(
        self,
        request,
        provider,
        error=None,
        exception=None,
        extra_context=None,
    ):
        provider_id = getattr(provider, "id", "unknown")
        state_id = (extra_context or {}).get("state_id")
        logger.error(
            "Social auth error provider=%s error=%s state_id=%s exception=%r",
            provider_id,
            error,
            state_id,
            exception,
            exc_info=exception if exception else False,
        )
        return super().on_authentication_error(
            request,
            provider,
            error=error,
            exception=exception,
            extra_context=extra_context,
        )
