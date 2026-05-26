# API Reference - IoMT Hospital Monitoring System

## Base URL
```
http://localhost:5000/api
```

## Authentication
This prototype uses no authentication. In production, implement JWT/OAuth2.

---

## Endpoints

### 1. Patient Management

#### GET /patients
**Description**: Retrieve all patients with statistics

**Response**:
```json
{
  "patients": [
    {
      "id": "PS1000",
      "name": "Arjun Sharma",
      "age": 45,
      "gender": "M",
      "bloodGroup": "O+",
      "contact": "+91-9876543210",
      "email": "patient@hospital.in",
      "hr": 78,
      "bp": "120/80",
      "temp": 36.8,
      "condition": "Normal",
      "assignedDoctor": "Dr. Sharma"
    }
  ],
  "statistics": {
    "total_patients": 20,
    "average_hr": 85.2,
    "average_bp_sys": 122.5,
    "average_temp": 37.1,
    "critical_patients": 2,
    "observation_patients": 5
  }
}
```

---

#### GET /patient/{id}
**Description**: Get single patient with blockchain and history

**URL Parameters**:
- `id` (string, required): Patient ID (e.g., "PS1000")

**Response**:
```json
{
  "patient": {
    "id": "PS1000",
    "name": "Arjun Sharma",
    "age": 45,
    ...
  },
  "blockchain": [
    {
      "index": 0,
      "timestamp": "2026-05-04T10:30:00.000000",
      "patient_id": "PS1000",
      "health_data": {"hr": 78, "bp": "120/80", "temp": 36.8},
      "previous_hash": "0",
      "nonce": 45,
      "hash": "000a3f5b2c8d..."
    },
    {
      "index": 1,
      "timestamp": "2026-05-04T10:35:00.000000",
      "patient_id": "PS1000",
      "health_data": {"hr": 80, "bp": "121/81", "temp": 36.9},
      "previous_hash": "000a3f5b2c8d...",
      "nonce": 78,
      "hash": "0005c8e1f2a9..."
    }
  ],
  "tampering": {
    "is_tampered": false,
    "first_break_point": -1,
    "total_blocks": 2,
    "tampered_blocks": []
  },
  "history": []
}
```

---

#### POST /update_patient
**Description**: Update patient vitals and record to blockchain

**Request Body**:
```json
{
  "id": "PS1000",
  "hr": 85,
  "bp": "125/82",
  "temp": 37.2
}
```

**Response**:
```json
{
  "success": true,
  "patient": {
    "id": "PS1000",
    "name": "Arjun Sharma",
    "hr": 85,
    "bp": "125/82",
    "temp": 37.2,
    "lastUpdated": "2026-05-04T10:40:00.000000"
  },
  "tampering_detected": {
    "patient_id": "PS1000",
    "is_tampered": false,
    "timestamp": "2026-05-04T10:40:00.000000",
    "changes": {}
  },
  "blockchain_valid": true
}
```

---

#### POST /add_patient
**Description**: Add new patient to system

**Request Body**:
```json
{
  "name": "Priya Singh",
  "age": 32,
  "gender": "F",
  "bloodGroup": "AB+",
  "contact": "+91-9876543211",
  "email": "priya@hospital.in",
  "condition": "Normal",
  "hr": 72,
  "bp": "118/76",
  "temp": 36.8
}
```

**Response**:
```json
{
  "success": true,
  "patient": {
    "id": "PS1020",
    "name": "Priya Singh",
    "age": 32,
    ...
  }
}
```

---

### 2. Blockchain Management

#### GET /blockchain/verify
**Description**: Verify integrity of all patient blockchains

**Response**:
```json
{
  "PS1000": {
    "is_tampered": false,
    "first_break_point": -1,
    "total_blocks": 15,
    "tampered_blocks": []
  },
  "PS1001": {
    "is_tampered": true,
    "first_break_point": 5,
    "total_blocks": 12,
    "tampered_blocks": [5, 6, 7, 8, 9, 10, 11, 12]
  }
}
```

**Interpretation**:
- `is_tampered`: true if any block's hash doesn't match
- `first_break_point`: Index where chain breaks (first invalid block)
- `tampered_blocks`: Array of all affected blocks after break point

---

#### GET /blockchain/patient/{id}
**Description**: Get blockchain for specific patient

**URL Parameters**:
- `id` (string, required): Patient ID

