# Problem Statement: AI-Powered Photo Retrieval Discovery Engine

## 1. Context & Role

You are a **Product Manager on the Core Experience team at Google Photos**.

Google Photos serves as the primary photo and video repository for millions of users worldwide. Over years of usage, users accumulate **thousands of photos, videos, screenshots, documents, and other visual memories**. The sheer volume of stored media creates a fundamental retrieval challenge that grows worse over time.

---

## 2. The Core Problem

### 2.1 The Retrieval Gap

While Google Photos offers robust search capabilities for users who **know exactly what they are looking for**, the experience breaks down significantly when a user's **memory is incomplete or imprecise**.

Users frequently find themselves in a situation where:

- They **know** a specific photo exists in their library.
- They **cannot** remember critical metadata — when it was taken, where it was taken, which album it belongs to, or the right keywords to search for it.

### 2.2 Real-World Examples

| Scenario | What the User Remembers | What the User Has Forgotten |
|---|---|---|
| *"That small café we went to during our Goa trip."* | A café, a trip to Goa, the visual scene | Exact date, location name, who was in the photo, album |
| *"The picture of the medicine I took when I was sick last year."* | A medicine, being sick, approximate timeframe ("last year") | Exact date, type of medicine, where the photo was taken |

These examples illustrate a broader pattern: **human memory of visual information is associative, emotional, and contextual** — not keyword-based. The current retrieval experience, however, is optimized for precise, keyword-driven queries.

---

## 3. Strategic Goal

> **Increase the percentage of users who successfully retrieve a photo they remember but cannot precisely describe when they start searching.**

### 3.1 What This Is

- An effort to bridge the gap between **how humans remember** visual content and **how the system enables retrieval**.
- A focus on improving retrieval for **fuzzy, incomplete, or contextual recall** scenarios.

### 3.2 What This Is NOT

- This is **not** a general search improvement initiative.
- This is **not** about improving results for well-formed, precise queries.
- This is **not** about search ranking, indexing speed, or general relevance tuning.

---

## 4. Scope of the Challenge

The task is threefold:

1. **Understand** how people remember old visual information — what cognitive patterns, cues, and mental models do users rely on when trying to find a past photo?
2. **Identify** where the existing retrieval experience breaks down — at what points in the user journey does the system fail to bridge the gap between fuzzy memory and successful retrieval?
3. **Discover** an opportunity that can meaningfully improve successful retrieval — grounded in real user evidence, not assumptions.

---

## 5. Deliverable: AI-Powered Discovery Engine

### 5.1 Objective

Before proposing any solution, build an **AI-powered system** that analyzes user feedback and conversations about photo retrieval **at scale**. The engine should surface evidence-backed insights that inform product decisions.

### 5.2 Permitted Technology Stack

You may use any combination of the following (or equivalent AI-native tools):

| Category | Tools |
|---|---|
| **LLMs / Assistants** | Claude, GPTs, Perplexity |
| **Agents & Workflows** | AI Agents, n8n, Zapier |
| **Retrieval & Synthesis** | RAG (Retrieval-Augmented Generation) |
| **Custom** | Any AI-native stack of your choice |

### 5.3 Data Sources

The discovery engine should analyze **publicly available sources**, including but not limited to:

- 📱 **Google Play Store reviews** — Android user feedback on Google Photos
- 🍎 **App Store reviews** — iOS user feedback on Google Photos
- 💬 **Reddit discussions** — Subreddits like r/googlephotos, r/Android, r/photography, etc.
- 🗣️ **Google Photos Community / Support forums** — Official Google support threads
- 🐦 **Social media conversations** — Twitter/X, Mastodon, Bluesky, etc.
- 📺 **YouTube comments** — On Google Photos tutorials, reviews, and feature walkthroughs
- 🌐 **Other forums & public discussions** — Quora, Stack Exchange, tech blogs, etc.

---

## 6. Guiding Research Questions

The discovery engine should help uncover insights around (but not limited to) the following dimensions:

### 6.1 Retrieval Struggles
> *What kinds of old photos do users struggle to retrieve?*
- Are there specific categories (travel, medical, receipts, screenshots, people, events) that are disproportionately hard to find?

### 6.2 Memory Cues
> *What information do people actually remember about a photo?*
- Do users recall emotions, people, places, time-of-day, seasons, events, or visual attributes?

### 6.3 Memory Gaps
> *What information have they forgotten?*
- Which metadata dimensions (date, location, faces, text) are most commonly lost over time?

### 6.4 Search Behavior
> *How do users formulate searches when their memory is incomplete?*
- Do users try natural language queries, browse timelines, scroll through albums, or ask others for help?

---

## 7. Expected Depth of Analysis

> [!IMPORTANT]
> The discovery workflow should go **beyond** summarizing reviews or performing basic sentiment analysis.

The engine must enable you to:

- **Identify** distinct retrieval problem archetypes from real user evidence.
- **Compare** different retrieval breakdowns and opportunity areas.
- **Quantify** (where possible) the frequency and severity of each problem type.
- **Prioritize** opportunities based on user impact, frequency, and feasibility.

The output should serve as a **rigorous, evidence-grounded foundation** for any subsequent product recommendations or solution proposals.

---

## 8. Success Criteria

| Dimension | What Good Looks Like |
|---|---|
| **Coverage** | Multiple data sources analyzed, not just one or two |
| **Depth** | Insights go beyond surface-level sentiment into behavioral patterns |
| **Evidence** | Every insight is grounded in real user quotes or data points |
| **Structure** | Retrieval problems are categorized, compared, and prioritized |
| **Actionability** | Findings clearly point toward specific opportunity areas for product improvement |

---

*This problem statement serves as the foundational brief for the Google Photos Retrieval Discovery Engine project.*
