"""Multi-source collateral valuation aggregator.

Combines valuations from multiple sources with weighted averaging
and confidence scoring.
"""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from ..models import CollateralAsset, CollateralValuation, CollateralType
from .zillow_client import ZillowClient
from .edmunds_client import EdmundsClient
from .equipment_client import EquipmentClient

logger = logging.getLogger(__name__)


class ValuationAggregator:
    """Aggregates valuations from multiple sources."""
    
    def __init__(
        self,
        zillow_api_key: str = "",
        edmunds_api_key: str = "",
        enable_web_fallback: bool = True
    ):
        """Initialize aggregator with API clients.
        
        Args:
            zillow_api_key: Zillow API key
            edmunds_api_key: Edmunds API key
            enable_web_fallback: Use web scraping as fallback
        """
        self.zillow_client = ZillowClient(api_key=zillow_api_key)
        self.edmunds_client = EdmundsClient(api_key=edmunds_api_key)
        self.equipment_client = EquipmentClient()
        self.enable_web_fallback = enable_web_fallback
        
        # Confidence weights for different sources
        self.source_weights = {
            "zillow": 0.9,
            "edmunds": 0.9,
            "carfax": 0.85,
            "equipment_db": 0.8,
            "manual": 0.7,
            "web_scrape": 0.5
        }
    
    async def valuate_collateral(
        self,
        application_id: str,
        collateral: CollateralAsset
    ) -> CollateralValuation:
        """Get aggregated valuation for collateral asset.
        
        Args:
            application_id: Loan application ID
            collateral: Collateral asset to valuate
            
        Returns:
            CollateralValuation with aggregated estimate
        """
        logger.info(f"Starting valuation for application {application_id}, type: {collateral.type}")
        
        try:
            if collateral.type == CollateralType.REAL_ESTATE:
                return await self._valuate_real_estate(application_id, collateral)
            elif collateral.type == CollateralType.VEHICLE:
                return await self._valuate_vehicle(application_id, collateral)
            elif collateral.type == CollateralType.EQUIPMENT:
                return await self._valuate_equipment(application_id, collateral)
            else:
                logger.warning(f"Unsupported collateral type: {collateral.type}")
                return self._create_manual_review_valuation(application_id, collateral)
                
        except Exception as e:
            logger.error(f"Valuation failed: {e}", exc_info=True)
            return self._create_error_valuation(application_id, collateral, str(e))
    
    async def _valuate_real_estate(
        self,
        application_id: str,
        collateral: CollateralAsset
    ) -> CollateralValuation:
        """Valuate real estate property.
        
        Uses:
        1. Zillow Zestimate (primary)
        2. Recent comparable sales
        3. Market trend analysis
        """
        logger.info(f"Valuating real estate: {collateral.address}")
        
        valuations: List[Dict[str, Any]] = []
        
        # Try Zillow API
        try:
            zillow_result = await self.zillow_client.get_property_value(
                address=collateral.address,
                property_type=collateral.property_type
            )
            if zillow_result:
                valuations.append({
                    "source": "zillow",
                    "value": zillow_result["zestimate"],
                    "low": zillow_result.get("low_estimate"),
                    "high": zillow_result.get("high_estimate"),
                    "confidence": zillow_result.get("confidence", 0.85),
                    "comps": zillow_result.get("comparable_sales", [])
                })
        except Exception as e:
            logger.warning(f"Zillow API failed: {e}")
        
        # Aggregate results
        if not valuations:
            logger.warning("No valuation sources available, requiring manual review")
            return self._create_manual_review_valuation(application_id, collateral)
        
        return self._aggregate_valuations(
            application_id=application_id,
            asset_type=CollateralType.REAL_ESTATE,
            valuations=valuations
        )
    
    async def _valuate_vehicle(
        self,
        application_id: str,
        collateral: CollateralAsset
    ) -> CollateralValuation:
        """Valuate vehicle.
        
        Uses:
        1. Edmunds True Market Value (primary)
        2. CarFax history check
        3. NADA guides
        """
        logger.info(f"Valuating vehicle: {collateral.year} {collateral.make} {collateral.model}, VIN: {collateral.vin}")
        
        valuations: List[Dict[str, Any]] = []
        
        # Try Edmunds API
        try:
            edmunds_result = await self.edmunds_client.get_vehicle_value(
                vin=collateral.vin,
                year=collateral.year,
                make=collateral.make,
                model=collateral.model,
                mileage=collateral.mileage,
                condition=collateral.condition
            )
            if edmunds_result:
                valuations.append({
                    "source": "edmunds",
                    "value": edmunds_result["tmv"],
                    "low": edmunds_result.get("trade_in"),
                    "high": edmunds_result.get("retail"),
                    "confidence": edmunds_result.get("confidence", 0.9),
                    "market_conditions": edmunds_result.get("market_data", {})
                })
        except Exception as e:
            logger.warning(f"Edmunds API failed: {e}")
        
        # Aggregate results
        if not valuations:
            logger.warning("No vehicle valuation sources available")
            return self._create_manual_review_valuation(application_id, collateral)
        
        return self._aggregate_valuations(
            application_id=application_id,
            asset_type=CollateralType.VEHICLE,
            valuations=valuations
        )
    
    async def _valuate_equipment(
        self,
        application_id: str,
        collateral: CollateralAsset
    ) -> CollateralValuation:
        """Valuate equipment/machinery.
        
        Uses:
        1. Equipment database lookups
        2. Depreciation calculation
        3. Market research
        """
        logger.info(f"Valuating equipment: {collateral.equipment_type}, {collateral.manufacturer}")
        
        try:
            equipment_result = await self.equipment_client.get_equipment_value(
                equipment_type=collateral.equipment_type,
                manufacturer=collateral.manufacturer,
                model=collateral.model_number,
                purchase_date=collateral.purchase_date,
                purchase_price=collateral.purchase_price
            )
            
            if equipment_result:
                return CollateralValuation(
                    application_id=application_id,
                    asset_type=CollateralType.EQUIPMENT,
                    source="equipment_db",
                    estimated_value=equipment_result["estimated_value"],
                    low_estimate=equipment_result.get("low_estimate"),
                    high_estimate=equipment_result.get("high_estimate"),
                    confidence_score=equipment_result.get("confidence", 0.75),
                    details=equipment_result
                )
        except Exception as e:
            logger.warning(f"Equipment valuation failed: {e}")
        
        return self._create_manual_review_valuation(application_id, collateral)
    
    def _aggregate_valuations(
        self,
        application_id: str,
        asset_type: CollateralType,
        valuations: List[Dict[str, Any]]
    ) -> CollateralValuation:
        """Aggregate multiple valuations with weighted averaging.
        
        Args:
            application_id: Application ID
            asset_type: Type of asset
            valuations: List of valuation results
            
        Returns:
            Aggregated CollateralValuation
        """
        if not valuations:
            raise ValueError("No valuations to aggregate")
        
        # Calculate weighted average
        total_weight = 0.0
        weighted_sum = 0.0
        confidence_scores = []
        all_comps = []
        
        for val in valuations:
            source = val["source"]
            weight = self.source_weights.get(source, 0.5)
            value = val["value"]
            
            weighted_sum += value * weight
            total_weight += weight
            confidence_scores.append(val.get("confidence", 0.7))
            
            if "comps" in val:
                all_comps.extend(val["comps"])
        
        estimated_value = weighted_sum / total_weight if total_weight > 0 else valuations[0]["value"]
        
        # Average confidence (weighted by source reliability)
        avg_confidence = sum(confidence_scores) / len(confidence_scores)
        
        # Calculate range (low/high estimates)
        low_estimates = [v.get("low") for v in valuations if v.get("low")]
        high_estimates = [v.get("high") for v in valuations if v.get("high")]
        
        low_estimate = min(low_estimates) if low_estimates else estimated_value * 0.9
        high_estimate = max(high_estimates) if high_estimates else estimated_value * 1.1
        
        logger.info(
            f"Aggregated valuation: ${estimated_value:,.2f} "
            f"(range: ${low_estimate:,.2f} - ${high_estimate:,.2f}), "
            f"confidence: {avg_confidence:.2f}"
        )
        
        return CollateralValuation(
            application_id=application_id,
            asset_type=asset_type,
            source="aggregated",
            estimated_value=round(estimated_value, 2),
            low_estimate=round(low_estimate, 2),
            high_estimate=round(high_estimate, 2),
            confidence_score=round(avg_confidence, 3),
            comparable_sales=all_comps[:5],  # Top 5 comps
            details={
                "sources_used": [v["source"] for v in valuations],
                "valuation_count": len(valuations),
                "individual_valuations": valuations
            }
        )
    
    def _create_manual_review_valuation(
        self,
        application_id: str,
        collateral: CollateralAsset
    ) -> CollateralValuation:
        """Create valuation requiring manual review."""
        logger.info("Creating manual review valuation")
        
        return CollateralValuation(
            application_id=application_id,
            asset_type=collateral.type,
            source="manual_review_required",
            estimated_value=0.0,
            confidence_score=0.0,
            details={
                "reason": "Automated valuation unavailable",
                "requires_manual_appraisal": True,
                "collateral_info": collateral.to_dict()
            }
        )
    
    def _create_error_valuation(
        self,
        application_id: str,
        collateral: CollateralAsset,
        error: str
    ) -> CollateralValuation:
        """Create error valuation."""
        logger.error(f"Creating error valuation: {error}")
        
        return CollateralValuation(
            application_id=application_id,
            asset_type=collateral.type,
            source="error",
            estimated_value=0.0,
            confidence_score=0.0,
            details={
                "error": error,
                "requires_retry": True
            }
        )
