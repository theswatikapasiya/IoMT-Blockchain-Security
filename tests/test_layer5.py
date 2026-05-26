"""
Layer 5 Automated Secure API Gateway and Cloud Transmission Verification Test Suite
Tests rate limiting, JWT authentication, RBAC restrictions, sanitization checks,
AES encryption, cloud integrity audits, backups failover recovery, and K8s configuration existence.
"""

import os
import sys
import json
import hashlib
import unittest
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from blockchain.cloud_gateway import cloud_security_gateway, DATA_LAKE_PATH, BACKUP_PATH, AUDIT_LOG_PATH
from app import app


class TestLayer5CloudGatewaySecurity(unittest.TestCase):
    
    def setUp(self):
        # Reset threat metrics and databases for clean isolation
        cloud_security_gateway.threat_metrics = {
            "total_requests": 0,
            "blocked_malformed_requests": 0,
            "rate_limit_violations": 0,
            "authentication_failures": 0,
            "unauthorized_attempts": 0,
            "blocked_injections": 0,
            "total_backups_created": 0,
            "failover_occurrences": 0
        }
        cloud_security_gateway.request_logs.clear()
        
        # Clean local databases
        for path in [DATA_LAKE_PATH, BACKUP_PATH]:
            with open(path, "w") as f:
                json.dump({}, f)
        with open(AUDIT_LOG_PATH, "w") as f:
            json.dump([], f)
            
        # Flask test client
        self.client = app.test_client()

    def test_01_api_gateway_rate_limiting(self):
        """Verify API Gateway rate limiting checks block excessive requests"""
        print("\n☁️  Running Layer 5 Test: Rate Limiting & Gateway...")
        ip = "192.168.1.50"
        
        # Send 5 requests (within limit)
        for _ in range(5):
            self.assertFalse(cloud_security_gateway.is_rate_limited(ip))
            
        # 6th request must be rate limited
        self.assertTrue(cloud_security_gateway.is_rate_limited(ip))
        self.assertEqual(cloud_security_gateway.threat_metrics["rate_limit_violations"], 1)
        print("   Rate limiting gatekeeper successfully blocked excessive requests.")

    def test_02_request_authentication_jwt(self):
        """Verify JSON Web Token authentication generation and signature verification"""
        print("\n☁️  Running Layer 5 Test: JWT Authentication...")
        
        # Generate token
        token = cloud_security_gateway.generate_jwt_token("dr_swati", "Doctor")
        self.assertIsNotNone(token)
        
        # Verify valid token
        success, decoded = cloud_security_gateway.verify_jwt_token(token)
        self.assertTrue(success)
        self.assertEqual(decoded["sub"], "dr_swati")
        self.assertEqual(decoded["role"], "Doctor")
        
        # Verify invalid token
        bad_token = token + "corrupted_signature"
        success_bad, decoded_bad = cloud_security_gateway.verify_jwt_token(bad_token)
        self.assertFalse(success_bad)
        self.assertIn("error", decoded_bad)
        self.assertEqual(cloud_security_gateway.threat_metrics["authentication_failures"], 1)
        print("   JWT Token generation and signature verification checks passed.")

    def test_03_role_based_access_control_rbac(self):
        """Verify Role-Based Access Control policies boundaries"""
        print("\n☁️  Running Layer 5 Test: Role-Based Access Control (RBAC)...")
        
        # Action requires Doctor or Admin
        allowed_roles = ["Doctor", "Admin"]
        
        # Doctor allowed
        self.assertTrue(cloud_security_gateway.verify_rbac("Doctor", allowed_roles))
        
        # Admin allowed
        self.assertTrue(cloud_security_gateway.verify_rbac("Admin", allowed_roles))
        
        # Nurse denied
        self.assertFalse(cloud_security_gateway.verify_rbac("Nurse", allowed_roles))
        self.assertEqual(cloud_security_gateway.threat_metrics["unauthorized_attempts"], 1)
        
        # Researcher denied
        self.assertFalse(cloud_security_gateway.verify_rbac("Researcher", allowed_roles))
        self.assertEqual(cloud_security_gateway.threat_metrics["unauthorized_attempts"], 2)
        print("   RBAC policies correctly restricted unauthorized role mappings.")

    def test_04_request_validation_and_sanitization(self):
        """Verify request sanitization blocks SQL injection, XSS, and command injections"""
        print("\n☁️  Running Layer 5 Test: Validation & Sanitization...")
        
        # Clean payload
        clean_payload = {"patient_id": "PS101", "name": "Varun Patel", "hr": 82}
        is_clean, reason = cloud_security_gateway.validate_and_sanitize(clean_payload)
        self.assertTrue(is_clean)
        self.assertEqual(reason, "CLEAN")
        
        # SQL Injection payload
        sql_payload = {"patient_id": "PS101", "name": "Varun; DROP TABLE patients;--", "hr": 82}
        is_clean, reason = cloud_security_gateway.validate_and_sanitize(sql_payload)
        self.assertFalse(is_clean)
        self.assertIn("SQL_INJECTION", reason)
        
        # Command Injection payload
        cmd_payload = {"patient_id": "PS101", "name": "Varun", "shell_command": "system('rm -rf /')"}
        is_clean, reason = cloud_security_gateway.validate_and_sanitize(cmd_payload)
        self.assertFalse(is_clean)
        self.assertIn("COMMAND_INJECTION", reason)
        
        # XSS payload
        xss_payload = {"patient_id": "PS101", "name": "<script>alert('XSS')</script>"}
        is_clean, reason = cloud_security_gateway.validate_and_sanitize(xss_payload)
        self.assertFalse(is_clean)
        self.assertIn("XSS_ATTACK", reason)
        
        self.assertEqual(cloud_security_gateway.threat_metrics["blocked_injections"], 3)
        print("   Validation engine blocked SQL injection, command execution, and script injections.")

    def test_05_payload_encryption_aes_cbc(self):
        """Verify AES-256 payload encryption and decryption matching"""
        print("\n☁️  Running Layer 5 Test: AES-256 End-to-End Encryption...")
        
        vitals_payload = '{"hr": 78, "bp": "120/80", "temp": 36.8}'
        
        # Encrypt
        encrypted = cloud_security_gateway.encrypt_payload(vitals_payload)
        self.assertNotEqual(vitals_payload, encrypted)
        
        # Decrypt
        decrypted = cloud_security_gateway.decrypt_payload(encrypted)
        self.assertEqual(vitals_payload, decrypted)
        print("   AES-256-CBC payload encryption and decryption verified matching.")

    def test_06_cloud_integrity_revalidation(self):
        """Verify cloud integrity revalidation rejects packets modified in transit"""
        print("\n☁️  Running Layer 5 Test: Cloud Integrity Verification...")
        
        # Mined block info
        patient_id = "PS1000"
        health_data = {"hr": 72, "bp": "118/76", "temp": 36.7}
        prev_hash = "0" * 64
        block_index = 1
        nonce = 10
        
        block_recalc_data = {
            "index": block_index,
            "timestamp": "2026-05-26T20:00:00Z",
            "patient_id": patient_id,
            "health_data": health_data,
            "previous_hash": prev_hash,
            "nonce": nonce,
            "validation_status": "ACCEPT",
            "trust_score": 100.0,
            "label": "NORMAL"
        }
        
        # Calculate correct hash
        block_string = json.dumps(block_recalc_data, sort_keys=True)
        correct_hash = hashlib.sha256(block_string.encode()).hexdigest()
        
        # Transmit with correct hash
        token = cloud_security_gateway.generate_jwt_token("dr_swati", "Doctor")
        headers = {"Authorization": f"Bearer {token}"}
        
        payload = {
            "patient_id": patient_id,
            "hash": correct_hash,
            "previous_hash": prev_hash,
            "index": block_index,
            "nonce": nonce,
            "timestamp": "2026-05-26T20:00:00Z",
            "health_data": health_data,
            "trust_score": 100.0,
            "validation_status": "ACCEPT",
            "label": "NORMAL"
        }
        
        # Valid transmission
        response = self.client.post("/api/cloud/transmit", json=payload, headers=headers)
        self.assertEqual(response.status_code, 200)
        
        # Tampered transmission: Heart Rate changed from 72 to 140
        payload["health_data"]["hr"] = 140
        response_tampered = self.client.post("/api/cloud/transmit", json=payload, headers=headers)
        
        # Should be rejected with 400 Bad Request
        self.assertEqual(response_tampered.status_code, 400)
        self.assertIn("hash mismatch", response_tampered.get_json()["error"].lower())
        print("   Cloud engine successfully rejected tampered block payloads.")

    def test_07_secure_storage_and_partitioning(self):
        """Verify secure cloud storage and patient partition segmentation"""
        print("\n☁️  Running Layer 5 Test: Secure Storage & Segmentation...")
        
        # Ingest records for patient 1 and 2
        p1 = "PS_PAT_1"
        p2 = "PS_PAT_2"
        
        encrypted_1 = cloud_security_gateway.encrypt_payload('{"hr": 70}')
        encrypted_2 = cloud_security_gateway.encrypt_payload('{"hr": 80}')
        
        meta = {"block_index": 1}
        
        cloud_security_gateway.save_to_cloud_lake(p1, encrypted_1, meta)
        cloud_security_gateway.save_to_cloud_lake(p2, encrypted_2, meta)
        
        # Check partitions
        p1_records = cloud_security_gateway.read_from_cloud_lake(p1)
        p2_records = cloud_security_gateway.read_from_cloud_lake(p2)
        
        self.assertEqual(len(p1_records), 1)
        self.assertEqual(len(p2_records), 1)
        self.assertEqual(p1_records[0]["encrypted_data"], encrypted_1)
        self.assertEqual(p2_records[0]["encrypted_data"], encrypted_2)
        print("   Data lake successfully partitioned and segmented records by Patient ID.")

    def test_08_disaster_recovery_failover(self):
        """Verify backup snapshot creation and stand-by failover disaster recovery"""
        print("\n☁️  Running Layer 5 Test: Disaster Recovery Failover...")
        
        # Save a record
        cloud_security_gateway.save_to_cloud_lake("PS101", "encrypted_data_string", {"index": 1})
        self.assertEqual(cloud_security_gateway.threat_metrics["total_backups_created"], 1)
        
        # Corrupt main file (simulation)
        with open(DATA_LAKE_PATH, "w") as f:
            f.write("{ CORRUPTED_DATA_NULL }")
            
        # Verify it is corrupted
        with self.assertRaises(Exception):
            with open(DATA_LAKE_PATH, "r") as f:
                json.load(f)
                
        # Trigger Standby Recovery Failover
        success = cloud_security_gateway.simulate_failover()
        self.assertTrue(success)
        self.assertEqual(cloud_security_gateway.threat_metrics["failover_occurrences"], 1)
        
        # Verify main database restored and readable
        with open(DATA_LAKE_PATH, "r") as f:
            restored_data = json.load(f)
        self.assertIn("PS101", restored_data)
        print("   Backup snapshot replication and automatic database failover verified.")

    def test_09_monitoring_observability(self):
        """Verify logging of security events and threat observability counters"""
        print("\n☁️  Running Layer 5 Test: Compliance Audit & Monitoring...")
        
        cloud_security_gateway.log_cloud_event("dr_swati", "Doctor", "READ", "PATIENT_PS1000", "SUCCESS")
        
        with open(AUDIT_LOG_PATH, "r") as f:
            logs = json.load(f)
            
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0]["username"], "dr_swati")
        self.assertEqual(logs[0]["action"], "READ")
        self.assertEqual(logs[0]["outcome"], "SUCCESS")
        print("   Cloud audit logs recorded actors, actions, and outcomes for compliance.")

    def test_10_k8s_docker_specs_existence(self):
        """Verify Dockerfile and Kubernetes deployment manifest configurations exist"""
        print("\n☁️  Running Layer 5 Test: Container & K8s Specs...")
        
        self.assertTrue(os.path.exists("Dockerfile"))
        self.assertTrue(os.path.exists("k8s-deployment.yaml"))
        
        # Check liveness probes mapping inside YAML
        with open("k8s-deployment.yaml", "r") as f:
            content = f.read()
            
        self.assertIn("livenessProbe", content)
        self.assertIn("replicas: 3", content)
        self.assertIn("HorizontalPodAutoscaler", content)
        print("   Dockerfile and k8s-deployment.yaml (with HPA and health checks) confirmed.")


if __name__ == "__main__":
    unittest.main()
