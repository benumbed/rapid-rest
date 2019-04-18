from rapidrest.apiresource import ApiResource, ApiResponse

class BananaBlenderError(Exception): pass

class V1(ApiResource):
    endpoint_name = "v1"
    description = "Root endpoint"
    
    def get(self):
        """
        @brief      Example of a GET
        
        @param      self  The object
        
        @return     { description_of_the_return_value }
        """
        raise BananaBlenderError("whoopsie")

    def post(self):
        return ApiResponse(body=self._current_request.body, status_code=201)
