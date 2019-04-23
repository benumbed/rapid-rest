# -*- coding: utf-8 -*-
"""
Application layer for the Rapid-REST server.

"""
import flask
import importlib
import logging
import os
import yaml
from logging.config import dictConfig

from rapidrest import utils, routebuilder, errorhandlers, integrations

def _init_logging(level:str="DEBUG", format:str="%(asctime)s - %(name)s - %(levelname)s - %(message)s"):
    """
    @brief      Initializes the logging
    """
    log_level = os.environ.get("LOGLEVEL", level)

    dictConfig({
        'version': 1,
        'formatters': {'default': {
            'format': format,
        }},
        'handlers': {'wsgi': {
            'class': 'logging.StreamHandler',
            'stream': 'ext://flask.logging.wsgi_errors_stream',
            'formatter': 'default'
        }},
        'root': {
            'level': log_level,
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
        # We don't (always) use hvac directly, vaultclient abstracts some stuff away and makes Vault a bit easier to use
        vaultclient = importlib.import_module("vaultclient")
    except ImportError:
        log.info("vaultclient package not available, disabling Vault support")
        return False

    vault_keys = {"VAULT_ROLE_ID", "VAULT_URL", "VAULT_WRAPPED_SECRET", "VAULT_SECRETS_MOUNT", "VAULT_SECRETS_PATH"}
    missing_vault_vars = utils.check_required_args(vault_keys, os.environ)

    # Login to Vault
    if not missing_vault_vars:
        log.info("Attempting to log into Vault at %s", os.environ["VAULT_URL"])
        try:
            app.config["vault"] = vaultclient.VaultClient(
                os.environ["VAULT_URL"],
                os.environ["VAULT_ROLE_ID"],
                os.environ["VAULT_WRAPPED_SECRET"]
            )
            app.config["vault"].login()
        except Exception as e:
            log.error(f"Failed to initialize Vault connection: {e}")
            return False

        if not app.config["vault"].logged_in:
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

    log.info("Successfully connected to Vault")
    return True


def load_secrets_from_vault(app) -> dict:
    """
    Loads the API's secrets from Vault

    :param app: The Flask app

    :return Dictionary of secrets on success, empty dict otherwise
    """
    log = app.logger
    vault = app.config["vault"]

    # If Vault is enabled, we will fetch the application's keys from Vault storage
    try:
        secrets = vault.get_secrets(os.environ["VAULT_SECRETS_PATH"], os.environ["VAULT_SECRETS_MOUNT"])
    except Exception as e:
        log.error("Could not load secrets from Vault: %s", e)
        return dict()

    log.info("Loaded secrets from Vault")
    return secrets


def load_api_config(api_py_root) -> dict:
    """
    Loads the API's 'api_config.yml' file

    @param api_py_root: The Python path to the API root (NOT the FS root, we'll infer that from the base of the API)

    @return: Parsed YAML
    """
    log = logging.getLogger("config_loader")
    try:
        api_resource = importlib.import_module(api_py_root)
    except ImportError:
        log.error(f"Failed to load 'api_config.yml' from {api_py_root}")
        return {}

    try:
        api_config_path = "{}/api_config.yml".format(api_resource.__path__[0])
    except TypeError:
        log.error("It looks like the API root is missing an __init__.py file")
        return {}
    
    if not os.path.exists(api_config_path):
        log.error(f"The config file '{api_config_path}' does not exist")
        return {}

    with open(api_config_path, "r") as cfg_file:
        try:
            api_cfg = yaml.load(cfg_file, Loader=yaml.FullLoader)
        except yaml.YAMLError as e:
            log.error(f"Failed to load config from '{api_config_path}': {e}")
            return {}

    return api_cfg


def start(*_):
    """
    @brief      Entry point for an external app server like Waitress or gunicorn
    
    @param      _     Ignored WSGI input
    
    @return     WSGI application
    """
    api_root = os.environ.get("API_ROOT", None)
    if os.environ.get("API_ROOT", None) is None:
        # We set the environment in this case for the tests
        api_root = os.environ["API_ROOT"] = "rapidrest_dummyapi.v1"
    api_cfg = load_api_config(api_root)
    if not api_cfg:
        exit(3)

    if not bool(os.environ.get("DISABLE_ROOT_LOGGER", False)):
        log_cfg = api_cfg["logging"] if "logging" in api_cfg else {}
        _init_logging(**log_cfg) # Install a root logger before Flask, or things get annoying

    app = flask.Flask(api_cfg["api_name"])
    app.logger.name = api_root
    errorhandlers.register_handlers(app)
    app.config["api_config"] = api_cfg
    app.config["vault"] = None

    # Load the API before we load secrets, so we know what the API needs
    integration_modules = list()
    try:
        integration_modules = routebuilder.load_api(app, api_root)
    except routebuilder.RouteBuilderError as e:
        app.logger.error("Failed to load API: %s", e)
        exit(2)

    vault_enabled = enable_vault(app) if "VAULT_URL" in os.environ else False
    require_vault = bool(os.environ.get("REQUIRE_VAULT", False))
    if require_vault and vault_enabled:
        if app.config["vault"] is not None:
            app.config["vault"].stop_refresh_process()
        app.logger.error("Vault support was required, but enabling Vault failed, exiting")
        exit(1)

    app.config["api_config"]["secrets"] = dict()
    try:
        if vault_enabled:
            app.config["api_config"]["secrets"] = load_secrets_from_vault(app)

        integrations.initialize_api_integrations(integration_modules, app.config["api_config"], app.config["vault"])
    except Exception:
        if app.config["vault"] is not None:
            app.config["vault"].stop_refresh_process()
        raise

    return app
