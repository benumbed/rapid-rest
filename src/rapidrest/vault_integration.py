# -*- coding: utf-8 -*-
"""
Provides Vault integration functionality for RapidRest

"""
import importlib
import logging
import os

from rapidrest import utils

_LOGGER = logging.getLogger("vault_integration")

def load_vault(app):
    """

    :return:
    """
    if "_vault" in app.config and app.config["_vault"] is not None:
        return app.config["_vault"]

    if "VAULT_URL" in os.environ and os.environ["VAULT_URL"] != "":
        app.config["_vault"] = enable_vault()
        app.config["api_config"]["secrets"] = load_secrets_from_vault()

    return app.config["_vault"]


def enable_vault():
    """
    @brief      Enables access to Hashicorp's Vault.  Vault support currently only works with approle, and the secret-id
                must be wrapped.  The only supported secrets engine is currently KV v2 (since the VaultClient library
                currently only supports KV v2).

    @return     vaultclient.VaultClient or None on failure
    """
    try:
        # We don't (always) use hvac directly, vaultclient abstracts some stuff away and makes Vault a bit easier to use
        vaultclient = importlib.import_module("vaultclient")
    except ImportError:
        _LOGGER.info("vaultclient package not available, disabling Vault support")
        return False

    vault_keys = {"VAULT_ROLE_ID", "VAULT_URL", "VAULT_WRAPPED_SECRET", "VAULT_SECRETS_MOUNT", "VAULT_SECRETS_PATH"}
    missing_vault_vars = utils.check_required_args(vault_keys, os.environ)

    if missing_vault_vars:
        _LOGGER.error(f"Vault connection failed, missing environment variables: {missing_vault_vars}")
        return None

    # Login to Vault
    _LOGGER.info("Attempting to log into Vault at %s", os.environ["VAULT_URL"])
    try:
        vc = vaultclient.VaultClient(
            os.environ["VAULT_URL"],
            os.environ["VAULT_ROLE_ID"],
            os.environ["VAULT_WRAPPED_SECRET"]
        )
        vc.login()
    except Exception as e:
        _LOGGER.error(f"Failed to initialize Vault connection: {e}")
        return None

    if not vc.logged_in:
        _LOGGER.error("Vault login failed")
        return None

    _LOGGER.info("Vault integration enabled, will load secrets from Vault (%s) at '%s/%s'",
             os.environ["VAULT_URL"],
             os.environ["VAULT_SECRETS_MOUNT"],
             os.environ["VAULT_SECRETS_PATH"],
             )

    _LOGGER.info("Successfully connected to Vault")
    return vc


def load_secrets_from_vault() -> dict:
    """
    Loads the API's secrets from Vault

    :return Dictionary of secrets on success, empty dict otherwise
    """

    # If Vault is enabled, we will fetch the application's keys from Vault storage
    try:
        secrets = _VAULT_CLIENT.get_secrets(os.environ["VAULT_SECRETS_PATH"], os.environ["VAULT_SECRETS_MOUNT"])
    except Exception as e:
        _LOGGER.error("Could not load secrets from Vault: %s", e)
        return dict()

    _LOGGER.info("Loaded secrets from Vault")
    return secrets
