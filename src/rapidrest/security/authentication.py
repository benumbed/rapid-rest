# -*- coding: utf-8 -*-
"""
Authentication layer for the Rapid-REST server.

The authentication for RapidREST is based off Amazon's Signature v4. We, however, use Vault for a majority of the 
server operations.  This ensures that services do not need to know the users' encryption key.

"""
import base64
import sys
import flask

VALID_AUTH_VERSIONS = ["1"]
DEFAULT_AUTH_VERSION = 1

def _get_endpoint_sec_cfg(app:flask.app, url_rule:str):
    """
    Gets the endpoint's security config

    @param app: The Flask application
    @param url_rule: The url rule that was invoked
    @return:
    """
    sec_cfg = app.config["api_config"]["security"]


    return sec_cfg["endpoint_control"][url_rule] if ("endpoint_control" in sec_cfg and
                                                      url_rule in sec_cfg["endpoint_control"]) else None


def _v1_authn_mechanism(app:flask.app, request:flask.Request, auth_dict:dict):
    """
    Represents what is classified as the official v1 authentication mechanism


    @return: N
    """
    if "vault" not in app.config:
        flask.abort(500, "Authentication requires Vault, which is not enabled")
    vault = app.config["vault"]

    # Assemble the signed elements into request string
    # HTTP Method + Host + Date + resource (URI) + base64-encoded body
    sig_elements = [request.method, request.headers["Host"], request.url,
                    base64.encodebytes(request.data).decode("utf-8")]

    sig_string = "\n".join(sig_elements)

    # vault.verify_hmac_signature()


def authenticate_endpoint(app:flask.app, request:flask.request):
    """
    @brief      Should be run by the dispatch_request hook.  Note that this will abort if auth fails.

    @param app: The Flask application
    @param request: The current request
    """
    sec_cfg = _get_endpoint_sec_cfg(app, str(request.url_rule))
    if sec_cfg is None and app.config["api_config"]["security"]["whitelist"]:
        flask.abort(403, "This endpoint has no security configuration and whitelisting is enabled")

    # Check for auth header
    if "Authorization" not in request.headers:
        flask.abort(403, "Authorization header is missing")

    auth_dict = {}
    for token in request.headers["Authorization"].split(";"):
        try:
            key, value = token.split("=")
        except ValueError:
            continue
        auth_dict[key] = value

    auth_ver = DEFAULT_AUTH_VERSION
    if "version" in auth_dict:
        if auth_dict["version"] not in VALID_AUTH_VERSIONS:
            flask.abort(400, f"Invalid auth version. Valid versions are: {VALID_AUTH_VERSIONS}")
        auth_ver = auth_dict["version"]

    auth_method = f"_v{auth_ver}_authn_mechanism"

    auth_method = getattr(sys.modules[__name__], auth_method, None)
    if auth_method is None:
        flask.abort(500, f"The v{auth_ver} authentication mechanism is not implemented")

    auth_method(app, request, auth_dict)

