# API Request/Response Examples

Complete examples of all API endpoints with sample payloads and responses.

## 1. Upload Datasets

### Request: Upload Given Database

```bash
curl -X POST "http://127.0.0.1:8000/upload/given" \
  -F "file=@given.csv"
```

### Response: 200 OK

```json
{
  "message": "given uploaded successfully",
  "rows": 100,
  "columns": ["id", "name", "university_name", "email"]
}
```

---

### Request: Upload Master Database 1

```bash
curl -X POST "http://127.0.0.1:8000/upload/master1" \
  -F "file=@master1.csv"
```

### Response: 200 OK

```json
{
  "message": "master1 uploaded successfully",
  "rows": 95,
  "columns": ["id", "name", "university_name", "email"]
}
```

---

### Request: Upload Master Database 2

```bash
curl -X POST "http://127.0.0.1:8000/upload/master2" \
  -F "file=@master2.csv"
```

### Response: 200 OK

```json
{
  "message": "master2 uploaded successfully",
  "rows": 92,
  "columns": ["id", "name", "university_name", "email"]
}
```

---

## 2. Check Upload Status

### Request

```bash
curl -X GET "http://127.0.0.1:8000/status"
```

### Response: 200 OK

```json
{
  "given": true,
  "master1": true,
  "master2": true,
  "given_rows": 100,
  "master1_rows": 95,
  "master2_rows": 92
}
```

**Note:** All three must be `true` before comparing.

---

## 3. Compare Datasets

### Request: Compare with Master1 as Preferred

```bash
curl -X POST "http://127.0.0.1:8000/compare?preferred_master=master1" \
  -H "Content-Type: application/json"
```

### Response: 200 OK

```json
{
  "anomalies": [
    {
      "record_id": 5,
      "field": "university_name",
      "given_value": "University of Texxas",
      "correct_value": "University of Texas",
      "reason": "Spelling error",
      "recommendations": ["University of Texas at Austin", "Texas A&M University"]
    },
    {
      "record_id": 12,
      "field": "email",
      "given_value": "john@exmple.com",
      "correct_value": "john@example.com",
      "reason": "Typo in domain",
      "recommendations": ["john@example.org"]
    },
    {
      "record_id": 8,
      "field": "name",
      "given_value": "john smith",
      "correct_value": "John Smith",
      "reason": "Capitalization inconsistency",
      "recommendations": ["John Smith", "JOHN SMITH"]
    },
    {
      "record_id": 23,
      "field": "university_name",
      "given_value": "MIT",
      "correct_value": "Massachusetts Institute of Technology",
      "reason": "Abbreviation vs full name",
      "recommendations": [
        "Massachusetts Institute of Technology",
        "M.I.T."
      ]
    }
  ]
}
```

### Error Response: Missing Dataset

```bash
curl -X POST "http://127.0.0.1:8000/compare?preferred_master=master1"
```

**Response: 400 Bad Request**

```json
{
  "detail": "Upload given, master1, and master2 first"
}
```

### Error Response: Invalid Master

```bash
curl -X POST "http://127.0.0.1:8000/compare?preferred_master=master3"
```

**Response: 400 Bad Request**

```json
{
  "detail": "preferred_master must be 'master1' or 'master2'"
}
```

---

## 4. Apply Fixes

### Request

```bash
curl -X POST "http://127.0.0.1:8000/apply-fixes" \
  -H "Content-Type: application/json" \
  -d '[
    {
      "record_id": 5,
      "field": "university_name",
      "correct_value": "University of Texas"
    },
    {
      "record_id": 12,
      "field": "email",
      "correct_value": "john@example.com"
    },
    {
      "record_id": 8,
      "field": "name",
      "correct_value": "John Smith"
    }
  ]'
```

### Response: 200 OK

```json
{
  "message": "Successfully applied 3 fixes",
  "updated_rows": 3
}
```

### Error Response: No Given Dataset

```bash
curl -X POST "http://127.0.0.1:8000/apply-fixes" \
  -H "Content-Type: application/json" \
  -d '[]'
```

**Response: 400 Bad Request**

```json
{
  "detail": "No given dataset found"
}
```

### Error Response: Empty Fixes

```bash
curl -X POST "http://127.0.0.1:8000/apply-fixes" \
  -H "Content-Type: application/json" \
  -d '[]'
```

