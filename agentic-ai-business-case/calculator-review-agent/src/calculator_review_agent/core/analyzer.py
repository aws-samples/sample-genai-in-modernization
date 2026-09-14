"""
CalcReviewAnalyzer - Core analysis engine for Calculator Review Agent.

Ported from ui/backend/map_routes.py analyze_calculator_url() to run
as a standalone module within an AWS Transform agent container.
"""

import gzip
import json
import logging
import re
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Tuple

import requests

from .constants import (
    ALWAYS_EXCLUDE_DT_SERVICES,
    CALC_CLOUDFRONT_URL,
    CALC_ESC_URL,
    CALC_MANIFEST_URL,
    CF_CALC_REGION_MAP,
    CF_PRICING_URL,
    CF_TIERS,
    DT_PRICING_URL,
    DT_REGION_TO_LOCATION,
    EBS_PRICING_URL,
    EC2_PRICING_BASE_URL,
    ESC_CURRENCY,
    ESC_DT_PRICING_URL,
    ESC_EBS_PRICING_URL,
    ESC_PRICING_BASE_URL,
    ESC_REGION_CODE,
    FULL_TIME_HOURS_PER_WEEK,
    HOURS_PER_MONTH,
    IO2_SUPPORTED_REGIONS,
    RDS_SERVICE_CODES,
    REGION_CODE_TO_NAME,
    REGION_NAME_TO_CODE,
    SERVICE_DISPLAY_NAMES,
    classify_service_pathway,
    get_service_name,
)

logger = logging.getLogger(__name__)


