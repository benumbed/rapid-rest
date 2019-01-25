from flask import jsonify, make_response
from flask.views import MethodView

class Pants(MethodView):
    endpoint_name = "pants"
    _description = "Pants endpoint"
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

    
    def get(self, id=None):
        """
        @brief      Example of a GET
        
        @param      self  The object
        
        @return     { description_of_the_return_value }
        """
        make_response((jsonify({"example": True}), 200, {"Content-Type": "application/json"}))
        