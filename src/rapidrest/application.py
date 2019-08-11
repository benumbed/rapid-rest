# -*- coding: utf-8 -*-
"""
Application layer for the Rapid-REST server.

"""
import flask
import importlib
import logging
import os
import yaml
from functools import partial
from logging.config import dictConfig

from rapidrest import utils, routebuilder, errorhandlers, integrations, vault_integration

def _init_logging(level:str="DEBUG", log_format:str="%(asctime)s - %(name)s - %(levelname)s - %(message)s"):
    """
    @brief      Initializes the logging
    """
    log_level = os.environ.get("LOGLEVEL", level).upper()

    dictConfig({
        'version': 1,
        'formatters': {'default': {
            'format': log_format,
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
    app.config["vault_fetcher"] = partial(vault_integration.load_vault, app)

    # Load the API before we load secrets, so we know what the API needs
    integration_modules = list()
    try:
        integration_modules = routebuilder.load_api(app, api_root)
    except routebuilder.RouteBuilderError as e:
        app.logger.error("Failed to load API: %s", e)
        exit(2)

    ints_loaded = integrations.initialize_api_integrations(
        integration_modules,
        app.config["api_config"],
        app.config["vault_fetcher"]()
    )
    if not ints_loaded:
        exit(4)

    return app
