# -*- coding: utf-8 -*-
"""
Utilities used throughout the API server
"""

def check_required_args(required_args, provided_args, logger=None, log_msg=None):
    """
    @brief      Checks to see if the provided args have the required args in them
    
    @param      required_args  The required arguments
    @param      provided_args  The provided arguments
    @param      logger         The logger (optional)
    @param      log_msg        The log message (optional, expects to have one substitution for missing key names)
    
    @return     set - Empty set on success, missing args on failure
    """
    log_err = log_msg if log_msg is not None else "Missing required args: {}"
    if not isinstance(required_args, set):
        required_args = set(required_args)
    if not isinstance(provided_args, set):
        provided_args = set(provided_args)
    response = set()

    if not provided_args.issuperset(required_args):
        response = required_args.difference(provided_args)
        if logger is not None:
            logger.error(log_err.format(response))

    return response

        
def apply_needed_defaults(provided_args, defaults):
    """
    @brief      Applies defaults to the provided ags list (for keys which do not exist)
    
    @param      provided_args  The provided arguments
    @param      defaults       The defaults
    
    @return     dict
    """
    for default in defaults:
        if default in provided_args:
            continue
        provided_args[default] = defaults[default]

    return provided_args