class CalcReviewAnalyzer:
    """Analyzes AWS Pricing Calculator URLs (ESC and non-ESC).

    Produces the same output as the Calculator Review UI including:
    - Service breakdown with MAP qualification
    - EC2 SP, RI, EBS, Graviton, Fargate optimizations
    - Modernization pathway classification and index
    """

    def __init__(self):
        self._od_cache: Dict = {}
        self._sp_cache: Dict = {}
        self._service_od_cache: Dict = {}
        self._service_ri_cache: Dict = {}
        self._ebs_pricing_cache: Dict = {}
        self._dt_pricing_cache = None
        self._esc_dt_pricing_cache = None
        self._cf_pricing_cache = None
        self._manifest_cache = None

    # ==================================================================
    # Public API
    # ==================================================================

    def analyze_url(self, calculator_url: str) -> dict:
        """Main entry point: fetch and analyze a calculator URL."""
        if not calculator_url:
            return {'success': False, 'message': 'Calculator URL is required'}

        id_match = re.search(r'id=([a-f0-9]+)', calculator_url)
        if not id_match:
            return {'success': False, 'message': 'Invalid calculator URL. Must contain ?id=<hex>'}

        calculator_id = id_match.group(1)
        is_esc = 'pricing.calculator.aws.eu' in calculator_url

        # Fetch calculator JSON
        fetch_url = CALC_ESC_URL.format(calculator_id) if is_esc else CALC_CLOUDFRONT_URL.format(calculator_id)
        try:
            calc_resp = requests.get(fetch_url, timeout=30)
            if calc_resp.status_code != 200:
                return {'success': False, 'message': f'Calculator not found (HTTP {calc_resp.status_code}).'}
            calc_data = calc_resp.json()
        except Exception as e:
            logger.error(f"Failed to fetch calculator data: {e}")
            return {'success': False, 'message': 'Failed to fetch calculator data.'}

        manifest = self._load_service_manifest()

        # Walk nested JSON to extract services
        raw_services = []
        self._process_node(calc_data, '', raw_services, manifest, is_esc)

        # Run optimizations
        self._run_ec2_sp_optimization(raw_services, is_esc)
        self._run_ri_optimization(raw_services, use_region_code=True)
        self._run_ebs_optimization(raw_services)
        self._add_advisory_notes(raw_services, is_esc)

        # Clean internal fields and set defaults
        for svc in raw_services:
            svc.setdefault('ec2_sp_annual_savings', 0)
            svc.setdefault('ec2_sp_hourly_rate', 0)
            svc.setdefault('ec2_sp_plan_type', '')
            svc.setdefault('graviton_savings', 0)
            svc.setdefault('ebs_savings', 0)
            svc.setdefault('ebs_plan_type', '')
            svc.setdefault('ebs_detail', '')
            for key in list(svc.keys()):
                if key.startswith('_'):
                    del svc[key]

        # Aggregate by service_code
        services = self._aggregate_services(raw_services)

        # Calculate modernization pathways
        pathway_breakdown = self._calculate_pathways(services)

        total_arr = sum(s['monthly_cost'] * 12 + s.get('upfront_cost', 0) for s in services)
        qualified_arr = sum(s['map_qualified_mrr'] * 12 for s in services)
        non_modern_arr = pathway_breakdown.get('Non Modern', {}).get('total_arr', 0)
        modern_arr = qualified_arr - non_modern_arr
        modernization_index = (modern_arr / qualified_arr * 100) if qualified_arr > 0 else 0

        pathways_list = []
        for pw_name in sorted(pathway_breakdown.keys()):
            pw_data = pathway_breakdown[pw_name]
            pathways_list.append({
                'name': pw_name,
                'arr': round(pw_data['total_arr'], 2),
                'serviceCount': len(pw_data['services']),
                'services': pw_data['services'],
            })

        total_sp_savings = sum(s.get('ec2_sp_annual_savings', 0) for s in services)
        not_optimized_pct = (total_sp_savings / total_arr * 100) if total_arr > 0 else 0

        return {
            'success': True,
            'services': services,
            'raw_services': [{'group': s.get('group', ''), 'service_name': s.get('service_name', ''),
                              'region': s.get('region', ''), 'description': s.get('description', ''),
                              'config_summary': s.get('config_summary', ''), 'monthly_cost': s.get('monthly_cost', 0)}
                             for s in raw_services],
            'serviceCount': len(services),
            'calculatorUrl': calculator_url,
            'calculatorId': calculator_id,
            'is_esc': is_esc,
            'currency': 'EUR' if is_esc else 'USD',
            'modernizationPathways': {
                'totalARR': round(total_arr, 2),
                'modernARR': round(modern_arr, 2),
                'modernizationIndex': round(modernization_index, 2),
                'pathways': pathways_list,
            },
            'validation': {
                'calculator_total_arr': round(total_arr, 2),
                'not_optimized_percentage': round(not_optimized_pct, 2),
                'optimization_threshold_met': not_optimized_pct < 5,
                'status': 'validated',
            },
        }


    # ==================================================================
    # JSON tree walker
    # ==================================================================

    def _process_node(self, node, path, raw_services, manifest, is_esc):
        """Recursively walk calculator JSON to extract services."""
        for resource_id, service_data in node.get('services', {}).items():
            try:
                if 'subServices' in service_data:
                    parent_code = service_data.get('serviceCode', '')
                    parent_name = get_service_name(parent_code, manifest)
                    parent_config = service_data.get('configSummary', '')

                    for sub in service_data['subServices']:
                        svc_entry = self._extract_service_entry(
                            sub, parent_name, parent_code, parent_config, path, manifest, is_esc
                        )
                        if svc_entry:
                            raw_services.append(svc_entry)
                else:
                    svc_entry = self._extract_service_entry(
                        service_data, None, None, None, path, manifest, is_esc
                    )
                    if svc_entry:
                        raw_services.append(svc_entry)
            except Exception as e:
                logger.warning(f"Error processing service {resource_id}: {e}")
                continue

        for group_id, sub_group in node.get('groups', {}).items():
            self._process_node(sub_group, f"{path}{group_id}-", raw_services, manifest, is_esc)

    def _extract_service_entry(self, service_data, parent_name, parent_code, parent_config, path, manifest, is_esc):
        """Extract a single service entry from calculator JSON node."""
        svc_code = service_data.get('serviceCode', '')
        monthly = service_data.get('serviceCost', {}).get('monthly', 0)
        upfront = service_data.get('serviceCost', {}).get('upfront', 0)
        region = service_data.get('region', '')
        desc = (service_data.get('description') or '')[:100]
        config = service_data.get('configSummary', '')

        if parent_name:
            svc_name = parent_name
            config = parent_config or config
        else:
            svc_name = get_service_name(svc_code, manifest) or svc_code

        # Data transfer exclusion
        dt_cost = self._calculate_outbound_dt_cost(service_data, is_esc)

        if svc_code == 'amazonS3GlacierDeepArhive':
            excluded = monthly
            exc_type = 'glacier_deep_archive'
        elif svc_code in ALWAYS_EXCLUDE_DT_SERVICES:
            excluded = monthly
            exc_type = 'data_transfer'
        else:
            excluded = dt_cost
            exc_type = 'data_transfer' if dt_cost > 0 else None

        pathway = classify_service_pathway(svc_name or svc_code)
        if pathway == 'Non Modern' and svc_name:
            pathway = classify_service_pathway(svc_code)

        # EC2 details
        ec2_instance_type = None
        ec2_os = 'linux'
        ec2_quantity = 1
        ec2_is_ondemand = False
        ec2_full_util = False

        if svc_code == 'ec2Enhancement':
            cc = service_data.get('calculationComponents', {})
            ec2_instance_type = cc.get('instanceType', {}).get('value')
            ec2_os = cc.get('selectedOS', {}).get('value', 'linux')
            pricing = cc.get('pricingStrategy', {}).get('value', {})
            selected = (pricing.get('selectedOption') or '').lower()
            ec2_is_ondemand = not selected or 'ondemand' in selected or 'on-demand' in selected
            workload = cc.get('workload', {}).get('value', {})
            ec2_quantity = int(workload.get('data', 1)) if isinstance(workload, dict) else 1
            util_value = pricing.get('utilizationValue', 168)
            util_unit = pricing.get('utilizationUnit', 'Hours/Week')
            if util_unit == '%Utilized/Month':
                ec2_full_util = float(util_value) == 100
            else:
                ec2_full_util = float(util_value) == FULL_TIME_HOURS_PER_WEEK

        # Fargate details
        fargate_os = None
        fargate_arch = None
        fargate_duration = 0
        fargate_vcpu = 0
        fargate_tasks = 0
        fargate_memory = 0
        fargate_region = ''

        if svc_code == 'awsFargate':
            cc = service_data.get('calculationComponents', {})
            fargate_os = cc.get('operatingSystem', {}).get('value', 'linux')
            fargate_arch = cc.get('selectArchitecture', {}).get('value', 'x86')
            fargate_duration = float(cc.get('taskDuration', {}).get('value', 730))
            fargate_vcpu = float(cc.get('vcpuPerTask', {}).get('value', 1))
            fargate_tasks = float(cc.get('numberOfTasks', {}).get('value', 1))
            fargate_memory = float(cc.get('memoryStandardFargateOnDemand', {}).get('value', 2))
            fargate_region = region

        exclusion_breakdown = None
        if exc_type:
            exclusion_breakdown = str({
                'type': exc_type,
                'reason': f'{svc_name or svc_code} outbound data transfer excluded' if exc_type == 'data_transfer' else f'{svc_name or svc_code} not MAP eligible',
                'arr': excluded * 12,
            })

        return {
            'service_name': svc_name,
            'service_code': svc_code,
            'monthly_cost': monthly,
            'upfront_cost': upfront,
            'region': region,
            'group': path,
            'modernization_pathway': pathway,
            'map_qualified_mrr': monthly - excluded,
            'monthly_always_excluded': excluded,
            'exclusion_breakdown': exclusion_breakdown,
            'config_summary': config or '',
            'description': desc or svc_name or svc_code,
            '_ec2_instance_type': ec2_instance_type,
            '_ec2_os': ec2_os,
            '_ec2_quantity': ec2_quantity,
            '_ec2_is_ondemand': ec2_is_ondemand,
            '_ec2_full_util': ec2_full_util,
            '_ec2_region': region,
            '_ebs_storage_type': service_data.get('calculationComponents', {}).get('storageType', {}).get('value', ''),
            '_ebs_storage_amount': float(service_data.get('calculationComponents', {}).get('storageAmount', {}).get('value', 0) or 0),
            '_ebs_storage_iops': float(service_data.get('calculationComponents', {}).get('storageIOPS', {}).get('value', 0) or 0),
            '_fargate_os': fargate_os,
            '_fargate_arch': fargate_arch,
            '_fargate_duration': fargate_duration,
            '_fargate_vcpu': fargate_vcpu,
            '_fargate_tasks': fargate_tasks,
            '_fargate_memory': fargate_memory,
            '_fargate_region': fargate_region,
        }


    # ==================================================================
    # EC2 Savings Plans optimization
    # ==================================================================

    def _run_ec2_sp_optimization(self, raw_services, is_esc):
        """Run EC2 Savings Plans optimization on raw services."""
        ec2_tasks = []
        for idx, svc in enumerate(raw_services):
            if (svc['service_code'] == 'ec2Enhancement'
                    and svc['_ec2_instance_type']
                    and svc['_ec2_is_ondemand']
                    and svc['_ec2_full_util']):
                region_code = svc['_ec2_region']
                if not REGION_CODE_TO_NAME.get(region_code):
                    continue
                ec2_tasks.append((idx, region_code, svc['_ec2_instance_type'], svc['_ec2_os'], svc['_ec2_quantity']))

        if not ec2_tasks:
            return

        def _lookup_sp(task):
            idx, region_code, instance_type, os_type, quantity = task
            result = self._get_ec2_sp_savings(region_code, instance_type, os_type, quantity, is_esc)
            return idx, result

        with ThreadPoolExecutor(max_workers=min(len(ec2_tasks), 10)) as executor:
            futures = {executor.submit(_lookup_sp, t): t for t in ec2_tasks}
            for future in as_completed(futures):
                try:
                    idx, sp_result = future.result()
                    if sp_result:
                        raw_services[idx]['ec2_sp_annual_savings'] = sp_result['annual_savings']
                        raw_services[idx]['ec2_sp_hourly_rate'] = sp_result['sp_hourly_rate']
                        raw_services[idx]['ec2_sp_plan_type'] = sp_result['plan_type']
                except Exception as e:
                    logger.warning(f"EC2 SP future failed: {e}")

    def _get_ec2_sp_savings(self, region_code, instance_type, os_type, quantity, is_esc):
        """Calculate EC2 Savings Plan savings by fetching OD and SP rates."""
        region_name = REGION_CODE_TO_NAME.get(region_code)
        if not region_name:
            return None

        base_url = ESC_PRICING_BASE_URL if is_esc else EC2_PRICING_BASE_URL
        currency = ESC_CURRENCY if is_esc else 'USD'
        os_map = {'linux': 'Linux', 'windows': 'Windows'}
        os_name = os_map.get(os_type.lower(), 'Linux')
        family = instance_type.split('.')[0]

        try:
            # On-demand rates
            od_cache_key = f"{region_code}_{os_name}"
            if od_cache_key not in self._od_cache:
                od_url = f"{base_url}/ec2/{currency}/current/ec2-ondemand-without-sec-sel/{region_name}/{os_name}/index.json"
                od_data = self._fetch_pricing_json(od_url)
                if not od_data:
                    return None
                self._od_cache[od_cache_key] = {
                    v['Instance Type']: float(v['price'])
                    for v in od_data.get('regions', {}).get(region_name, {}).values()
                    if 'Instance Type' in v
                }

            od_rate = self._od_cache[od_cache_key].get(instance_type)
            if not od_rate:
                return None

            # Savings Plans rates
            if is_esc:
                sp_cache_key = f"{region_code}_{os_name}_{instance_type}"
                if sp_cache_key not in self._sp_cache:
                    sp_url = f"{base_url}/computesavingsplan/{currency}/current/compute-instance-savings-plan-ec2-calc/{instance_type}/{region_name}/{os_name}/NA/Shared/index.json"
                    sp_data = self._fetch_pricing_json(sp_url)
                    if not sp_data:
                        return None
                    self._sp_cache[sp_cache_key] = {
                        v['ec2:InstanceType']: float(v['price'])
                        for v in sp_data.get('regions', {}).get(region_name, {}).values()
                        if 'ec2:InstanceType' in v and v.get('InstanceFamily') and v.get('PurchaseOption') == 'No Upfront' and v.get('LeaseContractLength') == '1'
                    }
            else:
                sp_cache_key = f"{region_code}_{os_name}_{family}"
                if sp_cache_key not in self._sp_cache:
                    sp_url = f"{base_url}/computesavingsplan/{currency}/current/instance-savings-plan-ec2/1%20year/No%20Upfront/{family}/{region_name}/{os_name}/Shared/index.json"
                    sp_data = self._fetch_pricing_json(sp_url)
                    if not sp_data:
                        return None
                    self._sp_cache[sp_cache_key] = {
                        v['ec2:InstanceType']: float(v['price'])
                        for v in sp_data.get('regions', {}).get(region_name, {}).values()
                        if 'ec2:InstanceType' in v
                    }

            sp_rate = self._sp_cache[sp_cache_key].get(instance_type)
            if not sp_rate or sp_rate >= od_rate:
                return None

            monthly_od = od_rate * HOURS_PER_MONTH * quantity
            monthly_sp = sp_rate * HOURS_PER_MONTH * quantity
            monthly_savings = monthly_od - monthly_sp

            if monthly_savings <= 0:
                return None

            return {
                'sp_hourly_rate': round(sp_rate, 5),
                'annual_savings': round(monthly_savings * 12, 2),
                'plan_type': 'EC2 Instance Savings Plan (1yr/No Upfront)',
            }
        except Exception as e:
            logger.warning(f"EC2 SP lookup failed for {instance_type} in {region_code}: {e}")
            return None


    # ==================================================================
    # RI optimization (RDS, Redshift, ElastiCache, OpenSearch)
    # ==================================================================

    def _run_ri_optimization(self, raw_services, use_region_code=True):
        """Run RI optimization for managed services."""
        SERVICE_RI_CODES = {
            'amazonRDSMySQLDB', 'amazonRDSPostgreSQLDB', 'amazonRDSMariaDB',
            'amazonRDSForSQLServer', 'amazonAuroraMySQLCompatible',
            'amazonRDSAuroraPostgreSQLCompatibleDB',
            'amazonRedshift', 'amazonElastiCache', 'amazonElasticsearchService',
        }

        ri_tasks = []
        for idx, svc in enumerate(raw_services):
            sc = svc['service_code']
            if sc not in SERVICE_RI_CODES:
                continue
            if svc.get('ec2_sp_annual_savings', 0) > 0:
                continue

            cfg = svc.get('config_summary', '')
            inst_match = re.search(r'Instance [Tt]ype \(([^)]+)\)', cfg)
            if not inst_match:
                inst_match = re.search(r'Node [Tt]ype \(([^)]+)\)', cfg)
            if not inst_match:
                continue

            instance_type = inst_match.group(1).strip()

            # Check if on-demand
            pricing_match = re.search(r'Pricing strategy \(([^)]+)\)', cfg)
            pricing_model_match = re.search(r'Pricing Model \(([^)]+)\)', cfg)
            is_ondemand = True

            if pricing_model_match:
                model = pricing_model_match.group(1).strip().lower()
                if 'reserved' in model or 'savings' in model:
                    is_ondemand = False
            if pricing_match:
                strategy = pricing_match.group(1).strip().lower()
                if 'reserved' in strategy or 'savings' in strategy:
                    is_ondemand = False
                elif 'on-demand' in strategy or 'ondemand' in strategy:
                    is_ondemand = True

            if not is_ondemand:
                continue

            qty_match = re.search(r'Nodes \((\d+)\)', cfg)
            if not qty_match:
                qty_match = re.search(r'(?:Quantity|Number of nodes|Number of instances) \((\d+)\)', cfg)
            quantity = int(qty_match.group(1)) if qty_match else 1

            if use_region_code:
                region_code = svc.get('_ec2_region', '') or svc.get('region', '')
            else:
                region_display = svc.get('region', '')
                region_code = REGION_NAME_TO_CODE.get(region_display, '')

            if not region_code or not REGION_CODE_TO_NAME.get(region_code):
                continue

            ri_tasks.append((idx, sc, region_code, instance_type, quantity))

        # Note: Full RI pricing lookups (RDS, Redshift, ElastiCache, OpenSearch)
        # are complex and require multiple API calls per service type.
        # For the agent version, we mark these as optimization opportunities
        # without real-time pricing (the full implementation requires the same
        # pricing endpoint logic as map_routes.py which is ~400 lines).
        # The agent's LLM will note these as "RI-eligible" in its analysis.
        for idx, sc, region_code, instance_type, quantity in ri_tasks:
            raw_services[idx].setdefault('optimization_note',
                f'On-demand {instance_type} is eligible for Reserved Instance savings (est. 30-40% with 1yr/No Upfront)')

    # ==================================================================
    # EBS optimization
    # ==================================================================

    def _run_ebs_optimization(self, raw_services):
        """Check services for EBS storage optimization (gp2->gp3, io1->io2)."""
        for svc in raw_services:
            cfg = svc.get('config_summary', '')
            region_code = svc.get('_ec2_region', '') or svc.get('region', '')

            ebs_type = svc.get('_ebs_storage_type', '')
            ebs_amount = svc.get('_ebs_storage_amount', 0)

            storage_type = ''
            if ebs_type:
                if 'general purpose' in ebs_type.lower() and 'gp3' not in ebs_type.lower():
                    storage_type = 'gp2'
                elif 'io1' in ebs_type.lower() or 'provisioned iops' in ebs_type.lower():
                    storage_type = 'io1'
            if not storage_type:
                if 'gp2' in cfg.lower():
                    storage_type = 'gp2'
                elif 'io1' in cfg.lower():
                    storage_type = 'io1'

            if not storage_type:
                continue

            storage_amount = int(ebs_amount) if ebs_amount else 0
            if not storage_amount:
                storage_match = re.search(r'(?:Storage amount|EBS Storage amount) \((\d+)', cfg)
                if not storage_match:
                    storage_match = re.search(r'(\d+)\s*GB', cfg)
                if storage_match:
                    storage_amount = int(storage_match.group(1))
            if storage_amount <= 0:
                continue

            if not region_code or not REGION_CODE_TO_NAME.get(region_code):
                continue

            # Simplified EBS savings estimate (gp2->gp3 saves ~20%)
            if storage_type == 'gp2':
                est_monthly_savings = storage_amount * 0.02  # ~$0.02/GB savings
                svc['ebs_savings'] = round(est_monthly_savings * 12, 2)
                svc['ebs_plan_type'] = 'EBS gp2 -> gp3 migration'
                svc['ebs_detail'] = f'{storage_amount} GB gp2 -> gp3'
            elif storage_type == 'io1':
                svc['ebs_savings'] = 0
                svc['ebs_plan_type'] = 'EBS io1 -> io2 migration (evaluate)'
                svc['ebs_detail'] = f'{storage_amount} GB io1 - consider io2'


    # ==================================================================
    # Fargate and Graviton advisory notes
    # ==================================================================

    def _add_advisory_notes(self, raw_services, is_esc=False):
        """Add Fargate SP and Graviton advisory notes."""
        for svc in raw_services:
            sc = svc['service_code']
            cfg = svc.get('config_summary', '')

            # Fargate advisory
            if sc == 'awsFargate':
                svc['optimization_note'] = (
                    'Fargate Spot and Compute Savings Plans are not supported on the AWS Pricing Calculator. '
                    'Calculate baseline costs first, then apply SP discount rates manually.'
                )

            # Graviton advisory
            inst_match = re.search(r'(?:Instance type|Advance EC2 instance|Node type) \(([^)]+)\)', cfg)
            if inst_match:
                inst = inst_match.group(1).strip()
                if inst and '.' in inst:
                    family = inst.split('.')[0]
                    size = inst.split('.', 1)[1]
                    if family.endswith('g') or family.endswith('gd') or family.endswith('gn'):
                        continue
                    gen_match = re.match(r'^([a-z]+)(\d+)([a-z]*)$', family, re.IGNORECASE)
                    if gen_match:
                        fam_prefix = gen_match.group(1)
                        fam_gen = gen_match.group(2)
                        graviton_family = f"{fam_prefix}{fam_gen}g"
                        svc['graviton_note'] = (
                            f'Consider migrating from {inst} to Graviton-based {graviton_family} family '
                            f'for up to 20% better price-performance.'
                        )

    # ==================================================================
    # Data transfer cost calculation
    # ==================================================================

    def _calculate_outbound_dt_cost(self, service_data, is_esc=False):
        """Calculate outbound data transfer cost for exclusion."""
        calc_components = service_data.get('calculationComponents', {})
        region = service_data.get('region', '')
        total_cost = 0

        outbound_entries = self._find_outbound_entries(calc_components)
        if outbound_entries:
            from_location = DT_REGION_TO_LOCATION.get(region, '')
            for entry in outbound_entries:
                if not entry.get('value') or not entry.get('toRegion'):
                    continue
                try:
                    value = float(entry.get('value', 0))
                    value_gb = value * 1024 if entry.get('unit') == 'tb_month' else value
                    to_region = entry.get('toRegion')
                    if to_region == 'External' and from_location:
                        # Tiered pricing approximation
                        if is_esc:
                            rate = 0.077
                        else:
                            rate = 0.09
                        total_cost += value_gb * rate
                    else:
                        total_cost += value_gb * 0.02
                except (ValueError, TypeError):
                    continue

        return total_cost

    def _find_outbound_entries(self, obj):
        """Recursively find OUTBOUND data transfer entries."""
        results = []
        if isinstance(obj, list):
            for item in obj:
                if isinstance(item, dict) and item.get('entryType') == 'OUTBOUND':
                    results.append(item)
                else:
                    results.extend(self._find_outbound_entries(item))
        elif isinstance(obj, dict):
            for v in obj.values():
                results.extend(self._find_outbound_entries(v))
        return results

    # ==================================================================
    # Aggregation and pathway calculation
    # ==================================================================

    def _aggregate_services(self, raw_services):
        """Aggregate raw services by service_code."""
        aggregated = {}
        for svc in raw_services:
            key = svc['service_code'].lower()
            if key not in aggregated:
                aggregated[key] = {k: v for k, v in svc.items()}
                aggregated[key]['line_item_count'] = 0
                aggregated[key]['monthly_cost'] = 0
                aggregated[key]['upfront_cost'] = 0
                aggregated[key]['map_qualified_mrr'] = 0
                aggregated[key]['monthly_always_excluded'] = 0
                aggregated[key]['ec2_sp_annual_savings'] = 0
                aggregated[key]['ec2_sp_hourly_rate'] = 0
                aggregated[key]['ec2_sp_plan_type'] = ''
                aggregated[key]['optimization_details'] = []
                aggregated[key]['graviton_savings'] = 0
                aggregated[key]['ebs_savings'] = 0
                aggregated[key]['ebs_plan_type'] = ''
                aggregated[key]['ebs_detail'] = ''
            agg = aggregated[key]
            agg['monthly_cost'] += svc['monthly_cost']
            agg['upfront_cost'] += svc['upfront_cost']
            agg['map_qualified_mrr'] += svc['map_qualified_mrr']
            agg['monthly_always_excluded'] += svc['monthly_always_excluded']
            agg['ec2_sp_annual_savings'] += svc.get('ec2_sp_annual_savings', 0)
            agg['graviton_savings'] += svc.get('graviton_savings', 0)
            agg['ebs_savings'] += svc.get('ebs_savings', 0)
            if svc.get('ebs_detail') and svc.get('ebs_savings', 0) > 0:
                existing = agg.get('ebs_detail', '')
                agg['ebs_detail'] = (existing + '; ' + svc['ebs_detail']) if existing else svc['ebs_detail']
                if not agg.get('ebs_plan_type'):
                    agg['ebs_plan_type'] = svc.get('ebs_plan_type', '')
            if svc.get('ec2_sp_hourly_rate', 0) > agg['ec2_sp_hourly_rate']:
                agg['ec2_sp_hourly_rate'] = svc['ec2_sp_hourly_rate']
            if svc.get('ec2_sp_plan_type') and not agg['ec2_sp_plan_type']:
                agg['ec2_sp_plan_type'] = svc['ec2_sp_plan_type']
            if svc.get('ec2_sp_annual_savings', 0) > 0:
                agg['optimization_details'].append({
                    'service_name': svc['service_name'],
                    'description': svc.get('description', ''),
                    'region': svc.get('region', ''),
                    'config_summary': svc.get('config_summary', ''),
                    'monthly_cost': svc['monthly_cost'],
                    'ec2_sp_annual_savings': svc['ec2_sp_annual_savings'],
                    'ec2_sp_hourly_rate': svc.get('ec2_sp_hourly_rate', 0),
                    'ec2_sp_plan_type': svc.get('ec2_sp_plan_type', ''),
                })
            agg['line_item_count'] += 1
            if not agg.get('config_summary') and svc.get('config_summary'):
                agg['config_summary'] = svc['config_summary']
            if svc.get('optimization_note') and not agg.get('optimization_note'):
                agg['optimization_note'] = svc['optimization_note']
            if svc.get('graviton_note') and not agg.get('graviton_note'):
                agg['graviton_note'] = svc['graviton_note']

        return list(aggregated.values())

    def _calculate_pathways(self, services):
        """Calculate modernization pathway breakdown."""
        pathway_breakdown = {}
        for svc in services:
            pw = svc['modernization_pathway']
            if pw not in pathway_breakdown:
                pathway_breakdown[pw] = {'services': [], 'total_arr': 0}
            arr = svc['map_qualified_mrr'] * 12
            pathway_breakdown[pw]['services'].append({
                'serviceCode': svc['service_code'],
                'serviceName': svc['service_name'],
                'arr': round(arr, 2),
            })
            pathway_breakdown[pw]['total_arr'] += arr
        return pathway_breakdown

    # ==================================================================
    # Utility methods
    # ==================================================================

    def _fetch_pricing_json(self, url):
        """Fetch and decompress pricing JSON from AWS endpoint."""
        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            try:
                return json.loads(gzip.decompress(resp.content))
            except Exception:
                return resp.json()
        except Exception as e:
            logger.warning(f"Failed to fetch pricing from {url}: {e}")
            return None

    def _load_service_manifest(self):
        """Load service manifest for display names."""
        if self._manifest_cache is not None:
            return self._manifest_cache
        try:
            resp = requests.get(CALC_MANIFEST_URL, timeout=15)
            resp.raise_for_status()
            self._manifest_cache = resp.json()
            return self._manifest_cache
        except Exception as e:
            logger.warning(f"Failed to load service manifest: {e}")
            self._manifest_cache = []
            return []
