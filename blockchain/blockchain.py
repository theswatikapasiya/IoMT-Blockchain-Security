"""
Healthcare Blockchain Module
Implements a simplified but functional blockchain for patient health records
Features: Immutability, Tamper Detection, SHA-256 Hashing
"""

import hashlib
import json
from datetime import datetime
from typing import List, Dict, Any


class Block:
    """Represents a single block in the blockchain"""
    
    def __init__(self, patient_id: str, health_data: Dict[str, Any], 
                 previous_hash: str = "0", index: int = 0,
                 validation_status: str = "ACCEPT", trust_score: float = 100.0,
                 label: str = "NORMAL", timestamp: str = None):
        self.index = index
        self.timestamp = timestamp or datetime.utcnow().isoformat()
        self.patient_id = patient_id
        self.health_data = health_data  # {hr, bp, temp, timestamp}
        self.previous_hash = previous_hash
        self.nonce = 0
        self.validation_status = validation_status
        self.trust_score = trust_score
        self.label = label
        self.hash = self.calculate_hash()
    
    def calculate_hash(self) -> str:
        """Calculate SHA-256 hash of the block"""
        block_data = {
            "index": self.index,
            "timestamp": self.timestamp,
            "patient_id": self.patient_id,
            "health_data": self.health_data,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce,
            "validation_status": self.validation_status,
            "trust_score": self.trust_score,
            "label": self.label
        }
        block_string = json.dumps(block_data, sort_keys=True)
        return hashlib.sha256(block_string.encode()).hexdigest()
    
    def mine_block(self, difficulty: int = 2):
        """Proof of Work: Find nonce such that hash starts with difficulty zeros"""
        target = "0" * difficulty
        while self.hash[:difficulty] != target:
            self.nonce += 1
            self.hash = self.calculate_hash()
    
    def to_dict(self):
        """Convert block to dictionary"""
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "patient_id": self.patient_id,
            "health_data": self.health_data,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce,
            "validation_status": self.validation_status,
            "trust_score": self.trust_score,
            "label": self.label,
            "hash": self.hash
        }


class PatientBlockchain:
    """Manages blockchain for a single patient"""
    
    def __init__(self, patient_id: str):
        self.patient_id = patient_id
        self.chain: List[Block] = []
        self.difficulty = 2
        
        # Create genesis block
        genesis_block = Block(patient_id, {}, "0", 0)
        genesis_block.mine_block(self.difficulty)
        self.chain.append(genesis_block)
    
    def get_latest_block(self) -> Block:
        """Get the most recent block"""
        return self.chain[-1]
    
    def add_record(self, health_data: Dict[str, Any], validation_status: str = "ACCEPT",
                   trust_score: float = 100.0, label: str = "NORMAL") -> Block:
        """Add new health record to blockchain"""
        latest_block = self.get_latest_block()
        new_block = Block(
            patient_id=self.patient_id,
            health_data=health_data,
            previous_hash=latest_block.hash,
            index=len(self.chain),
            validation_status=validation_status,
            trust_score=trust_score,
            label=label,
            timestamp=health_data.get("timestamp") or datetime.utcnow().isoformat()
        )
        new_block.mine_block(self.difficulty)
        self.chain.append(new_block)
        return new_block
    
    def is_chain_valid(self) -> tuple[bool, int]:
        """
        Validate entire blockchain
        Returns: (is_valid, first_invalid_index)
        """
        if not self.chain:
            return True, -1
            
        # Verify genesis block (index 0)
        genesis = self.chain[0]
        if genesis.hash != genesis.calculate_hash():
            return False, 0
            
        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            previous_block = self.chain[i - 1]
            
            # Verify current block's hash
            if current_block.hash != current_block.calculate_hash():
                return False, i
            
            # Verify link to previous block
            if current_block.previous_hash != previous_block.hash:
                return False, i
            
            # Verify block index sequencing
            if current_block.index != i:
                return False, i
                
            # Verify transaction completeness (for non-genesis blocks)
            if not isinstance(current_block.health_data, dict) or not all(k in current_block.health_data for k in ["hr", "bp", "temp"]):
                return False, i
        
        return True, -1
    
    def detect_tampering(self) -> Dict[str, Any]:
        """
        Detect if any record has been tampered with
        Returns tampering info with affected indices
        """
        is_valid, invalid_index = self.is_chain_valid()
        
        return {
            "is_tampered": not is_valid,
            "first_break_point": invalid_index,
            "total_blocks": len(self.chain),
            "tampered_blocks": [] if is_valid else list(range(invalid_index, len(self.chain)))
        }
    
    def get_chain_snapshot(self) -> List[Dict]:
        """Get entire chain as list of dictionaries"""
        return [block.to_dict() for block in self.chain]
    
    def verify_integrity(self) -> bool:
        """Quick integrity check"""
        is_valid, _ = self.is_chain_valid()
        return is_valid


