"""
LinkedIn Features Module

This module provides comprehensive LinkedIn profile analysis, job matching,
skill extraction, and recommendation capabilities for the AI Agent System.

Components:
- Profile Parser: Extract and analyze LinkedIn profile data
- Job Matcher: Match profiles to job opportunities with scoring
- Skill Extractor: NLP-based skill extraction and categorization
- Recommendation Engine: Generate personalized recommendations
- Profile Analyzer: Comprehensive profile analysis and insights
- Industry Insights: Industry trends and market analysis
"""

from linkedin.models import (
    LinkedInProfile,
    JobPosting,
    Skill,
    SkillCategory,
    Experience,
    Education,
    Certification,
    MatchScore,
    Recommendation,
    ProfileAnalysis,
    IndustryInsight,
)

from linkedin.profile_parser import ProfileParser
from linkedin.job_matcher import JobMatcher
from linkedin.skill_extractor import SkillExtractor
from linkedin.recommender import RecommendationEngine
from linkedin.profile_analyzer import ProfileAnalyzer
from linkedin.industry_insights import IndustryInsightsEngine

__all__ = [
    # Models
    "LinkedInProfile",
    "JobPosting",
    "Skill",
    "SkillCategory",
    "Experience",
    "Education",
    "Certification",
    "MatchScore",
    "Recommendation",
    "ProfileAnalysis",
    "IndustryInsight",
    # Components
    "ProfileParser",
    "JobMatcher",
    "SkillExtractor",
    "RecommendationEngine",
    "ProfileAnalyzer",
    "IndustryInsightsEngine",
]

__version__ = "1.0.0"
