
import unittest
from unittest.mock import MagicMock, ANY
import sys
import os
import json

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from daminion_client import DaminionClient

class TestDaminionPayload(unittest.TestCase):
    def test_batch_update_payload_structure(self):
        """
        Verify that batch_update_tags sends the correctly formatted JSON payload
        matching the Daminion API documentation.
        """
        client = DaminionClient("http://test", "user", "pass")
        client.authenticated = True
        client._make_request = MagicMock(return_value={'success': True})
        
        item_ids = ["1", "2"]
        tags = {
            "Keywords": ["k1", "k2"],
            "Category": ["c1"]
        }
        
        client.batch_update_tags(item_ids, tags)
        
        # Check the call args
        args, kwargs = client._make_request.call_args
        endpoint = args[0]
        method = kwargs.get('method')
        data = kwargs.get('data')
        
        self.assertEqual(endpoint, "/api/ItemData/BatchChange")
        self.assertEqual(method, "POST")
        
        # Data is dict passed to _make_request, which then json dumps it.
        # Wait, _make_request takes `data` as Dict.
        
        expected_structure = {
            "ids": [1, 2],
            "delete": False,
            "data": [
                # Order might vary so we check content
            ]
        }
        
        self.assertIn("ids", data)
        self.assertEqual(data["ids"], [1, 2])
        self.assertIn("data", data)
        self.assertTrue(isinstance(data["data"], list))
        
        # Verify Items
        # Expected:
        # { "guid": "Keywords", "value": "k1", "remove": False }
        # { "guid": "Keywords", "value": "k2", "remove": False }
        # { "guid": "Category", "value": "c1", "remove": False }
        
        expected_items = [
            {"guid": "Keywords", "value": "k1", "remove": False},
            {"guid": "Keywords", "value": "k2", "remove": False},
            {"guid": "Category", "value": "c1", "remove": False}
        ]
        
        for item in expected_items:
            self.assertIn(item, data["data"])

if __name__ == '__main__':
    unittest.main()
