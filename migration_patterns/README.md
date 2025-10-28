# Migration Patterns Prompt Library

## Description

The Migration Patterns Prompt Library provides a prompt generation function for developing comprehensive AWS migration strategies. It leverages Amazon Bedrock's models to generate data-driven migration recommendations based on AWS Calculator exports.

## Primary Purpose

The primary purpose of this library is to transform raw AWS Calculator data into actionable migration strategies by:

- Analyzing cost optimization and performance drivers from AWS service configurations
- Generating multiple modernization patterns with varying complexity levels
- Creating detailed migration wave planning with cost projections
- Providing milestone predictions and acceleration strategies for MAP funding requirements

## Key Features

### 1. **Multi-Pattern Analysis**
- Generates three distinct modernization approaches
- Compares patterns to identify consistent strategic elements
- Synthesizes optimal final strategy from cross-pattern analysis

### 2. **Wave-Based Migration Planning**
- Creates structured migration waves with service groupings
- Provides duration estimates for each migration phase
- Calculates cumulative AWS spend (USD) projections per wave

### 3. **MAP Milestone Predictions**
- Predicts achievement of $50,000 USD milestone timing
- Offers acceleration strategies for early milestone achievement
- Includes risk assessment and mitigation recommendations

### 4. **Cost Optimization Focus**
- Emphasizes cost optimization and performance as key migration drivers
- Provides mathematical accuracy for Compute, Storage, and Database calculations


## Input Parameters

### Function: `get_migration_patterns_prompt(services_summary, scope_text)`

| Parameter Name | Type | Description |
|----------------|------|-------------|
| `services_summary` | `pandas.DataFrame` or `str` | AWS Calculator CSV data containing service configurations, costs, and technical specifications. Expected to include compute, storage, and database service details with pricing information. |
| `scope_text` | `str` | Optional migration scope details providing additional context such as business requirements, constraints, timelines, compliance needs, or specific modernization objectives. Can be empty string or None. |

## Expected Output Structure

The generated prompt produces a comprehensive migration strategy with the following structure:

### 1. **Calculator Data Analysis**
- Cost optimization analysis focusing on performance drivers
- Technical assessment of current service configurations

### 2. **Three Migration Patterns**
It provides three distinct migration patterns based on workloads.
For example: 
- **Pattern 1**: Minimal changes approach (lift-and-shift focus)
- **Pattern 2**: Moderate modernization (selective optimization)
- **Pattern 3**: Comprehensive modernization (full cloud-native transformation)

### 3. **Pattern Comparison and Synthesis**
- Cross-pattern consistency analysis
- Final strategy recommendation incorporating best elements

### 4. **High Level Wave Plan Table**
```
| Wave | Description | Services/Workloads | Duration | Cumulative USD Spend |
|------|-------------|-------------------|----------|---------------------|
| 1    | Foundation  | Core Infrastructure| X months | $X,XXX |
| 2    | Applications| Business Apps     | X months | $X,XXX |
| ...  | ...         | ...               | ...      | ...    |
```

### 5. **Strategic Questions and Recommendations**
- **Milestone Prediction**: Month for first $50,000 USD achievement
- **Acceleration Strategies**: Recommendations if milestone exceeds 4 months
- **Risk Assessment**: Risks and assumptions for acceleration strategies
- **Duration Rationale**: Reasoning for wave duration estimates

## Usage Context

This prompt library integrates with:
- **Migration Strategy Page** (`pages/02_migration_strategy.py`): Primary consumer of the prompt
- **Resource Planning Module Page**: `pages/03_resource_planning.py` downstream consumer of generated strategies