**Response**:
```json
{
  "chain": [
    {
      "index": 0,
      "timestamp": "2026-05-04T10:00:00.000000",
      "patient_id": "PS1000",
      "health_data": {"hr": 78, "bp": "120/80", "temp": 36.8},
      "previous_hash": "0",
      "nonce": 45,
      "hash": "000a3f5b2c8d..."
    }
  ],
  "tampering": {
    "is_tampered": false,
    "first_break_point": -1,
    "total_blocks": 5,
    "tampered_blocks": []
  }
}
```

---

### 3. Tamper Detection

#### GET /tamper/history
**Description**: Get all tampering incidents across system

**Response**:
```json
{
  "logs": [
    {
      "patient_id": "PS1003",
      "is_tampered": true,
      "timestamp": "2026-05-04T11:25:00.000000",
      "changes": {
        "hr": {"old": 78, "new": 150},
        "temp": {"old": 36.8, "new": 41.2}
      },
      "severity": "CRITICAL"
    }
  ]
}
```

---

#### GET /tamper/patient/{id}
**Description**: Get tampering history for specific patient

**URL Parameters**:
- `id` (string, required): Patient ID

**Response**:
```json
{
  "history": [
    {
      "patient_id": "PS1000",
      "is_tampered": false,
      "timestamp": "2026-05-04T10:40:00.000000",
      "changes": {},
      "severity": "NONE"
    }
  ],
  "report": {
    "patient_id": "PS1000",
    "total_tampering_incidents": 0,
    "incidents": [],
    "report_generated": "2026-05-04T12:00:00.000000"
  }
}
```

---

#### POST /anomalies/check
**Description**: Check vital signs for medical anomalies

**Request Body**:
```json
{
  "patient_id": "PS1000",
  "hr": 45,
  "bp": "90/55",
  "temp": 34.2
}
```

**Response**:
```json
{
  "has_anomaly": true,
  "anomalies": [
    {
      "type": "hr_anomaly",
      "value": 45,
      "range": [40, 180],
      "severity": "MEDIUM"
    },
    {
      "type": "bp_sys_anomaly",
      "value": 90,
      "range": [70, 180],
      "severity": "HIGH"
    },
    {
      "type": "temp_anomaly",
      "value": 34.2,
      "range": [34, 42],
      "severity": "HIGH"
    }
  ],
  "patient_id": "PS1000",
  "timestamp": "2026-05-04T12:00:00.000000"
}
```

---

### 4. Analytics & Statistics

#### GET /statistics
**Description**: Get system-wide statistics and blockchain integrity

**Response**:
```json
{
  "total_patients": 20,
  "average_hr": 85.2,
  "average_bp_sys": 122.5,
  "average_temp": 37.1,
  "critical_patients": 2,
  "observation_patients": 5,
  "blockchain_status": {
    "total_blockchains": 20,
    "tampered_records": 0,
    "integrity_score": 100.0
  }
}
```

---

## Error Responses

### 404 - Not Found
```json
{
  "error": "Patient not found"
}
```

### 400 - Bad Request
```json
{
  "error": "Invalid patient data"
}
```

### 500 - Server Error
```json
{
  "error": "Server error"
}
```

---

## Status Codes
| Code | Meaning                      |
|------|------------------------------|
| 200  | Success                      |
| 201  | Created                      |
| 400  | Bad Request                  |
| 404  | Not Found                    |
| 500  | Internal Server Error        |

---

## Data Types

### Patient Object
```typescript
{
  id: string              // "PS1000" format
  name: string            // Full name
  age: number             // 18-85
  gender: string          // "M" or "F"
  bloodGroup: string      // "O+", "A-", etc.
  contact: string         // Phone number
  email: string           // Email address
  admissionDate: string   // ISO timestamp
  condition: string       // "Normal", "Observation", "Critical"
  assignedDoctor: string  // Doctor name
  hr: number              // Heart rate (bpm)
  bp: string              // "120/80" format
  temp: number            // Temperature (°C)
  lastUpdated: string     // ISO timestamp
  history: array          // Previous records
}
```

### Block Object
```typescript
{
  index: number                    // Block position in chain
  timestamp: string                // ISO datetime
  patient_id: string               // "PS1000"
  health_data: {
    hr: number
    bp: string
    temp: number
  }
  previous_hash: string            // SHA-256 of previous block
  nonce: number                    // Proof of work value
  hash: string                     // SHA-256 of current block
}
```

---

## Rate Limiting
- No rate limiting in prototype
- Production should implement: 100 req/min per IP

## Caching
- Dashboard auto-refreshes every 3 seconds
- Implement Redis caching for production

## Version
- API Version: 1.0.0
- Last Updated: May 4, 2026

