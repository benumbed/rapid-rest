# -*- coding: utf-8 -*-
"""
Tests the rapid-rest authentication layer

"""
import json
import os
import unittest
import webtest
from unittest.mock import patch

from rapidrest import application, utils
from vaultutilscommon import vaultinstance
from rapidrest.security.authentication import create_v1_auth_header


class TestRapidRestAuthentication(unittest.TestCase):
    """
    @brief      Class for testing rapid rest's auth layer.
    """

    @classmethod
    def setUpClass(cls):
        cls.v_url, cls.v_root, cls.v_cont = vaultinstance.create(cls.__name__, port=8289, kill_existing=True)
        cls.approle = "restauthapprole"
        cls.kv_mountpoint = "basic_kv_v2"

        cls.transit_key = "TransitKey"
        cls.hmac_key = vaultinstance.create_transit_key(cls.transit_key,cls.v_url, cls.v_root, do_setup=True)

        vaultinstance.create_kv_v2_store(cls.kv_mountpoint, cls.v_url, cls.v_root, cls.approle)
        cls.secret_id, cls.role_id = vaultinstance.create_approle(cls.approle, cls.v_url, cls.v_root, wrapped=True,
                                                                  policies=(f"{cls.approle}-access",
                                                                            f"{cls.transit_key}-use-key"))

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


    def test_authentication_v1(self):
        """
        This tests that the v1 authn mechanism works

        """
        endpoint_patch = {
            "/v1/pants": {
                "POST": {
                    "authentication": True
                }
            }
        }

        body_data = {
            "Testing": 123
        }
        key_name = "auth_test_key"
        key = vaultinstance.create_transit_key(key_name, self.v_url, self.v_root)

        with patch.dict(self.app.config["api_config"]["security"]["endpoint_control"], endpoint_patch):

            # POST with body data
            auth_header = create_v1_auth_header(key_name, key, "POST", "localhost:80", "/v1/pants",
                                                json.dumps(body_data))
            resp = self.srv.post_json("/v1/pants", body_data, headers={"Authorization": auth_header})
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.content_type, "application/json")
            self.assertDictEqual(resp.json_body, {"pants_post": True})

            # POST with no body
            auth_header = create_v1_auth_header(key_name, key, "POST", "localhost:80", "/v1/pants")
            resp = self.srv.post("/v1/pants", headers={"Authorization": auth_header})
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.content_type, "application/json")
            self.assertDictEqual(resp.json_body, {"pants_post": True})


    def test_bad_authentication_v1(self):
        endpoint_patch = {
            "/v1/pants": {
                "POST": {
                    "authentication": True
                }
            }
        }

        body_data = {
            "Testing": 123
        }
        key_name = "auth_test_key"
        key = vaultinstance.create_transit_key(key_name, self.v_url, self.v_root)


        with patch.dict(self.app.config["api_config"]["security"]["endpoint_control"], endpoint_patch):
            # Missing body (in sig)
            auth_header = create_v1_auth_header(key_name, key, "POST", "localhost:80", "/v1/pants")
            resp = self.srv.post_json("/v1/pants", body_data, headers={"Authorization": auth_header},
                                 expect_errors=True)
            self.assertEqual(resp.status_code, 403)

            # Missing body (in actual request)
            auth_header = create_v1_auth_header(key_name, key, "POST", "localhost:80", "/v1/pants",
                                                json.dumps(body_data))
            resp = self.srv.post("/v1/pants", headers={"Authorization": auth_header},
                                      expect_errors=True)
            self.assertEqual(resp.status_code, 403)

            # Different method
            auth_header = create_v1_auth_header(key_name, key, "POST", "localhost:80", "/v1/pants")
            resp = self.srv.get("/v1/pants", headers={"Authorization": auth_header}, expect_errors=True)
            self.assertEqual(resp.status_code, 403)

            # Different hostname
            auth_header = create_v1_auth_header(key_name, key, "GET", "badhostname", "/v1/pants")
            resp = self.srv.get("/v1/pants", headers={"Authorization": auth_header}, expect_errors=True)
            self.assertEqual(resp.status_code, 403)

            # Different URL
            auth_header = create_v1_auth_header(key_name, key, "GET", "localhost:80", "/v1/pants?v=1")
            resp = self.srv.get("/v1/pants", headers={"Authorization": auth_header}, expect_errors=True)
            self.assertEqual(resp.status_code, 403)

            # Wrong principal
            auth_header = create_v1_auth_header("some-other-principal", key, "GET", "localhost:80", "/v1/pants")
            resp = self.srv.get("/v1/pants", headers={"Authorization": auth_header}, expect_errors=True)
            self.assertEqual(resp.status_code, 403)

            # Wrong key
            auth_header = create_v1_auth_header(key_name, "holyshitbadkeyman".encode("utf-8"), "GET", "localhost:80",
                                                "/v1/pants")
            resp = self.srv.get("/v1/pants", headers={"Authorization": auth_header}, expect_errors=True)
            self.assertEqual(resp.status_code, 403)


