# -*- coding: utf-8 -*-
"""
Application layer for the Rapid-REST server
"""
import flask
import importlib
import pkgutil

def load_api(app, api_root_path):
    """
    @brief      Loads an api.
    
    @param      app            The application
    @param      api_root_path  The Python path to the API root package
    
    @return     { description_of_the_return_value }
    """
    log = app.logger

    try:
        api_root = importlib.import_module(api_root_path)
    except ImportError:
        log.error("Failed to load the API at '%s'", api_root_path)
        return False
    else:
        log.debug("Found API resource at '%s', attempting to load it", api_root_path)

    # Now we do some magic to traverse the package and find all the resources we need to load
    for module in pkgutil.walk_packages(api_root.__path__):
        # If the 'module' is actually a package, we need to recurse to handle it
        if module.ispkg:
            load_api(app, f"{api_root_path}.{module.name}")
        
        # Load any base requirements from this resource

        # Create url rule(s)