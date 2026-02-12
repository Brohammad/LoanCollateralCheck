"""Market risk analysis for collateral assets.

Analyzes market conditions, volatility, and trends that affect collateral value.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class MarketRiskAnalyzer:
    """Analyze market risk for different collateral types."""
    
    def analyze_market_risk(
        self,
        collateral_type: str,
        market_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Analyze market risk for collateral.
        
        Args:
            collateral_type: Type of collateral
            market_data: Optional market data from valuation
            
        Returns:
            Market risk assessment
        """
        logger.info(f"Analyzing market risk for: {collateral_type}")
        
        if collateral_type == "real_estate":
            return self._analyze_real_estate_market(market_data)
        elif collateral_type == "vehicle":
            return self._analyze_vehicle_market(market_data)
        elif collateral_type == "equipment":
            return self._analyze_equipment_market(market_data)
        else:
            return self._analyze_generic_market(market_data)
    
    def _analyze_real_estate_market(
        self,
        market_data: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze real estate market conditions.
        
        Args:
            market_data: Market data from valuation
            
        Returns:
            Real estate market risk assessment
        """
        if not market_data:
            return self._create_default_assessment("real_estate")
        
        # Extract market indicators
        price_trend_30d = market_data.get("price_trend_30d", 0.0)
        price_trend_12m = market_data.get("price_trend_12m", 0.0)
        days_on_market = market_data.get("days_on_market", 30)
        inventory_level = market_data.get("inventory_level", "medium")
        
        # Assess market conditions
        if price_trend_12m > 0.10:  # >10% annual growth
            trend_assessment = "strong_appreciation"
            trend_risk = 0.2  # Low risk
        elif price_trend_12m > 0.03:  # 3-10% growth
            trend_assessment = "moderate_appreciation"
            trend_risk = 0.3
        elif price_trend_12m > -0.03:  # -3% to 3%
            trend_assessment = "stable"
            trend_risk = 0.4
        else:  # Declining
            trend_assessment = "declining"
            trend_risk = 0.7  # Higher risk
        
        # Assess liquidity (days on market)
        if days_on_market < 30:
            liquidity = "high"
            liquidity_risk = 0.2
        elif days_on_market < 60:
            liquidity = "medium"
            liquidity_risk = 0.4
        else:
            liquidity = "low"
            liquidity_risk = 0.6
        
        # Inventory level risk
        inventory_risk_map = {
            "low": 0.2,     # Low inventory = competitive market
            "medium": 0.4,  # Balanced
            "high": 0.6     # High inventory = buyer's market
        }
        inventory_risk = inventory_risk_map.get(inventory_level, 0.4)
        
        # Calculate overall market risk
        market_risk_score = (trend_risk * 0.4) + (liquidity_risk * 0.3) + (inventory_risk * 0.3)
        
        return {
            "collateral_type": "real_estate",
            "market_risk_score": round(market_risk_score, 3),
            "risk_level": self._score_to_risk_level(market_risk_score),
            "price_trend": {
                "30_day": round(price_trend_30d * 100, 2),
                "12_month": round(price_trend_12m * 100, 2),
                "assessment": trend_assessment
            },
            "liquidity": {
                "level": liquidity,
                "days_on_market": days_on_market
            },
            "inventory_level": inventory_level,
            "market_stability": "stable" if abs(price_trend_12m) < 0.05 else "volatile",
            "concerns": self._identify_market_concerns(
                price_trend_12m, days_on_market, inventory_level
            )
        }
    
    def _analyze_vehicle_market(
        self,
        market_data: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze vehicle market conditions.
        
        Args:
            market_data: Market data from valuation
            
        Returns:
            Vehicle market risk assessment
        """
        if not market_data:
            return self._create_default_assessment("vehicle")
        
        demand = market_data.get("demand", "medium")
        price_trend_30d = market_data.get("price_trend_30d", 0.0)
        days_to_sell = market_data.get("days_to_sell", 45)
        
        # Demand risk
        demand_risk_map = {
            "high": 0.2,
            "medium": 0.4,
            "low": 0.7
        }
        demand_risk = demand_risk_map.get(demand, 0.5)
        
        # Depreciation risk (vehicles depreciate faster)
        if price_trend_30d < -0.02:  # >2% monthly decline
            depreciation_risk = 0.8
        elif price_trend_30d < 0:
            depreciation_risk = 0.5
        else:
            depreciation_risk = 0.3
        
        # Liquidity risk
        liquidity_risk = min(days_to_sell / 90, 0.9)  # Normalize to 0-0.9
        
        market_risk_score = (demand_risk * 0.4) + (depreciation_risk * 0.3) + (liquidity_risk * 0.3)
        
        return {
            "collateral_type": "vehicle",
            "market_risk_score": round(market_risk_score, 3),
            "risk_level": self._score_to_risk_level(market_risk_score),
            "demand": demand,
            "depreciation_trend": "accelerating" if price_trend_30d < -0.02 else "normal",
            "estimated_days_to_sell": days_to_sell,
            "liquidity": "good" if days_to_sell < 45 else "fair" if days_to_sell < 60 else "poor"
        }
    
    def _analyze_equipment_market(
        self,
        market_data: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze equipment market conditions.
        
        Args:
            market_data: Market data
            
        Returns:
            Equipment market risk assessment
        """
        if not market_data:
            return self._create_default_assessment("equipment")
        
        demand = market_data.get("demand", "medium")
        liquidity = market_data.get("liquidity", "medium")
        
        # Equipment markets are typically less liquid
        demand_risk_map = {"high": 0.3, "medium": 0.5, "low": 0.8}
        liquidity_risk_map = {"high": 0.3, "medium": 0.5, "low": 0.8}
        
        demand_risk = demand_risk_map.get(demand, 0.5)
        liquidity_risk = liquidity_risk_map.get(liquidity, 0.5)
        
        # Equipment has higher inherent market risk due to specialization
        market_risk_score = max((demand_risk + liquidity_risk) / 2, 0.5)
        
        return {
            "collateral_type": "equipment",
            "market_risk_score": round(market_risk_score, 3),
            "risk_level": self._score_to_risk_level(market_risk_score),
            "demand": demand,
            "liquidity": liquidity,
            "notes": "Equipment markets typically have higher risk due to specialization and lower liquidity"
        }
    
    def _analyze_generic_market(
        self,
        market_data: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generic market analysis for unknown collateral types."""
        return {
            "collateral_type": "unknown",
            "market_risk_score": 0.6,
            "risk_level": "medium",
            "notes": "Generic market assessment - manual review recommended"
        }
    
    def _score_to_risk_level(self, score: float) -> str:
        """Convert risk score to risk level.
        
        Args:
            score: Risk score (0-1)
            
        Returns:
            Risk level string
        """
        if score < 0.3:
            return "low"
        elif score < 0.5:
            return "medium"
        elif score < 0.75:
            return "high"
        else:
            return "very_high"
    
    def _identify_market_concerns(
        self,
        price_trend: float,
        days_on_market: int,
        inventory_level: str
    ) -> list:
        """Identify specific market concerns.
        
        Args:
            price_trend: 12-month price trend
            days_on_market: Average days on market
            inventory_level: Inventory level
            
        Returns:
            List of concerns
        """
        concerns = []
        
        if price_trend < -0.05:
            concerns.append("Market experiencing price decline")
        
        if days_on_market > 90:
            concerns.append("Extended time on market indicates low demand")
        
        if inventory_level == "high":
            concerns.append("High inventory may pressure prices downward")
        
        if not concerns:
            concerns.append("No significant market concerns identified")
        
        return concerns
    
    def _create_default_assessment(self, collateral_type: str) -> Dict[str, Any]:
        """Create default assessment when market data unavailable.
        
        Args:
            collateral_type: Type of collateral
            
        Returns:
            Default assessment
        """
        return {
            "collateral_type": collateral_type,
            "market_risk_score": 0.5,
            "risk_level": "medium",
            "notes": "Limited market data available - using conservative assessment"
        }
