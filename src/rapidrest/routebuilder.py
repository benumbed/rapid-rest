# -*- coding: utf-8 -*-
"""
Application layer for the Rapid-REST server
"""
import importlib
import inspect
import pkgutil


class RouteBuilderError(Exception): pass
class IntegrationBootError(RouteBuilderError): pass


def _load_integrations(app, module, api_path, module_py_path, log):
    """
    @brief      Loads integrations.

    """
    integration_boot = getattr(module, "initialize_ext_resources", None)
    if integration_boot is None:
        raise IntegrationBootError(
            f"ext_integrations.py in {api_path} is missing required 'initialize_ext_resources' method")

    log.debug(f"Running bootstrap for integrations in {api_path}")
    if not integration_boot(app):
        raise IntegrationBootError(f"Failed to run integration bootstrap for {module_py_path}")


def _add_url_rule(app, url, view, log, method_map=None):
    """
    Adds an url rule.
    
    @param app:                 The application
    @param url:                 The url
    @param view:                The view method
    @param log:                 The logger
    @param method_map:          Maps methods to their _id parameters
    """
    app.add_url_rule(
        url,
        view_func=view,
        provide_automatic_options=True,
        methods=method_map["non-id"]
    )
    log.debug(f"Added endpoint {url}")

    for method, id_param in method_map["id"].items():
        rule = f"{url}/<{id_param}>"
        app.add_url_rule(
            rule,
            view_func=view,
            methods=[method]
        )
        log.debug(f"Added 'id' endpoint '{rule}'")


def _gather_restrictions(app, ep_class, log):
    """
    @brief      Gathers an endpoint's restrictions
    
    @return     { description_of_the_return_value }
    """
    pass

def _resource_initializer(app, root, module, log):
    """
    @brief      This loads a resource class that was discovered by `load_api`
    
    @param      app     The application
    @param      root    The api path
    @param      module  The module
    @param      log     The log
    """
    module_name = module.__name__.split(".")[-1]
    module_py_path = f"{root}.{module_name}" if root else f"{module_name}"
    url = "/{}".format("/".join(module_py_path.split(".")))

    # Make sure the class we expect is there
    res_class_name = module_name.capitalize()
    resource_class = getattr(module, res_class_name, None)
    if resource_class is None:
        log.warning(f"{module_py_path} does not have the expected class '{res_class_name}', skipping")
        return
    elif getattr(resource_class, "as_view", None) is None:
        log.warning(f"{module_py_path}.{res_class_name} does not inherit from flask.views.MethodView, skipping")
        return

    # Create url rule(s)
    view = resource_class.as_view(resource_class.endpoint_name)

    # Make sure that methods that need 'id'-type rules get them
    method_map = { "non-id": [], "id": {} }
    for method in view.view_class.methods:
        meth_sig = inspect.signature(getattr(view.view_class, method.lower()))

        id_params = [param_obj for param_obj in meth_sig.parameters.values() if param_obj.name.endswith("_id")]
        if id_params:
            method_map["id"][method] = id_params[0].name

        if id_params and id_params[0].default == inspect.Parameter.empty:
            pass
        else:
            method_map["non-id"].append(method)

        # Some methods have to have an ID for them to function
        if method in {"PUT", "DELETE", "PATCH"} and method not in method_map["id"]:
            raise RouteBuilderError(str(f"Method '{method}' in {module_py_path} is required to have an '_id'-style "
                                    "parameter"))

    log.debug(f"Adding view for {url}")
    _add_url_rule(app, url, view, log, method_map=method_map)




def load_api(app, api_path, _root=""):
    """
    @brief      Loads an api.
    
    @param      app       The application
    @param      api_path  The Python path to the API package
    @param      _root     Used for recursion, do not set this
    """
    log = app.logger

    try:
        api_resource = importlib.import_module(api_path)
    except ImportError:
        raise RouteBuilderError(f"Failed to load the API at '{api_path}'")

    log.debug(f"Found API resource at '{api_path}', attempting to load it")

    base_resource_name = api_resource.__name__.split(".")[-1]
    sub_resource_root = f"{_root}.{base_resource_name}" if _root else base_resource_name

    # This should only run at the very beginning, probably a better way to do this but I'm braindead
    if not _root:
        _resource_initializer(app, _root, api_resource, log)

    # Now we do some magic to traverse the package and find all the sub-resources we need to load
    log.debug(f"About to walk packages for {api_resource.__path__}")

    for module_info in pkgutil.walk_packages(api_resource.__path__):
        module_py_path = f"{api_path}.{module_info.name}"
        if module_py_path == api_resource.__path__:
            continue
        log.debug(f"Handling {module_py_path}")

        # If the 'module' is actually a package, we need to recurse to handle it
        if module_info.ispkg :
            log.debug(f"Recursing to handle {module_py_path}")
            load_api(app, module_py_path, _root=sub_resource_root)

        try:
            module = importlib.import_module(module_py_path)
        except ImportError as e:
            raise RouteBuilderError(f"Failed to import API resource {module_py_path}: {e}")

        log.debug(f"Imported module {module}")

        # Load integrations for this resource, if needed
        if module_info.name == "ext_integrations":
            _load_integrations(app, module, api_path, module_py_path, log)
            continue

        log.debug(f"Initializing resource {module_py_path}")
        _resource_initializer(app, sub_resource_root, module, log)
