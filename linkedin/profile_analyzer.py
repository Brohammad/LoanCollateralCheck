"""
LinkedIn Profile Analyzer

Comprehensive profile analysis providing insights on strengths, weaknesses,
completeness, market competitiveness, and recommendations for improvement.
"""

import logging
from typing import Dict, List, Optional
from collections import Counter
from datetime import datetime

from linkedin.models import (
    LinkedInProfile,
    ProfileAnalysis,
    ExperienceLevel,
    SkillCategory,
)
from linkedin.skill_extractor import SkillExtractor

logger = logging.getLogger(__name__)


class ProfileAnalyzer:
    """
    Analyze LinkedIn profiles for completeness, quality, and market competitiveness
    
    Features:
    - Profile strength scoring
    - Completeness assessment
    - Skill analysis and categorization
    - Career progression evaluation
    - Market competitiveness analysis
    - Improvement recommendations
    """
    
    # Weights for profile strength calculation
    STRENGTH_WEIGHTS = {
        "completeness": 0.30,
        "experience_quality": 0.25,
        "skills_quality": 0.20,
        "education": 0.10,
        "certifications": 0.10,
        "engagement": 0.05,
    }
    
    def __init__(self, skill_extractor: Optional[SkillExtractor] = None):
        """
        Initialize profile analyzer
        
        Args:
            skill_extractor: SkillExtractor instance
        """
        self.skill_extractor = skill_extractor or SkillExtractor()
    
    def analyze_profile(self, profile: LinkedInProfile) -> ProfileAnalysis:
        """
        Perform comprehensive profile analysis
        
        Args:
            profile: LinkedInProfile to analyze
        
        Returns:
            ProfileAnalysis with detailed insights
        """
        # Calculate component scores
        completeness = self._calculate_completeness(profile)
        exp_quality = self._assess_experience_quality(profile)
        skill_quality = self._assess_skill_quality(profile)
        edu_score = self._assess_education(profile)
        cert_score = self._assess_certifications(profile)
        engagement = self._assess_engagement(profile)
        
        # Calculate overall profile strength
        profile_strength = (
            completeness * self.STRENGTH_WEIGHTS["completeness"] +
            exp_quality * self.STRENGTH_WEIGHTS["experience_quality"] +
            skill_quality * self.STRENGTH_WEIGHTS["skills_quality"] +
            edu_score * self.STRENGTH_WEIGHTS["education"] +
            cert_score * self.STRENGTH_WEIGHTS["certifications"] +
            engagement * self.STRENGTH_WEIGHTS["engagement"]
        )
        
        # Skill analysis
        skill_analysis = self.skill_extractor.analyze_skill_trends(profile.skills)
        skill_categories = skill_analysis["by_category"]
        
        # Get top skills (by endorsements)
        top_skills = sorted(
            profile.skills,
            key=lambda s: (s.endorsements, s.proficiency_level or 0),
            reverse=True
        )[:10]
        top_skill_names = [s.name for s in top_skills]
        
        # Identify emerging and gap skills
        emerging_skills = skill_analysis.get("emerging_skills", [])
        skill_gaps = self._identify_skill_gaps(profile)
        
        # Experience analysis
        total_years = profile.total_experience_years
        experience_level = self._calculate_experience_level(total_years)
        industries = list({exp.industry for exp in profile.experiences})
        career_progression = self._assess_career_progression(profile)
        
        # Education analysis
        highest_degree = self._get_highest_degree(profile)
        institutions = [edu.institution for edu in profile.education]
        
        # Market analysis
        market_competitiveness = self._assess_market_competitiveness(profile)
        salary_estimate = self._estimate_salary(profile)
        demand_level = self._assess_demand_level(profile)
        
        # Identify strengths and weaknesses
        strengths = self._identify_strengths(profile, profile_strength)
        weaknesses = self._identify_weaknesses(profile, profile_strength)
        improvement_areas = self._identify_improvement_areas(profile, weaknesses)
        next_steps = self._generate_next_steps(profile, improvement_areas)
        
        return ProfileAnalysis(
            profile_id=profile.profile_id,
            profile_strength_score=round(profile_strength, 2),
            completeness_score=round(completeness, 2),
            total_skills=len(profile.skills),
            skill_categories={k: v for k, v in skill_categories.items()},
            top_skills=top_skill_names,
            emerging_skills=emerging_skills,
            skill_gaps=skill_gaps,
            total_experience_years=total_years,
            experience_level=experience_level,
            industries=industries,
            career_progression=career_progression,
            highest_degree=highest_degree,
            education_institutions=institutions,
            market_competitiveness=round(market_competitiveness, 2),
            salary_estimate=salary_estimate,
            demand_level=demand_level,
            strengths=strengths,
            weaknesses=weaknesses,
            improvement_areas=improvement_areas,
            next_steps=next_steps,
            analyzed_at=datetime.utcnow(),
        )
    
    def _calculate_completeness(self, profile: LinkedInProfile) -> float:
        """Calculate profile completeness score (0-100)"""
        score = 0
        total_sections = 12  # Total number of profile sections we check
        
        # Basic info (20 points - 5 fields)
        if profile.first_name:
            score += 4
        if profile.last_name:
            score += 4
        if profile.headline:
            score += 4
        if profile.location:
            score += 4
        if profile.summary:
            score += 4
        
        # Contact (10 points - 2 fields)
        if profile.email:
            score += 5
        if profile.linkedin_url:
            score += 5
        
        # Experience (20 points)
        if profile.experiences:
            score += 10
            if len(profile.experiences) >= 2:
                score += 5
            # Check experience quality
            if any(exp.description for exp in profile.experiences):
                score += 5
        
        # Education (15 points)
        if profile.education:
            score += 10
            if len(profile.education) >= 1:
                score += 5
        
        # Skills (20 points)
        if profile.skills:
            score += 10
            if len(profile.skills) >= 5:
                score += 5
            if len(profile.skills) >= 10:
                score += 5
        
        # Certifications (15 points)
        if profile.certifications:
            score += 10
            if len(profile.certifications) >= 2:
                score += 5
        
        return min(100, score)
    
    def _assess_experience_quality(self, profile: LinkedInProfile) -> float:
        """Assess quality of experience section (0-100)"""
        if not profile.experiences:
            return 0
        
        score = 0
        
        # Length and detail
        avg_description_length = sum(
            len(exp.description or "") for exp in profile.experiences
        ) / len(profile.experiences)
        
        if avg_description_length > 200:
            score += 30
        elif avg_description_length > 100:
            score += 20
        elif avg_description_length > 50:
            score += 10
        
        # Diversity of experience
        if len(profile.experiences) >= 3:
            score += 20
        elif len(profile.experiences) >= 2:
            score += 10
        
        # Current employment
        if profile.current_position:
            score += 15
        
        # Skills mentioned in experiences
        experiences_with_skills = sum(1 for exp in profile.experiences if exp.skills_used)
        if experiences_with_skills > 0:
            score += 15
        
        # Career progression (titles suggest growth)
        if self._has_progression_in_titles(profile):
            score += 20
        
        return min(100, score)
    
    def _assess_skill_quality(self, profile: LinkedInProfile) -> float:
        """Assess quality of skills section (0-100)"""
        if not profile.skills:
            return 0
        
        score = 0
        
        # Number of skills
        num_skills = len(profile.skills)
        if num_skills >= 15:
            score += 25
        elif num_skills >= 10:
            score += 20
        elif num_skills >= 5:
            score += 15
        else:
            score += 10
        
        # Endorsed skills
        endorsed_skills = [s for s in profile.skills if s.endorsements > 0]
        if endorsed_skills:
            score += 20
            avg_endorsements = sum(s.endorsements for s in endorsed_skills) / len(endorsed_skills)
            if avg_endorsements >= 10:
                score += 10
        
        # Verified skills
        verified_skills = [s for s in profile.skills if s.verified]
        if verified_skills:
            score += 15
        
        # Skill diversity (multiple categories)
        categories = {s.category for s in profile.skills}
        if len(categories) >= 4:
            score += 15
        elif len(categories) >= 3:
            score += 10
        elif len(categories) >= 2:
            score += 5
        
        # Proficiency levels specified
        skills_with_proficiency = [s for s in profile.skills if s.proficiency_level]
        if len(skills_with_proficiency) > len(profile.skills) / 2:
            score += 15
        
        return min(100, score)
    
    def _assess_education(self, profile: LinkedInProfile) -> float:
        """Assess education section (0-100)"""
        if not profile.education:
            return 0
        
        score = 50  # Base score for having education
        
        # Degree level
        highest_degree = self._get_highest_degree(profile)
        if highest_degree:
            if "phd" in highest_degree.lower() or "doctorate" in highest_degree.lower():
                score += 30
            elif "master" in highest_degree.lower() or "ms" in highest_degree.lower():
                score += 20
            elif "bachelor" in highest_degree.lower() or "bs" in highest_degree.lower():
                score += 10
        
        # Multiple degrees
        if len(profile.education) >= 2:
            score += 10
        
        # Field of study specified
        if all(edu.field_of_study for edu in profile.education):
            score += 10
        
        return min(100, score)
    
    def _assess_certifications(self, profile: LinkedInProfile) -> float:
        """Assess certifications (0-100)"""
        if not profile.certifications:
            return 0
        
        score = 40  # Base score for having certifications
        
        # Number of certifications
        num_certs = len(profile.certifications)
        if num_certs >= 5:
            score += 30
        elif num_certs >= 3:
            score += 20
        elif num_certs >= 2:
            score += 10
        
        # Active certifications
        active_certs = [c for c in profile.certifications if c.is_active]
        if active_certs:
            score += 15
        
        # Verified certifications (with credential ID/URL)
        verified_certs = [c for c in profile.certifications if c.credential_id or c.credential_url]
        if len(verified_certs) >= len(profile.certifications) / 2:
            score += 15
        
        return min(100, score)
    
    def _assess_engagement(self, profile: LinkedInProfile) -> float:
        """Assess profile engagement metrics (0-100)"""
        score = 0
        
        # Profile views
        if profile.profile_views >= 100:
            score += 40
        elif profile.profile_views >= 50:
            score += 30
        elif profile.profile_views >= 20:
            score += 20
        elif profile.profile_views > 0:
            score += 10
        
        # Connections
        if profile.connections_count >= 500:
            score += 60
        elif profile.connections_count >= 200:
            score += 40
        elif profile.connections_count >= 50:
            score += 20
        elif profile.connections_count > 0:
            score += 10
        
        return min(100, score)
    
    def _calculate_experience_level(self, years: float) -> ExperienceLevel:
        """Map years of experience to level"""
        if years < 1:
            return ExperienceLevel.ENTRY_LEVEL
        elif years < 2:
            return ExperienceLevel.ASSOCIATE
        elif years < 5:
            return ExperienceLevel.MID_LEVEL
        elif years < 8:
            return ExperienceLevel.SENIOR
        elif years < 12:
            return ExperienceLevel.LEAD
        elif years < 15:
            return ExperienceLevel.PRINCIPAL
        else:
            return ExperienceLevel.EXECUTIVE
    
    def _assess_career_progression(self, profile: LinkedInProfile) -> str:
        """Assess career progression quality"""
        if not profile.experiences or len(profile.experiences) < 2:
            return "Insufficient data"
        
        # Check for progression in titles
        if self._has_progression_in_titles(profile):
            return "Strong upward trajectory with clear progression"
        
        # Check for consistent growth
        experiences_sorted = sorted(profile.experiences, key=lambda x: x.start_date)
        
        # Check company prestige/size progression (simplified heuristic)
        # In production, would use company data
        if len(experiences_sorted) >= 3:
            return "Steady career growth across multiple roles"
        
        return "Moderate progression with room for growth"
    
    def _has_progression_in_titles(self, profile: LinkedInProfile) -> bool:
        """Check if titles show progression (e.g., Junior -> Senior)"""
        progression_keywords = [
            ["junior", "associate", "mid", "senior", "lead", "principal", "staff"],
            ["intern", "engineer", "senior engineer", "lead engineer", "principal engineer"],
            ["analyst", "senior analyst", "manager", "senior manager", "director"],
        ]
        
        titles = [exp.title.lower() for exp in profile.experiences]
        
        for keyword_chain in progression_keywords:
            # Check if titles contain words in progression order
            positions = []
            for title in titles:
                for i, keyword in enumerate(keyword_chain):
                    if keyword in title:
                        positions.append(i)
                        break
            
            # If we found progression (increasing indices)
            if len(positions) >= 2 and positions == sorted(positions):
                return True
        
        return False
    
    def _get_highest_degree(self, profile: LinkedInProfile) -> Optional[str]:
        """Get highest degree from education"""
        if not profile.education:
            return None
        
        degree_rank = {
            "phd": 5, "doctorate": 5,
            "master": 4, "ms": 4, "ma": 4, "mba": 4,
            "bachelor": 3, "bs": 3, "ba": 3,
            "associate": 2, "as": 2,
            "diploma": 1,
        }
        
        highest = None
        highest_rank = 0
        
        for edu in profile.education:
            degree_lower = edu.degree.lower()
            for key, rank in degree_rank.items():
                if key in degree_lower and rank > highest_rank:
                    highest = edu.degree
                    highest_rank = rank
        
        return highest
    
    def _identify_skill_gaps(self, profile: LinkedInProfile) -> List[str]:
        """Identify skill gaps based on role and industry"""
        # Get target role from current position
        target_role = profile.current_position.title if profile.current_position else None
        
        if not target_role:
            return []
        
        # Get recommended skills for role
        recommended = self.skill_extractor.get_skill_recommendations(
            profile.skills,
            target_role,
            max_results=10
        )
        
        return recommended[:5]  # Return top 5 gaps
    
    def _assess_market_competitiveness(self, profile: LinkedInProfile) -> float:
        """Assess how competitive profile is in job market (0-100)"""
        score = 0
        
        # Experience level contributes
        years = profile.total_experience_years
        if years >= 5:
            score += 30
        elif years >= 2:
            score += 20
        elif years >= 1:
            score += 10
        
        # In-demand skills
        in_demand_skills = ["Python", "AWS", "Machine Learning", "React", "Kubernetes", "Docker"]
        profile_skill_names = {s.name for s in profile.skills}
        demand_matches = sum(1 for skill in in_demand_skills if skill in profile_skill_names)
        score += min(30, demand_matches * 6)
        
        # Education
        highest_degree = self._get_highest_degree(profile)
        if highest_degree:
            if "master" in highest_degree.lower() or "phd" in highest_degree.lower():
                score += 20
            elif "bachelor" in highest_degree.lower():
                score += 10
        
        # Certifications
        if profile.certifications:
            active_certs = [c for c in profile.certifications if c.is_active]
            score += min(20, len(active_certs) * 5)
        
        return min(100, score)
    
    def _estimate_salary(self, profile: LinkedInProfile) -> Optional[str]:
        """Estimate salary range based on profile"""
        # Simplified estimation based on experience and skills
        years = profile.total_experience_years
        
        # Base salary by experience
        if years >= 15:
            base_low, base_high = 150000, 250000
        elif years >= 10:
            base_low, base_high = 120000, 180000
        elif years >= 7:
            base_low, base_high = 100000, 150000
        elif years >= 5:
            base_low, base_high = 80000, 120000
        elif years >= 3:
            base_low, base_high = 70000, 100000
        elif years >= 1:
            base_low, base_high = 60000, 80000
        else:
            base_low, base_high = 50000, 70000
        
        # Adjust for in-demand skills
        in_demand_skills = ["AWS", "Machine Learning", "Python", "Kubernetes", "React"]
        profile_skill_names = {s.name for s in profile.skills}
        demand_matches = sum(1 for skill in in_demand_skills if skill in profile_skill_names)
        
        adjustment = 1.0 + (demand_matches * 0.1)  # 10% increase per in-demand skill
        
        adjusted_low = int(base_low * adjustment)
        adjusted_high = int(base_high * adjustment)
        
        return f"${adjusted_low:,} - ${adjusted_high:,}"
    
    def _assess_demand_level(self, profile: LinkedInProfile) -> str:
        """Assess market demand level for profile"""
        competitiveness = self._assess_market_competitiveness(profile)
        
        if competitiveness >= 75:
            return "high"
        elif competitiveness >= 50:
            return "medium"
        else:
            return "low"
    
    def _identify_strengths(self, profile: LinkedInProfile, overall_score: float) -> List[str]:
        """Identify profile strengths"""
        strengths = []
        
        if overall_score >= 80:
            strengths.append("Exceptionally strong overall profile")
        
        if len(profile.skills) >= 10:
            strengths.append(f"Diverse skill set with {len(profile.skills)} skills")
        
        if profile.total_experience_years >= 5:
            strengths.append(f"{profile.total_experience_years:.1f} years of professional experience")
        
        # Check for endorsements
        total_endorsements = sum(s.endorsements for s in profile.skills)
        if total_endorsements >= 50:
            strengths.append(f"Well-endorsed skills ({total_endorsements} total endorsements)")
        
        # Active certifications
        if profile.certifications:
            active = [c for c in profile.certifications if c.is_active]
            if active:
                strengths.append(f"{len(active)} active professional certifications")
        
        # Career progression
        if self._has_progression_in_titles(profile):
            strengths.append("Clear career progression and growth")
        
        return strengths
    
    def _identify_weaknesses(self, profile: LinkedInProfile, overall_score: float) -> List[str]:
        """Identify profile weaknesses"""
        weaknesses = []
        
        if not profile.summary:
            weaknesses.append("Missing professional summary")
        
        if not profile.headline:
            weaknesses.append("Missing headline")
        
        if len(profile.skills) < 5:
            weaknesses.append("Limited skills listed (should have at least 10-15)")
        
        if not profile.certifications:
            weaknesses.append("No certifications listed")
        
        if profile.connections_count < 50:
            weaknesses.append("Low number of connections")
        
        # Check for skill endorsements
        endorsed_skills = [s for s in profile.skills if s.endorsements > 0]
        if len(endorsed_skills) < len(profile.skills) / 2:
            weaknesses.append("Most skills lack endorsements")
        
        # Check experience descriptions
        experiences_with_desc = [e for e in profile.experiences if e.description]
        if len(experiences_with_desc) < len(profile.experiences) / 2:
            weaknesses.append("Many experiences lack detailed descriptions")
        
        return weaknesses
    
    def _identify_improvement_areas(self, profile: LinkedInProfile, weaknesses: List[str]) -> List[str]:
        """Identify specific areas for improvement"""
        improvements = []
        
        for weakness in weaknesses:
            if "summary" in weakness.lower():
                improvements.append("Add a compelling professional summary highlighting key achievements")
            elif "headline" in weakness.lower():
                improvements.append("Create an attention-grabbing headline with your role and key skills")
            elif "skills" in weakness.lower() and "limited" in weakness.lower():
                improvements.append("Add more relevant skills (target 15-20 skills)")
            elif "certification" in weakness.lower():
                improvements.append("Obtain industry-recognized certifications")
            elif "connection" in weakness.lower():
                improvements.append("Actively network and grow connections")
            elif "endorsement" in weakness.lower():
                improvements.append("Request endorsements from colleagues and connections")
            elif "description" in weakness.lower():
                improvements.append("Add detailed descriptions to work experiences")
        
        return improvements
    
    def _generate_next_steps(self, profile: LinkedInProfile, improvement_areas: List[str]) -> List[str]:
        """Generate actionable next steps"""
        next_steps = []
        
        # Prioritize based on impact
        if not profile.summary:
            next_steps.append("Write a professional summary (150-300 words)")
        
        if len(profile.skills) < 10:
            next_steps.append("Add 5-10 more relevant skills to your profile")
        
        if improvement_areas:
            # Add first 3 improvement areas as next steps
            next_steps.extend(improvement_areas[:3])
        
        # General recommendations
        next_steps.append("Request recommendations from former colleagues or managers")
        next_steps.append("Share relevant content and engage with your network regularly")
        
        return next_steps[:5]  # Return top 5 next steps
