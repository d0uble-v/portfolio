'''
Custom Django middleware built for the project. Used together with the
GetActingUserMixin from the `model-mixins.py` file.
'''


from django.utils.deprecation import MiddlewareMixin
from consultmed.models.mixins import GetActingUserMixin


class ActingUserTrackingMiddleware(MiddlewareMixin):
    '''
    This middleware sets the request object as a local thread variable, 
    making it available to the model-level utilities and thus allowing
    to track the user performing a CRUD operation.
    '''

    def process_request(self, request):
        for model in GetActingUserMixin.__subclasses__():
            model.thread.request = request

    def process_response(self, request, response):
        for model in GetActingUserMixin.__subclasses__():
            if hasattr(model.thread, 'request'):
                del model.thread.request

        return response
