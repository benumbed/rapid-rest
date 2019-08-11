# -*- coding: utf-8 -*-
"""
Utilities to manage the integrations that an API requires to function

"""
import logging
import os

from rapidrest.exceptions import IntegrationLoadError
from vaultclient import VaultClient

log = logging.getLogger(__name__)

def integrations_required_keys(modules:list) -> set:
    """
    Gets the variables that the external integrations need to function

    :param modules: Integration initialization modules

    :return: The keys required to initialize all the integrations for this API
    """
    req_keys = set()
    for module in modules:
        keys = getattr(module, "REQ_EXT_VARS", None)
        if keys is None:
            continue
        req_keys.update(keys)

    return req_keys


def initialize_api_integrations(modules:list, api_config:dict, vault:VaultClient):
    """
    Initializes all the API integrations

    :param modules: The list of modules to process
    :param api_config: The API configuration dictionary
    :param vault: The initialized Vault client
    """
    int_cfg = _get_req_key_values(integrations_required_keys(modules), api_config, vault)
    try:
        for module in modules:
            _init_integration(module, int_cfg)
    except Exception:
        return False

    return True


def _get_req_key_values(req_keys:set, api_config:dict, vault:VaultClient) -> dict:
    """
    Gets the values for required keys

    :param req_keys: The set of required keys
    :param api_config: The API configuration dictionary
    :param vault: The initialized Vault client

    :return: Mapping of key/values
    """
    # Order of precedence goes --> thataway
    search_objs = (api_config, api_config["secrets"], os.environ)

    # Wasteful? Yeah, kinda, but most likely as fast as something with continue, and less code
    req_map = {key: obj[key] for key in req_keys for obj in search_objs if key in obj}
    # Special case for Vault
    if "VAULT" in req_keys:
        req_map["VAULT"] = vault
    missing_keys = req_keys.difference(req_map)
    if missing_keys:
        raise IntegrationLoadError(f"Could not load the required keys for API external integrations: {missing_keys}")

    return req_map


def _init_integration(module, cfg:dict):
    """
    Loads integrations.

    :param module: The init module to work with
    """
    path = module.__name__
    root_path = path.split(".")[:-2]

    integration_boot = getattr(module, "initialize_ext_resources", None)
    if integration_boot is None:
        raise IntegrationLoadError(
            f"ext_integrations.py in {root_path} is missing required 'initialize_ext_resources' method")

    log.debug(f"Running bootstrap for integrations in {root_path}")
    try:
        integration_boot(cfg)
    except Exception as e:
        log.error(f"Failed to run integration bootstrap for {path}: {e}")
        raise IntegrationLoadError(f"Failed to run integration bootstrap for {path}: {e}")
