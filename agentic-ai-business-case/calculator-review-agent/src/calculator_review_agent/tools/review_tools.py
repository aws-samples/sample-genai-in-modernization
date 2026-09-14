"""
Calculator Review Tool for AWS Transform Agent.

Accepts an AWS Pricing Calculator URL (ESC or non-ESC), fetches the estimate,
and produces the same structured analysis as the Calculator Review UI:
- Tab 1: Service breakdown with costs, MAP qualification, optimization opportunities
- Tab 2: Modernization pathways with index and validation summary
"""

import json
import logging
import re
from typing import Dict

from strands.tools import tool

# Import the core analysis engine
from calculator_review_agent.core.analyzer import CalcReviewAnalyzer

logger = logging.getLogger(__name__)


@tool
def analyze_calculator_url(calculator_url: str) -> dict:
    """Analyze an AWS Pricing Calculator URL for infrastructure completeness and optimization.

    Accepts both ESC (pricing.calculator.aws.eu) and non-ESC (calculator.aws) URLs.
    Fetches the estimate data and produces a full analysis including:

    Tab 1 - Service Breakdown:
    - Per-service costs (monthly, upfront, MAP-qualified MRR)
    - Data transfer exclusions
    - EC2 Savings Plans optimization (real-time pricing lookups)
    - RDS/Redshift/ElastiCache/OpenSearch Reserved Instance optimization
    - EBS storage optimization (gp2→gp3, io1→io2)
    - Fargate Compute Savings Plan calculations
    - Graviton migration savings estimates

    Tab 2 - Modernization Pathways:
    - Service classification into AWS modernization pathways
    - Modernization Index (modern ARR / qualified ARR)
    - Per-pathway ARR breakdown
    - Validation summary (optimization coverage)

    Args:
        calculator_url: AWS Pricing Calculator URL
                        (e.g. https://calculator.aws/#/estimate?id=abc123
                         or https://pricing.calculator.aws.eu/#/estimate?id=abc123)

    Returns:
        Dictionary with full analysis matching the Calculator Review UI output
    """
    analyzer = CalcReviewAnalyzer()
    return analyzer.analyze_url(calculator_url)
