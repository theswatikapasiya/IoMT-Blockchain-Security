"""
Layer 2 Automated Security Verification Test Suite
Performs validation checks on device registry, cryptographic signatures,
timestamp windows, MQTT topic limits, physiological boundaries,
behavioral drifts, device health, and decision engine routing.
"""

import os
import sys
import json
import unittest
import pandas as pd
import hmac
import hashlib
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from blockchain.zero_trust import ZeroTrustValidator, REGISTRY_PATH, AUDIT_LOG_PATH, QUARANTINE_PATH
from blockchain.data_generator import PatientDataGenerator

class TestLayer2Security(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        # Delete existing registry to start fresh
        if os.path.exists(REGISTRY_PATH):
            try:
                os.remove(REGISTRY_PATH)
            except:
                pass
        cls.validator = ZeroTrustValidator()
        cls.generator = PatientDataGenerator(seed=202)
        cls.generator.create_patient_dataset(5)
        cls.patients = cls.generator.get_all_patients()
        cls.patient_id = cls.patients[0]["id"]
        
    def test_01_trusted_packet(self):
        """Validate that normal packets from registered devices are accepted with high trust"""
        print("\n🔒 Running Layer 2 Test: Normal Trusted Ingestion...")
        packet = self.generator.update_patient_vitals(self.patient_id)
        
        # Enforce zero-trust validation
        decision, score, reasons = self.validator.validate_packet(packet, topic="iot/hospital/patients", is_tls=True)
        
        self.assertEqual(decision, "ACCEPT")
        self.assertGreaterEqual(score, 80.0)
        self.assertEqual(len(reasons), 0)
        print(f"   Device {packet['device_id']}: Decision={decision}, Score={score}%, Failures={reasons}")

    def test_02_unregistered_device(self):
        """Validate that unregistered rogue devices are rejected immediately"""
        print("\n🔒 Running Layer 2 Test: Unregistered Device Rejection...")
        packet = self.generator.update_patient_vitals(self.patient_id)
        packet["device_id"] = "ECG_ROGUE_9999" # Modifying to rogue device
        
        decision, score, reasons = self.validator.validate_packet(packet)
        self.assertEqual(decision, "REJECT")
        self.assertEqual(score, 0.0)
        self.assertIn("DEVICE_NOT_REGISTERED", reasons)
        print(f"   Rogue Ingestion: Decision={decision}, Reasons={reasons}")

    def test_03_signature_mismatch(self):
        """Validate that cryptographic signature mismatches result in quarantine routing"""
        print("\n🔒 Running Layer 2 Test: Cryptographic Signature Mismatch...")
        # Inject signature mismatch attack
        self.generator.inject_attack(self.patient_id, "sig_mismatch")
        packet = self.generator.update_patient_vitals(self.patient_id)
        
        decision, score, reasons = self.validator.validate_packet(packet)
        self.assertEqual(decision, "QUARANTINE")
        self.assertIn("CRYPTOGRAPHIC_SIGNATURE_MISMATCH", reasons)
        print(f"   Signature Mismatch: Decision={decision}, Reasons={reasons}")
        
        # Clear attack
        self.generator.inject_attack(self.patient_id, None)

    def test_04_invalid_token(self):
        """Validate that invalid API tokens trigger quarantine routing"""
        print("\n🔒 Running Layer 2 Test: Invalid API Token Gatekeeping...")
        self.generator.inject_attack(self.patient_id, "invalid_token")
        packet = self.generator.update_patient_vitals(self.patient_id)
        
        decision, score, reasons = self.validator.validate_packet(packet)
        self.assertEqual(decision, "QUARANTINE")
        self.assertIn("INVALID_API_TOKEN", reasons)
        print(f"   Token Mismatch: Decision={decision}, Reasons={reasons}")
        
        self.generator.inject_attack(self.patient_id, None)

    def test_05_timestamp_freshness(self):
        """Validate that stale backdated packets fail freshness validation"""
        print("\n🔒 Running Layer 2 Test: Timestamp Freshness Window...")
        self.generator.inject_attack(self.patient_id, "delay")
        packet = self.generator.update_patient_vitals(self.patient_id)
        
        # Delayed packets are sent over unencrypted channel in our simulation
        is_tls = packet["communication_metadata"]["encryption"] != "None"
        
        decision, score, reasons = self.validator.validate_packet(
            packet, topic="iot/hospital/patients", is_tls=is_tls
        )
        self.assertEqual(decision, "QUARANTINE")
        self.assertIn("TIMESTAMP_EXCEEDS_FRESHNESS_WINDOW", reasons)
        self.assertIn("UNENCRYPTED_COMMUNICATION_CHANNEL", reasons)
        print(f"   Stale Channel Packet: Decision={decision}, Reasons={reasons}")
        
        self.generator.inject_attack(self.patient_id, None)

    def test_06_replay_duplicates(self):
        """Validate that exact packets replayed (same timestamp) are isolated in quarantine"""
        print("\n🔒 Running Layer 2 Test: Packet Replay Detection...")
        # Inject replay attack (first update gets normal, second replays it)
        self.generator.inject_attack(self.patient_id, "replay")
        
        # Normal packet
        packet1 = self.generator.update_patient_vitals(self.patient_id)
        self.validator.validate_packet(packet1)
        
        # Replayed duplicate
        packet2 = self.generator.update_patient_vitals(self.patient_id)
        decision, score, reasons = self.validator.validate_packet(packet2)
        
        self.assertEqual(decision, "QUARANTINE")
        self.assertTrue(
            "DUPLICATE_TIMESTAMP_DETECTED" in reasons or "CHRONOLOGICAL_SEQUENCE_VIOLATION_OR_REPLAY" in reasons,
            "Replay detection failed"
        )
        print(f"   Replay Duplicate: Decision={decision}, Reasons={reasons}")
        
        self.generator.inject_attack(self.patient_id, None)

    def test_07_physiological_bounds(self):
        """Validate that impossible physiological parameters are blocked"""
        print("\n🔒 Running Layer 2 Test: Physiological Range bounds...")
        self.generator.inject_attack(self.patient_id, "spoofing")
        packet = self.generator.update_patient_vitals(self.patient_id)
        
        decision, score, reasons = self.validator.validate_packet(packet)
        
        self.assertEqual(decision, "QUARANTINE")
        self.assertIn("HR_OUT_OF_PHYSIOLOGICAL_BOUNDS", reasons)
        self.assertIn("TEMP_OUT_OF_PHYSIOLOGICAL_BOUNDS", reasons)
        print(f"   Physiological Outliers: Decision={decision}, Reasons={reasons}")
        
        self.generator.inject_attack(self.patient_id, None)

    def test_08_behavioral_jump(self):
        """Validate that sudden vital jumps for an active patient are flagged/rejected"""
        print("\n🔒 Running Layer 2 Test: Behavioral Consistency transitions...")
        # First send normal packet
        packet1 = self.generator.update_patient_vitals(self.patient_id)
        self.validator.validate_packet(packet1)
        
        # Modify next packet to have an abrupt HR jump from baseline (e.g., HR = 180 when baseline is 70)
        packet2 = self.generator.update_patient_vitals(self.patient_id)
        packet2["hr"] = 185
        
        # Signature will mismatch if we modify HR but don't re-sign,
        # but to test behavioral consistency cleanly, we sign it manually using registry key
        dev_key = self.validator.device_registry[packet2["device_id"]]["auth_key"]
        payload_str = f"{packet2['patient_id']}|{packet2['hr']}|{packet2['bp']}|{packet2['temp']}|{packet2['timestamp']}"
        packet2["packet_signature"] = hmac.new(dev_key.encode(), payload_str.encode(), hashlib.sha256).hexdigest()
        
        decision, score, reasons = self.validator.validate_packet(packet2)
        self.assertIn("HR_ABRUPT_BEHAVIORAL_JUMP", reasons)
        print(f"   Anomalous Vital Jump: Decision={decision}, Score={score}%, Reasons={reasons}")

    def test_09_device_health_quarantine(self):
        """Validate that repeating warnings degrade trust score and flag the device for maintenance"""
        print("\n🔒 Running Layer 2 Test: Device Health & Warnings Accumulation...")
        p_id = self.patients[2]["id"]
        dev_id = self.patients[2]["device_id"]
        
        # Reset device registry state
        self.validator.device_registry[dev_id]["recent_failures"] = 0
        self.validator.device_registry[dev_id]["status"] = "Active"
        
        # Inject 4 physiological warnings to trigger malfunction isolation
        dev_key = self.validator.device_registry[dev_id]["auth_key"]
        for i in range(4):
            packet = self.generator.update_patient_vitals(p_id)
            packet["hr"] = 250 # Out of bounds, triggers physiological warning on every step
            # Re-sign to pass cryptographic checks
            payload_str = f"{packet['patient_id']}|{packet['hr']}|{packet['bp']}|{packet['temp']}|{packet['timestamp']}"
            packet["packet_signature"] = hmac.new(dev_key.encode(), payload_str.encode(), hashlib.sha256).hexdigest()
            
            decision, score, reasons = self.validator.validate_packet(packet)
            
        # Verify status transitions
        updated_dev = self.validator.device_registry[dev_id]
        self.assertEqual(updated_dev["status"], "Maintenance Required")
        self.assertTrue(updated_dev["recent_failures"] >= 3)
        self.assertIn("HARDWARE_MALFUNCTION_DECLARED", reasons)
        print(f"   Device Status: ID={dev_id}, Status={updated_dev['status']}, Reasons={reasons}")

    def test_10_forensic_logging(self):
        """Validate that all validation decisions are written to security logs"""
        print("\n🔒 Running Layer 2 Test: Security Audit Logging & Compliance...")
        self.assertTrue(os.path.exists(AUDIT_LOG_PATH))
        self.assertTrue(os.path.exists(QUARANTINE_PATH))
        
        with open(AUDIT_LOG_PATH, "r") as f:
            audit_logs = json.load(f)
        self.assertGreater(len(audit_logs), 0)
        
        # Check last log structure
        last_log = audit_logs[-1]
        self.assertIn("timestamp", last_log)
        self.assertIn("device_id", last_log)
        self.assertIn("decision", last_log)
        self.assertIn("trust_score", last_log)
        self.assertIn("rejection_reasons", last_log)
        print(f"   Log Entry verified. Total logs: {len(audit_logs)}. Last Decision: {last_log['decision']} for {last_log['device_id']}")

if __name__ == "__main__":
    unittest.main()
