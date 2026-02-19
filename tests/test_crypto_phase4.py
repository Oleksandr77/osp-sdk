import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from osp_core.crypto import JCS
import json

def test_crypto_algorithms():
    print("🧪 Starting Crypto Algorithm Tests...")
    
    data = {"hello": "world", "audit": "phase4"}
    
    algorithms = [
        "ES256", "ES384", "ES512",
        "RS256", "RS384", "RS512",
        "EdDSA",
        "HS256", "HS512"
    ]
    
    for alg in algorithms:
        try:
            print(f"  > Testing {alg}...", end=" ")
            
            # 1. Generate Key
            priv, pub = JCS.generate_key(alg)
            
            # 2. Sign
            # for HMAC, priv contains the secret, pub is None
            if alg.startswith("HS"):
                signature = JCS.sign(data, priv, alg)
                valid = JCS.verify(data, signature, priv, alg)
            else:
                signature = JCS.sign(data, priv, alg)
                valid = JCS.verify(data, signature, pub, alg)
            
            if valid:
                print("✅ Passed")
            else:
                print("❌ Failed (Invalid Signature)")
                
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_crypto_algorithms()
