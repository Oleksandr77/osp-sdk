from fastapi import Request, HTTPException
import logging
import base64
from typing import Optional

# Assumption: osp_core is in path
try:
    from osp_core.crypto import JCS
except ImportError:
    import sys, os
    sys.path.append(os.path.join(os.path.dirname(__file__), "../../"))
    from osp_core.crypto import JCS

logger = logging.getLogger("osp.security.signature")

class SignatureVerifier:
    def __init__(self, public_key_pem: bytes = None):
        self.public_key = public_key_pem
        self.enforce = False # Start in Soft Mode

    def set_public_key(self, pem: bytes):
        self.public_key = pem

    def set_enforcement(self, enabled: bool):
        self.enforce = enabled

    async def verify_request(self, request: Request, body_bytes: bytes):
        """
        Verifies the X-OSP-Signature header.
        """
        signature = request.headers.get("X-OSP-Signature")
        
        if not signature:
            msg = "Missing X-OSP-Signature header."
            if self.enforce:
                logger.error(f"Authentication Failed: {msg}")
                raise HTTPException(status_code=401, detail=msg)
            else:
                logger.warning(f"Soft Auth Warning: {msg}")
                return

        if not self.public_key:
             logger.warning("No public key configured for verification. Skipping.")
             return

        try:
            # Parse body to JSON object for JCS
            import json
            data = json.loads(body_bytes)
            
            # Verify — read algorithm from header (supports all 9 spec algorithms)
            alg = request.headers.get("X-OSP-Alg", "ES256")
            is_valid = JCS.verify(data, signature, self.public_key, alg=alg)
            
            if not is_valid:
                msg = "Invalid Signature."
                if self.enforce:
                     logger.error(f"Authentication Failed: {msg}")
                     raise HTTPException(status_code=401, detail=msg)
                else:
                     logger.warning(f"Soft Auth Warning: {msg} (Proceeding in permissive mode)")
            else:
                logger.info("Signature Verified Successfully.")
                
        except Exception as e:
            logger.error(f"Signature Verification Error: {e}")
            if self.enforce:
                raise HTTPException(status_code=401, detail=f"Verification Error: {str(e)}")
