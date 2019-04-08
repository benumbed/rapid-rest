# -*- coding: utf-8 -*-
"""
Basic error handlers

"""
from flask import jsonify, make_response
from werkzeug.exceptions import HTTPException

def register_handlers(app):
    """
    @brief      Registers the default error handlers for RapidRest
    
    @param      codes  The codes
    
    @return     flask.Response
    """
    app.register_error_handler(HTTPException, _handle_http_errors)
    app.register_error_handler(Exception, _handle_unregistered)

def _handle_http_errors(err):
    """
    @brief      Handles known HTTP exceptions
    
    @param      err   The error
    
    @return     flask.Response
    """
    code_to_type_map = {
        "4": "Client",
        "5": "Server",
        "Unknown": "Unknown",
    }

    resp = {
        "err": True,
        "err_type": code_to_type_map.get(str(err.code)[0], "Unknown"),
        "err_detail": str(err)
    }

    return make_response(jsonify(resp), err.code)


def _handle_unregistered(err):
    """
    @brief      Handles all non-registered exceptions (traps Exception)
    
    @param      err   The error
    
    @return     flask.Response
    """
    resp = {
        "err": True,
        "err_type": f"Unknown:{err.__class__.__name__}",
        "err_detail": str(err)
    }

    return make_response(jsonify(resp), 500)
