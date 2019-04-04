# -*- coding: utf-8 -*-
"""
Application layer for the Rapid-REST server.

"""
import flask
import importlib
import os
from logging.config import dictConfig

from rapidrest import utils, routebuilder, errorhandlers

# TODO: This needs to be configurable
def _init_logging():
    """
    @brief      Initializes the logging
    """
    dictConfig({
        'version': 1,
        'formatters': {'default': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        }},
        'handlers': {'wsgi': {
            'class': 'logging.StreamHandler',
            'stream': 'ext://flask.logging.wsgi_errors_stream',
            'formatter': 'default'
        }},
        'root': {
            'level': "DEBUG",
            'handlers': ['wsgi']
        }
    })


def enable_vault(app):
    """
    @brief      Enables access to Hashicorp's Vault.  Vault support currently only works with approle, and the secret-id
                must be wrapped.  The only supported secrets engine is currently KV v2 (since the VaultClient library
                currently only supports KV v2).
    
    @param      app       The Flask application
    
    @return     bool - True on success, False otherwise
    """
    log = app.logger

    try:
        # We don't use hvac directly, vaultclient abstracts some stuff away and makes Vault a bit easier to use
        vaultclient = importlib.import_module("vaultclient")
    except ImportError:
        log.info("vaultclient package not available, disabling Vault support")
        return False

    vault_keys = {"VAULT_ROLE_ID", "VAULT_URL", "VAULT_WRAPPED_SECRET", "VAULT_SECRETS_MOUNT", "VAULT_SECRETS_PATH"}

    missing_vault_vars = utils.check_required_args(vault_keys, os.environ)

    # Login to Vault
    if not missing_vault_vars:
        app.config["vault"] = vaultclient.VaultClient(
            os.environ["VAULT_URL"], 
            os.environ["VAULT_ROLE_ID"], 
            os.environ["VAULT_WRAPPED_SECRET"]
        )
        if not app.config["vault"].login():
            log.error("Vault login failed")
            return False

        log.info("Vault integration enabled, will load secrets from Vault (%s) at '%s/%s'", 
            os.environ["VAULT_URL"], 
            os.environ["VAULT_SECRETS_MOUNT"],
            os.environ["VAULT_SECRETS_PATH"],
        )

    else:
        log.error(f"Vault connection failed, missing environment variables: {missing_vault_vars}")
        return False

    vault = app.config["vault"]
    # If Vault is enabled, we will fetch the application's keys from Vault storage
    try:
        app.config["secrets"] = vault.get_secrets(os.environ["VAULT_SECRETS_PATH"], os.environ["VAULT_SECRETS_MOUNT"])
    except vaultclient.VaultClientError as e:
        log.error("Could not load secrets from Vault: %s", e)
        return False

    log.info("Loaded secrets from Vault")
    return True


def start(*_):
    """
    @brief      Entry point for an external app server like Waitress or gunicorn
    
    @param      _     Ignored WSGI input
    
    @return     WSGI application
    """
    if not bool(os.environ.get("RAPIDREST_DISABLE_ROOT_LOGGER", False)):
        _init_logging() # Install a root logger before Flask, or things get annoying

    app_name = os.environ.get("RAPIDREST_APP_NAME", "rapidrest.application")
    app = flask.Flask(app_name)
    app.logger.name = app_name
    errorhandlers.register_handlers(app)

    # Load the API before we load secrets, so we know what the API needs
    api_root = os.environ.get("RAPIDREST_API_ROOT", "rapidrest_dummyapi.v1")
    try:
        routebuilder.load_api(app, api_root)
    except routebuilder.RouteBuilderError as e:
        app.logger.error("Failed to load API: %s", e)
        exit(2)

    require_vault = bool(os.environ.get("RAPIDREST_REQUIRE_VAULT", False))
    if require_vault and not enable_vault(app):
        app.logger.error("Vault support was required, but enabling Vault failed, exiting")
        exit(1)


    return app
    