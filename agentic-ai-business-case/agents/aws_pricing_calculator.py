"""
AWS Pricing Calculator - Deterministic ARR Calculation
Uses AWS Price List API for exact, consistent pricing
Supports right-sizing based on actual utilization
"""
import boto3
import json
from functools import lru_cache
from typing import Dict, List, Tuple, Optional
import pandas as pd
from botocore.exceptions import ClientError
from config import PRICING_CONFIG, RIGHT_SIZING_CONFIG

class AWSPricingCalculator:
    """
    Deterministic AWS pricing calculator using AWS Price List API
    Provides exact, repeatable cost calculations for EC2 instances
    """
    
    # Instance type specifications (vCPU, Memory GB)
    INSTANCE_SPECS = {
        # ============ GENERAL PURPOSE ============
        
        # M5 (Current Generation - Intel)
        'm5.large': (2, 8),
        'm5.xlarge': (4, 16),
        'm5.2xlarge': (8, 32),
        'm5.4xlarge': (16, 64),
        'm5.8xlarge': (32, 128),
        'm5.12xlarge': (48, 192),
        'm5.16xlarge': (64, 256),
        'm5.24xlarge': (96, 384),
        
        # M6i (Newer Generation - Intel Ice Lake)
        'm6i.large': (2, 8),
        'm6i.xlarge': (4, 16),
        'm6i.2xlarge': (8, 32),
        'm6i.4xlarge': (16, 64),
        'm6i.8xlarge': (32, 128),
        'm6i.12xlarge': (48, 192),
        'm6i.16xlarge': (64, 256),
        'm6i.24xlarge': (96, 384),
        'm6i.32xlarge': (128, 512),
        
        # M6a (AMD EPYC - 10% cheaper than m6i)
        'm6a.large': (2, 8),
        'm6a.xlarge': (4, 16),
        'm6a.2xlarge': (8, 32),
        'm6a.4xlarge': (16, 64),
        'm6a.8xlarge': (32, 128),
        'm6a.12xlarge': (48, 192),
        'm6a.16xlarge': (64, 256),
        'm6a.24xlarge': (96, 384),
        'm6a.32xlarge': (128, 512),
        'm6a.48xlarge': (192, 768),
        
        # M7i (Latest Generation - Intel Sapphire Rapids)
        'm7i.large': (2, 8),
        'm7i.xlarge': (4, 16),
        'm7i.2xlarge': (8, 32),
        'm7i.4xlarge': (16, 64),
        'm7i.8xlarge': (32, 128),
        'm7i.12xlarge': (48, 192),
        'm7i.16xlarge': (64, 256),
        'm7i.24xlarge': (96, 384),
        'm7i.48xlarge': (192, 768),
        
        # M6g (Graviton2 - ARM, 20% cheaper)
        'm6g.medium': (1, 4),
        'm6g.large': (2, 8),
        'm6g.xlarge': (4, 16),
        'm6g.2xlarge': (8, 32),
        'm6g.4xlarge': (16, 64),
        'm6g.8xlarge': (32, 128),
        'm6g.12xlarge': (48, 192),
        'm6g.16xlarge': (64, 256),
        
        # M7g (Graviton3 - Latest ARM, 25% better performance)
        'm7g.medium': (1, 4),
        'm7g.large': (2, 8),
        'm7g.xlarge': (4, 16),
        'm7g.2xlarge': (8, 32),
        'm7g.4xlarge': (16, 64),
        'm7g.8xlarge': (32, 128),
        'm7g.12xlarge': (48, 192),
        'm7g.16xlarge': (64, 256),
        
        # T3 (Burstable - Low cost for variable workloads)
        't3.micro': (2, 1),
        't3.small': (2, 2),
        't3.medium': (2, 4),
        't3.large': (2, 8),
        't3.xlarge': (4, 16),
        't3.2xlarge': (8, 32),
        
        # T4g (Burstable Graviton - 20% cheaper than t3)
        't4g.micro': (2, 1),
        't4g.small': (2, 2),
        't4g.medium': (2, 4),
        't4g.large': (2, 8),
        't4g.xlarge': (4, 16),
        't4g.2xlarge': (8, 32),
        
        # ============ COMPUTE OPTIMIZED ============
        
        # C5 (Current Generation)
        'c5.large': (2, 4),
        'c5.xlarge': (4, 8),
        'c5.2xlarge': (8, 16),
        'c5.4xlarge': (16, 32),
        'c5.9xlarge': (36, 72),
        'c5.12xlarge': (48, 96),
        'c5.18xlarge': (72, 144),
        'c5.24xlarge': (96, 192),
        
        # C6i (Newer Generation - Intel Ice Lake)
        'c6i.large': (2, 4),
        'c6i.xlarge': (4, 8),
        'c6i.2xlarge': (8, 16),
        'c6i.4xlarge': (16, 32),
        'c6i.8xlarge': (32, 64),
        'c6i.12xlarge': (48, 96),
        'c6i.16xlarge': (64, 128),
        'c6i.24xlarge': (96, 192),
        'c6i.32xlarge': (128, 256),
        
        # C6a (AMD EPYC)
        'c6a.large': (2, 4),
        'c6a.xlarge': (4, 8),
        'c6a.2xlarge': (8, 16),
        'c6a.4xlarge': (16, 32),
        'c6a.8xlarge': (32, 64),
        'c6a.12xlarge': (48, 96),
        'c6a.16xlarge': (64, 128),
        'c6a.24xlarge': (96, 192),
        'c6a.32xlarge': (128, 256),
        'c6a.48xlarge': (192, 384),
        
        # C7i (Latest Generation - Intel Sapphire Rapids)
        'c7i.large': (2, 4),
        'c7i.xlarge': (4, 8),
        'c7i.2xlarge': (8, 16),
        'c7i.4xlarge': (16, 32),
        'c7i.8xlarge': (32, 64),
        'c7i.12xlarge': (48, 96),
        'c7i.16xlarge': (64, 128),
        'c7i.24xlarge': (96, 192),
        'c7i.48xlarge': (192, 384),
        
        # C6g (Graviton2 - ARM)
        'c6g.medium': (1, 2),
        'c6g.large': (2, 4),
        'c6g.xlarge': (4, 8),
        'c6g.2xlarge': (8, 16),
        'c6g.4xlarge': (16, 32),
        'c6g.8xlarge': (32, 64),
        'c6g.12xlarge': (48, 96),
        'c6g.16xlarge': (64, 128),
        
        # C7g (Graviton3 - Latest ARM)
        'c7g.medium': (1, 2),
        'c7g.large': (2, 4),
        'c7g.xlarge': (4, 8),
        'c7g.2xlarge': (8, 16),
        'c7g.4xlarge': (16, 32),
        'c7g.8xlarge': (32, 64),
        'c7g.12xlarge': (48, 96),
        'c7g.16xlarge': (64, 128),
        
        # ============ MEMORY OPTIMIZED ============
        
        # R5 (Current Generation)
        'r5.large': (2, 16),
        'r5.xlarge': (4, 32),
        'r5.2xlarge': (8, 64),
        'r5.4xlarge': (16, 128),
        'r5.8xlarge': (32, 256),
        'r5.12xlarge': (48, 384),
        'r5.16xlarge': (64, 512),
        'r5.24xlarge': (96, 768),
        
        # R6i (Newer Generation - Intel Ice Lake)
        'r6i.large': (2, 16),
        'r6i.xlarge': (4, 32),
        'r6i.2xlarge': (8, 64),
        'r6i.4xlarge': (16, 128),
        'r6i.8xlarge': (32, 256),
        'r6i.12xlarge': (48, 384),
        'r6i.16xlarge': (64, 512),
        'r6i.24xlarge': (96, 768),
        'r6i.32xlarge': (128, 1024),
        
        # R6a (AMD EPYC)
        'r6a.large': (2, 16),
        'r6a.xlarge': (4, 32),
        'r6a.2xlarge': (8, 64),
        'r6a.4xlarge': (16, 128),
        'r6a.8xlarge': (32, 256),
        'r6a.12xlarge': (48, 384),
        'r6a.16xlarge': (64, 512),
        'r6a.24xlarge': (96, 768),
        'r6a.32xlarge': (128, 1024),
        'r6a.48xlarge': (192, 1536),
        
        # R7i (Latest Generation - Intel Sapphire Rapids)
        'r7i.large': (2, 16),
        'r7i.xlarge': (4, 32),
        'r7i.2xlarge': (8, 64),
        'r7i.4xlarge': (16, 128),
        'r7i.8xlarge': (32, 256),
        'r7i.12xlarge': (48, 384),
        'r7i.16xlarge': (64, 512),
        'r7i.24xlarge': (96, 768),
        'r7i.48xlarge': (192, 1536),
        
        # R6g (Graviton2 - ARM)
        'r6g.medium': (1, 8),
        'r6g.large': (2, 16),
        'r6g.xlarge': (4, 32),
        'r6g.2xlarge': (8, 64),
        'r6g.4xlarge': (16, 128),
        'r6g.8xlarge': (32, 256),
        'r6g.12xlarge': (48, 384),
        'r6g.16xlarge': (64, 512),
        
        # R7g (Graviton3 - Latest ARM)
        'r7g.medium': (1, 8),
        'r7g.large': (2, 16),
        'r7g.xlarge': (4, 32),
        'r7g.2xlarge': (8, 64),
        'r7g.4xlarge': (16, 128),
        'r7g.8xlarge': (32, 256),
        'r7g.12xlarge': (48, 384),
        'r7g.16xlarge': (64, 512),
        
        # X2i (High Memory - Up to 2 TB RAM)
        'x2idn.16xlarge': (64, 1024),
        'x2idn.24xlarge': (96, 1536),
        'x2idn.32xlarge': (128, 2048),
        'x2iedn.xlarge': (4, 128),
        'x2iedn.2xlarge': (8, 256),
        'x2iedn.4xlarge': (16, 512),
        'x2iedn.8xlarge': (32, 1024),
        'x2iedn.16xlarge': (64, 2048),
        'x2iedn.24xlarge': (96, 3072),
        'x2iedn.32xlarge': (128, 4096),
        
        # ============ STORAGE OPTIMIZED ============
        
        # I3 (NVMe SSD Storage)
        'i3.large': (2, 15.25),
        'i3.xlarge': (4, 30.5),
        'i3.2xlarge': (8, 61),
        'i3.4xlarge': (16, 122),
        'i3.8xlarge': (32, 244),
        'i3.16xlarge': (64, 488),
        
        # I4i (Latest NVMe SSD - 30% better price/performance)
        'i4i.large': (2, 16),
        'i4i.xlarge': (4, 32),
        'i4i.2xlarge': (8, 64),
        'i4i.4xlarge': (16, 128),
        'i4i.8xlarge': (32, 256),
        'i4i.16xlarge': (64, 512),
        'i4i.32xlarge': (128, 1024),
        
        # D3 (Dense HDD Storage)
        'd3.xlarge': (4, 32),
        'd3.2xlarge': (8, 64),
        'd3.4xlarge': (16, 128),
        'd3.8xlarge': (32, 256),
        
        # ============ ACCELERATED COMPUTING ============
        
        # G4dn (NVIDIA T4 GPUs - ML Inference)
        'g4dn.xlarge': (4, 16),
        'g4dn.2xlarge': (8, 32),
        'g4dn.4xlarge': (16, 64),
        'g4dn.8xlarge': (32, 128),
        'g4dn.12xlarge': (48, 192),
        'g4dn.16xlarge': (64, 256),
        
        # G5 (NVIDIA A10G GPUs - ML Training/Inference)
        'g5.xlarge': (4, 16),
        'g5.2xlarge': (8, 32),
        'g5.4xlarge': (16, 64),
        'g5.8xlarge': (32, 128),
        'g5.12xlarge': (48, 192),
        'g5.16xlarge': (64, 256),
        'g5.24xlarge': (96, 384),
        'g5.48xlarge': (192, 768),
        
        # P3 (NVIDIA V100 GPUs - ML Training)
        'p3.2xlarge': (8, 61),
        'p3.8xlarge': (32, 244),
        'p3.16xlarge': (64, 488),
        
        # P4d (NVIDIA A100 GPUs - Latest ML Training)
        'p4d.24xlarge': (96, 1152),
    }
    
    # Region code to location name mapping (for AWS Pricing API)
    REGION_LOCATIONS = {
        'us-east-1': 'US East (N. Virginia)',
        'us-east-2': 'US East (Ohio)',
        'us-west-1': 'US West (N. California)',
        'us-west-2': 'US West (Oregon)',
        'eu-west-1': 'EU (Ireland)',
        'eu-west-2': 'EU (London)',
        'eu-west-3': 'EU (Paris)',
        'eu-central-1': 'EU (Frankfurt)',
        'ap-southeast-1': 'Asia Pacific (Singapore)',
        'ap-southeast-2': 'Asia Pacific (Sydney)',
        'ap-northeast-1': 'Asia Pacific (Tokyo)',
        'ap-south-1': 'Asia Pacific (Mumbai)',
        'ca-central-1': 'Canada (Central)',
        'sa-east-1': 'South America (Sao Paulo)',
    }
    
    # Fallback pricing (used if API fails) - us-east-1, 3-Year No Upfront RI
    # Prices are approximate hourly rates for 3-Year Reserved Instances (No Upfront)
    FALLBACK_PRICING = {
        # ===== GENERAL PURPOSE =====
        # M5 (Current Generation)
        'm5.large': {'Linux': 0.069, 'Windows': 0.165},
        'm5.xlarge': {'Linux': 0.138, 'Windows': 0.330},
        'm5.2xlarge': {'Linux': 0.276, 'Windows': 0.660},
        'm5.4xlarge': {'Linux': 0.552, 'Windows': 1.320},
        'm5.8xlarge': {'Linux': 1.104, 'Windows': 2.640},
        'm5.12xlarge': {'Linux': 1.656, 'Windows': 3.960},
        'm5.16xlarge': {'Linux': 2.208, 'Windows': 5.280},
        'm5.24xlarge': {'Linux': 3.312, 'Windows': 7.920},
        # M6i (5% better price/performance than m5)
        'm6i.large': {'Linux': 0.066, 'Windows': 0.157},
        'm6i.xlarge': {'Linux': 0.131, 'Windows': 0.314},
        'm6i.2xlarge': {'Linux': 0.262, 'Windows': 0.627},
        'm6i.4xlarge': {'Linux': 0.524, 'Windows': 1.254},
        'm6i.8xlarge': {'Linux': 1.049, 'Windows': 2.509},
        'm6i.12xlarge': {'Linux': 1.573, 'Windows': 3.763},
        'm6i.16xlarge': {'Linux': 2.097, 'Windows': 5.017},
        'm6i.24xlarge': {'Linux': 3.146, 'Windows': 7.526},
        'm6i.32xlarge': {'Linux': 4.194, 'Windows': 10.034},
        # M6a (AMD - 10% cheaper than m6i)
        'm6a.large': {'Linux': 0.059, 'Windows': 0.141},
        'm6a.xlarge': {'Linux': 0.118, 'Windows': 0.283},
        'm6a.2xlarge': {'Linux': 0.236, 'Windows': 0.564},
        'm6a.4xlarge': {'Linux': 0.472, 'Windows': 1.129},
        'm6a.8xlarge': {'Linux': 0.944, 'Windows': 2.258},
        'm6a.12xlarge': {'Linux': 1.416, 'Windows': 3.387},
        'm6a.16xlarge': {'Linux': 1.888, 'Windows': 4.516},
        'm6a.24xlarge': {'Linux': 2.832, 'Windows': 6.774},
        'm6a.32xlarge': {'Linux': 3.776, 'Windows': 9.032},
        'm6a.48xlarge': {'Linux': 5.664, 'Windows': 13.548},
        # M7i (Latest - 15% better performance)
        'm7i.large': {'Linux': 0.063, 'Windows': 0.150},
        'm7i.xlarge': {'Linux': 0.125, 'Windows': 0.300},
        'm7i.2xlarge': {'Linux': 0.250, 'Windows': 0.600},
        'm7i.4xlarge': {'Linux': 0.500, 'Windows': 1.200},
        'm7i.8xlarge': {'Linux': 1.000, 'Windows': 2.400},
        'm7i.12xlarge': {'Linux': 1.500, 'Windows': 3.600},
        'm7i.16xlarge': {'Linux': 2.000, 'Windows': 4.800},
        'm7i.24xlarge': {'Linux': 3.000, 'Windows': 7.200},
        'm7i.48xlarge': {'Linux': 6.000, 'Windows': 14.400},
        # M6g/M7g (Graviton - 20% cheaper, Linux only)
        'm6g.medium': {'Linux': 0.028, 'Windows': 0.028},  # No Windows on Graviton
        'm6g.large': {'Linux': 0.055, 'Windows': 0.055},
        'm6g.xlarge': {'Linux': 0.110, 'Windows': 0.110},
        'm6g.2xlarge': {'Linux': 0.221, 'Windows': 0.221},
        'm6g.4xlarge': {'Linux': 0.442, 'Windows': 0.442},
        'm6g.8xlarge': {'Linux': 0.883, 'Windows': 0.883},
        'm6g.12xlarge': {'Linux': 1.325, 'Windows': 1.325},
        'm6g.16xlarge': {'Linux': 1.766, 'Windows': 1.766},
        'm7g.medium': {'Linux': 0.026, 'Windows': 0.026},
        'm7g.large': {'Linux': 0.052, 'Windows': 0.052},
        'm7g.xlarge': {'Linux': 0.105, 'Windows': 0.105},
        'm7g.2xlarge': {'Linux': 0.210, 'Windows': 0.210},
        'm7g.4xlarge': {'Linux': 0.420, 'Windows': 0.420},
        'm7g.8xlarge': {'Linux': 0.840, 'Windows': 0.840},
        'm7g.12xlarge': {'Linux': 1.260, 'Windows': 1.260},
        'm7g.16xlarge': {'Linux': 1.680, 'Windows': 1.680},
        # T3/T4g (Burstable - 40% cheaper)
        't3.micro': {'Linux': 0.007, 'Windows': 0.014},
        't3.small': {'Linux': 0.014, 'Windows': 0.028},
        't3.medium': {'Linux': 0.028, 'Windows': 0.056},
        't3.large': {'Linux': 0.056, 'Windows': 0.112},
        't3.xlarge': {'Linux': 0.112, 'Windows': 0.224},
        't3.2xlarge': {'Linux': 0.224, 'Windows': 0.448},
        't4g.micro': {'Linux': 0.006, 'Windows': 0.006},
        't4g.small': {'Linux': 0.011, 'Windows': 0.011},
        't4g.medium': {'Linux': 0.022, 'Windows': 0.022},
        't4g.large': {'Linux': 0.045, 'Windows': 0.045},
        't4g.xlarge': {'Linux': 0.090, 'Windows': 0.090},
        't4g.2xlarge': {'Linux': 0.179, 'Windows': 0.179},
        
        # ===== COMPUTE OPTIMIZED =====
        # C5 (Current Generation)
        'c5.large': {'Linux': 0.061, 'Windows': 0.157},
        'c5.xlarge': {'Linux': 0.122, 'Windows': 0.314},
        'c5.2xlarge': {'Linux': 0.244, 'Windows': 0.628},
        'c5.4xlarge': {'Linux': 0.488, 'Windows': 1.256},
        'c5.9xlarge': {'Linux': 1.098, 'Windows': 2.826},
        'c5.12xlarge': {'Linux': 1.464, 'Windows': 3.768},
        'c5.18xlarge': {'Linux': 2.196, 'Windows': 5.652},
        'c5.24xlarge': {'Linux': 2.928, 'Windows': 7.536},
        # C6i (5% better price/performance)
        'c6i.large': {'Linux': 0.058, 'Windows': 0.149},
        'c6i.xlarge': {'Linux': 0.116, 'Windows': 0.298},
        'c6i.2xlarge': {'Linux': 0.232, 'Windows': 0.597},
        'c6i.4xlarge': {'Linux': 0.464, 'Windows': 1.193},
        'c6i.8xlarge': {'Linux': 0.928, 'Windows': 2.386},
        'c6i.12xlarge': {'Linux': 1.391, 'Windows': 3.579},
        'c6i.16xlarge': {'Linux': 1.855, 'Windows': 4.772},
        'c6i.24xlarge': {'Linux': 2.783, 'Windows': 7.158},
        'c6i.32xlarge': {'Linux': 3.710, 'Windows': 9.544},
        # C6a (AMD - 10% cheaper)
        'c6a.large': {'Linux': 0.052, 'Windows': 0.134},
        'c6a.xlarge': {'Linux': 0.104, 'Windows': 0.268},
        'c6a.2xlarge': {'Linux': 0.209, 'Windows': 0.537},
        'c6a.4xlarge': {'Linux': 0.418, 'Windows': 1.074},
        'c6a.8xlarge': {'Linux': 0.835, 'Windows': 2.147},
        'c6a.12xlarge': {'Linux': 1.252, 'Windows': 3.221},
        'c6a.16xlarge': {'Linux': 1.670, 'Windows': 4.295},
        'c6a.24xlarge': {'Linux': 2.504, 'Windows': 6.442},
        'c6a.32xlarge': {'Linux': 3.339, 'Windows': 8.590},
        'c6a.48xlarge': {'Linux': 5.009, 'Windows': 12.884},
        # C7i (Latest)
        'c7i.large': {'Linux': 0.055, 'Windows': 0.142},
        'c7i.xlarge': {'Linux': 0.110, 'Windows': 0.283},
        'c7i.2xlarge': {'Linux': 0.221, 'Windows': 0.567},
        'c7i.4xlarge': {'Linux': 0.441, 'Windows': 1.134},
        'c7i.8xlarge': {'Linux': 0.883, 'Windows': 2.268},
        'c7i.12xlarge': {'Linux': 1.324, 'Windows': 3.402},
        'c7i.16xlarge': {'Linux': 1.765, 'Windows': 4.536},
        'c7i.24xlarge': {'Linux': 2.648, 'Windows': 6.804},
        'c7i.48xlarge': {'Linux': 5.295, 'Windows': 13.608},
        # C6g/C7g (Graviton - 20% cheaper, Linux only)
        'c6g.medium': {'Linux': 0.024, 'Windows': 0.024},
        'c6g.large': {'Linux': 0.049, 'Windows': 0.049},
        'c6g.xlarge': {'Linux': 0.098, 'Windows': 0.098},
        'c6g.2xlarge': {'Linux': 0.195, 'Windows': 0.195},
        'c6g.4xlarge': {'Linux': 0.390, 'Windows': 0.390},
        'c6g.8xlarge': {'Linux': 0.781, 'Windows': 0.781},
        'c6g.12xlarge': {'Linux': 1.171, 'Windows': 1.171},
        'c6g.16xlarge': {'Linux': 1.562, 'Windows': 1.562},
        'c7g.medium': {'Linux': 0.023, 'Windows': 0.023},
        'c7g.large': {'Linux': 0.047, 'Windows': 0.047},
        'c7g.xlarge': {'Linux': 0.093, 'Windows': 0.093},
        'c7g.2xlarge': {'Linux': 0.186, 'Windows': 0.186},
        'c7g.4xlarge': {'Linux': 0.371, 'Windows': 0.371},
        'c7g.8xlarge': {'Linux': 0.743, 'Windows': 0.743},
        'c7g.12xlarge': {'Linux': 1.114, 'Windows': 1.114},
        'c7g.16xlarge': {'Linux': 1.486, 'Windows': 1.486},
        
        # ===== MEMORY OPTIMIZED =====
        # R5 (Current Generation)
        'r5.large': {'Linux': 0.090, 'Windows': 0.186},
        'r5.xlarge': {'Linux': 0.180, 'Windows': 0.372},
        'r5.2xlarge': {'Linux': 0.360, 'Windows': 0.744},
        'r5.4xlarge': {'Linux': 0.720, 'Windows': 1.488},
        'r5.8xlarge': {'Linux': 1.440, 'Windows': 2.976},
        'r5.12xlarge': {'Linux': 2.160, 'Windows': 4.464},
        'r5.16xlarge': {'Linux': 2.880, 'Windows': 5.952},
        'r5.24xlarge': {'Linux': 4.320, 'Windows': 8.928},
        # R6i (5% better price/performance)
        'r6i.large': {'Linux': 0.086, 'Windows': 0.177},
        'r6i.xlarge': {'Linux': 0.171, 'Windows': 0.353},
        'r6i.2xlarge': {'Linux': 0.342, 'Windows': 0.707},
        'r6i.4xlarge': {'Linux': 0.684, 'Windows': 1.413},
        'r6i.8xlarge': {'Linux': 1.368, 'Windows': 2.827},
        'r6i.12xlarge': {'Linux': 2.052, 'Windows': 4.241},
        'r6i.16xlarge': {'Linux': 2.736, 'Windows': 5.654},
        'r6i.24xlarge': {'Linux': 4.104, 'Windows': 8.481},
        'r6i.32xlarge': {'Linux': 5.472, 'Windows': 11.308},
        # R6a (AMD - 10% cheaper)
        'r6a.large': {'Linux': 0.077, 'Windows': 0.159},
        'r6a.xlarge': {'Linux': 0.154, 'Windows': 0.318},
        'r6a.2xlarge': {'Linux': 0.308, 'Windows': 0.636},
        'r6a.4xlarge': {'Linux': 0.616, 'Windows': 1.272},
        'r6a.8xlarge': {'Linux': 1.231, 'Windows': 2.544},
        'r6a.12xlarge': {'Linux': 1.847, 'Windows': 3.817},
        'r6a.16xlarge': {'Linux': 2.462, 'Windows': 5.089},
        'r6a.24xlarge': {'Linux': 3.694, 'Windows': 7.633},
        'r6a.32xlarge': {'Linux': 4.925, 'Windows': 10.177},
        'r6a.48xlarge': {'Linux': 7.387, 'Windows': 15.266},
        # R7i (Latest)
        'r7i.large': {'Linux': 0.082, 'Windows': 0.169},
        'r7i.xlarge': {'Linux': 0.163, 'Windows': 0.337},
        'r7i.2xlarge': {'Linux': 0.326, 'Windows': 0.674},
        'r7i.4xlarge': {'Linux': 0.653, 'Windows': 1.349},
        'r7i.8xlarge': {'Linux': 1.305, 'Windows': 2.697},
        'r7i.12xlarge': {'Linux': 1.958, 'Windows': 4.046},
        'r7i.16xlarge': {'Linux': 2.610, 'Windows': 5.394},
        'r7i.24xlarge': {'Linux': 3.916, 'Windows': 8.091},
        'r7i.48xlarge': {'Linux': 7.831, 'Windows': 16.182},
        # R6g/R7g (Graviton - 20% cheaper, Linux only)
        'r6g.medium': {'Linux': 0.036, 'Windows': 0.036},
        'r6g.large': {'Linux': 0.072, 'Windows': 0.072},
        'r6g.xlarge': {'Linux': 0.144, 'Windows': 0.144},
        'r6g.2xlarge': {'Linux': 0.288, 'Windows': 0.288},
        'r6g.4xlarge': {'Linux': 0.576, 'Windows': 0.576},
        'r6g.8xlarge': {'Linux': 1.152, 'Windows': 1.152},
        'r6g.12xlarge': {'Linux': 1.728, 'Windows': 1.728},
        'r6g.16xlarge': {'Linux': 2.304, 'Windows': 2.304},
        'r7g.medium': {'Linux': 0.034, 'Windows': 0.034},
        'r7g.large': {'Linux': 0.069, 'Windows': 0.069},
        'r7g.xlarge': {'Linux': 0.137, 'Windows': 0.137},
        'r7g.2xlarge': {'Linux': 0.274, 'Windows': 0.274},
        'r7g.4xlarge': {'Linux': 0.547, 'Windows': 0.547},
        'r7g.8xlarge': {'Linux': 1.094, 'Windows': 1.094},
        'r7g.12xlarge': {'Linux': 1.642, 'Windows': 1.642},
        'r7g.16xlarge': {'Linux': 2.189, 'Windows': 2.189},
        
        # ===== STORAGE OPTIMIZED =====
        # I3 (NVMe SSD)
        'i3.large': {'Linux': 0.111, 'Windows': 0.207},
        'i3.xlarge': {'Linux': 0.222, 'Windows': 0.414},
        'i3.2xlarge': {'Linux': 0.444, 'Windows': 0.828},
        'i3.4xlarge': {'Linux': 0.888, 'Windows': 1.656},
        'i3.8xlarge': {'Linux': 1.776, 'Windows': 3.312},
        'i3.16xlarge': {'Linux': 3.552, 'Windows': 6.624},
        # I4i (Latest NVMe - 30% better price/performance)
        'i4i.large': {'Linux': 0.078, 'Windows': 0.145},
        'i4i.xlarge': {'Linux': 0.156, 'Windows': 0.290},
        'i4i.2xlarge': {'Linux': 0.311, 'Windows': 0.579},
        'i4i.4xlarge': {'Linux': 0.622, 'Windows': 1.158},
        'i4i.8xlarge': {'Linux': 1.244, 'Windows': 2.316},
        'i4i.16xlarge': {'Linux': 2.488, 'Windows': 4.632},
        'i4i.32xlarge': {'Linux': 4.976, 'Windows': 9.264},
        # D3 (Dense HDD)
        'd3.xlarge': {'Linux': 0.149, 'Windows': 0.245},
        'd3.2xlarge': {'Linux': 0.298, 'Windows': 0.490},
        'd3.4xlarge': {'Linux': 0.596, 'Windows': 0.980},
        'd3.8xlarge': {'Linux': 1.192, 'Windows': 1.960},
        
        # ===== ACCELERATED COMPUTING =====
        # G4dn (NVIDIA T4 - ML Inference)
        'g4dn.xlarge': {'Linux': 0.392, 'Windows': 0.488},
        'g4dn.2xlarge': {'Linux': 0.564, 'Windows': 0.660},
        'g4dn.4xlarge': {'Linux': 0.902, 'Windows': 0.998},
        'g4dn.8xlarge': {'Linux': 1.628, 'Windows': 1.724},
        'g4dn.12xlarge': {'Linux': 2.934, 'Windows': 3.030},
        'g4dn.16xlarge': {'Linux': 3.256, 'Windows': 3.352},
        # G5 (NVIDIA A10G - ML Training/Inference)
        'g5.xlarge': {'Linux': 0.752, 'Windows': 0.848},
        'g5.2xlarge': {'Linux': 0.902, 'Windows': 0.998},
        'g5.4xlarge': {'Linux': 1.204, 'Windows': 1.300},
        'g5.8xlarge': {'Linux': 1.808, 'Windows': 1.904},
        'g5.12xlarge': {'Linux': 3.622, 'Windows': 3.718},
        'g5.16xlarge': {'Linux': 3.256, 'Windows': 3.352},
        'g5.24xlarge': {'Linux': 5.434, 'Windows': 5.530},
        'g5.48xlarge': {'Linux': 10.868, 'Windows': 10.964},
        # P3 (NVIDIA V100 - ML Training)
        'p3.2xlarge': {'Linux': 2.229, 'Windows': 2.325},
        'p3.8xlarge': {'Linux': 8.916, 'Windows': 9.012},
        'p3.16xlarge': {'Linux': 17.832, 'Windows': 17.928},
        # P4d (NVIDIA A100 - Latest ML)
        'p4d.24xlarge': {'Linux': 23.040, 'Windows': 23.136},
    }
    
    def __init__(self, region=None, use_api=None, pricing_model=None):
        """
        Initialize pricing calculator
        
        Args:
            region: Target AWS region for pricing (defaults to config)
            use_api: If True, use AWS Pricing API; if False, use fallback pricing (defaults to config)
            pricing_model: Pricing model to use ('3yr_ec2_sp', '3yr_compute_sp', '3yr_no_upfront', '1yr_no_upfront', 'on_demand')
        """
        # Use config defaults if not specified
        self.target_region = region or PRICING_CONFIG.get('default_region', 'us-east-1')
        self.use_api = use_api if use_api is not None else PRICING_CONFIG.get('use_aws_pricing_api', False)
        self.pricing_model = pricing_model or PRICING_CONFIG.get('pricing_model', '3yr_compute_sp')
        self.pricing_client = None
        self.verbose = PRICING_CONFIG.get('verbose_logging', True)
        self._last_upfront_fee = 0.0  # Track upfront fees for Partial/All Upfront RIs
        
        if self.use_api:
            try:
                # Pricing API is only available in us-east-1
                self.pricing_client = boto3.client('pricing', region_name='us-east-1')
                if self.verbose:
                    print(f"✓ AWS Pricing API initialized for region: {self.target_region}")
            except Exception as e:
                if self.verbose:
                    print(f"⚠ AWS Pricing API not available: {e}")
                    print(f"  Using fallback pricing for {self.target_region}")
                self.use_api = False
    
    def map_vm_to_instance_type(self, vcpu: int, memory_gb: float, os: str = '', prefer_graviton: bool = False) -> str:
        """
        Deterministic mapping: VM specs → AWS instance type
        
        Algorithm:
        1. Calculate memory-to-vCPU ratio
        2. Determine instance family (compute/general/memory optimized)
        3. Select generation (prefer newer: m7i > m6i > m5)
        4. Find closest instance size
        5. Consider Graviton for Linux workloads (20% cheaper)
        
        Args:
            vcpu: Number of vCPUs
            memory_gb: Memory in GB
            os: Operating system (for Graviton eligibility)
            prefer_graviton: If True, prefer Graviton instances for Linux
        
        Returns:
            Instance type string (e.g., 'm6i.xlarge')
        """
        if vcpu <= 0 or memory_gb <= 0:
            return 'm6i.large'  # Default fallback (newer generation)
        
        # Calculate memory-to-vCPU ratio
        memory_ratio = memory_gb / vcpu
        
        # Determine instance family based on ratio
        # Compute: ~2 GB/vCPU (c-family)
        # General: ~4 GB/vCPU (m-family)
        # Memory: ~8 GB/vCPU (r-family)
        if memory_ratio < 3:
            base_family = 'c'
        elif memory_ratio > 6:
            base_family = 'r'
        else:
            base_family = 'm'
        
        # Check if Graviton is suitable (Linux only, no Windows support)
        is_linux = 'linux' in os.lower() or 'red hat' in os.lower() or 'ubuntu' in os.lower() or 'centos' in os.lower()
        use_graviton = prefer_graviton and is_linux and 'windows' not in os.lower()
        
        # Select generation (prefer newer for better price/performance)
        # Priority: Latest (7i/7g) > Newer (6i/6a/6g) > Current (5)
        if use_graviton:
            # Graviton instances (ARM-based, 20% cheaper)
            family_priority = [f'{base_family}7g', f'{base_family}6g']
        else:
            # x86 instances (Intel/AMD)
            family_priority = [
                f'{base_family}7i',  # Latest Intel Sapphire Rapids
                f'{base_family}6i',  # Intel Ice Lake
                f'{base_family}6a',  # AMD EPYC (10% cheaper)
                f'{base_family}5',   # Current generation
            ]
        
        # Special case: Very small VMs (1-2 vCPU, <8GB) → Consider burstable
        if vcpu <= 2 and memory_gb <= 8:
            if use_graviton:
                family_priority.insert(0, 't4g')  # Graviton burstable
            else:
                family_priority.insert(0, 't3')   # x86 burstable
        
        # Find best match across preferred families
        best_match = None
        min_diff = float('inf')
        
        for family in family_priority:
            for instance_type, (inst_vcpu, inst_memory) in self.INSTANCE_SPECS.items():
                if not instance_type.startswith(family):
                    continue
                
                # Prefer instances that meet or exceed requirements
                if inst_vcpu >= vcpu and inst_memory >= memory_gb:
                    # Calculate difference (prefer closer match)
                    vcpu_diff = abs(inst_vcpu - vcpu)
                    memory_diff = abs(inst_memory - memory_gb) / 10  # Weight memory less
                    diff = vcpu_diff + memory_diff
                    
                    if diff < min_diff:
                        min_diff = diff
                        best_match = instance_type
            
            # If found a match in this family, use it
            if best_match:
                break
        
        # If no match found (VM too large), use largest instance in preferred family
        if not best_match:
            for family in family_priority:
                family_instances = [k for k in self.INSTANCE_SPECS.keys() if k.startswith(family)]
                if family_instances:
                    best_match = max(family_instances, key=lambda x: self.INSTANCE_SPECS[x][0])
                    break
        
        # Final fallback
        if not best_match:
            best_match = 'm6i.large'
        
        return best_match
    
    @lru_cache(maxsize=500)
    def get_ec2_price_from_api(self, instance_type: str, os_type: str, region: str) -> float:
        """
        Get exact EC2 pricing from AWS Price List API
        Cached to avoid repeated API calls
        
        Args:
            instance_type: EC2 instance type (e.g., 'm5.xlarge')
            os_type: 'Linux' or 'Windows'
            region: AWS region code
        
        Returns:
            Hourly rate for 3-Year No Upfront Reserved Instance
        """
        if not self.pricing_client:
            raise Exception("Pricing API not available")
        
        location = self.REGION_LOCATIONS.get(region, 'US East (N. Virginia)')
        
        try:
            filters = [
                {'Type': 'TERM_MATCH', 'Field': 'instanceType', 'Value': instance_type},
                {'Type': 'TERM_MATCH', 'Field': 'operatingSystem', 'Value': os_type},
                {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': location},
                {'Type': 'TERM_MATCH', 'Field': 'tenancy', 'Value': 'Shared'},
                {'Type': 'TERM_MATCH', 'Field': 'preInstalledSw', 'Value': 'NA'},
                {'Type': 'TERM_MATCH', 'Field': 'capacitystatus', 'Value': 'Used'}
            ]
            
            response = self.pricing_client.get_products(
                ServiceCode='AmazonEC2',
                Filters=filters,
                MaxResults=100
            )
            
            if not response.get('PriceList'):
                raise Exception(f"No pricing found for {instance_type} {os_type} in {region}")
            
            # Parse pricing data - look for 3-Year No Upfront Reserved Instance
            for price_item in response['PriceList']:
                price_data = json.loads(price_item)
                
                # Look in Reserved Instance terms
                terms = price_data.get('terms', {}).get('Reserved', {})
                
                for term_key, term_data in terms.items():
                    term_attributes = term_data.get('termAttributes', {})
                    
                    # Check for 3-Year No Upfront
                    if (term_attributes.get('LeaseContractLength') == '3yr' and
                        term_attributes.get('PurchaseOption') == 'No Upfront'):
                        
                        # Extract hourly rate
                        price_dimensions = term_data.get('priceDimensions', {})
                        for dimension in price_dimensions.values():
                            price_per_unit = dimension.get('pricePerUnit', {})
                            if 'USD' in price_per_unit:
                                return float(price_per_unit['USD'])
            
            raise Exception(f"3-Year No Upfront pricing not found for {instance_type}")
            
        except Exception as e:
            print(f"⚠ API pricing failed for {instance_type}: {e}")
            raise
    
    def get_ec2_price(self, instance_type: str, os_type: str) -> float:
        """
        Get EC2 pricing - tries API first, falls back to hardcoded pricing
        
        Args:
            instance_type: EC2 instance type
            os_type: 'Linux' or 'Windows'
        
        Returns:
            Hourly rate for 3-Year No Upfront RI
        """
        if self.use_api:
            try:
                return self.get_ec2_price_from_api(instance_type, os_type, self.target_region)
            except Exception as e:
                print(f"  Falling back to hardcoded pricing for {instance_type}")
                self.use_api = False  # Disable API for subsequent calls
        
        # Use fallback pricing
        if instance_type in self.FALLBACK_PRICING:
            base_price = self.FALLBACK_PRICING[instance_type][os_type]
            
            # Apply regional multiplier if not us-east-1
            regional_multiplier = self._get_regional_multiplier(self.target_region)
            return base_price * regional_multiplier
        
        # If instance type not in fallback, estimate based on specs
        vcpu, memory = self.INSTANCE_SPECS.get(instance_type, (4, 16))
        base_rate = 0.035 * vcpu  # Rough estimate: $0.035/vCPU/hour
        if os_type == 'Windows':
            base_rate *= 2.4  # Windows licensing premium
        
        return base_rate
    
    @lru_cache(maxsize=500)
    def get_ec2_price_by_term(self, instance_type: str, os_type: str, region: str, term: str = '3yr', purchase_option: str = 'No Upfront') -> float:
        """
        Get EC2 pricing from AWS Price List API for specific term
        
        Args:
            instance_type: EC2 instance type (e.g., 'm5.xlarge')
            os_type: 'Linux' or 'Windows'
            region: AWS region code
            term: '1yr', '3yr' for Reserved Instances, '3yr_compute_sp' for Compute Savings Plan, 'on_demand' for On-Demand
            purchase_option: 'No Upfront', 'Partial Upfront', or 'All Upfront'
        
        Returns:
            Hourly rate
        """
        # Handle Compute Savings Plan by getting actual pricing from Savings Plans API
        if term == '3yr_compute_sp':
            if not self.use_api:
                # Use fallback pricing directly (Compute SP is ~10% more expensive than EC2 Instance SP)
                fallback_price = self.get_ec2_price(instance_type, os_type)
                ec2_sp_price = fallback_price * 0.95  # EC2 Instance SP discount
                return ec2_sp_price * 1.10  # Compute SP is 10% more expensive
            try:
                return self.get_savings_plan_price(instance_type, os_type, region, '3yr', plan_type='COMPUTE_SP')
            except Exception as e:
                print(f"⚠️  Compute Savings Plan API failed, using fallback: {e}")
                # Fallback: Use fallback pricing with markup
                fallback_price = self.get_ec2_price(instance_type, os_type)
                ec2_sp_price = fallback_price * 0.95
                return ec2_sp_price * 1.10
        
        # Handle EC2 Instance Savings Plan
        if term == '3yr_ec2_sp':
            if not self.use_api:
                # Use fallback pricing directly (EC2 Instance SP is ~5% cheaper than 3yr RI)
                fallback_price = self.get_ec2_price(instance_type, os_type)
                return fallback_price * 0.95
            try:
                return self.get_savings_plan_price(instance_type, os_type, region, '3yr', plan_type='EC2_INSTANCE_SP')
            except Exception as e:
                print(f"⚠️  EC2 Instance Savings Plan API failed, using fallback: {e}")
                # Fallback: Use fallback pricing with 5% discount
                fallback_price = self.get_ec2_price(instance_type, os_type)
                return fallback_price * 0.95
        
        # Handle 1-Year Compute Savings Plan
        if term == '1yr_compute_sp':
            try:
                return self.get_savings_plan_price(instance_type, os_type, region, '1yr', plan_type='COMPUTE_SP')
            except Exception as e:
                print(f"⚠️  1-Year Compute Savings Plan API failed, using fallback: {e}")
                # Fallback: Get On-Demand and apply typical 42% discount
                on_demand_price = self.get_ec2_price_by_term(instance_type, os_type, region, 'on_demand')
                return on_demand_price * 0.58  # 42% discount from On-Demand
        
        # Handle 1-Year EC2 Instance Savings Plan
        if term == '1yr_ec2_sp':
            try:
                return self.get_savings_plan_price(instance_type, os_type, region, '1yr', plan_type='EC2_INSTANCE_SP')
            except Exception as e:
                print(f"⚠️  1-Year EC2 Instance Savings Plan API failed, using fallback: {e}")
                # Fallback: Get On-Demand and apply typical 38% discount
                on_demand_price = self.get_ec2_price_by_term(instance_type, os_type, region, 'on_demand')
                return on_demand_price * 0.62  # 38% discount from On-Demand
        if not self.pricing_client:
            raise Exception("Pricing API not available")
        
        location = self.REGION_LOCATIONS.get(region, 'US East (N. Virginia)')
        
        try:
            filters = [
                {'Type': 'TERM_MATCH', 'Field': 'instanceType', 'Value': instance_type},
                {'Type': 'TERM_MATCH', 'Field': 'operatingSystem', 'Value': os_type},
                {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': location},
                {'Type': 'TERM_MATCH', 'Field': 'tenancy', 'Value': 'Shared'},
                {'Type': 'TERM_MATCH', 'Field': 'preInstalledSw', 'Value': 'NA'},
                {'Type': 'TERM_MATCH', 'Field': 'capacitystatus', 'Value': 'Used'}
            ]
            
            response = self.pricing_client.get_products(
                ServiceCode='AmazonEC2',
                Filters=filters,
                MaxResults=100
            )
            
            if not response.get('PriceList'):
                raise Exception(f"No pricing found for {instance_type} {os_type} in {region}")
            
            # Parse pricing data
            for price_item in response['PriceList']:
                price_data = json.loads(price_item)
                
                if term == 'on_demand':
                    # Look in On-Demand terms
                    terms = price_data.get('terms', {}).get('OnDemand', {})
                    for term_key, term_data in terms.items():
                        price_dimensions = term_data.get('priceDimensions', {})
                        for dimension in price_dimensions.values():
                            price_per_unit = dimension.get('pricePerUnit', {})
                            if 'USD' in price_per_unit:
                                return float(price_per_unit['USD'])
                else:
                    # Look in Reserved Instance terms
                    terms = price_data.get('terms', {}).get('Reserved', {})
                    for term_key, term_data in terms.items():
                        term_attributes = term_data.get('termAttributes', {})
                        
                        # Check for matching term and purchase option
                        if (term_attributes.get('LeaseContractLength') == term and
                            term_attributes.get('PurchaseOption') == purchase_option):
                            
                            # Extract hourly rate
                            price_dimensions = term_data.get('priceDimensions', {})
                            for dimension in price_dimensions.values():
                                price_per_unit = dimension.get('pricePerUnit', {})
                                if 'USD' in price_per_unit:
                                    return float(price_per_unit['USD'])
            
            raise Exception(f"{term} {purchase_option} pricing not found for {instance_type}")
            
        except Exception as e:
            print(f"⚠ API pricing failed for {instance_type} ({term}): {e}")
            raise
    
    @lru_cache(maxsize=500)
    def get_rds_price_from_api(self, instance_type: str, engine: str, region: str, term: str = '3yr', purchase_option: str = 'No Upfront', deployment_type: str = 'Single-AZ') -> float:
        """
        Get RDS pricing from AWS Price List API
        
        Args:
            instance_type: RDS instance type (e.g., 'db.m6i.xlarge')
            engine: Database engine ('MySQL', 'PostgreSQL', 'Oracle', 'SQL Server', 'MariaDB')
            region: AWS region code
            term: '1yr' or '3yr' for Reserved Instances, 'on_demand' for On-Demand
            purchase_option: 'No Upfront', 'Partial Upfront', or 'All Upfront'
            deployment_type: 'Single-AZ' or 'Multi-AZ'
        
        Returns:
            Hourly rate
        
        Note: Oracle RDS does not support 'No Upfront' for 3-year RIs. 
              Will automatically use 'Partial Upfront' for Oracle.
        """
        if not self.pricing_client:
            raise Exception("Pricing API not available")
        
        location = self.REGION_LOCATIONS.get(region, 'US East (N. Virginia)')
        
        # Map engine names to AWS API format
        engine_map = {
            'mysql': 'MySQL',
            'postgresql': 'PostgreSQL',
            'postgres': 'PostgreSQL',
            'oracle': 'Oracle',
            'sqlserver': 'SQL Server',
            'sql server': 'SQL Server',
            'mariadb': 'MariaDB'
        }
        aws_engine = engine_map.get(engine.lower(), engine)
        
        # RDS special handling: No Upfront not available for 3-year RIs (all engines)
        original_purchase_option = purchase_option
        if term == '3yr' and purchase_option == 'No Upfront':
            purchase_option = 'Partial Upfront'
            print(f"ℹ️  {aws_engine} RDS: Using 'Partial Upfront' (No Upfront not available for 3-year RIs)")
        
        try:
            filters = [
                {'Type': 'TERM_MATCH', 'Field': 'instanceType', 'Value': instance_type},
                {'Type': 'TERM_MATCH', 'Field': 'databaseEngine', 'Value': aws_engine},
                {'Type': 'TERM_MATCH', 'Field': 'deploymentOption', 'Value': deployment_type},
                {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': location},
            ]
            
            response = self.pricing_client.get_products(
                ServiceCode='AmazonRDS',
                Filters=filters,
                MaxResults=100
            )
            
            if not response.get('PriceList'):
                raise Exception(f"No pricing found for {instance_type} {engine} in {region}")
            
            # Parse pricing data
            for price_item in response['PriceList']:
                price_data = json.loads(price_item)
                
                if term == 'on_demand':
                    # Look in On-Demand terms
                    terms = price_data.get('terms', {}).get('OnDemand', {})
                    for term_key, term_data in terms.items():
                        price_dimensions = term_data.get('priceDimensions', {})
                        for dimension in price_dimensions.values():
                            price_per_unit = dimension.get('pricePerUnit', {})
                            if 'USD' in price_per_unit:
                                return float(price_per_unit['USD'])
                else:
                    # Look in Reserved Instance terms
                    terms = price_data.get('terms', {}).get('Reserved', {})
                    for term_key, term_data in terms.items():
                        term_attributes = term_data.get('termAttributes', {})
                        
                        # Check for matching term and purchase option
                        if (term_attributes.get('LeaseContractLength') == term and
                            term_attributes.get('PurchaseOption') == purchase_option):
                            
                            # Extract hourly rate AND upfront fee (for Partial/All Upfront)
                            price_dimensions = term_data.get('priceDimensions', {})
                            hourly_rate = None
                            upfront_fee = 0.0
                            
                            for dimension in price_dimensions.values():
                                unit = dimension.get('unit', '')
                                price_per_unit = dimension.get('pricePerUnit', {})
                                
                                if 'USD' in price_per_unit:
                                    price = float(price_per_unit['USD'])
                                    
                                    if unit == 'Hrs':
                                        hourly_rate = price
                                    elif unit == 'Quantity':
                                        upfront_fee = price
                            
                            if hourly_rate is not None:
                                # Store upfront fee in instance variable for later retrieval
                                self._last_upfront_fee = upfront_fee
                                return hourly_rate
            
            raise Exception(f"{term} {purchase_option} pricing not found for {instance_type} {engine}")
            
        except Exception as e:
            print(f"⚠ API pricing failed for {instance_type} {engine} ({term}): {e}")
            raise
    
    @lru_cache(maxsize=500)
    def get_savings_plan_price(self, instance_type: str, os_type: str, region: str, term: str = '3yr', plan_type: str = 'EC2_INSTANCE_SP') -> float:
        """
        Get Savings Plan pricing from AWS Savings Plans API
        
        Args:
            instance_type: EC2 instance type (e.g., 'm5.xlarge')
            os_type: 'Linux' or 'Windows'
            region: AWS region code
            term: '1yr' or '3yr'
            plan_type: 'COMPUTE_SP' for Compute Savings Plan or 'EC2_INSTANCE_SP' for EC2 Instance Savings Plan
        
        Returns:
            Hourly rate for Savings Plan
        """
        try:
            sp_client = boto3.client('savingsplans', region_name='us-east-1')  # API is in us-east-1
            
            # Map term to duration
            duration_seconds = 94608000 if term == '3yr' else 31536000  # 3 years or 1 year in seconds
            
            # Map OS type
            os_map = {'Linux': 'Linux/UNIX', 'Windows': 'Windows'}
            platform = os_map.get(os_type, 'Linux/UNIX')
            
            # Build filters based on plan type
            filters = [
                {'name': 'region', 'values': [region]},
                {'name': 'productDescription', 'values': [platform]},
                {'name': 'tenancy', 'values': ['shared']}
            ]
            
            # For EC2 Instance Savings Plan, we need to filter by instance type
            # For Compute Savings Plan, instance type filter is not applicable (it's more flexible)
            if plan_type == 'EC2_INSTANCE_SP':
                filters.append({'name': 'instanceType', 'values': [instance_type]})
            
            # Map plan_type to AWS API enum values
            api_plan_type = 'EC2Instance' if plan_type == 'EC2_INSTANCE_SP' else 'Compute'
            
            # Get Savings Plan offering rates (with pagination support for Compute SP)
            next_token = None
            max_pages = 5  # Limit pagination to prevent infinite loops
            page = 0
            
            while page < max_pages:
                page += 1
                
                params = {
                    'savingsPlanOfferingIds': [],
                    'savingsPlanPaymentOptions': ['No Upfront'],
                    'savingsPlanTypes': [api_plan_type],
                    'products': ['EC2'],
                    'serviceCodes': ['AmazonEC2'],
                    'filters': filters,
                    'maxResults': 1000
                }
                
                if next_token:
                    params['nextToken'] = next_token
                
                response = sp_client.describe_savings_plans_offering_rates(**params)
                
                # Find matching rate
                for offering in response.get('searchResults', []):
                    if offering.get('savingsPlanOffering', {}).get('durationSeconds') == duration_seconds:
                        # For Compute SP, we need to match instance type from properties
                        if plan_type == 'COMPUTE_SP':
                            properties = offering.get('properties', [])
                            instance_match = False
                            for prop in properties:
                                if prop.get('name') == 'instanceType' and prop.get('value') == instance_type:
                                    instance_match = True
                                    break
                            if not instance_match:
                                continue
                        
                        # Get the rate
                        rate = float(offering.get('rate', 0))
                        if rate > 0:
                            return rate
                
                # Check if there are more pages
                next_token = response.get('nextToken')
                if not next_token:
                    break
            
            raise Exception(f"No {plan_type} rate found for {instance_type} {os_type} in {region}")
            
        except Exception as e:
            print(f"⚠️  Savings Plan API error ({plan_type}): {e}")
            raise
    
    def _get_regional_multiplier(self, region: str) -> float:
        """Get pricing multiplier for different regions (relative to us-east-1)"""
        multipliers = {
            'us-east-1': 1.0,
            'us-east-2': 1.0,
            'us-west-1': 1.05,
            'us-west-2': 1.0,
            'eu-west-1': 1.05,
            'eu-west-2': 1.05,
            'eu-west-3': 1.08,
            'eu-central-1': 1.08,
            'ap-southeast-1': 1.10,
            'ap-southeast-2': 1.10,
            'ap-northeast-1': 1.12,
            'ap-south-1': 1.08,
            'ca-central-1': 1.05,
            'sa-east-1': 1.25,
        }
        return multipliers.get(region, 1.0)
    
    def apply_right_sizing(self, vcpu: int, memory_gb: float, storage_gb: float,
                          cpu_util: Optional[float] = None, 
                          memory_util: Optional[float] = None,
                          storage_used_gb: Optional[float] = None) -> Tuple[int, float, float]:
        """
        Apply right-sizing based on actual utilization
        
        Args:
            vcpu: Provisioned vCPUs
            memory_gb: Provisioned memory in GB
            storage_gb: Provisioned storage in GB
            cpu_util: CPU utilization percentage (0-100)
            memory_util: Memory utilization percentage (0-100)
            storage_used_gb: Actually used storage in GB
        
        Returns:
            Tuple of (right_sized_vcpu, right_sized_memory_gb, right_sized_storage_gb)
        """
        if not RIGHT_SIZING_CONFIG.get('enable_right_sizing', False):
            return vcpu, memory_gb, storage_gb
        
        # Right-size CPU
        if cpu_util is not None and cpu_util > 0:
            # Use actual utilization data
            headroom = RIGHT_SIZING_CONFIG.get('cpu_headroom_percentage', 0) / 100
            required_vcpu = (vcpu * cpu_util / 100) * (1 + headroom)
            vcpu = max(int(required_vcpu), RIGHT_SIZING_CONFIG.get('min_vcpu', 2))
        else:
            # No utilization data - apply ATX assumption (25% peak utilization)
            peak_util = RIGHT_SIZING_CONFIG.get('cpu_peak_utilization_percent', 25) / 100
            headroom = RIGHT_SIZING_CONFIG.get('cpu_headroom_percentage', 0) / 100
            required_vcpu = (vcpu * peak_util) * (1 + headroom)
            vcpu = max(int(required_vcpu), RIGHT_SIZING_CONFIG.get('min_vcpu', 2))
        
        # Right-size Memory
        if memory_util is not None and memory_util > 0:
            # Use actual utilization data
            headroom = RIGHT_SIZING_CONFIG.get('memory_headroom_percentage', 0) / 100
            required_memory = (memory_gb * memory_util / 100) * (1 + headroom)
            memory_gb = max(required_memory, RIGHT_SIZING_CONFIG.get('min_memory_gb', 4))
        else:
            # No utilization data - apply ATX assumption (60% peak utilization)
            peak_util = RIGHT_SIZING_CONFIG.get('memory_peak_utilization_percent', 60) / 100
            headroom = RIGHT_SIZING_CONFIG.get('memory_headroom_percentage', 0) / 100
            required_memory = (memory_gb * peak_util) * (1 + headroom)
            memory_gb = max(required_memory, RIGHT_SIZING_CONFIG.get('min_memory_gb', 4))
        
        # Right-size Storage
        if storage_used_gb is not None and storage_used_gb > 0:
            # Use actual storage usage data
            utilization = RIGHT_SIZING_CONFIG.get('storage_utilization_percent', 50) / 100
            headroom = RIGHT_SIZING_CONFIG.get('storage_headroom_percentage', 0) / 100
            # Calculate based on actual usage with headroom
            optimized_storage = storage_used_gb * (1 + headroom)
            storage_gb = max(optimized_storage, 10)  # Minimum 10 GB
        elif storage_gb is None or storage_gb == 0:
            # No storage data at all - use default
            storage_gb = RIGHT_SIZING_CONFIG.get('default_provisioned_storage_gib', 500)
        elif RIGHT_SIZING_CONFIG.get('storage_sizing_method') == 'used':
            # Have provisioned storage but no usage data - apply utilization assumption
            utilization = RIGHT_SIZING_CONFIG.get('storage_utilization_percent', 50) / 100
            headroom = RIGHT_SIZING_CONFIG.get('storage_headroom_percentage', 0) / 100
            storage_gb = storage_gb * utilization * (1 + headroom)
        
        return vcpu, memory_gb, storage_gb
    
    def calculate_vm_cost(self, vcpu: int, memory_gb: float, storage_gb: float, 
                         os: str, vm_name: str = '',
                         cpu_util: Optional[float] = None,
                         memory_util: Optional[float] = None,
                         storage_used_gb: Optional[float] = None,
                         pricing_model: str = None) -> Dict:
        """
        Calculate exact monthly cost for a single VM
        
        Args:
            vcpu: Number of vCPUs (provisioned)
            memory_gb: Memory in GB (provisioned)
            storage_gb: Storage in GB (provisioned)
            os: Operating system
            vm_name: VM name (for reference)
            cpu_util: CPU utilization % (optional, for right-sizing)
            memory_util: Memory utilization % (optional, for right-sizing)
            storage_used_gb: Actually used storage GB (optional, for right-sizing)
            pricing_model: Pricing model to use (overrides instance default)
        
        Returns:
            Dictionary with detailed cost breakdown
        """
        # Store original specs
        original_vcpu, original_memory_gb, original_storage_gb = vcpu, memory_gb, storage_gb
        
        # 0. Apply right-sizing if enabled and utilization data available
        vcpu, memory_gb, storage_gb = self.apply_right_sizing(
            vcpu, memory_gb, storage_gb,
            cpu_util, memory_util, storage_used_gb
        )
        
        # 1. Map to instance type (deterministic)
        prefer_graviton = PRICING_CONFIG.get('prefer_graviton', False)
        instance_type = self.map_vm_to_instance_type(vcpu, memory_gb, os, prefer_graviton)
        
        # 2. Determine OS type for pricing (use shared detection logic for consistency)
        from os_detection import detect_os_type
        os_type = detect_os_type(os)
        # For pricing, treat 'Other' as 'Linux' (more conservative estimate)
        if os_type == 'Other':
            os_type = 'Linux'
        
        # 3. Get exact EC2 pricing using specified or configured pricing model
        pricing_model = pricing_model or self.pricing_model or PRICING_CONFIG.get('pricing_model', '3yr_no_upfront')
        if pricing_model == '3yr_ec2_sp':
            # Use EC2 Instance Savings Plan pricing
            hourly_rate = self.get_ec2_price_by_term(instance_type, os_type, self.target_region, term='3yr_ec2_sp')
        elif pricing_model == '3yr_compute_sp':
            # Use Compute Savings Plan pricing
            hourly_rate = self.get_ec2_price_by_term(instance_type, os_type, self.target_region, term='3yr_compute_sp')
        else:
            # Use default RI pricing
            hourly_rate = self.get_ec2_price(instance_type, os_type)
        
        # 4. Calculate compute cost (730 hours/month average)
        monthly_compute = hourly_rate * 730
        
        # 5. Calculate storage cost (EBS gp3: configurable rate per GB-month)
        base_storage_rate = PRICING_CONFIG.get('storage_rate_per_gb', 0.08)
        storage_rate = base_storage_rate * self._get_regional_multiplier(self.target_region)
        monthly_storage = storage_gb * storage_rate
        
        # 6. Calculate data transfer (configurable percentage of compute cost)
        data_transfer_pct = PRICING_CONFIG.get('data_transfer_percentage', 0.05)
        monthly_data_transfer = monthly_compute * data_transfer_pct
        
        # 7. Total monthly cost
        monthly_total = monthly_compute + monthly_storage + monthly_data_transfer
        
        result = {
            'vm_name': vm_name,
            'vcpu': vcpu,
            'memory_gb': round(memory_gb, 2),
            'storage_gb': round(storage_gb, 2),
            'os': os,
            'instance_type': instance_type,
            'os_type': os_type,
            'hourly_rate': round(hourly_rate, 4),
            'monthly_compute': round(monthly_compute, 2),
            'monthly_storage': round(monthly_storage, 2),
            'monthly_data_transfer': round(monthly_data_transfer, 2),
            'monthly_total': round(monthly_total, 2)
        }
        
        # Add right-sizing info if applied
        if RIGHT_SIZING_CONFIG.get('enable_right_sizing', False):
            result['right_sizing_applied'] = True
            result['original_vcpu'] = original_vcpu
            result['original_memory_gb'] = round(original_memory_gb, 2)
            result['original_storage_gb'] = round(original_storage_gb, 2)
            result['vcpu_reduction'] = round((1 - vcpu/original_vcpu) * 100, 1) if original_vcpu > 0 else 0
            result['memory_reduction'] = round((1 - memory_gb/original_memory_gb) * 100, 1) if original_memory_gb > 0 else 0
            result['storage_reduction'] = round((1 - storage_gb/original_storage_gb) * 100, 1) if original_storage_gb > 0 else 0
        
        return result
    
    def calculate_arr_from_dataframe(self, df: pd.DataFrame, pricing_model: str = None) -> Dict:
        """
        Calculate total ARR from RVTools DataFrame
        
        Args:
            df: DataFrame with columns: CPUs, Memory (MB), Provisioned MiB, OS, VM (name)
            pricing_model: Pricing model to use (overrides instance default)
        
        Returns:
            Dictionary with aggregated results and breakdown
        """
        # Use provided pricing_model or fall back to instance default
        pricing_model = pricing_model or self.pricing_model
        
        results = []
        
        print(f"\n{'='*80}")
        print(f"CALCULATING AWS ARR - DETERMINISTIC PRICING")
        print(f"{'='*80}")
        print(f"Region: {self.target_region}")
        print(f"Pricing Model: {pricing_model}")
        print(f"VMs to analyze: {len(df)}")
        print(f"{'='*80}\n")
        
        for idx, row in df.iterrows():
            # Extract VM specs
            vcpu = int(row.get('CPUs', 2))
            memory_mb = float(row.get('Memory', 8192))
            memory_gb = memory_mb / 1024
            
            # Storage column can have different names
            storage_col = None
            for col in ['Provisioned MiB', 'Provisioned MB', 'Total disk capacity MiB']:
                if col in row.index:
                    storage_col = col
                    break
            
            storage_mb = float(row.get(storage_col, 102400)) if storage_col else 102400
            storage_gb = storage_mb / 1024
            
            # OS detection - try multiple column names (prioritize VMware Tools over config file)
            # RVTools column names: "OS according to the VMware Tools" or "OS according to the configuration file"
            os = None
            for os_col in ['OS according to the VMware Tools', 'OS according to the configuration file', 'OS', 'Guest OS']:
                if os_col in row.index:
                    os_value = str(row.get(os_col, '')).strip()
                    if os_value and os_value.lower() not in ['nan', 'none', '', 'unknown']:
                        os = os_value
                        break
            
            # If no OS found, default to Linux (more conservative cost estimate)
            if not os:
                os = 'Linux'
            
            vm_name = str(row.get('VM', f'VM-{idx}'))
            
            # Calculate cost with specified pricing model
            cost = self.calculate_vm_cost(vcpu, memory_gb, storage_gb, os, vm_name, pricing_model=pricing_model)
            results.append(cost)
            
            # Progress indicator
            if (idx + 1) % 100 == 0:
                print(f"  Processed {idx + 1}/{len(df)} VMs...")
        
        # Create results DataFrame
        df_results = pd.DataFrame(results)
        
        # Calculate aggregates
        total_monthly = df_results['monthly_total'].sum()
        total_arr = total_monthly * 12
        
        # Breakdown by instance type
        instance_breakdown = df_results.groupby('instance_type').agg({
            'monthly_total': 'sum',
            'vm_name': 'count'
        }).rename(columns={'vm_name': 'vm_count'})
        instance_breakdown['monthly_cost'] = instance_breakdown['monthly_total']
        instance_breakdown = instance_breakdown[['vm_count', 'monthly_cost']].to_dict('index')
        
        # Breakdown by OS
        os_breakdown = df_results.groupby('os_type').agg({
            'monthly_total': 'sum',
            'vm_name': 'count'
        }).rename(columns={'vm_name': 'vm_count'})
        os_breakdown['monthly_cost'] = os_breakdown['monthly_total']
        os_breakdown = os_breakdown[['vm_count', 'monthly_cost']].to_dict('index')
        
        # Cost component breakdown
        total_compute = df_results['monthly_compute'].sum()
        total_storage = df_results['monthly_storage'].sum()
        total_data_transfer = df_results['monthly_data_transfer'].sum()
        
        print(f"\n{'='*80}")
        print(f"CALCULATION COMPLETE")
        print(f"{'='*80}")
        print(f"Total VMs: {len(results)}")
        print(f"Total Monthly Cost: ${total_monthly:,.2f}")
        print(f"Total Annual Cost (ARR): ${total_arr:,.2f}")
        print(f"{'='*80}\n")
        
        return {
            'summary': {
                'total_vms': len(results),
                'total_monthly_cost': round(total_monthly, 2),
                'total_arr': round(total_arr, 2),
                'region': self.target_region,
                'pricing_model': pricing_model
            },
            'cost_breakdown': {
                'monthly_compute': round(total_compute, 2),
                'monthly_storage': round(total_storage, 2),
                'monthly_data_transfer': round(total_data_transfer, 2),
                'monthly_total': round(total_monthly, 2)
            },
            'instance_type_breakdown': instance_breakdown,
            'os_breakdown': os_breakdown,
            'detailed_results': df_results
        }


if __name__ == "__main__":
    # Test the pricing calculator
    print("Testing AWS Pricing Calculator...")
    
    calculator = AWSPricingCalculator(region='us-east-1', use_api=False)
    
    # Test single VM calculation
    print("\n=== Test 1: Single VM Calculation ===")
    result = calculator.calculate_vm_cost(
        vcpu=4,
        memory_gb=16,
        storage_gb=100,
        os='Windows Server 2019',
        vm_name='test-vm-01'
    )
    
    print(f"VM: {result['vm_name']}")
    print(f"Instance Type: {result['instance_type']}")
    print(f"Hourly Rate: ${result['hourly_rate']}")
    print(f"Monthly Cost: ${result['monthly_total']}")
    
    # Test instance type mapping
    print("\n=== Test 2: Instance Type Mapping ===")
    test_cases = [
        (2, 8, 'Linux', 'm5.large'),
        (4, 16, 'Windows', 'm5.xlarge'),
        (8, 16, 'Linux', 'c5.2xlarge'),  # Compute optimized
        (4, 32, 'Linux', 'r5.xlarge'),   # Memory optimized
    ]
    
    for vcpu, memory, os, expected in test_cases:
        mapped = calculator.map_vm_to_instance_type(vcpu, memory, os)
        status = "✓" if mapped == expected else "✗"
        print(f"{status} {vcpu} vCPU, {memory} GB → {mapped} (expected: {expected})")
    
    print("\n✓ Pricing calculator tests complete")
