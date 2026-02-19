import unittest
import sys
import os
import time
from cryptography.hazmat.primitives import serialization

# Add osp_core parent to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from osp_core.models import RegistryEntry, TrustAnchor, HashingConfig
from osp_core.crypto import JCS

class TestModels(unittest.TestCase):
    def test_registry_entry_signing(self):
        # Generate keys
        priv, pub = JCS.generate_key("ES256")
        
        # Create Entry
        entry = RegistryEntry(
            entry_type="REGISTER",
            skill_ref="my.skill@1.0.0",
            timestamp=int(time.time()),
            signed_by="key-123",
            content_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", # empty sha256
            signature="", # pending
            alg="ES256",
            trust_anchor=TrustAnchor(type="self_signed"),
            hashing_config=HashingConfig()
        )
        
        # Sign
        entry.sign(priv)
        
        self.assertTrue(len(entry.signature) > 0)
        
        # Verify
        # Reconstruct data dict
        data = entry.model_dump(exclude={"signature"})
        self.assertTrue(JCS.verify(data, entry.signature, pub, "ES256"))

if __name__ == '__main__':
    unittest.main()
