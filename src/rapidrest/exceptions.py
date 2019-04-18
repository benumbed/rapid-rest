# -*- coding: utf-8 -*-
"""
Exceptions for rapid-rest

"""

class RapidRestError(Exception): pass
class RapidRestVaultError(RapidRestError): pass
class IntegrationLoadError(RapidRestError): pass
