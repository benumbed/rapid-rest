# -*- coding: utf-8 -*-
"""
Tests the rapid-rest system

"""
import unittest
import webtest

from rapidrest import application

# TODO: Need to test the integration setup/mapping system

class TestRapidRest(unittest.TestCase):
    """
    @brief      Class for testing rapid rest.
    """

    @classmethod
    def setUpClass(cls):
        cls.app = application.start()
        # This test suite does not need to test the auth system, so we disable it
        cls.app.config["api_config"]["security"]["whitelist"] = False
        cls.srv = webtest.TestApp(cls.app)



    def test_get(self):
        resp = self.srv.get("/v1/pants")

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.content_type, "application/json")

        body_data = resp.json_body
        self.assertDictEqual(body_data, {"pants_get": True})


    def test_get_with_id(self):
        resp = self.srv.get("/v1/pants/1")

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.content_type, "application/json")

        body_data = resp.json_body
        self.assertDictEqual(body_data, {"pants_get": True, "id": "1"})


    def test_not_found(self):
        """
        @brief      Ensures 404s are generated properly
        
        @param      self  The object
        """
        resp = self.srv.get("/v1/dne", expect_errors=True)

        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.content_type, "application/json")

        body_data = resp.json_body
        self.assertIn("err", body_data)
        self.assertIn("err_detail", body_data)
        self.assertIn("err_type", body_data)

        self.assertEqual(body_data["err"], True)
        self.assertEqual(body_data["err_type"], "Client")
        self.assertIn("404 not found", body_data["err_detail"].lower())


    def test_unknown_error(self):
        """
        @brief      Ensures that non-HTTP errors still get trapped and formatted properly
        
        @param      self  The object
        """
        resp = self.srv.get("/v1", expect_errors=True)

        self.assertEqual(resp.status_code, 500)
        self.assertEqual(resp.content_type, "application/json")

        body_data = resp.json_body
        self.assertIn("err", body_data)
        self.assertIn("err_detail", body_data)
        self.assertIn("err_type", body_data)

        self.assertEqual(body_data["err"], True)
        self.assertEqual(body_data["err_type"], "Unknown:BananaBlenderError")
        self.assertEqual(body_data["err_detail"], "whoopsie")


    def test_attached_current_request(self):
        """
        Ensures that the current request is attached to the resource class

        """
        sent_body = {
            "sent": True,
            "body": "by Bob Barker"
        }
        resp = self.srv.post_json("/v1", sent_body)

        self.assertDictEqual(resp.json_body, sent_body)

        sent_body_v2 = {
            "sent": False,
            "body": "by Pants McGee"
        }
        resp = self.srv.post_json("/v1", sent_body_v2)

        self.assertDictEqual(resp.json_body, sent_body_v2)
