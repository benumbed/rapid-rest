# -*- coding: utf-8 -*-
"""
Tests the rapid-rest authentication layer

"""
import os
import unittest
import webtest
from unittest.mock import patch

from rapidrest import application
from vaultutilscommon import vaultinstance


class TestRapidRestAuthentication(unittest.TestCase):
    """
    @brief      Class for testing rapid rest's auth layer.
    """

    @classmethod
    def setUpClass(cls):
        cls.v_url, cls.v_root, cls.v_cont = vaultinstance.create(cls.__name__, port=8289, kill_existing=True)
        cls.approle = "restauthapprole"
        cls.kv_mountpoint = "basic_kv_v2"
        vaultinstance.create_kv_v2_store(cls.kv_mountpoint, cls.v_url, cls.v_root, cls.approle)
        cls.secret_id, cls.role_id = vaultinstance.create_approle(cls.approle, cls.v_url, cls.v_root, wrapped=True,
                                                                  policies=(f"{cls.approle}-access",))

        os.environ["VAULT_URL"] = cls.v_url
        os.environ["VAULT_ROLE_ID"] = cls.role_id
        os.environ["VAULT_WRAPPED_SECRET"] = cls.secret_id
        os.environ["VAULT_SECRETS_MOUNT"] = cls.kv_mountpoint
        os.environ["VAULT_SECRETS_PATH"] = "_dynamic"

        cls.app = application.start()
        cls.srv = webtest.TestApp(cls.app)


    @classmethod
    def tearDownClass(cls):
        # If we don't stop the vault client the token refresh process will run indefinitely
        del cls.app.config["vault"]


    def test_whitelisting(self):
        resp = self.srv.post("/v1/pants", expect_errors=True, headers={"Authorization":""})

        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.content_type, "application/json")

        body_data = resp.json_body
        self.assertIn("403 forbidden", body_data["err_detail"].lower())
        self.assertIn("whitelist", body_data["err_detail"].lower())
        self.assertEqual(body_data["err_type"], "Client")


        # Disable whitelisting and endpoint controls, should allow the call now
        whitelist_patch = {
            "whitelist": False
        }
        with patch.dict(self.app.config["api_config"]["security"], whitelist_patch):
            resp = self.srv.post("/v1/pants", headers={"Authorization":""})

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.content_type, "application/json")


    def test_whitelisting_authn_disabled(self):
        endpoint_patch = {
            "/v1/pants": {
                "POST": {
                    "authentication": False
                }
            }
        }

        with patch.dict(self.app.config["api_config"]["security"]["endpoint_control"], endpoint_patch):
            resp = self.srv.post("/v1/pants", headers={"Authorization":""})

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.content_type, "application/json")

        body_data = resp.json_body
        self.assertDictEqual(body_data, {"pants_post": True})


    def test_authentication(self):
        """
        FIXME: THIS IS NOT DONE YET

        @return:
        """
        endpoint_patch = {
            "/v1/pants": {
                "POST": {
                    "authentication": True
                }
            }
        }

        with patch.dict(self.app.config["api_config"]["security"]["endpoint_control"], endpoint_patch):
            resp = self.srv.post("/v1/pants", headers={"Authorization": ""})

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.content_type, "application/json")

        body_data = resp.json_body
        self.assertDictEqual(body_data, {"pants_post": True})

    # def test_get(self):
    #     resp = self.srv.post("/v1/pants")
    #
    #     print(resp.body)
    #
    #     self.assertEqual(resp.status_code, 200)
    #     self.assertEqual(resp.content_type, "application/json")
    #
    #     body_data = resp.json_body
    #     self.assertDictEqual(body_data, {"pants_post": True})


    # def test_get_with_id(self):
    #     resp = self.srv.get("/v1/pants/1")

    #     self.assertEqual(resp.status_code, 200)
    #     self.assertEqual(resp.content_type, "application/json")

    #     body_data = resp.json_body
    #     self.assertDictEqual(body_data, {"example": True, "id": "1"})


    # def test_not_found(self):
    #     """
    #     @brief      Ensures 404s are generated properly
        
    #     @param      self  The object
    #     """
    #     resp = self.srv.get("/v1/dne", expect_errors=True)

    #     self.assertEqual(resp.status_code, 404)
    #     self.assertEqual(resp.content_type, "application/json")

    #     body_data = resp.json_body
    #     self.assertIn("err", body_data)
    #     self.assertIn("err_detail", body_data)
    #     self.assertIn("err_type", body_data)

    #     self.assertEqual(body_data["err"], True)
    #     self.assertEqual(body_data["err_type"], "Client")
    #     self.assertIn("404 not found", body_data["err_detail"].lower())


    # def test_unknown_error(self):
    #     """
    #     @brief      Ensures that non-HTTP errors still get trapped and formatted properly
        
    #     @param      self  The object
    #     """
    #     resp = self.srv.get("/v1", expect_errors=True)

    #     self.assertEqual(resp.status_code, 500)
    #     self.assertEqual(resp.content_type, "application/json")

    #     body_data = resp.json_body
    #     self.assertIn("err", body_data)
    #     self.assertIn("err_detail", body_data)
    #     self.assertIn("err_type", body_data)

    #     self.assertEqual(body_data["err"], True)
    #     self.assertEqual(body_data["err_type"], "Unknown:BananaBlenderError")
    #     self.assertEqual(body_data["err_detail"], "whoopsie")
    #     
