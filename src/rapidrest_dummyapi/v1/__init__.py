from flask import jsonify, make_response
from flask.views import MethodView

class V1(MethodView):
    endpoint_name = "v1"
    _description = "Root endpoint"
    _parameter_definitions = {
        "name": {
            "description": "The 'nice' name of the job",
            "arg_type": "str",
            "required": True,
            "default": None,
        },
    }

    
    @property
    def parameters(self):
        return self._parameter_definitions

    
    def get(self):
        """
        @brief      Example of a GET
        
        @param      self  The object
        
        @return     { description_of_the_return_value }
        """
        make_response((jsonify({"example": True}), 200, {"Content-Type": "application/json"}))
        