# -*- coding: utf-8 -*-
"""
Subclasses Flask's MethodView to provide some extra functionality (and enforce some things)

"""
from collections import namedtuple
from flask import current_app, request, Response, abort, make_response, jsonify
from flask.views import MethodView

from rapidrest.security import authentication

ApiResponse = namedtuple("ApiResponse", field_names=("body", "status_code", "headers"), defaults=({},))

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

        resp = super().dispatch_request(*args, **kwargs)

        if isinstance(resp, Response):
            return resp

        elif isinstance(resp, ApiResponse):
            body = jsonify(resp.body) if isinstance(resp.body, dict) else resp.body

            actual_resp:Response = make_response((body, resp.status_code))
            actual_resp.headers["Content-Type"] = "application/json"
            actual_resp.headers.extend(resp.headers)

            return actual_resp

        else:
            abort(500, "API resource did not return a known response type")