**Response: 400 Bad Request**

```json
{
  "detail": "No fixes provided"
}
```

---

## 5. Retrieve Dataset

### Request: Get Given Dataset

```bash
curl -X GET "http://127.0.0.1:8000/data/given"
```

### Response: 200 OK

```json
[
  {
    "id": 1,
    "name": "John Smith",
    "university_name": "University of Texas",
    "email": "john@example.com"
  },
  {
    "id": 2,
    "name": "Jane Doe",
    "university_name": "MIT",
    "email": "jane@mit.edu"
  },
  {
    "id": 3,
    "name": "Bob Johnson",
    "university_name": "Stanford University",
    "email": "bob@stanford.edu"
  }
]
```

### Error Response: Dataset Not Found

```bash
curl -X GET "http://127.0.0.1:8000/data/invalid"
```

**Response: 404 Not Found**

```json
{
  "detail": "Dataset 'invalid' not found"
}
```

---

## 6. Root Endpoint

### Request

```bash
curl -X GET "http://127.0.0.1:8000/"
```

### Response: 200 OK

```json
{
  "message": "Backend is running"
}
```

---

## Frontend Integration Examples

### JavaScript/TypeScript (Using Axios)

```typescript
import { dataDiscrepancyAPI } from '@/lib/api';

// Upload a file
const uploadResponse = await dataDiscrepancyAPI.uploadFile(file, 'given');
console.log(`Uploaded ${uploadResponse.rows} records`);

// Check status
const status = await dataDiscrepancyAPI.getStatus();
if (status.given && status.master1 && status.master2) {
  console.log('All datasets uploaded!');
}

// Compare datasets
const comparisonResult = await dataDiscrepancyAPI.compareDatasets('master1');
console.log(`Found ${comparisonResult.anomalies.length} anomalies`);

// Apply fixes
const fixes = [
  { record_id: 5, field: "university_name", correct_value: "University of Texas" },
  { record_id: 12, field: "email", correct_value: "john@example.com" }
];
const applyResult = await dataDiscrepancyAPI.applyFixes(fixes);
console.log(applyResult.message);

// Get dataset
const givenData = await dataDiscrepancyAPI.getData('given');
console.log(`Current dataset has ${givenData.length} records`);
```

---

## Complete Workflow Example

### Step 1: Check Initial Status

```bash
curl "http://127.0.0.1:8000/status"
# Response: {"given": false, "master1": false, "master2": false, ...}
```

### Step 2: Upload All Three Files

```bash
curl -X POST "http://127.0.0.1:8000/upload/given" -F "file=@given.csv"
curl -X POST "http://127.0.0.1:8000/upload/master1" -F "file=@master1.csv"
curl -X POST "http://127.0.0.1:8000/upload/master2" -F "file=@master2.csv"
```

### Step 3: Verify Upload Status

```bash
curl "http://127.0.0.1:8000/status"
# Response: {"given": true, "master1": true, "master2": true, ...}
```

### Step 4: Run Comparison

```bash
curl -X POST "http://127.0.0.1:8000/compare?preferred_master=master1"
# Returns: {"anomalies": [...]}
```

### Step 5: Apply Selected Fixes

```bash
curl -X POST "http://127.0.0.1:8000/apply-fixes" \
  -H "Content-Type: application/json" \
  -d '[{"record_id": 5, "field": "university_name", "correct_value": "University of Texas"}]'
# Returns: {"message": "Successfully applied 1 fixes", "updated_rows": 1}
```

### Step 6: Verify Changes

```bash
curl "http://127.0.0.1:8000/data/given"
# Returns updated dataset with corrections applied
```

---

## Response Status Codes

| Code | Meaning | Example |
|------|---------|---------|
| 200 | Success | Upload successful, data retrieved |
| 400 | Bad Request | Missing file, invalid parameters |
| 404 | Not Found | Dataset doesn't exist |
| 500 | Server Error | LLM API failure, JSON parsing error |

---

## Rate Limiting Considerations

- No built-in rate limiting currently
- Gemini API has quota limits (check Google Cloud Console)
- Large datasets (>10MB) may timeout - consider pagination

---

## Data Type Handling

- All values are stored as strings by default
- Pandas infers types from CSV
- Recommendations are returned as string arrays
- Record IDs should be numeric or ordinal

---

**Note:** All responses use `Content-Type: application/json`
