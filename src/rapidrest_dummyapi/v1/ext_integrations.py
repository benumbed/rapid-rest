# -*- coding: utf-8 -*-
"""
Example of a rapidrest integrations file
"""

# These keys will be 'expected' in the environment, and the application will not load without them
REQ_EXT_VARS = {"API_ROOT"}

INTEGRATION_MAP = {}

def initialize_ext_resources(cfg):
    """
    Initializes any external integrations needed by this resource

    :param cfg: The external integrations config
    """
    INTEGRATION_MAP["API_ROOT"] = cfg["API_ROOT"]