class BlockchainManager:
    """Manages blockchains for multiple patients"""
    
    def __init__(self):
        self.blockchains: Dict[str, PatientBlockchain] = {}
    
    def create_patient_blockchain(self, patient_id: str) -> PatientBlockchain:
        """Create new patient blockchain"""
        if patient_id not in self.blockchains:
            self.blockchains[patient_id] = PatientBlockchain(patient_id)
        return self.blockchains[patient_id]
    
    def record_health_data(self, patient_id: str, health_data: Dict[str, Any],
                           validation_status: str = None, trust_score: float = None,
                           label: str = None) -> Block:
        """Record health data for patient"""
        if patient_id not in self.blockchains:
            self.create_patient_blockchain(patient_id)
            
        # Ingestion guard & default values extraction
        if validation_status is None:
            validation_status = health_data.get("validation_status", "ACCEPT")
        if trust_score is None:
            trust_score = health_data.get("trust_score", 100.0)
        if label is None:
            label = health_data.get("label", "NORMAL")
            
        # Ingestion decision check
        if validation_status not in ["ACCEPT", "FLAG"]:
            raise ValueError(f"Intake Rejected: Ingestion of packet status '{validation_status}' is blocked.")
            
        clean_health_data = {
            "hr": health_data.get("hr"),
            "bp": health_data.get("bp"),
            "temp": health_data.get("temp"),
            "timestamp": health_data.get("timestamp") or datetime.utcnow().isoformat()
        }
        
        return self.blockchains[patient_id].add_record(
            health_data=clean_health_data,
            validation_status=validation_status,
            trust_score=trust_score,
            label=label
        )
    
    def add_record(self, patient_id: str, health_data: Dict[str, Any]) -> Block:
        """Alias for compatibility with background thread in app.py"""
        return self.record_health_data(patient_id, health_data)
    
    def verify_patient_integrity(self, patient_id: str) -> Dict[str, Any]:
        """Verify patient's blockchain integrity"""
        if patient_id not in self.blockchains:
            return {"error": "Patient not found", "is_tampered": False, "tampered_blocks": []}
        
        return self.blockchains[patient_id].detect_tampering()
    
    def get_patient_chain(self, patient_id: str) -> List[Dict]:
        """Get patient's entire blockchain"""
        if patient_id not in self.blockchains:
            return []
        
        return self.blockchains[patient_id].get_chain_snapshot()
    
    def verify_all_patients(self) -> Dict[str, Dict[str, Any]]:
        """Verify integrity of all patient blockchains"""
        results = {}
        for patient_id, blockchain in self.blockchains.items():
            results[patient_id] = blockchain.detect_tampering()
        return results
        
    def get_blockchain_health_metrics(self) -> Dict[str, Any]:
        """
        Calculate health and security monitoring metrics across all blockchains
        """
        total_blockchains = len(self.blockchains)
        total_blocks = 0
        tampered_blockchains = 0
        invalid_block_count = 0
        suspicious_blocks = 0
        
        for patient_id, bc in self.blockchains.items():
            chain_len = len(bc.chain)
            total_blocks += chain_len
            
            tamper_info = bc.detect_tampering()
            if tamper_info["is_tampered"]:
                tampered_blockchains += 1
                invalid_block_count += len(tamper_info["tampered_blocks"])
                
            for block in bc.chain:
                if block.index == 0:
                    continue
                    
                is_suspicious = False
                if getattr(block, "label", "NORMAL") != "NORMAL":
                    is_suspicious = True
                elif getattr(block, "validation_status", "ACCEPT") == "FLAG":
                    is_suspicious = True
                elif getattr(block, "trust_score", 100.0) < 80.0:
                    is_suspicious = True
                    
                if is_suspicious:
                    suspicious_blocks += 1
                    
        total_tx_blocks = max(1, total_blocks - total_blockchains)
        suspicious_rate = round((suspicious_blocks / total_tx_blocks) * 100, 2)
        health_score = round(((total_blockchains - tampered_blockchains) / max(1, total_blockchains)) * 100, 2)
        
        return {
            "total_blockchains": total_blockchains,
            "total_blocks": total_blocks,
            "tampered_blockchains": tampered_blockchains,
            "invalid_block_count": invalid_block_count,
            "suspicious_blocks": suspicious_blocks,
            "suspicious_transaction_rate_percent": suspicious_rate,
            "blockchain_health_score_percent": health_score
        }
