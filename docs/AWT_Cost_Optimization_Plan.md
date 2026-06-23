# AWT Cost Optimization Strategy

## Current Status (as of 2026.02.20)

### AI API Cost Status
| Item | Yesterday (DOM only) | Today (Observation-based) |
|------|---------------------|----------------------------|
| Request count | 18 | 43 |
| Token usage | 427,638 | 571,663 |
| Cost | $0.07 | $0.64 |
| Cost per request | $0.004 | $0.015 |

- After introducing observation-based crawling, cost per request increased ~4x
- Cause: AI receives observation data per element (screenshot OCR, changed text, DOM changes)
- Current model: OpenAI GPT (AWT_SERVICE_AI_MODEL setting)

### Revenue vs Cost Simulation

| User count | Daily cost | Monthly cost | Monthly revenue (Pro $29) | Margin | Margin rate |
|------------|------------|--------------|--------------------------|--------|-------------|
| 1 person (dev) | $0.64 | $19.2 | - | - | - |
| 10 people | $6.4 | $192 | $290 | $98 | 34% |
| 50 people | $32 | $960 | $1,450 | $490 | 34% |
| 100 people | $64 | $1,920 | $2,900 | $980 | 34% |
| 500 people | $320 | $9,600 | $14,500 | $4,900 | 34% |

> ⚠️ Above simulation based on current dev testing (includes multiple repeated tests per day)
> Actual users expected to test 1-2 times per day, much lower cost

### Expected Cost per Real User

| User count | Daily cost (1-2 times) | Monthly cost | Monthly revenue | Margin | Margin rate |
|------------|------------------------|--------------|-----------------|--------|-------------|
| 10 people | $0.30 | $9 | $290 | $281 | 97% |
| 50 people | $1.50 | $45 | $1,450 | $1,405 | 97% |
| 100 people | $3.00 | $90 | $2,900 | $2,810 | 97% |
| 500 people | $15.00 | $450 | $14,500 | $14,050 | 97% |

---

## Cost Optimization Strategy

### Stage 1: Caching (Expected cost reduction: 50-70%)
- **Scan result caching**: Reuse previous observation data when rescanning same URL
  - Cache validity: 24 hours (adjustable based on site change frequency)
  - User can "force rescan" to ignore cache
- **Scenario template caching**: Reuse scenario patterns for same site type
- Implementation difficulty: ★★☆ (Add cache table to DB)

### Stage 2: Observation Data Compression (Expected cost reduction: 30-40%)
- Send **only changed parts** to AI instead of full OCR text
- Send **only text summary** to AI instead of screenshot images
- Remove unnecessary attributes from DOM data (style, class, etc.)
- Compress observation data into structured JSON
- Implementation difficulty: ★★☆

### Stage 3: Model Switching (Expected cost reduction: 40-60%)
- **Simple tasks** → GPT-4o-mini ($0.15/1M input tokens)
  - Site type determination
  - Basic test plan generation
  - Scenario validation
- **Complex tasks** → GPT-4o ($2.50/1M input tokens)
  - Complex business scenario generation
  - Fix Guide modification suggestions
  - GitHub Auto-fix PR code generation
- Implementation difficulty: ★☆☆ (Only change model parameter in API call)

### Stage 4: Plan-by-plan Limit Reinforcement
| Item | Free | Pro ($29) | Team ($99) |
|------|------|-----------|------------|
| Monthly tests | 5 times | 500 times | 2,000 times |
| Scan max_pages | 5 | 20 | 50 |
| Observation elements | 5 | 15 | 30 |
| AI retry | 0 times | 1 time | 3 times |
| Cache validity | 1 hour | 24 hours | 7 days |

### Stage 5: Self Model / Open Source LLM Review (Long-term)
- Process simple tasks with open source models like Llama 3, Mistral
- Run on local GPU or low-cost GPU cloud (RunPod, Vast.ai)
- Convert API cost to infrastructure cost (advantageous at scale)
- Review timing: 500+ monthly active users

---

## Implementation Priority

| Priority | Strategy | Reduction effect | Difficulty | Implementation timing |
|----------|----------|-------------------|-------------|----------------------|
| 1 | Caching | 50-70% | ★★☆ | Right after service stabilization |
| 2 | Model switching | 40-60% | ★☆☆ | Right after service stabilization |
| 3 | Data compression | 30-40% | ★★☆ | 10+ users |
| 4 | Plan limits | Cost control | ★☆☆ | Already partially applied |
| 5 | Self model | 80-90% | ★★★★ | 500+ users |

> 💡 Just caching + model switching can reduce current cost to 1/3~1/5
> Expected margin improvement: 34% → 80%+

---

## Cost Monitoring

(Continuing content would follow...)
