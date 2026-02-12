"""Equipment valuation client for machinery and equipment appraisal.

Provides equipment valuations using industry databases and depreciation models.
"""

import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
from dateutil.relativedelta import relativedelta
import logging

logger = logging.getLogger(__name__)


class EquipmentClient:
    """Client for equipment/machinery valuation."""
    
    def __init__(self):
        """Initialize equipment valuation client."""
        self.equipment_database = self._load_equipment_database()
        
    def _load_equipment_database(self) -> Dict[str, Any]:
        """Load equipment reference database.
        
        In production, this would connect to industry databases like:
        - Equipment Watch
        - Machinery Trader
        - Manufacturer databases
        """
        return {
            "construction": {
                "excavator": {
                    "depreciation_rate": 0.12,
                    "useful_life_years": 10,
                    "market_demand": "high"
                },
                "bulldozer": {
                    "depreciation_rate": 0.10,
                    "useful_life_years": 15,
                    "market_demand": "medium"
                },
                "crane": {
                    "depreciation_rate": 0.08,
                    "useful_life_years": 20,
                    "market_demand": "high"
                }
            },
            "agricultural": {
                "tractor": {
                    "depreciation_rate": 0.15,
                    "useful_life_years": 12,
                    "market_demand": "high"
                },
                "combine": {
                    "depreciation_rate": 0.14,
                    "useful_life_years": 10,
                    "market_demand": "medium"
                }
            },
            "manufacturing": {
                "cnc_machine": {
                    "depreciation_rate": 0.10,
                    "useful_life_years": 15,
                    "market_demand": "high"
                },
                "injection_molder": {
                    "depreciation_rate": 0.12,
                    "useful_life_years": 12,
                    "market_demand": "medium"
                }
            }
        }
    
    async def get_equipment_value(
        self,
        equipment_type: str,
        manufacturer: str,
        model: str,
        purchase_date: Optional[datetime] = None,
        purchase_price: Optional[float] = None,
        condition: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get equipment valuation.
        
        Args:
            equipment_type: Type of equipment (e.g., 'excavator', 'tractor')
            manufacturer: Manufacturer name
            model: Model number/name
            purchase_date: Original purchase date
            purchase_price: Original purchase price
            condition: Equipment condition
            
        Returns:
            Dict with estimated value and depreciation details
        """
        logger.info(f"Valuating equipment: {equipment_type} by {manufacturer}")
        
        try:
            # Find equipment in database
            equipment_info = self._find_equipment_info(equipment_type)
            
            if not equipment_info:
                logger.warning(f"Equipment type '{equipment_type}' not found in database")
                return self._get_generic_equipment_valuation(
                    equipment_type, purchase_price, purchase_date, condition
                )
            
            # Calculate current value
            current_value = self._calculate_depreciated_value(
                purchase_price=purchase_price or 100000,  # Default estimate
                purchase_date=purchase_date or datetime.now(),
                depreciation_rate=equipment_info["depreciation_rate"],
                useful_life_years=equipment_info["useful_life_years"],
                condition=condition
            )
            
            return {
                "equipment_type": equipment_type,
                "manufacturer": manufacturer,
                "model": model,
                "estimated_value": round(current_value, 2),
                "low_estimate": round(current_value * 0.85, 2),
                "high_estimate": round(current_value * 1.15, 2),
                "confidence": 0.75,
                "valuation_date": datetime.now().isoformat(),
                "depreciation_info": {
                    "annual_rate": equipment_info["depreciation_rate"],
                    "useful_life_years": equipment_info["useful_life_years"],
                    "age_years": self._calculate_age_years(purchase_date) if purchase_date else None,
                    "remaining_life_pct": self._calculate_remaining_life(
                        purchase_date, equipment_info["useful_life_years"]
                    ) if purchase_date else None
                },
                "market_data": {
                    "demand": equipment_info["market_demand"],
                    "liquidity": "medium",
                    "replacement_cost": purchase_price * 1.2 if purchase_price else None
                },
                "condition": condition or "good",
                "source": "equipment_db"
            }
            
        except Exception as e:
            logger.error(f"Equipment valuation error: {e}", exc_info=True)
            return None
    
    def _find_equipment_info(self, equipment_type: str) -> Optional[Dict[str, Any]]:
        """Find equipment information in database.
        
        Args:
            equipment_type: Type of equipment
            
        Returns:
            Equipment info dict or None
        """
        equipment_type_lower = equipment_type.lower()
        
        for category, equipment_dict in self.equipment_database.items():
            for equip_name, equip_info in equipment_dict.items():
                if equip_name in equipment_type_lower or equipment_type_lower in equip_name:
                    return equip_info
        
        return None
    
    def _calculate_depreciated_value(
        self,
        purchase_price: float,
        purchase_date: datetime,
        depreciation_rate: float,
        useful_life_years: int,
        condition: Optional[str] = None
    ) -> float:
        """Calculate depreciated equipment value.
        
        Uses declining balance depreciation method.
        
        Args:
            purchase_price: Original purchase price
            purchase_date: Purchase date
            depreciation_rate: Annual depreciation rate
            useful_life_years: Equipment useful life in years
            condition: Current condition
            
        Returns:
            Depreciated value
        """
        age_years = self._calculate_age_years(purchase_date)
        
        # Declining balance depreciation
        depreciated_value = purchase_price * ((1 - depreciation_rate) ** age_years)
        
        # Don't depreciate below 10% of original value (salvage value)
        salvage_value = purchase_price * 0.10
        depreciated_value = max(depreciated_value, salvage_value)
        
        # Condition adjustment
        condition_multipliers = {
            "excellent": 1.15,
            "good": 1.00,
            "fair": 0.85,
            "poor": 0.70
        }
        condition_mult = condition_multipliers.get(condition or "good", 1.0)
        
        return depreciated_value * condition_mult
    
    def _calculate_age_years(self, purchase_date: datetime) -> float:
        """Calculate equipment age in years.
        
        Args:
            purchase_date: Purchase date
            
        Returns:
            Age in years (decimal)
        """
        delta = relativedelta(datetime.now(), purchase_date)
        return delta.years + (delta.months / 12.0)
    
    def _calculate_remaining_life(
        self,
        purchase_date: datetime,
        useful_life_years: int
    ) -> float:
        """Calculate remaining useful life percentage.
        
        Args:
            purchase_date: Purchase date
            useful_life_years: Total useful life
            
        Returns:
            Remaining life as percentage (0-1)
        """
        age_years = self._calculate_age_years(purchase_date)
        remaining = max(0, useful_life_years - age_years)
        return remaining / useful_life_years
    
    def _get_generic_equipment_valuation(
        self,
        equipment_type: str,
        purchase_price: Optional[float],
        purchase_date: Optional[datetime],
        condition: Optional[str]
    ) -> Dict[str, Any]:
        """Get generic equipment valuation for unknown types.
        
        Uses conservative depreciation assumptions.
        """
        logger.info(f"Using generic valuation for: {equipment_type}")
        
        # Generic depreciation (15% per year)
        if purchase_price and purchase_date:
            age_years = self._calculate_age_years(purchase_date)
            estimated_value = purchase_price * ((1 - 0.15) ** age_years)
            estimated_value = max(estimated_value, purchase_price * 0.10)  # Min 10%
        else:
            estimated_value = 50000  # Generic estimate
        
        return {
            "equipment_type": equipment_type,
            "estimated_value": round(estimated_value, 2),
            "low_estimate": round(estimated_value * 0.70, 2),
            "high_estimate": round(estimated_value * 1.30, 2),
            "confidence": 0.50,  # Lower confidence for generic valuation
            "valuation_date": datetime.now().isoformat(),
            "notes": "Generic valuation - manual appraisal recommended",
            "source": "generic_model"
        }
