"""
LinkedIn Industry Insights Engine

Provides industry trends, market analysis, salary data, and career insights
based on aggregated data and market intelligence.
"""

import logging
from typing import Dict, List, Optional
from datetime import date
from collections import defaultdict

from linkedin.models import (
    IndustryInsight,
    IndustryType,
    LinkedInProfile,
    SkillCategory,
)

logger = logging.getLogger(__name__)


class IndustryInsightsEngine:
    """
    Generate industry insights and market intelligence
    
    Features:
    - Trending skills by industry
    - Salary benchmarks
    - Job growth projections
    - Emerging roles
    - Market demand analysis
    """
    
    def __init__(self):
        """Initialize industry insights engine"""
        self.industry_data = self._load_industry_data()
        self.salary_data = self._load_salary_data()
        self.skills_data = self._load_skills_trends()
    
    def get_industry_insights(self, industry: IndustryType) -> IndustryInsight:
        """
        Get comprehensive insights for an industry
        
        Args:
            industry: Industry to analyze
        
        Returns:
            IndustryInsight with trends and analysis
        """
        data = self.industry_data.get(industry, {})
        
        return IndustryInsight(
            industry=industry,
            trending_skills=data.get("trending_skills", []),
            declining_skills=data.get("declining_skills", []),
            emerging_roles=data.get("emerging_roles", []),
            average_salary=data.get("average_salary"),
            job_growth_rate=data.get("job_growth_rate"),
            demand_level=data.get("demand_level", "medium"),
            key_insights=data.get("key_insights", []),
            future_outlook=data.get("future_outlook"),
            top_companies=data.get("top_companies", []),
            data_date=date.today(),
            sources=["LinkedIn", "Bureau of Labor Statistics", "Industry Reports"],
        )
    
    def compare_industries(
        self,
        industries: List[IndustryType]
    ) -> Dict[str, any]:
        """
        Compare multiple industries
        
        Args:
            industries: List of industries to compare
        
        Returns:
            Comparison data
        """
        insights = [self.get_industry_insights(ind) for ind in industries]
        
        return {
            "industries": [ins.industry for ins in insights],
            "avg_salaries": [ins.average_salary for ins in insights],
            "growth_rates": [ins.job_growth_rate for ins in insights],
            "demand_levels": [ins.demand_level for ins in insights],
            "top_skills": {
                ins.industry: ins.trending_skills[:5]
                for ins in insights
            },
        }
    
    def get_trending_skills_global(self, top_n: int = 20) -> List[str]:
        """
        Get globally trending skills across all industries
        
        Args:
            top_n: Number of skills to return
        
        Returns:
            List of trending skill names
        """
        # Aggregate from all industries
        all_trending = []
        for industry_data in self.industry_data.values():
            all_trending.extend(industry_data.get("trending_skills", []))
        
        # Count occurrences
        skill_counts = defaultdict(int)
        for skill in all_trending:
            skill_counts[skill] += 1
        
        # Sort by count
        sorted_skills = sorted(skill_counts.items(), key=lambda x: x[1], reverse=True)
        
        return [skill for skill, count in sorted_skills[:top_n]]
    
    def get_salary_benchmark(
        self,
        role: str,
        experience_years: float,
        location: Optional[str] = None,
        industry: Optional[IndustryType] = None
    ) -> Dict[str, any]:
        """
        Get salary benchmark for a role
        
        Args:
            role: Job role/title
            experience_years: Years of experience
            location: Location (affects cost of living adjustment)
            industry: Industry
        
        Returns:
            Salary benchmark data
        """
        # Base salary by experience
        base_salary = self._calculate_base_salary(role, experience_years)
        
        # Industry adjustment
        if industry:
            industry_multiplier = self.salary_data.get("industry_multipliers", {}).get(
                industry, 1.0
            )
            base_salary = {
                k: int(v * industry_multiplier)
                for k, v in base_salary.items()
            }
        
        # Location adjustment
        if location:
            location_multiplier = self._get_location_multiplier(location)
            base_salary = {
                k: int(v * location_multiplier)
                for k, v in base_salary.items()
            }
        
        return {
            "role": role,
            "experience_years": experience_years,
            "base_salary_range": f"${base_salary['low']:,} - ${base_salary['high']:,}",
            "median_salary": f"${base_salary['median']:,}",
            "percentile_25": f"${base_salary['p25']:,}",
            "percentile_75": f"${base_salary['p75']:,}",
            "industry": industry,
            "location": location,
            "data_date": date.today().isoformat(),
        }
    
    def analyze_profile_market_position(
        self,
        profile: LinkedInProfile
    ) -> Dict[str, any]:
        """
        Analyze where profile stands in the market
        
        Args:
            profile: LinkedInProfile to analyze
        
        Returns:
            Market position analysis
        """
        # Get industry
        industry = None
        if profile.current_position:
            industry = profile.current_position.industry
        
        # Get salary estimate
        role = profile.current_position.title if profile.current_position else "Unknown"
        salary_data = self.get_salary_benchmark(
            role=role,
            experience_years=profile.total_experience_years,
            location=profile.location,
            industry=industry,
        )
        
        # Get industry insights
        industry_insights = None
        if industry:
            industry_insights = self.get_industry_insights(industry)
        
        # Skill gap analysis
        profile_skills = {s.name for s in profile.skills}
        trending_skills = industry_insights.trending_skills if industry_insights else []
        matching_trending = [s for s in trending_skills if s in profile_skills]
        missing_trending = [s for s in trending_skills if s not in profile_skills]
        
        return {
            "current_role": role,
            "industry": industry,
            "experience_years": profile.total_experience_years,
            "estimated_salary": salary_data,
            "skill_alignment": {
                "matching_trending_skills": matching_trending,
                "missing_trending_skills": missing_trending[:5],
                "alignment_score": len(matching_trending) / len(trending_skills) * 100 if trending_skills else 0,
            },
            "market_demand": industry_insights.demand_level if industry_insights else "unknown",
            "industry_growth": industry_insights.job_growth_rate if industry_insights else None,
            "recommendations": self._generate_market_recommendations(
                profile, industry_insights, matching_trending, missing_trending
            ),
        }
    
    def get_career_path_insights(
        self,
        current_role: str,
        target_role: str,
        industry: Optional[IndustryType] = None
    ) -> Dict[str, any]:
        """
        Get insights on career path from current to target role
        
        Args:
            current_role: Current job role
            target_role: Target job role
            industry: Industry context
        
        Returns:
            Career path insights
        """
        # Get role data
        current_data = self._get_role_data(current_role)
        target_data = self._get_role_data(target_role)
        
        # Skill gap
        skill_gap = list(set(target_data["required_skills"]) - set(current_data["required_skills"]))
        
        # Timeline estimate
        timeline = self._estimate_transition_timeline(current_role, target_role)
        
        # Steps to transition
        steps = self._generate_transition_steps(current_role, target_role, skill_gap)
        
        return {
            "current_role": current_role,
            "target_role": target_role,
            "industry": industry,
            "skill_gap": skill_gap,
            "skills_to_develop": skill_gap[:5],
            "estimated_timeline": timeline,
            "transition_steps": steps,
            "difficulty_level": self._assess_transition_difficulty(current_role, target_role),
            "success_rate": self._estimate_success_rate(current_role, target_role),
        }
    
    def _load_industry_data(self) -> Dict[IndustryType, Dict]:
        """Load industry data (in production, from database)"""
        return {
            IndustryType.TECHNOLOGY: {
                "trending_skills": [
                    "Python", "AWS", "Kubernetes", "Machine Learning", "React",
                    "TypeScript", "Docker", "CI/CD", "Microservices", "GraphQL"
                ],
                "declining_skills": ["jQuery", "AngularJS", "Perl", "Flash"],
                "emerging_roles": [
                    "ML Engineer", "DevOps Engineer", "Cloud Architect",
                    "Data Engineer", "Site Reliability Engineer"
                ],
                "average_salary": "$95,000 - $150,000",
                "job_growth_rate": 15.2,
                "demand_level": "high",
                "key_insights": [
                    "AI/ML skills in highest demand",
                    "Cloud computing dominates infrastructure",
                    "DevOps practices becoming standard",
                    "Remote work widely accepted"
                ],
                "future_outlook": "Strong growth expected with AI adoption",
                "top_companies": [
                    "Google", "Microsoft", "Amazon", "Meta", "Apple",
                    "Netflix", "Salesforce", "Adobe"
                ],
            },
            IndustryType.FINANCE: {
                "trending_skills": [
                    "Python", "SQL", "Risk Management", "Financial Modeling",
                    "Data Analysis", "Blockchain", "Compliance", "Excel"
                ],
                "declining_skills": ["VBA", "COBOL", "Legacy Systems"],
                "emerging_roles": [
                    "Quantitative Analyst", "Risk Analyst", "Fintech Developer",
                    "Blockchain Developer", "Financial Data Scientist"
                ],
                "average_salary": "$85,000 - $140,000",
                "job_growth_rate": 8.5,
                "demand_level": "medium",
                "key_insights": [
                    "Fintech disrupting traditional banking",
                    "Regulatory compliance increasingly important",
                    "Data analytics crucial for decision making",
                    "Blockchain creating new opportunities"
                ],
                "future_outlook": "Transformation through technology",
                "top_companies": [
                    "JPMorgan Chase", "Goldman Sachs", "Morgan Stanley",
                    "BlackRock", "Fidelity", "Charles Schwab"
                ],
            },
            IndustryType.HEALTHCARE: {
                "trending_skills": [
                    "Healthcare IT", "EMR Systems", "Patient Care", "Medical Coding",
                    "Healthcare Analytics", "Telemedicine", "HIPAA Compliance"
                ],
                "declining_skills": ["Paper Records", "Manual Processes"],
                "emerging_roles": [
                    "Healthcare Data Analyst", "Telemedicine Coordinator",
                    "Clinical Informatics Specialist", "Health Tech Developer"
                ],
                "average_salary": "$70,000 - $110,000",
                "job_growth_rate": 12.8,
                "demand_level": "high",
                "key_insights": [
                    "Telemedicine adoption accelerating",
                    "Data analytics improving patient outcomes",
                    "AI assisting in diagnostics",
                    "Aging population driving demand"
                ],
                "future_outlook": "Strong growth driven by aging demographics",
                "top_companies": [
                    "Kaiser Permanente", "Mayo Clinic", "Cleveland Clinic",
                    "Johns Hopkins", "UnitedHealth Group"
                ],
            },
            IndustryType.CONSULTING: {
                "trending_skills": [
                    "Strategy", "Management Consulting", "Data Analysis",
                    "Business Development", "Change Management", "Excel",
                    "PowerPoint", "Stakeholder Management"
                ],
                "declining_skills": [],
                "emerging_roles": [
                    "Digital Transformation Consultant", "Data Strategy Consultant",
                    "Sustainability Consultant", "Cybersecurity Consultant"
                ],
                "average_salary": "$90,000 - $160,000",
                "job_growth_rate": 10.5,
                "demand_level": "medium",
                "key_insights": [
                    "Digital transformation driving demand",
                    "Industry specialization valued",
                    "Data-driven consulting growing",
                    "Hybrid consulting models emerging"
                ],
                "future_outlook": "Adapting to digital-first business models",
                "top_companies": [
                    "McKinsey", "BCG", "Bain", "Deloitte", "EY",
                    "PwC", "Accenture", "KPMG"
                ],
            },
        }
    
    def _load_salary_data(self) -> Dict:
        """Load salary data"""
        return {
            "industry_multipliers": {
                IndustryType.TECHNOLOGY: 1.15,
                IndustryType.FINANCE: 1.10,
                IndustryType.HEALTHCARE: 0.95,
                IndustryType.CONSULTING: 1.12,
                IndustryType.RETAIL: 0.85,
                IndustryType.EDUCATION: 0.80,
            },
            "location_multipliers": {
                "san francisco": 1.4,
                "new york": 1.35,
                "seattle": 1.25,
                "boston": 1.20,
                "austin": 1.10,
                "denver": 1.05,
                "remote": 1.00,
            },
        }
    
    def _load_skills_trends(self) -> Dict:
        """Load skills trend data"""
        return {
            "hot_skills_2026": [
                "Artificial Intelligence", "Machine Learning", "Python",
                "Cloud Computing", "Kubernetes", "React", "TypeScript",
                "Data Science", "Cybersecurity", "DevOps"
            ],
            "declining_skills": [
                "Flash", "Silverlight", "jQuery", "AngularJS",
                "Perl", "ColdFusion"
            ],
        }
    
    def _calculate_base_salary(self, role: str, experience_years: float) -> Dict[str, int]:
        """Calculate base salary by role and experience"""
        # Simplified salary calculation
        role_lower = role.lower()
        
        # Base by experience
        if experience_years >= 15:
            base = 150000
        elif experience_years >= 10:
            base = 120000
        elif experience_years >= 7:
            base = 100000
        elif experience_years >= 5:
            base = 85000
        elif experience_years >= 3:
            base = 75000
        elif experience_years >= 1:
            base = 65000
        else:
            base = 55000
        
        # Role multiplier
        if any(kw in role_lower for kw in ["director", "vp", "executive", "head"]):
            base *= 1.5
        elif any(kw in role_lower for kw in ["lead", "principal", "staff"]):
            base *= 1.3
        elif any(kw in role_lower for kw in ["senior", "sr"]):
            base *= 1.2
        elif any(kw in role_lower for kw in ["junior", "jr", "entry"]):
            base *= 0.8
        
        # Generate range
        return {
            "low": int(base * 0.85),
            "median": base,
            "high": int(base * 1.25),
            "p25": int(base * 0.90),
            "p75": int(base * 1.15),
        }
    
    def _get_location_multiplier(self, location: str) -> float:
        """Get salary multiplier for location"""
        location_lower = location.lower()
        
        for loc_key, multiplier in self.salary_data["location_multipliers"].items():
            if loc_key in location_lower:
                return multiplier
        
        return 1.0  # Default
    
    def _get_role_data(self, role: str) -> Dict:
        """Get data for a role"""
        role_lower = role.lower()
        
        # Simplified role data
        if "software engineer" in role_lower or "developer" in role_lower:
            return {
                "required_skills": ["Python", "Git", "SQL", "REST APIs", "Testing"],
                "avg_salary": 95000,
            }
        elif "data scientist" in role_lower:
            return {
                "required_skills": ["Python", "Statistics", "Machine Learning", "SQL", "Data Visualization"],
                "avg_salary": 110000,
            }
        elif "product manager" in role_lower:
            return {
                "required_skills": ["Product Strategy", "Agile", "Data Analysis", "Stakeholder Management"],
                "avg_salary": 115000,
            }
        else:
            return {
                "required_skills": ["Communication", "Problem Solving", "Teamwork"],
                "avg_salary": 75000,
            }
    
    def _estimate_transition_timeline(self, current_role: str, target_role: str) -> str:
        """Estimate timeline for role transition"""
        # Simplified estimation
        current_lower = current_role.lower()
        target_lower = target_role.lower()
        
        # Same field, different level
        if any(kw in current_lower and kw in target_lower for kw in ["engineer", "manager", "analyst"]):
            if "senior" in target_lower and "junior" in current_lower:
                return "2-4 years"
            elif "lead" in target_lower and "senior" in current_lower:
                return "1-3 years"
            else:
                return "1-2 years"
        
        # Different field
        return "2-5 years"
    
    def _generate_transition_steps(
        self,
        current_role: str,
        target_role: str,
        skill_gap: List[str]
    ) -> List[str]:
        """Generate steps for role transition"""
        steps = []
        
        if skill_gap:
            steps.append(f"Acquire skills: {', '.join(skill_gap[:3])}")
            steps.append("Take relevant online courses and certifications")
        
        steps.extend([
            "Gain experience through side projects or freelance work",
            "Network with professionals in target role",
            "Update resume and LinkedIn profile to highlight relevant skills",
            "Apply for intermediate roles if needed",
            "Prepare for interviews focusing on target role requirements",
        ])
        
        return steps
    
    def _assess_transition_difficulty(self, current_role: str, target_role: str) -> str:
        """Assess difficulty of role transition"""
        # Simplified assessment
        if current_role.lower() == target_role.lower():
            return "easy"
        
        # Check if same field
        fields = ["engineer", "manager", "analyst", "designer", "scientist"]
        current_field = next((f for f in fields if f in current_role.lower()), None)
        target_field = next((f for f in fields if f in target_role.lower()), None)
        
        if current_field == target_field:
            return "moderate"
        
        return "challenging"
    
    def _estimate_success_rate(self, current_role: str, target_role: str) -> str:
        """Estimate success rate for transition"""
        difficulty = self._assess_transition_difficulty(current_role, target_role)
        
        if difficulty == "easy":
            return "90-95%"
        elif difficulty == "moderate":
            return "70-80%"
        else:
            return "50-60%"
    
    def _generate_market_recommendations(
        self,
        profile: LinkedInProfile,
        industry_insights: Optional[IndustryInsight],
        matching_trending: List[str],
        missing_trending: List[str]
    ) -> List[str]:
        """Generate market-based recommendations"""
        recommendations = []
        
        if missing_trending:
            recommendations.append(
                f"Learn trending skills: {', '.join(missing_trending[:3])}"
            )
        
        if matching_trending:
            recommendations.append(
                "Highlight your trending skills in job applications"
            )
        
        if industry_insights and industry_insights.job_growth_rate:
            if industry_insights.job_growth_rate > 10:
                recommendations.append(
                    f"Your industry ({industry_insights.industry}) has strong growth ({industry_insights.job_growth_rate}%)"
                )
        
        recommendations.extend([
            "Consider obtaining industry-recognized certifications",
            "Network actively within your industry",
            "Stay updated on industry trends and technologies",
        ])
        
        return recommendations[:5]
