from flask import jsonify, make_response

from rapidrest.apiresource import ApiResource, ApiResponse


class Recursive(ApiResource):
    endpoint_name = "recursive"
    description = "Recursive endpoint"

    def get(self, obj_id=""):
        """
        Example of a GET

        @param obj_id:

        @return     { description_of_the_return_value }
        """
        if obj_id:
            resp = make_response((jsonify({"recursive_get": True, "id": obj_id}), 200))
        else:
            resp = make_response((jsonify({"recursive_get": True}), 200))
        return resp

    def post(self):
        """

        """
        return ApiResponse(body={"recursive_post": True}, status_code=200)
