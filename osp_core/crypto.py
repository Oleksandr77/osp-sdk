import json
import hashlib
from typing import Any

class JCS:
    """
    JSON Canonicalization Scheme (RFC 8785) Implementation.
    """
    
    @staticmethod
    def _encode_key(key: str) -> bytes:
        return json.dumps(key, ensure_ascii=False).encode('utf-8')

    @staticmethod
    def _encode(data: Any) -> bytes:
        if data is None:
            return b"null"
        elif isinstance(data, bool):
            return b"true" if data else b"false"
        elif isinstance(data, int):
            return str(data).encode('utf-8')
        elif isinstance(data, float):
            # RFC 8785: "Numbers must not be encoded with exponential notation"
            # This is a simplified implementation for standard Python floats
            # Ideally one would check for NaN/Inf and handle standard formatting rigorously
            # For this MVP, we use standard repr or compact formatting
            # However, RFC 8785 requires specific ES6-like number formatting.
            # Python's json dump produces compatible output for most cases but spaces are tricky.
            # We'll use json.dumps with specific separators to ensure no spaces.
             return json.dumps(data, separators=(',', ':'), allow_nan=False).encode('utf-8')
        elif isinstance(data, str):
            return json.dumps(data, ensure_ascii=False).encode('utf-8')
        elif isinstance(data, list):
            items = [JCS._encode(item) for item in data]
            return b"[" + b",".join(items) + b"]"
        elif isinstance(data, dict):
            # Keys must be sorted elegantly by their UTF-16 code units (which matches standard sort for simple strings)
            # RFC 8785 requires sorting by UTF-16 code units.
            # Python string sort is by Unicode code points, which is equivalent for BMP chars.
            sorted_keys = sorted(data.keys())
            items = []
            for key in sorted_keys:
                encoded_key = JCS._encode_key(key)
                encoded_val = JCS._encode(data[key])
                items.append(encoded_key + b":" + encoded_val)
            return b"{" + b",".join(items) + b"}"
        else:
            raise TypeError(f"Type {type(data)} not serializable by JCS")

    @classmethod
    def canonicalize(cls, data: Any) -> bytes:
        """
        Returns the JCS bytes for the given data structure.
        """
        return cls._encode(data)

    @classmethod
    def hash(cls, data: Any, alg: str = "sha256") -> str:
        """
        Returns the hex digest of the JCS canonicalized data.
        """
        canonical = cls.canonicalize(data)
        if alg == "sha256":
            return hashlib.sha256(canonical).hexdigest()
        else:
            raise ValueError(f"Unsupported hash algorithm: {alg}")

    @staticmethod
    def generate_key(alg: str = "ES256"):
        """
        Generates a key pair or secret for the specified algorithm.
        Returns:
          - Asymmetric: (private_key_pem, public_key_pem) as bytes
          - Symmetric: (secret_key, None) as bytes (key is raw bytes or base64? Usually raw/hex for HMAC config)
        """
        from cryptography.hazmat.primitives.asymmetric import ec, rsa, ed25519
        from cryptography.hazmat.primitives import serialization
        import os
        import base64

        if alg == "ES256":
            private_key = ec.generate_private_key(ec.SECP256R1())
        elif alg == "ES384":
            private_key = ec.generate_private_key(ec.SECP384R1())
        elif alg == "ES512":
            private_key = ec.generate_private_key(ec.SECP521R1())
        elif alg == "RS256" or alg == "RS384" or alg == "RS512":
            private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        elif alg == "EdDSA":
            private_key = ed25519.Ed25519PrivateKey.generate()
        elif alg.startswith("HS"):
            # Symmetric key
            # Return 32 bytes for HS256, 64 for HS512
            length = 64 if alg == "HS512" else 32
            secret = os.urandom(length)
            return base64.b64encode(secret), None
        else:
            raise ValueError(f"Unsupported algorithm for generation: {alg}")

        priv_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        pub_pem = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return priv_pem, pub_pem

    @classmethod
    def sign(cls, data: Any, key_bytes: bytes, alg: str = "ES256") -> str:
        """
        Signs the JCS canonicalized data. Returns base64 encoded signature.
        key_bytes: PEM encoded private key OR raw secret bytes for HMAC.
        """
        import base64
        from cryptography.hazmat.primitives.asymmetric import ec, padding, rsa, ed25519
        from cryptography.hazmat.primitives import hashes, serialization, hmac

        canonical = cls.canonicalize(data)
        
        # HMAC Handling
        if alg.startswith("HS"):
            # key_bytes is expected to be base64 encoded secret or raw bytes?
            # Let's assume input is raw bytes or we decode if it looks like b64?
            # For simplicity, assume key_bytes IS the secret. 
            # If generated by generate_key, it returned b64 encoded bytes.
            try:
                secret = base64.b64decode(key_bytes)
            except:
                secret = key_bytes
                
            hash_alg = hashes.SHA512() if alg == "HS512" else hashes.SHA256()
            h = hmac.HMAC(secret, hash_alg)
            h.update(canonical)
            signature = h.finalize()
            return base64.b64encode(signature).decode('utf-8')

        # Asymmetric Handling
        private_key = serialization.load_pem_private_key(key_bytes, password=None)

        if alg.startswith("ES"):
            if not isinstance(private_key, ec.EllipticCurvePrivateKey):
                 raise TypeError(f"Key type mismatch for {alg}")
            
            hash_alg = hashes.SHA256()
            if alg == "ES384": hash_alg = hashes.SHA384()
            elif alg == "ES512": hash_alg = hashes.SHA512()
            
            signature = private_key.sign(
                canonical,
                ec.ECDSA(hash_alg)
            )
        elif alg.startswith("RS"):
            if not isinstance(private_key, rsa.RSAPrivateKey):
                 raise TypeError(f"Key type mismatch for {alg}")
            
            hash_alg = hashes.SHA256()
            if alg == "RS384": hash_alg = hashes.SHA384()
            elif alg == "RS512": hash_alg = hashes.SHA512()
            
            signature = private_key.sign(
                canonical,
                padding.PKCS1v15(),
                hash_alg
            )
        elif alg == "EdDSA":
            if not isinstance(private_key, ed25519.Ed25519PrivateKey):
                raise TypeError("Key type mismatch for EdDSA")
            signature = private_key.sign(canonical)
        else:
            raise ValueError(f"Unsupported algorithm: {alg}")

        return base64.b64encode(signature).decode('utf-8')

    @classmethod
    def verify(cls, data: Any, signature_b64: str, key_bytes: bytes, alg: str = "ES256") -> bool:
        """
        Verifies the signature against JCS canonicalized data.
        key_bytes: PEM public key OR HMAC secret.
        """
        import base64
        from cryptography.hazmat.primitives.asymmetric import ec, padding, rsa, ed25519
        from cryptography.hazmat.primitives import hashes, serialization, hmac
        from cryptography.exceptions import InvalidSignature

        canonical = cls.canonicalize(data)
        try:
            signature = base64.b64decode(signature_b64)
        except:
             return False

        try:
            # HMAC Handling
            if alg.startswith("HS"):
                try:
                    secret = base64.b64decode(key_bytes)
                except:
                    secret = key_bytes
                
                hash_alg = hashes.SHA512() if alg == "HS512" else hashes.SHA256()
                h = hmac.HMAC(secret, hash_alg)
                h.update(canonical)
                h.verify(signature)
                return True

            # Asymmetric Handling
            public_key = serialization.load_pem_public_key(key_bytes)

            if alg.startswith("ES"):
                if not isinstance(public_key, ec.EllipticCurvePublicKey):
                    raise TypeError(f"Key type mismatch for {alg}")
                
                hash_alg = hashes.SHA256()
                if alg == "ES384": hash_alg = hashes.SHA384()
                elif alg == "ES512": hash_alg = hashes.SHA512()
                
                public_key.verify(
                    signature,
                    canonical,
                    ec.ECDSA(hash_alg)
                )
            elif alg.startswith("RS"):
                 if not isinstance(public_key, rsa.RSAPublicKey):
                    raise TypeError(f"Key type mismatch for {alg}")
                 
                 hash_alg = hashes.SHA256()
                 if alg == "RS384": hash_alg = hashes.SHA384()
                 elif alg == "RS512": hash_alg = hashes.SHA512()
                 
                 public_key.verify(
                    signature,
                    canonical,
                    padding.PKCS1v15(),
                    hash_alg
                )
            elif alg == "EdDSA":
                if not isinstance(public_key, ed25519.Ed25519PublicKey):
                    raise TypeError("Key type mismatch for EdDSA")
                public_key.verify(signature, canonical)
            else:
                raise ValueError(f"Unsupported algorithm: {alg}")
            return True
        except InvalidSignature:
            return False
        except Exception as e:
            # logger.error(f"Verification error: {e}")
            return False
