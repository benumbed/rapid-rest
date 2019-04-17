# -*- coding: utf-8 -*-
"""
Authentication layer for the Rapid-REST server.

The authentication for RapidREST is based off Amazon's Signature v4. We, however, use Vault for a majority of the 
server operations.  This ensures that services do not need to know the users' encryption key.

"""
import base64
import flask
import hashlib
import hmac
import sys

from rapidrest.utils import check_required_args

VALID_AUTH_VERSIONS = ["v1"]
DEFAULT_AUTH_VERSION = "v1"

def create_hmac_signature(key:bytes, data_to_sign:str, hashmech:hashlib=hashlib.sha256) -> str:
    """
    Creates an HMAC signature for the provided data string

    @param key: HMAC key as bytes
    @param data_to_sign: The data that needs to be signed
    @param hashmech: The hashing mechanism to use, defaults to sha256

    @return: Base64 encoded signature
    """
    sig = hmac.new(key, data_to_sign.encode("utf-8"), hashmech).digest()

    return base64.b64encode(sig).decode("utf-8")


def create_v1_auth_header(principal_name:str, principal_key:bytes, method:str, host:str, url:str, body:str="") -> str:
    """
    Creates a v1 auth header

    :return: The v1 auth header
    """
    sig_elements = [method, host, url, base64.encodebytes(body.encode("utf-8")).decode("utf-8")]

    sig = create_hmac_signature(principal_key, "\n".join(sig_elements))
    return f"Version:v1;Hash:sha265;Principal:{principal_name};Signature:{sig}"


def _get_endpoint_sec_cfg(app:flask.app, url_rule:str, method:str) -> dict or None:
    """
    Gets the endpoint's security config

    @param app: The Flask application
    @param url_rule: The url rule that was invoked
    @param method: The HTTP method in use

    @return: The security config for the endpoint, else None
    """
    sec_cfg = app.config["api_config"]["security"]

    prelim_cfg = sec_cfg["endpoint_control"][url_rule] if ("endpoint_control" in sec_cfg and
                                                      url_rule in sec_cfg["endpoint_control"]) else {}

    return prelim_cfg[method] if method in prelim_cfg else None


def _v1_authn_mechanism(app:flask.app, request:flask.Request, auth_dict:dict) -> bool:
    """
    Represents what is classified as the official v1 authentication mechanism
    Authorization: Version:v1;Hash:sha265;Principal:<principal name>;Signature:<sig>

    @return: True if authenticated, False otherwise
    """
    if "vault" not in app.config:
        flask.abort(500, "Authentication requires Vault, which is not enabled")
    vault = app.config["vault"]

    required_auth_keys = ("Version", "Hash", "Principal", "Signature")

    missing_keys = check_required_args(required_auth_keys, auth_dict)
    if missing_keys:
        flask.abort(403, f"Invalid Authentication header, missing required keys: {missing_keys}")

    # Assemble the signed elements into request string
    # NOTE: Werkzeug will return a ? at the end of full_path regardless of whether there's a query string or not, so it
    # has to be stripped, as we can't expect users to remember to add a ? on the end of all their paths they sign
    path = request.full_path.rstrip("?") if request.full_path.endswith("?") else request.full_path
    sig_elements = [request.method, request.headers["Host"], path,
                    base64.encodebytes(request.data).decode("utf-8")]

    return vault.verify_hmac_signature(auth_dict["Principal"], "\n".join(sig_elements), auth_dict["Signature"])


def authenticate_endpoint(app:flask.app, request:flask.request) -> bool:
    """
    @brief      Should be run by the dispatch_request hook.  Note that this will abort if auth fails.

    @param app: The Flask application
    @param request: The current request
    """
    # TODO: Whitelisting being disabled implies blacklisting, which is not currently implemented, instead turning off
    # whitelisting just turns off auth entirely
    if not app.config["api_config"]["security"]["whitelist"]:
        return True

    sec_cfg = _get_endpoint_sec_cfg(app, str(request.url_rule), request.method)
    if sec_cfg is None:
        flask.abort(403, "This endpoint has no security configuration and whitelisting is enabled")
    # Auth is disabled for this endpoint
    elif not sec_cfg["authentication"]:
        return True

    # Check for auth header
    if "Authorization" not in request.headers:
        flask.abort(403, "Authorization header is missing")

    auth_dict = {}
    for token in request.headers["Authorization"].split(";"):
        try:
            key, value = token.split(":")
        except ValueError:
            continue
        auth_dict[key] = value

    auth_ver = DEFAULT_AUTH_VERSION
    if "Version" in auth_dict:
        if auth_dict["Version"] not in VALID_AUTH_VERSIONS:
            flask.abort(403, f"Invalid auth version. Valid versions are: {VALID_AUTH_VERSIONS}")
        auth_ver = auth_dict["Version"]
    else:
        flask.abort(403, "Authorization header does not include Version")

    auth_method = f"_{auth_ver}_authn_mechanism"

    auth_method = getattr(sys.modules[__name__], auth_method, None)
    if auth_method is None:
        flask.abort(400, f"There is no {auth_ver} authentication mechanism")

    return auth_method(app, request, auth_dict)

