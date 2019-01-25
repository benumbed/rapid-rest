# -*- coding: utf-8 -*-
"""
Example of a rapidrest integrations file
"""

# These keys will be 'expected' in the environment, and the application will not load without them
REQ_EXT_VARS = {"RAPIDREST_TEST"}
CONFIG_KEY = "v1_test_int"

def initialize_ext_resources(app):
    """
    @brief      Initializes any external integrations needed by this resource
    
    @return     bool - True on success, False otherwise
    """
    app.config[CONFIG_KEY] = {}
    
    return True