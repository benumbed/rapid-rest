from flask.views import MethodView

class BananaBlenderError(Exception): pass

class V1(MethodView):
    endpoint_name = "v1"
    description = "Root endpoint"
    
    def get(self):
        """
        @brief      Example of a GET
        
        @param      self  The object
        
        @return     { description_of_the_return_value }
        """
        raise BananaBlenderError("whoopsie")
        