from flask import jsonify, make_response

from rapidrest.apiresource import ApiResource

class Pants(ApiResource):
    endpoint_name = "pants"
    description = "Pants endpoint"

    def get(self, obj_id=""):
        """
        Example of a GET

        @param obj_id:

        @return     { description_of_the_return_value }
        """
        if obj_id:
            resp = make_response((jsonify({"pants_get": True, "id": obj_id}), 200))
        else:
            resp = make_response((jsonify({"pants_get": True}), 200))
        return resp
    

    def post(self):
        """

        """
        return make_response(jsonify({"pants_post": True}), 200)
