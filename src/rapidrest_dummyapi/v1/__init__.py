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
        """
        This is used to test objects that are auto-attached to the resource instance
        :return:
        """
        return ApiResponse(
            body={
                "body": self._current_request.body,
                "vault": str(self._vault),
                "api_config": self._api_config,
            },
            status_code=201
        )
