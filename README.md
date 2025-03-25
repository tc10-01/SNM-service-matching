# Neuro-Symbolic Service Matching (SNM)

Neuro-Symbolic Service Matching (SNM) is an innovative project that improves service matching by integrating Large Language Models (LLMs) with symbolic reasoning. Our approach addresses the challenge that service-provider websites often describe their offerings vaguely or inconsistently. By combining the flexibility of LLM-based extraction with the rigor of ontology-driven validation, SNM produces reliable, structured data for accurate service recommendations.

## Overview

Traditional service matching methods struggle with inconsistent and vague web content. SNM leverages a neuro-symbolic approach to extract key details from provider websites, validate and structure them using a domain-specific ontology, and finally generate personalized service recommendations. The system is designed with two main workflows: one for selecting the optimal model(s) for extraction and one for processing the data and generating recommendations.

## Features

### Automated Data Collection:
- **Web Scraping**: Gather raw text from provider websites.
- **API-based Collection**: Directly fetch structured data from service-provider APIs.

### Data Consolidation:
- Merge raw text with structured API data while preserving the original (raw) content for fallback and reference.

### Model Selection:
- Evaluate multiple candidate models (e.g., DeepSeek R1, ChatGPT, and others) using a feature-based and strength/limitations comparison.
- Select the most appropriate model(s) based on performance metrics like speed, chain-of-thought reasoning, cost, and domain suitability.

### Neurosymbolic Processing:
- Use LLM-based extraction that is "aware" of a pre-loaded ontology to produce structured service data (e.g., organization name, location, operating hours, eligibility conditions).
- Apply a multi-model confidence aggregator (e.g., voting) to refine extraction accuracy.
- Perform ontology instantiating and data reconciliation to ensure that the extracted information aligns with domain constraints.

### Service Recommendation:
- Combine the final structured service data with client profiles (demographic info, location, needs) to generate tailored recommendations.
- Include an optional human-in-the-loop review to validate or refine the outputs.

### Data Freshness Strategy:
- Employ scheduled, on-demand, and incremental update strategies to keep service data up to date.

## Architecture

The project is split into two main workflows:

### Model Selection Workflow

#### Candidate Model Comparison:
- **Input**: List of candidate models (e.g., DeepSeek R1, ChatGPT, domain-specific LLMs).
- **Output**: Two matrices:
  - Feature-Based Comparison Matrix: Evaluates chain-of-thought reasoning, speed, open-source status, cost, etc.
  - Strength-Limitations Comparison Matrix: Details strengths and weaknesses of each candidate.

#### Model Selection:
- **Input**: The comparison matrices.
- **Output**: A final list of chosen model(s) to be used in the service recommender workflow.

### Service Recommender Workflow

#### Information Collection:
- **Gather URLs**: Assemble a curated list of provider URLs before scraping.
- **API-based Info Collection**: Directly retrieve structured data via service-provider APIs.
- **Web Scraping**: Crawl the curated URLs to collect raw text (with HTML stripped, but preserving original content).

#### Data Consolidation:
- **Input**:
  - Raw text from web scraping.
  - Structured data from API-based collection.
- **Output**: A unified dataset that keeps both raw and pre-processed data.

#### Neurosymbolic Processing:
- See the detailed sub-workflow below.

#### Optional Human Review:
- An optional human-in-the-loop step to verify or refine the structured data.

#### Service Recommendation:
- **Input**:
  - Final structured service data (verified and reconciled).
  - Client information (demographics, location, needs).
- **Output**: Tailored service recommendations.

#### Data Update Strategy:
- Implement scheduled, on-demand, and incremental updates to keep the service data current.

### Detailed Neurosymbolic Processing Sub-Workflow

#### LLM-Based Extraction:
- **Input**: Raw text (preserved from web scraping) and the pre-loaded ontology.
- **Action**: The chosen LLM(s) extract key information (e.g., service name, hours, eligibility) using the ontology as a guide.
- **Output**: Preliminary structured data.

#### Confidence Aggregator (Multi-Model Voting):
- **Action**: If multiple models are used, aggregate outputs via a voting mechanism or weighted confidence scores.
- **Output**: Enhanced structured data with confidence levels.

#### Ontology Instantiating:
- **Action**: Integrate the extracted data into the ontology framework.
- **Output**: An instantiated, ontology-based representation of the service data (new classes are created if needed).

#### Finalize & Reconcile Structured Data:
- **Action**: Merge and reconcile the newly instantiated data with existing records, ensuring consistency and resolving any overlaps.
- **Output**: Final, stable structured data ready for recommendation. 