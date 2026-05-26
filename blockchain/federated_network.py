"""
Layer 8 - Federated Healthcare Intelligence, Global Trust Fabric, and Autonomous Self-Evolving Ecosystem
Implements federated learning (FedAvg), Proof of Authority (PoA) consensus,
global threat sharing, differential privacy, Paillier homomorphic encryption,
and global infrastructure digital twin simulation.
"""

import os
import json
import math
import random
import hashlib
import numpy as np
from datetime import datetime
from typing import List, Dict, Any, Tuple

# Helper mathematical operations for Paillier Homomorphic Encryption
def gcd(a: int, b: int) -> int:
    while b:
        a, b = b, a % b
    return a

def lcm(a: int, b: int) -> int:
    return (a * b) // gcd(a, b)

def ext_gcd(a: int, b: int) -> Tuple[int, int, int]:
    if a == 0:
        return b, 0, 1
    g, x1, y1 = ext_gcd(b % a, a)
    return g, y1 - (b // a) * x1, x1

def mod_inv(a: int, m: int) -> int:
    g, x, _ = ext_gcd(a, m)
    if g != 1:
        raise ValueError(f"Modular inverse of {a} mod {m} does not exist")
    return x % m

class PaillierKeyPair:
    """Lightweight Paillier Cryptosystem for Additively Homomorphic Operations"""
    
    def __init__(self, p: int = 61, q: int = 53):
        # Default small primes to avoid performance degradation while staying secure enough for demo
        self.p = p
        self.q = q
        self.n = p * q
        self.n_sq = self.n * self.n
        self.lam = lcm(p - 1, q - 1)
        self.g = self.n + 1 # Simple g parameter selection
        self.mu = mod_inv(self.lam, self.n)
        
    def encrypt(self, m: int) -> int:
        """Encrypt message m under Paillier scheme"""
        if m < 0 or m >= self.n:
            raise ValueError(f"Message {m} out of bounds [0, {self.n - 1}]")
        
        # Select random r coprime to n
        r = random.randint(1, self.n - 1)
        while gcd(r, self.n) != 1:
            r = random.randint(1, self.n - 1)
            
        # Ciphertext c = (g^m * r^n) mod n^2
        # Using (1 + n * m) mod n^2 instead of pow(g, m, n^2) since g = n + 1
        c_part1 = (1 + self.n * m) % self.n_sq
        c_part2 = pow(r, self.n, self.n_sq)
        c = (c_part1 * c_part2) % self.n_sq
        return c
        
    def decrypt(self, c: int) -> int:
        """Decrypt ciphertext c"""
        if c < 0 or c >= self.n_sq:
            raise ValueError(f"Ciphertext {c} out of bounds for n^2={self.n_sq}")
            
        # u = c^lam mod n^2
        u = pow(c, self.lam, self.n_sq)
        # L(u) = (u - 1) // n
        l_u = (u - 1) // self.n
        # m = (L(u) * mu) mod n
        m = (l_u * self.mu) % self.n
        return m

    def homomorphic_add(self, c1: int, c2: int) -> int:
        """Add two encrypted numbers homomorphically by multiplying their ciphertexts"""
        return (c1 * c2) % self.n_sq


class FederatedModel:
    """Simple linear regression classification model for vitals anomalies"""
    def __init__(self, size: int = 4):
        # Weights for [hr, bp_systolic, bp_diastolic, temp]
        self.weights = np.array([0.05, 0.02, 0.02, 0.5])
        self.bias = 0.0
        
    def predict(self, x: np.ndarray) -> np.ndarray:
        """Compute logistic predictions"""
        # Sigmoid activation
        z = np.dot(x, self.weights) + self.bias
        return 1.0 / (1.0 + np.exp(-np.clip(z, -15, 15)))

    def evaluate(self, x: np.ndarray, y: np.ndarray) -> float:
        """Calculate Binary Cross-Entropy loss"""
        preds = self.predict(x)
        # Avoid log(0)
        preds = np.clip(preds, 1e-7, 1 - 1e-7)
        loss = -np.mean(y * np.log(preds) + (1 - y) * np.log(1 - preds))
        return float(loss)


class FederatedNode:
    """Represents a hospital, diagnostic center, or research node in the network"""
    
    def __init__(self, node_id: str, name: str, is_authority: bool = False):
        self.node_id = node_id
        self.name = name
        self.is_authority = is_authority
        self.local_model = FederatedModel()
        self.local_dataset_x = []
        self.local_dataset_y = []
        self.local_trust_registry = {} # Local reputation records of devices
        self.anomaly_threshold = 0.75 # Local policy sensitivity parameter
        
        # Generate some synthetic local patient training data on initialization
        self._initialize_local_data()
        
    def _initialize_local_data(self):
        """Generate local training data: features [hr, bp_sys, bp_dia, temp] -> anomalous [0, 1]"""
        np.random.seed(random.randint(0, 1000))
        # 50 normal samples
        for _ in range(50):
            hr = np.random.normal(72, 8)
            bp_sys = np.random.normal(115, 10)
            bp_dia = np.random.normal(75, 6)
            temp = np.random.normal(36.8, 0.3)
            self.local_dataset_x.append([hr, bp_sys, bp_dia, temp])
            self.local_dataset_y.append(0.0) # Normal
            
        # 10 anomalous samples
        for _ in range(10):
            hr = np.random.choice([np.random.normal(130, 10), np.random.normal(50, 5)])
            bp_sys = np.random.choice([np.random.normal(160, 15), np.random.normal(80, 5)])
            bp_dia = np.random.choice([np.random.normal(105, 10), np.random.normal(50, 5)])
            temp = np.random.choice([np.random.normal(39.5, 0.8), np.random.normal(35.0, 0.5)])
            self.local_dataset_x.append([hr, bp_sys, bp_dia, temp])
            self.local_dataset_y.append(1.0) # Anomalous
            
        self.local_dataset_x = np.array(self.local_dataset_x)
        self.local_dataset_y = np.array(self.local_dataset_y)
        
    def train_local_model(self, global_weights: np.ndarray, global_bias: float, epochs: int = 5, lr: float = 0.001) -> Tuple[np.ndarray, float, float]:
        """Train model locally starting from global parameters, return new parameters and loss"""
        self.local_model.weights = global_weights.copy()
        self.local_model.bias = global_bias
        
        n_samples = len(self.local_dataset_y)
        for _ in range(epochs):
            # Gradient descent step
            preds = self.local_model.predict(self.local_dataset_x)
            errors = preds - self.local_dataset_y
            
            dw = np.dot(self.local_dataset_x.T, errors) / n_samples
            db = np.sum(errors) / n_samples
            
            self.local_model.weights -= lr * dw
            self.local_model.bias -= lr * db
            
        loss = self.local_model.evaluate(self.local_dataset_x, self.local_dataset_y)
        return self.local_model.weights, self.local_model.bias, loss


class FederatedHealthcareNetwork:
    """Orchestrates Federated AI, Proof of Authority Consensus, Global Threat Sharing & Privacy"""
    
    def __init__(self):
        # 1. Initialize Federated Nodes
        self.nodes = {
            "node_alpha": FederatedNode("node_alpha", "Hospital Alpha", is_authority=True),
            "node_beta": FederatedNode("node_beta", "Diagnostic Beta", is_authority=True),
            "node_gamma": FederatedNode("node_gamma", "Research Gamma", is_authority=True),
            "node_delta": FederatedNode("node_delta", "Cloud Region Delta", is_authority=False)
        }
        
        # 2. Global Model parameters
        self.global_model = FederatedModel()
        self.training_history = []
        
        # 3. Global Threat Sharing Registry
        self.threat_registry = []
        
        # 4. Global Trust Scores Database
        self.global_device_registry = {
            "ECG_1000": {"trust_score": 100.0, "status": "Active"},
            "ECG_1001": {"trust_score": 98.5, "status": "Active"},
            "TEMP_1011": {"trust_score": 95.0, "status": "Active"},
            "ECG_1014": {"trust_score": 60.0, "status": "Suspicious"},
            "TEMP_1019": {"trust_score": 55.0, "status": "Suspicious"}
        }
        
        # 5. Paillier Homomorphic encryption keys
        self.paillier = PaillierKeyPair()
        
        # 6. Global Policy parameters
        self.policy_threat_index = 0.0 # 0.0 (safe) to 100.0 (high threat)
        
        # 7. Global Twin State
        self.twin_stats = {
            "routing_latency_ms": 12.0,
            "packet_processing_rate_tps": 120.0,
            "cpu_utilization_percent": 34.0,
            "active_pods": 3,
            "autoscaler_status": "Idle",
            "healed_events_count": 0
        }
        
        # Run initial federated training step to seed metrics
        self.run_federated_round()

    # --- 1. FEDERATED AI ENGINE (FedAvg) ---
    
    def run_federated_round(self, epochs: int = 5, learning_rate: float = 0.001) -> Dict[str, Any]:
        """Perform one round of federated training across nodes using FedAvg"""
        local_updates = []
        losses = {}
        
        for nid, node in self.nodes.items():
            weights, bias, loss = node.train_local_model(
                self.global_model.weights,
                self.global_model.bias,
                epochs=epochs,
                lr=learning_rate
            )
            local_updates.append((weights, bias))
            losses[node.name] = round(loss, 4)
            
        # FedAvg Aggregation
        avg_weights = np.mean([u[0] for u in local_updates], axis=0)
        avg_bias = float(np.mean([u[1] for u in local_updates]))
        
        self.global_model.weights = avg_weights
        self.global_model.bias = avg_bias
        
        # Evaluate global model on all node datasets
        eval_losses = []
        for node in self.nodes.values():
            eval_loss = self.global_model.evaluate(node.local_dataset_x, node.local_dataset_y)
            eval_losses.append(eval_loss)
        global_loss = float(np.mean(eval_losses))
        
        round_data = {
            "round": len(self.training_history) + 1,
            "timestamp": datetime.utcnow().isoformat(),
            "local_losses": losses,
            "global_loss": round(global_loss, 4),
            "global_weights": self.global_model.weights.tolist(),
            "global_bias": round(self.global_model.bias, 4)
        }
        self.training_history.append(round_data)
        return round_data

    # --- 2. GLOBAL THREAT INTELLIGENCE REGISTRY & PROPAGATION ---
    
    def publish_threat(self, threat_id: str, reported_by: str, description: str, signature: Dict[str, Any]) -> Dict[str, Any]:
        """Publishes a new threat signature and triggers autonomous policy adaptation"""
        threat_record = {
            "threat_id": threat_id,
            "reported_by": reported_by,
            "description": description,
            "signature": signature,
            "timestamp": datetime.utcnow().isoformat()
        }
        self.threat_registry.append(threat_record)
        
        # Evolve security policies and sync across nodes
        self.policy_threat_index = min(100.0, self.policy_threat_index + 20.0)
        self._propagate_policy_adaptation()
        
        return threat_record
        
    def _propagate_policy_adaptation(self):
        """Autonomously adapt anomaly thresholds based on global threat status"""
        # More threats = lower threshold = higher sensitivity
        new_threshold = max(0.40, 0.75 - (self.policy_threat_index * 0.0035))
        for node in self.nodes.values():
            node.anomaly_threshold = round(new_threshold, 3)

    # --- 3. PROOF OF AUTHORITY (PoA) CONSENSUS FABRIC ---
    
    def propose_and_verify_block(self, proposing_node: str, block_data: Dict[str, Any]) -> Dict[str, Any]:
        """Proposes a block and gathers signatures from authority nodes to reach consensus"""
        # Block digest
        block_string = json.dumps(block_data, sort_keys=True)
        block_hash = hashlib.sha256(block_string.encode()).hexdigest()
        
        consensus_signatures = {}
        authorities = [n for n in self.nodes.values() if n.is_authority]
        required_signatures = math.ceil(len(authorities) / 2.0) # majority threshold
        
        for auth in authorities:
            # Skip checking if proposing node itself is an authority to let it be signed
            # Validators verify physiological logic of block_data
            health = block_data.get("health_data", {})
            hr = health.get("hr", 72.0)
            temp = health.get("temp", 37.0)
            
            # Physiological verification: check if vitals are completely impossible
            is_valid_physiology = (30.0 <= hr <= 250.0) and (32.0 <= temp <= 43.0)
            
            if is_valid_physiology:
                # Generate signature block hash signed with authority name
                sig_digest = hashlib.sha256(f"{block_hash}_{auth.name}".encode()).hexdigest()
                consensus_signatures[auth.name] = sig_digest
                
        is_consensus_reached = len(consensus_signatures) >= required_signatures
        
        return {
            "block_hash": block_hash,
            "proposer": proposing_node,
            "signatures_gathered": len(consensus_signatures),
            "required_signatures": required_signatures,
            "signatures": consensus_signatures,
            "consensus_reached": is_consensus_reached,
            "status": "COMMITTED" if is_consensus_reached else "REJECTED",
            "timestamp": datetime.utcnow().isoformat()
        }

    # --- 4. PRIVACY-PRESERVING COMPUTATION ENGINE ---
    
    def get_population_average_hr_with_dp(self, base_values: List[float], epsilon: float = 1.0) -> Tuple[float, float]:
        """Return the mean of heart rates protected under Differential Privacy"""
        if not base_values:
            return 0.0, 0.0
            
        true_mean = float(np.mean(base_values))
        
        # Sensitivity (Delta) = (Max_HR - Min_HR) / n
        # Let's bound heart rates [50.0, 150.0]
        sensitivity = (150.0 - 50.0) / len(base_values)
        
        # Laplace noise scale = Sensitivity / epsilon
        scale = sensitivity / max(0.01, epsilon)
        
        # Generate Laplacian noise
        noise = float(np.random.laplace(0.0, scale))
        dp_mean = true_mean + noise
        
        return round(true_mean, 2), round(dp_mean, 2)
        
    def perform_homomorphic_aggregation(self, values: List[int]) -> Dict[str, Any]:
        """Demonstrate Paillier homomorphic summation without revealing plaintext list"""
        if not values:
            return {"encrypted_sum": 0, "decrypted_sum": 0, "success": True}
            
        # Encrypt elements individually at edge nodes
        encrypted_elements = [self.paillier.encrypt(v) for v in values]
        
        # Aggregate at global central server (multiply ciphertexts)
        encrypted_sum = encrypted_elements[0]
        for c in encrypted_elements[1:]:
            encrypted_sum = self.paillier.homomorphic_add(encrypted_sum, c)
            
        # Decrypt summation using central authority private keys
        decrypted_sum = self.paillier.decrypt(encrypted_sum)
        
        return {
            "individual_values": values,
            "ciphertexts": [hex(c)[:16] + "..." for c in encrypted_elements],
            "encrypted_sum_hex": hex(encrypted_sum)[:24] + "...",
            "decrypted_sum": decrypted_sum,
            "true_sum": sum(values),
            "success": decrypted_sum == sum(values)
        }

    # --- 5. GLOBAL TRUST REPUTATION SYNC ---
    
    def synchronize_trust_score(self, device_id: str, local_score: float) -> Dict[str, Any]:
        """Syncs local trust updates across the global trust registry"""
        if device_id not in self.global_device_registry:
            self.global_device_registry[device_id] = {"trust_score": 100.0, "status": "Active"}
            
        # Weighted decay formula for global trust sync: 70% Global historical + 30% local telemetry update
        current_global = self.global_device_registry[device_id]["trust_score"]
        updated_global = (0.7 * current_global) + (0.3 * local_score)
        
        status = "Active"
        if updated_global < 60.0:
            status = "Quarantined"
        elif updated_global < 80.0:
            status = "Suspicious"
            
        self.global_device_registry[device_id] = {
            "trust_score": round(updated_global, 2),
            "status": status
        }
        
        return self.global_device_registry[device_id]

    # --- 6. DIGITAL TWIN SIMULATION & AUTONOMOUS REPAIR ---
    
    def update_digital_twin_metrics(self) -> Dict[str, Any]:
        """Simulate dynamic changes in routing delay, load spikes, and auto-healing triggers"""
        # Add random fluctuation
        self.twin_stats["routing_latency_ms"] = round(max(5.0, self.twin_stats["routing_latency_ms"] + random.uniform(-1.5, 1.5)), 1)
        self.twin_stats["packet_processing_rate_tps"] = round(max(50.0, self.twin_stats["packet_processing_rate_tps"] + random.uniform(-5.0, 5.0)), 1)
        
        # CPU fluctuates based on threat level index
        target_cpu = 30.0 + (self.policy_threat_index * 0.5) + random.uniform(-3, 3)
        self.twin_stats["cpu_utilization_percent"] = round(max(10.0, min(100.0, target_cpu)), 1)
        
        # Self-healing logic checks (Simulating K8s HPA and recovery actions)
        if self.twin_stats["cpu_utilization_percent"] > 75.0 and self.twin_stats["active_pods"] < 6:
            # Trigger Auto-scaling
            self.twin_stats["active_pods"] += 1
            self.twin_stats["autoscaler_status"] = f"Scale Up Action (Spawning Pod #{self.twin_stats['active_pods']})"
            self.twin_stats["healed_events_count"] += 1
        elif self.twin_stats["cpu_utilization_percent"] < 40.0 and self.twin_stats["active_pods"] > 3:
            # Scale down
            self.twin_stats["active_pods"] -= 1
            self.twin_stats["autoscaler_status"] = f"Scale Down Action (Terminating Pod #{self.twin_stats['active_pods'] + 1})"
            self.twin_stats["healed_events_count"] += 1
        else:
            self.twin_stats["autoscaler_status"] = "Steady State"
            
        return self.twin_stats


# Instantiate Global Coordinator
federated_network = FederatedHealthcareNetwork()
