import unittest
import json
import sys
import os
# Add osp_core parent to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from osp_core.crypto import JCS

class TestJCS(unittest.TestCase):
    def test_basic_types(self):
        self.assertEqual(JCS.canonicalize(None), b"null")
        self.assertEqual(JCS.canonicalize(True), b"true")
        self.assertEqual(JCS.canonicalize(False), b"false")
        self.assertEqual(JCS.canonicalize(123), b"123")
        self.assertEqual(JCS.canonicalize("hello"), b'"hello"')

    def test_list(self):
        data = [3, 2, 1]
        # Lists retain order
        self.assertEqual(JCS.canonicalize(data), b"[3,2,1]")

    def test_dict_sorting(self):
        data = {"c": 3, "a": 1, "b": 2}
        # Dicts sort keys
        self.assertEqual(JCS.canonicalize(data), b'{"a":1,"b":2,"c":3}')

    def test_nested(self):
        data = {"a": [2, 1], "b": {"y": 2, "x": 1}}
        self.assertEqual(JCS.canonicalize(data), b'{"a":[2,1],"b":{"x":1,"y":2}}')

    def test_whitespace(self):
        # Input has whitespace, output should not
        data = json.loads('{ "a":  1, "b": 2 }')
        self.assertEqual(JCS.canonicalize(data), b'{"a":1,"b":2}')

    def test_unicode(self):
        # Ensure unicode is preserved unescaped (unless control char)
        data = {"text": "привіт"}
        # JCS requires: "Strings are encoded as JSON strings... however, to minimize differences... 
        # generic JSON generators escape... but JCS requires that they NOT be escaped if possible"
        # json.dumps(ensure_ascii=False) does this for us.
        self.assertEqual(JCS.canonicalize(data), '{"text":"привіт"}'.encode('utf8'))

    def test_sign_verify_es256(self):
        data = {"foo": "bar", "baz": 123}
        priv, pub = JCS.generate_key("ES256")
        
        sig = JCS.sign(data, priv, "ES256")
        self.assertTrue(JCS.verify(data, sig, pub, "ES256"))
        
        # Tamper
        data["foo"] = "bar2"
        self.assertFalse(JCS.verify(data, sig, pub, "ES256"))

    def test_sign_verify_rs256(self):
        data = {"foo": "bar"}
        priv, pub = JCS.generate_key("RS256")
        
        sig = JCS.sign(data, priv, "RS256")
        self.assertTrue(JCS.verify(data, sig, pub, "RS256"))

if __name__ == '__main__':
    unittest.main()
