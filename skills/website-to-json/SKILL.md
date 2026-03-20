---
name: website-to-json
description: Extract structured JSON from websites, directories, and docs pages with presets and confidence scoring.
env_requirements:
  - CLAW0X_API_KEY
  - SKILL_SHARED_SECRET
required_env:
  - CLAW0X_API_KEY
allowed_tools:
  - web
  - fetch
---

# Website to JSON

Convert a public webpage into normalized JSON for downstream agents.

## When to Use
- The user provides a URL and needs structured data
- The page is an article, product page, company directory, or docs page
- The agent needs confidence-aware extraction
- The output must be stable and machine-readable

## Presets
- `article`
- `product_page`
- `company_directory`
- `docs_page`

## Input
| Parameter | Type | Required | Description |
|---|---|---:|---|
| url | string | yes | Public webpage URL |
| preset | string | yes | One of the supported presets |
| locale | string | no | Optional locale hint |
| include_sources | boolean | no | Include source URLs in output |

## Prerequisites
- The URL must be publicly reachable
- Set `CLAW0X_API_KEY` for Claw0x marketplace authorization
- The self-hosted endpoint should be configured with `SKILL_SHARED_SECRET` if you want token protection
- Pages that require login, cookies, or anti-bot bypass are out of scope for v1

## Required Environment Variables
- `CLAW0X_API_KEY` (required)
- `SKILL_SHARED_SECRET` (optional)

## Output
| Field | Type | Description |
|---|---|---|
| preset | string | Applied preset |
| url | string | Final resolved URL |
| data | object | Normalized extracted JSON |
| confidence | number | Overall confidence from 0 to 1 |
| source_coverage | number | Percentage of expected fields found |
| field_confidence | object | Confidence per field |
| source_urls | array | URLs used as evidence |
| warnings | array | Extraction caveats |

## Behavior
- Prefer stable, normalized fields
- Return empty or missing values rather than guessing
- Use confidence scoring to reflect uncertainty
- Keep the skill stateless

## API Call Example
```bash
curl -X POST https://your-endpoint.example.com \
  -H "Authorization: Bearer $CLAW0X_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "preset": "company_directory",
    "include_sources": true
  }'
```

## Example
```json
{
  "url": "https://example.com",
  "preset": "company_directory",
  "data": {
    "company_name": "Example Inc",
    "domain": "example.com",
    "industry": "Software",
    "hq_country": "United States"
  },
  "confidence": 0.91,
  "source_coverage": 0.78
}
```
