"""
Layer 4 Automated Blockchain Immutability and Consensus Validation Test Suite
Tests block creation, hash serialization, previous block linkages, proof of work,
tamper detection, consensus validation rules, and health metrics calculations.
"""

import os
import sys
import json
import unittest
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from blockchain.blockchain import Block, PatientBlockchain, BlockchainManager


class TestLayer4BlockchainConsensus(unittest.TestCase):
    
    def setUp(self):
        self.manager = BlockchainManager()
        self.patient_id = "PS101"
        self.bc = self.manager.create_patient_blockchain(self.patient_id)
        
    def test_01_block_creation_and_hash_enveloping(self):
        """Verify block creation and cryptographic hash enveloping of Layer 3 metrics"""
        print("\n🔗 Running Layer 4 Test: Block Hashing & Enveloping...")
        
        health_data = {"hr": 82, "bp": "120/80", "temp": 37.0}
        validation_status = "ACCEPT"
        trust_score = 95.5
        label = "NORMAL"
        
        block = Block(
            patient_id=self.patient_id,
            health_data=health_data,
            previous_hash="000abc",
            index=1,
            validation_status=validation_status,
            trust_score=trust_score,
            label=label
        )
        
        self.assertEqual(block.index, 1)
        self.assertEqual(block.validation_status, validation_status)
        self.assertEqual(block.trust_score, trust_score)
        self.assertEqual(block.label, label)
        
        # Verify hash changes if any Layer 3 metric is modified
        original_hash = block.hash
        
        block.trust_score = 90.0
        modified_hash = block.calculate_hash()
        self.assertNotEqual(original_hash, modified_hash)
        print("   Block serialization and metadata cryptographic hash validation successful.")

    def test_02_blockchain_sequential_linkage(self):
        """Verify sequential block linkages using previous_hash"""
        print("\n🔗 Running Layer 4 Test: Blockchain Sequential Linkage...")
        
        # Add a couple of telemetry blocks
        block1 = self.bc.add_record({"hr": 80, "bp": "120/80", "temp": 36.8}, "ACCEPT", 99.0, "NORMAL")
        block2 = self.bc.add_record({"hr": 85, "bp": "122/82", "temp": 37.0}, "FLAG", 78.0, "MINOR_ANOMALY")
        
        # Check chain lengths and sequence pointers
        self.assertEqual(len(self.bc.chain), 3)  # Genesis + Block 1 + Block 2
        self.assertEqual(block1.index, 1)
        self.assertEqual(block2.index, 2)
        
        self.assertEqual(block1.previous_hash, self.bc.chain[0].hash)
        self.assertEqual(block2.previous_hash, block1.hash)
        
        # Check initial chain validity
        is_valid, invalid_idx = self.bc.is_chain_valid()
        self.assertTrue(is_valid)
        self.assertEqual(invalid_idx, -1)
        print(f"   Linkage pointers verified. Chain length: {len(self.bc.chain)}")

    def test_03_immutability_and_tamper_detection(self):
        """Verify that modifying stored telemetry values invalidates the chain"""
        print("\n🔗 Running Layer 4 Test: Immutability & Tamper Detection...")
        
        self.bc.add_record({"hr": 78, "bp": "118/78", "temp": 36.9}, "ACCEPT", 99.0, "NORMAL")
        self.bc.add_record({"hr": 82, "bp": "120/80", "temp": 37.0}, "ACCEPT", 98.0, "NORMAL")
        
        # Initial validation passes
        self.assertTrue(self.bc.verify_integrity())
        
        # Attack Simulation: Modify HR of Block 1 from 78 to 150
        self.bc.chain[1].health_data["hr"] = 150
        
        # Chain should now be invalid
        is_valid, first_invalid_index = self.bc.is_chain_valid()
        self.assertFalse(is_valid)
        self.assertEqual(first_invalid_index, 1)  # Index 1 was tampered
        
        # Verify tampering detector returns correct details
        tamper_info = self.bc.detect_tampering()
        self.assertTrue(tamper_info["is_tampered"])
        self.assertEqual(tamper_info["first_break_point"], 1)
        self.assertIn(1, tamper_info["tampered_blocks"])
        self.assertIn(2, tamper_info["tampered_blocks"])  # Subsequent blocks are compromised
        print("   Silent telemetry modification caught! Chain validity failed at index 1.")

    def test_04_ingestion_guard_boundaries(self):
        """Verify that record ingestion guards block QUARANTINE or REJECT packets"""
        print("\n🔗 Running Layer 4 Test: Ingestion Guard Boundaries...")
        
        # Valid ingestions
        block1 = self.manager.record_health_data(self.patient_id, {"hr": 72, "bp": "120/80", "temp": 36.6}, "ACCEPT", 95.0, "NORMAL")
        self.assertIsNotNone(block1)
        
        block2 = self.manager.record_health_data(self.patient_id, {"hr": 95, "bp": "125/85", "temp": 37.2}, "FLAG", 75.0, "MINOR_ANOMALY")
        self.assertIsNotNone(block2)
        
        # Invalid ingestion (REJECT decision) should trigger ValueError
        with self.assertRaises(ValueError):
            self.manager.record_health_data(self.patient_id, {"hr": 150, "bp": "180/110", "temp": 39.5}, "REJECT", 10.0, "MALICIOUS_PACKET")
            
        # Invalid ingestion (QUARANTINE decision) should trigger ValueError
        with self.assertRaises(ValueError):
            self.manager.record_health_data(self.patient_id, {"hr": 80, "bp": "120/80", "temp": 36.6}, "QUARANTINE", 45.0, "REPLAY_ATTACK")
        print("   Intake Gatekeeper correctly blocked quarantined/rejected records.")

    def test_05_blockchain_health_metrics_calculations(self):
        """Verify health monitoring metrics are calculated correctly"""
        print("\n🔗 Running Layer 4 Test: Blockchain Health Metrics...")
        
        # Setup multiple patient blockchains
        p1 = "PS_PATIENT_1"
        p2 = "PS_PATIENT_2"
        
        self.manager.create_patient_blockchain(p1)
        self.manager.create_patient_blockchain(p2)
        
        # Add records to patient 1 (1 genesis + 2 records)
        self.manager.record_health_data(p1, {"hr": 70, "bp": "115/75", "temp": 36.5}, "ACCEPT", 98.0, "NORMAL")
        self.manager.record_health_data(p1, {"hr": 74, "bp": "118/76", "temp": 36.6}, "ACCEPT", 99.0, "NORMAL")
        
        # Add records to patient 2 (1 genesis + 1 record)
        self.manager.record_health_data(p2, {"hr": 82, "bp": "122/82", "temp": 37.1}, "FLAG", 79.0, "MINOR_ANOMALY")
        
        # Inspect normal stats
        metrics = self.manager.get_blockchain_health_metrics()
        
        # There are 3 blockchains: self.patient_id (has genesis), p1 (genesis+2), p2 (genesis+1)
        self.assertEqual(metrics["total_blockchains"], 3)
        self.assertEqual(metrics["tampered_blockchains"], 0)
        self.assertEqual(metrics["blockchain_health_score_percent"], 100.0)
        
        # Simulate tampering on patient 1
        self.manager.blockchains[p1].chain[1].health_data["hr"] = 180
        
        tampered_metrics = self.manager.get_blockchain_health_metrics()
        self.assertEqual(tampered_metrics["tampered_blockchains"], 1)
        self.assertEqual(tampered_metrics["invalid_block_count"], 2)  # Block 1 and Block 2 of patient 1
        self.assertLess(tampered_metrics["blockchain_health_score_percent"], 100.0)
        print(f"   Health Score (Healthy): {metrics['blockchain_health_score_percent']}%")
        print(f"   Health Score (Tampered): {tampered_metrics['blockchain_health_score_percent']}%")
        print("   Blockchain health metrics validation completed successfully.")


if __name__ == "__main__":
    unittest.main()
