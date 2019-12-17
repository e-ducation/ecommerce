"""
Middleware for analytics app to parse GA cookie.
"""
import pytz
import datetime
from ipware.ip import get_ip
from ecommerce.extensions.analytics.utils import get_google_analytics_client_id


class TrackingMiddleware(object):
    """
    Middleware that parse `_ga` cookie and save/update in user tracking context.
    """

    def process_request(self, request):
        user = request.user
        if user.is_authenticated():
            tracking_context = user.tracking_context or {}
            old_client_id = tracking_context.get('ga_client_id')
            ga_client_id = get_google_analytics_client_id(request)

            if ga_client_id and ga_client_id != old_client_id:
                tracking_context['ga_client_id'] = ga_client_id
                user.tracking_context = tracking_context
                user.save()

        post_dict = dict(request.POST)
        get_dict = dict(request.GET)
        censored_strings = ['password', 'newpassword', 'new_password', 'oldpassword', 'old_password', 'new_password1', 'new_password2']
        for string in censored_strings:
            if string in post_dict:
                post_dict[string] = '*' * 8
            if string in get_dict:
                get_dict[string] = '*' * 8
        event = {
            'GET': dict(get_dict),
            'POST': dict(post_dict),
        }

        self.server_track(request, request.META['PATH_INFO'], event)

    def server_track(self, request, event_type, event, page=None):
        """
            Log events related to server requests.
            Handle the situation where the request may be NULL, as may happen with management commands.
        """
        if event_type.startswith("/event_logs") and request.user.is_staff:
            return  # don't log
        try:
            username = request.user.username
        except:
            username = "anonymous"
        from eventtracking import tracker
        # define output:
        event = {
            "username": username,
            "ip": self._get_request_ip(request),
            "referer": self._get_request_header(request, 'HTTP_REFERER'),
            "accept_language": self._get_request_header(request, 'HTTP_ACCEPT_LANGUAGE'),
            "event_source": "server",
            "event_type": event_type,
            "event": event,
            "agent": self._get_request_header(request, 'HTTP_USER_AGENT').decode('latin1'),
            "page": page,
            "time": datetime.datetime.utcnow().replace(tzinfo=pytz.utc),
            "host": self._get_request_header(request, 'SERVER_NAME'),
            "context": tracker.get_tracker().resolve_context(),
            'nickname': self.get_user_nickname(request),
            'phone': self.get_user_phone(request),
            'user_id': self.get_user_primary_key(request),
            'port' : request.META['SERVER_PORT'] if request.META['SERVER_PORT'] else '',
        }
        with tracker.get_tracker().context('edx.course.ecommerce.info', event):
            tracker.emit(name='edx.course.ecommerce.info', data=event)    

    def _get_request_ip(self, request, default=''):
        """Helper method to get IP from a request's META dict, if present."""
        if request is not None and hasattr(request, 'META'):
            return get_ip(request)
        else:
            return default

    def _get_request_header(self, request, header_name, default=''):
        """Helper method to get header values from a request's META dict, if present."""
        if request is not None and hasattr(request, 'META') and header_name in request.META:
            return request.META[header_name]
        else:
            return default

    def get_user_primary_key(self, request):
        """Gets the primary key of the logged in Django user"""
        try:
            return request.user.pk
        except AttributeError:
            return ''

    def get_user_nickname(self, request):
        """Gets the user nickname of the logged in Django user"""
        try:
            return request.user.profile.name
        except AttributeError:
            return ''

    def get_user_phone(self, request):
        """Gets the user phone of the logged in Django user"""
        try:
            phone = request.user.profile.phone
            return phone if phone is not None else ''
        except AttributeError:
            return ''
    