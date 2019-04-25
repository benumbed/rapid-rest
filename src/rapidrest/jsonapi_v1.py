# -*- coding: utf-8 -*-
"""
Subclasses Flask's MethodView to provide some extra functionality (and enforce some things)

"""
import json
from flask import Response


class JSONAPIResponse(Response):
    """
    Specifies a proper JSON:API v1 response
    """
    def __init__(self, response=None, links=None, data=None, errors=None, meta=None, included=None, jsonapi=None,
                 status=None, headers=None):
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
            self._make_jsonapi_response(links=links, data=data, errors=errors, meta=meta, included=included,
                                        jsonapi=jsonapi)
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
