# -*- coding: utf-8 -*-
"""
Subclasses Flask's MethodView to provide some extra functionality (and enforce some things)

"""
from collections import namedtuple
from flask import current_app, request, Response, abort, make_response, jsonify
from flask.views import MethodView

from rapidrest.security import authentication

ApiResponse = namedtuple("ApiResponse", field_names=("body", "status_code", "headers"), defaults=({},))
ApiRequest = namedtuple("ApiRequest", field_names=("headers", "body", "flask_request"))

class ApiResource(MethodView):
    """
    @brief      Class for api resource.
    """

    def __init__(self, *args, **kwargs):
        self._current_request = None
        self._vault = None
        self._api_config = None

        super().__init__(*args, **kwargs)


    def dispatch_request(self, *args, **kwargs):
        """
        @brief      Request dispatcher

        @param      args    The arguments
        @param      kwargs  The kwargs

        @return     { description_of_the_return_value }
        """
        # Tie in authentication and authorization
        if not authentication.authenticate_endpoint(current_app, request):
            abort(403, "Authentication Failed")

        self._current_request = ApiRequest(body=request.get_json(), headers=request.headers, flask_request=request)
        self._vault = current_app.config["vault_fetcher"]()
        self._api_config = current_app.config["api_config"]

        resp = super().dispatch_request(*args, **kwargs)

        if isinstance(resp, Response):
            return resp

        elif isinstance(resp, ApiResponse):
            body = jsonify(resp.body) if isinstance(resp.body, dict) else resp.body

            actual_resp:Response = make_response((body, resp.status_code))
            actual_resp.headers["Content-Type"] = "application/json"
            actual_resp.headers.extend(resp.headers)

            return actual_resp

        abort(500, "API resource did not return a known response type")
