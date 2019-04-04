# -*- coding: utf-8 -*-
"""
Application layer for the Rapid-REST server
"""
import importlib
import pkgutil
from inspect import signature


class RouteBuilderError(Exception): pass
class IntegrationBootError(RouteBuilderError): pass


def _load_integrations(app, module, api_path, module_py_path, log):
    """
    @brief      Loads integrations.
    
    @return     { description_of_the_return_value }
    """
    integration_boot = getattr(module, "initialize_ext_resources", None)
    if integration_boot is None:
        raise IntegrationBootError(
            "rr_integrations in %s is missing required 'initialize_ext_resources' method", api_path
        )

    log.debug("Running bootstrap for integrations in %s", api_path)
    if not integration_boot(app):
        raise IntegrationBootError("Failed to run integration bootstrap for %s", module_py_path)

    return True


def _add_url_rule(app, url, view, log, id_rule=False):
    """
    @brief      Adds an url rule.
    
    @param      app             The application
    @param      url             The url
    @param      resource_class  The resource class
    @param      log             The log
    @param      id_rule         Indicates this is a request for a rule with /<id> on the end of it
    
    @return     The view method or None
    """
    app.add_url_rule(
        url,
        view_func=view,
        provide_automatic_options=True
    )
    log.debug("Added endpoint '%s'", url)

    if id_rule:
        rule = f"{url}/<obj_id>"
        app.add_url_rule(
            rule,
            # The lambda obfuscates the view func, so Flask won't complain about the same method being used for the 
            # id call
            view_func=lambda *args, **kwargs: view(*args, **kwargs),
        )
        log.debug(f"Added 'id' endpoint '{rule}'")

    return view if not id_rule else None


def _resource_initializer(app, root, module, log):
    """
    @brief      { function_description }
    
    @param      app     The application
    @param      root    The api path
    @param      module  The module
    @param      log     The log
    
    @return     { description_of_the_return_value }
    """
    reqired_id_methods = {"PUT", "DELETE", "PATCH"}
    optional_id_methods = {"GET"}

    module_name = module.__name__.split(".")[-1]
    module_py_path = f"{root}.{module_name}" if root else f"{module_name}"
    url = "/{}".format("/".join(module_py_path.split(".")))

    # Make sure the class we expect is there
    res_class_name = module_name.capitalize()
    resource_class = getattr(module, res_class_name, None)
    if resource_class is None:
        log.warning("%s does not have the expected class '%s', skipping", module_py_path, res_class_name)
        return
    elif getattr(resource_class, "as_view", None) is None:
        log.warning("%s.%s does not inherit from flask.views.MethodView, skipping", module_py_path, res_class_name)
        return

    # Create url rule(s)
    view = resource_class.as_view(resource_class.endpoint_name)

    # Create an 'id' endpoint if the methods in this resource need it
    needs_id_rule = False
    for method in view.view_class.methods:
        meth_sig = signature(getattr(view.view_class, method.lower()))

        # We have to check for both required ID methods and methods which can optionally have one
        if method in reqired_id_methods and "obj_id" not in meth_sig.parameters:
            raise RouteBuilderError(f"Method '{method}' in {module_py_path} is required to have an 'obj_id' parameter")
        elif method in optional_id_methods and "obj_id" not in meth_sig.parameters:
            continue

        needs_id_rule = True
        break

    _add_url_rule(app, url, view, log, id_rule=needs_id_rule)




def load_api(app, api_path, _root=""):
    """
    @brief      Loads an api.
    
    @param      app       The application
    @param      api_path  The Python path to the API package
    @param      _root     Used for recursion, do not set this
    
    @return     { description_of_the_return_value }
    """
    log = app.logger

    try:
        api_resource = importlib.import_module(api_path)
    except ImportError:
        raise RouteBuilderError("Failed to load the API at '%s'", api_path)

    log.debug("Found API resource at '%s', attempting to load it", api_path)

    base_resource_name = api_resource.__name__.split(".")[-1]
    sub_resource_root = f"{_root}.{base_resource_name}" if _root else base_resource_name

    _resource_initializer(app, _root, api_resource, log)

    # Now we do some magic to traverse the package and find all the sub-resources we need to load
    for module_info in pkgutil.walk_packages(api_resource.__path__):
        module_py_path = f"{api_path}.{module_info.name}"

        # If the 'module' is actually a package, we need to recurse to handle it
        if module_info.ispkg :
            load_api(app, module_py_path, _root=sub_resource_root)

        try:
            module = importlib.import_module(module_py_path)
        except ImportError as e:
            raise RouteBuilderError("Failed to import API resource %s: %s", module_py_path, e)

        # Load integrations for this resource, if needed
        if module_info.name == "rr_integrations":
            _load_integrations(app, module, api_path, module_py_path, log)
            continue

        _resource_initializer(app, sub_resource_root, module, log)

    return True