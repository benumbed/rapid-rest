# -*- coding: utf-8 -*-
"""
Subclasses Flask's MethodView to provide some extra functionality (and enforce some things)

"""
import json
from collections import namedtuple
from flask import current_app, request, Response, abort, make_response, jsonify
from flask.views import MethodView

from rapidrest.security import authentication

ApiResponse = namedtuple("ApiResponse", field_names=("headers","links", "data", "status_code", "headers"),
                         defaults=({"Content-Type": "application/vnd.api+json"},))
ApiRequest = namedtuple("ApiRequest", field_names=("headers", "body", "flask_request"))

class JSONAPIResponse(Response):
    """
    Specifies a proper JSON:API v1 response
    """
    def __init__(self, response=None, links=None, data=None, errors=None, meta=None, included=None, jsonapi=None, status=None, headers=None):
        """

        :param response:
        :param links:
        :param data:
        :param errors:
        :param meta:
        :param included:
        :param jsonapi:
        :param status:
        :param headers:
        """
        # Coercion in the case that non-JSON:API compliant data is sent in
        if response is not None:
            actual_response = {
                "data": response
            }
        else:
            self._make_jsonapi_response(links, data, errors, meta, included, jsonapi)
            actual_response = {}

        super().__init__(response=json.dumps(actual_response), status=status, headers=headers,
                         content_type="application/vnd.api+json")


    def _make_jsonapi_response(self, **kwargs):
        """

        :return:
        """
        if "data" not in kwargs and "errors" not in kwargs and "meta" not in kwargs:
            ret_dict = {
                "errors": [{
                    "title": "Invalid response configuration",
                    "detail": "JSON:API response must provide at least one of 'data', 'errors' or 'meta'",
                    "status": 500
                }]
            }
        elif "data" in kwargs and "errors" in kwargs:
            ret_dict = {
                "errors": [{
                    "title": "Invalid response configuration",
                    "detail": "JSON:API response must not provide both 'data' and 'errors'",
                    "status": 500
                }]
            }
        else:
            keys = ("links","data","errors","meta","included","jsonapi")
            ret_dict = {key: kwargs[key] for key in keys if not None}

        return ret_dict


class JSONAPIResource_v1(MethodView):
    """
    Provides a JSON:API v1 compliant resource

    """

    def __init__(self, *args, **kwargs):
        self._current_request = None
        self._vault = None
        self._api_config = None

        super().__init__(*args, **kwargs)


    def dispatch_request(self, *args, **kwargs) -> Response:
        """
        Request dispatcher for MethodView

        :param args: Passthrough
        :param kwargs: Passthrough

        :return: Flask response object
        """
        # Tie in authentication and authorization
        if not authentication.authenticate_endpoint(current_app, request):
            abort(403, "Authentication Failed")

        self._current_request = ApiRequest(body=request.get_json(), headers=request.headers, flask_request=request)
        self._vault = current_app.config["vault"] if "vault" in current_app.config else None
        self._api_config = current_app.config["api_config"]

        resp = super().dispatch_request(*args, **kwargs)

        response_template = {
            "links": {

            },
            "data": []
        }


        if isinstance(resp, Response):
            return resp

        elif isinstance(resp, ApiResponse):
            body = jsonify(resp.body) if isinstance(resp.body, dict) else resp.body

            actual_resp:Response = make_response((body, resp.status_code))
            actual_resp.headers["Content-Type"] = "application/json"
            actual_resp.headers.extend(resp.headers)

            return actual_resp

        abort(500, "API resource did not return a known response type")
