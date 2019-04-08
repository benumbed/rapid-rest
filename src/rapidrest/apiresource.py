# -*- coding: utf-8 -*-
"""
Subclasses Flask's MethodView to provide some extra functionality (and enforce some things)

"""
from flask import current_app, request
from flask.views import MethodView

from rapidrest.security import authentication

class ApiResource(MethodView):
    """
    @brief      Class for api resource.
    """
    restrictions = {}

    def dispatch_request(self, *args, **kwargs):
        """
        @brief      Request dispatcher

        @param      args    The arguments
        @param      kwargs  The kwargs

        @return     { description_of_the_return_value }
        """
        # Tie in authentication and authorization
        authentication.authenticate_endpoint(current_app, request)

        return super().dispatch_request(*args, **kwargs)
