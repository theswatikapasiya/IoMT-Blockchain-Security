"""
Secure API Gateway & Cloud Security Infrastructure (Layer 5)
Provides authentication, authorization (RBAC), validation, sanitization,
AES-256 encryption, cloud re-verification, audit logging, monitoring, and backups.
"""

import os
import re
import jwt
import time
import json
import base64
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend

# Security Configurations
JWT_SECRET = "iomt-cloud-security-secret-key-12345#"
AES_KEY_STRING = "iomt-cloud-aes-key-for-payload-3" # 32 bytes key
AES_KEY = AES_KEY_STRING.encode("utf-8")
DATA_LAKE_PATH = "data/processed/cloud_healthcare_lake.json"
BACKUP_PATH = "data/processed/cloud_healthcare_lake_backup.json"
AUDIT_LOG_PATH = "data/processed/cloud_audit_log.json"

class CloudGatewaySecurity:
    """Implements central cloud-native security controls for the API Gateway & Data Transmission"""
    
    def __init__(self):
        self.rate_limit_window = 2  # seconds
        self.max_requests_per_window = 5
        self.request_logs: Dict[str, List[float]] = {}  # IP -> list of timestamps
        self.threat_metrics = {
            "total_requests": 0,
            "blocked_malformed_requests": 0,
            "rate_limit_violations": 0,
            "authentication_failures": 0,
            "unauthorized_attempts": 0,
            "blocked_injections": 0,
            "total_backups_created": 0,
            "failover_occurrences": 0
        }
        
        # Ensure directories exist
        os.makedirs("data/processed", exist_ok=True)
        self._initialize_databases()
        
    def _initialize_databases(self):
        """Initializes empty JSON structures if they do not exist"""
        for path in [DATA_LAKE_PATH, BACKUP_PATH]:
            if not os.path.exists(path):
                with open(path, "w") as f:
                    json.dump({}, f, indent=4)
        if not os.path.exists(AUDIT_LOG_PATH):
            with open(AUDIT_LOG_PATH, "w") as f:
                json.dump([], f, indent=4)

    # ----------------------------------------------------
    # 1. API GATEWAY RATE LIMITING & ROUTING
    # ----------------------------------------------------
    def is_rate_limited(self, client_ip: str) -> bool:
        """Determines if a client has violated the rate limiting threshold"""
        current_time = time.time()
        if client_ip not in self.request_logs:
            self.request_logs[client_ip] = []
            
        # Filter request timestamps to only keep recent ones
        self.request_logs[client_ip] = [t for t in self.request_logs[client_ip] if current_time - t < self.rate_limit_window]
        
        if len(self.request_logs[client_ip]) >= self.max_requests_per_window:
            self.threat_metrics["rate_limit_violations"] += 1
            return True
            
        self.request_logs[client_ip].append(current_time)
        return False

    # ----------------------------------------------------
    # 2. REQUEST AUTHENTICATION (JWT)
    # ----------------------------------------------------
    def generate_jwt_token(self, username: str, role: str, expiry_minutes: int = 30) -> str:
        """Generates a signed JSON Web Token containing identity and privileges metadata"""
        payload = {
            "sub": username,
            "role": role,
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(minutes=expiry_minutes)
        }
        return jwt.encode(payload, JWT_SECRET, algorithm="HS256")
        
    def verify_jwt_token(self, token: str) -> Tuple[bool, Dict[str, Any]]:
        """Verifies JWT signature and returns authentication status and decoded payload"""
        try:
            decoded = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
            return True, decoded
        except jwt.ExpiredSignatureError:
            self.threat_metrics["authentication_failures"] += 1
            return False, {"error": "Token expired"}
        except jwt.InvalidTokenError:
            self.threat_metrics["authentication_failures"] += 1
            return False, {"error": "Invalid token"}

    # ----------------------------------------------------
    # 3. ROLE-BASED ACCESS CONTROL (RBAC)
    # ----------------------------------------------------
    def verify_rbac(self, user_role: str, required_roles: List[str]) -> bool:
        """Checks if a user's role satisfies endpoint privileges"""
        if user_role in required_roles:
            return True
        self.threat_metrics["unauthorized_attempts"] += 1
        return False

    # ----------------------------------------------------
    # 4. REQUEST VALIDATION AND SANITIZATION
    # ----------------------------------------------------
    def validate_and_sanitize(self, payload_dict: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Scans input payloads to block SQL injection, command injections, and XSS.
        Returns (is_clean, reason)
        """
        # 1. Packet Size Check
        payload_str = json.dumps(payload_dict)
        if len(payload_str.encode("utf-8")) > 65536: # 64 KB limit
            self.threat_metrics["blocked_malformed_requests"] += 1
            return False, "PAYLOAD_OVERSIZED_LIMIT"
            
        # 2. Malicious patterns regex
        sql_injection_patterns = [
            r"(?i)\bUNION\b.*\bSELECT\b",
            r"(?i)\bSELECT\b.*\bFROM\b",
            r"(?i)\bDROP\b\s+\bTABLE\b",
            r"(?i)'\s*OR\s*'\d+'\s*=\s*'\d+",
            r"(?i)--",
            r"(?i)\bINSERT\s+INTO\b"
        ]
        
        command_injection_patterns = [
            r"[;&|`]", # special shell characters
            r"\bsh\b",
            r"\bbash\b",
            r"\bcmd\b",
            r"\bsystem\b"
        ]
        
        xss_patterns = [
            r"(?i)<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>",
            r"(?i)javascript:",
            r"(?i)onload\s*=",
            r"(?i)onerror\s*="
        ]
        
        for key, val in payload_dict.items():
            val_str = str(val)
            
            # Check SQL Injection
            for pattern in sql_injection_patterns:
                if re.search(pattern, val_str):
                    self.threat_metrics["blocked_injections"] += 1
                    return False, f"SQL_INJECTION_DETECTED_IN_{key.upper()}"
                    
            # Check Command Injection
            for pattern in command_injection_patterns:
                if re.search(pattern, val_str):
                    self.threat_metrics["blocked_injections"] += 1
                    return False, f"COMMAND_INJECTION_DETECTED_IN_{key.upper()}"
                    
            # Check XSS
            for pattern in xss_patterns:
                if re.search(pattern, val_str):
                    self.threat_metrics["blocked_injections"] += 1
                    return False, f"XSS_ATTACK_DETECTED_IN_{key.upper()}"
                    
        return True, "CLEAN"

    # ----------------------------------------------------
    # 5. END-TO-END ENCRYPTION (AES-256-CBC)
    # ----------------------------------------------------
    def encrypt_payload(self, data_str: str) -> str:
        """Encrypts data string using AES-256-CBC with PKCS7 padding"""
        raw = data_str.encode("utf-8")
        
        # Pad data to AES block size (16 bytes)
        padder = padding.PKCS7(128).padder()
        padded_data = padder.update(raw) + padder.finalize()
        
        # Dynamic Initialization Vector (IV)
        iv = os.urandom(16)
        
        cipher = Cipher(algorithms.AES(AES_KEY), modes.CBC(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        encrypted = encryptor.update(padded_data) + encryptor.finalize()
        
        # Return base64 encoded string combination of IV + Encrypted text
        combined = iv + encrypted
        return base64.b64encode(combined).decode("utf-8")
        
    def decrypt_payload(self, encrypted_b64: str) -> str:
        """Decrypts AES-256-CBC encrypted base64 payload"""
        combined = base64.b64decode(encrypted_b64.encode("utf-8"))
        
        iv = combined[:16]
        ciphertext = combined[16:]
        
        cipher = Cipher(algorithms.AES(AES_KEY), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        decrypted_padded = decryptor.update(ciphertext) + decryptor.finalize()
        
        # Unpad
        unpadder = padding.PKCS7(128).unpadder()
        decrypted = unpadder.update(decrypted_padded) + unpadder.finalize()
        return decrypted.decode("utf-8")

    # ----------------------------------------------------
    # 6. CLOUD DATA STORAGE & LOGICAL PARTITIONING
    # ----------------------------------------------------
    def save_to_cloud_lake(self, patient_id: str, encrypted_payload: str, metadata: Dict[str, Any]) -> bool:
        """Saves encrypted telemetry logically partitioned by Patient ID to the Cloud Data Lake file"""
        try:
            with open(DATA_LAKE_PATH, "r") as f:
                data_lake = json.load(f)
                
            # Segmentation: Partition logically by patient_id
            if patient_id not in data_lake:
                data_lake[patient_id] = []
                
            record = {
                "timestamp": datetime.utcnow().isoformat(),
                "encrypted_data": encrypted_payload,
                "metadata": metadata
            }
            data_lake[patient_id].append(record)
            
            with open(DATA_LAKE_PATH, "w") as f:
                json.dump(data_lake, f, indent=4)
                
            # Create a backup immediately for disaster recovery/resilience (Step 13)
            self.create_backup()
            return True
        except Exception as e:
            print(f"⚠️  Cloud Storage Error: {e}")
            return False

    def read_from_cloud_lake(self, patient_id: str) -> List[Dict[str, Any]]:
        """Reads and partitions record outputs by Patient ID"""
        try:
            with open(DATA_LAKE_PATH, "r") as f:
                data_lake = json.load(f)
            return data_lake.get(patient_id, [])
        except:
            return []

    # ----------------------------------------------------
    # 7. FORENSIC CLOUD AUDIT LOGGING
    # ----------------------------------------------------
    def log_cloud_event(self, username: str, role: str, action: str, 
                        resource: str, outcome: str, details: str = ""):
        """Appends a secure, timestamped audit trail log in cloud_audit_log.json"""
        try:
            with open(AUDIT_LOG_PATH, "r") as f:
                logs = json.load(f)
                
            log_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "username": username,
                "role": role,
                "action": action,
                "resource": resource,
                "outcome": outcome,
                "details": details
            }
            logs.append(log_entry)
            
            with open(AUDIT_LOG_PATH, "w") as f:
                json.dump(logs, f, indent=4)
        except Exception as e:
            print(f"⚠️  Audit Logging Error: {e}")

    # ----------------------------------------------------
    # 8. BACKUP, RECOVERY AND DISASTER RESILIENCE
    # ----------------------------------------------------
    def create_backup(self) -> bool:
        """Saves a replica snapshot of the Data Lake database"""
        try:
            with open(DATA_LAKE_PATH, "r") as src, open(BACKUP_PATH, "w") as dest:
                data = json.load(src)
                json.dump(data, dest, indent=4)
            self.threat_metrics["total_backups_created"] += 1
            return True
        except Exception as e:
            print(f"⚠️  Disaster Backup Error: {e}")
            return False
            
    def simulate_failover(self) -> bool:
        """Simulates disaster failover recovery restoring the Data Lake from the standby backup"""
        try:
            # Overwrite main data lake with backup copy
            with open(BACKUP_PATH, "r") as backup_src, open(DATA_LAKE_PATH, "w") as main_dest:
                data = json.load(backup_src)
                json.dump(data, main_dest, indent=4)
            self.threat_metrics["failover_occurrences"] += 1
            self.log_cloud_event("SYSTEM", "Admin", "FAILOVER_RECOVERY", "DATA_LAKE", "SUCCESS", "Restored main lake from backup.")
            return True
        except Exception as e:
            print(f"⚠️  Failover Simulation Failed: {e}")
            return False

# Global Singleton Instance
cloud_security_gateway = CloudGatewaySecurity()
