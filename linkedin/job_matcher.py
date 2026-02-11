"""
LinkedIn Job Matcher

Intelligent job matching algorithm that scores profile-job compatibility
based on skills, experience, education, location, and other factors.
"""

import logging
from typing import List, Dict, Tuple, Optional
from datetime import datetime

from linkedin.models import (
    LinkedInProfile,
    JobPosting,
    MatchScore,
    SkillCategory,
    ExperienceLevel,
)
from linkedin.skill_extractor import SkillExtractor

logger = logging.getLogger(__name__)


class JobMatcher:
    """
    Match LinkedIn profiles to job postings with detailed scoring
    
    Features:
    - Multi-dimensional matching (skills, experience, education, location)
    - Weighted scoring algorithm
    - Gap analysis and improvement suggestions
    - Batch matching for multiple jobs
    """
    
    # Scoring weights (must sum to 1.0)
    WEIGHTS = {
        "skills": 0.45,  # Skills are most important
        "experience": 0.30,
        "education": 0.15,
        "location": 0.10,
    }
    
    def __init__(self, skill_extractor: Optional[SkillExtractor] = None):
        """
        Initialize job matcher
        
        Args:
            skill_extractor: SkillExtractor instance for skill analysis
        """
        self.skill_extractor = skill_extractor or SkillExtractor()
    
    def match_profile_to_job(
        self,
        profile: LinkedInProfile,
        job: JobPosting,
        detailed: bool = True
    ) -> MatchScore:
        """
        Calculate match score between profile and job
        
        Args:
            profile: LinkedInProfile to match
            job: JobPosting to match against
            detailed: Include detailed analysis (gaps, suggestions)
        
        Returns:
            MatchScore object with overall and component scores
        """
        # Calculate component scores
        skills_score, skills_details = self._score_skills_match(profile, job)
        experience_score, exp_details = self._score_experience_match(profile, job)
        education_score, edu_details = self._score_education_match(profile, job)
        location_score, loc_details = self._score_location_match(profile, job)
        
        # Calculate weighted overall score
        overall_score = (
            skills_score * self.WEIGHTS["skills"] +
            experience_score * self.WEIGHTS["experience"] +
            education_score * self.WEIGHTS["education"] +
            location_score * self.WEIGHTS["location"]
        )
        
        # Build match score object
        match_score = MatchScore(
            profile_id=profile.profile_id,
            job_id=job.job_id,
            overall_score=round(overall_score, 2),
            skills_match_score=round(skills_score, 2),
            experience_match_score=round(experience_score, 2),
            education_match_score=round(education_score, 2),
            location_match_score=round(location_score, 2),
            matched_skills=skills_details["matched"],
            missing_skills=skills_details["missing"],
            calculated_at=datetime.utcnow(),
        )
        
        if detailed:
            # Add detailed analysis
            match_score.matched_requirements = self._get_matched_requirements(
                profile, job, skills_details, exp_details, edu_details
            )
            match_score.missing_requirements = self._get_missing_requirements(
                profile, job, skills_details, exp_details, edu_details
            )
            match_score.strengths = self._identify_strengths(profile, job, match_score)
            match_score.gaps = self._identify_gaps(profile, job, match_score)
            match_score.improvement_suggestions = self._generate_improvement_suggestions(
                profile, job, match_score
            )
            
            # Calculate confidence based on data completeness
            match_score.confidence = self._calculate_confidence(profile, job)
        
        return match_score
    
    def match_profile_to_jobs(
        self,
        profile: LinkedInProfile,
        jobs: List[JobPosting],
        top_n: Optional[int] = None,
        min_score: float = 0.0
    ) -> List[MatchScore]:
        """
        Match profile against multiple jobs and rank them
        
        Args:
            profile: LinkedInProfile to match
            jobs: List of JobPostings to match against
            top_n: Return only top N matches
            min_score: Minimum score threshold (0-100)
        
        Returns:
            List of MatchScore objects sorted by score (highest first)
        """
        matches = []
        
        for job in jobs:
            try:
                match = self.match_profile_to_job(profile, job, detailed=False)
                if match.overall_score >= min_score:
                    matches.append(match)
            except Exception as e:
                logger.error(f"Error matching profile to job {job.job_id}: {e}")
        
        # Sort by overall score (descending)
        matches.sort(key=lambda x: x.overall_score, reverse=True)
        
        if top_n:
            matches = matches[:top_n]
        
        return matches
    
    def find_best_candidates(
        self,
        profiles: List[LinkedInProfile],
        job: JobPosting,
        top_n: int = 10,
        min_score: float = 50.0
    ) -> List[Tuple[LinkedInProfile, MatchScore]]:
        """
        Find best candidate profiles for a job
        
        Args:
            profiles: List of LinkedInProfiles
            job: JobPosting to match against
            top_n: Return top N candidates
            min_score: Minimum match score
        
        Returns:
            List of (profile, match_score) tuples sorted by score
        """
        candidates = []
        
        for profile in profiles:
            try:
                match = self.match_profile_to_job(profile, job, detailed=False)
                if match.overall_score >= min_score:
                    candidates.append((profile, match))
            except Exception as e:
                logger.error(f"Error matching profile {profile.profile_id}: {e}")
        
        # Sort by score
        candidates.sort(key=lambda x: x[1].overall_score, reverse=True)
        
        return candidates[:top_n]
    
    def _score_skills_match(
        self,
        profile: LinkedInProfile,
        job: JobPosting
    ) -> Tuple[float, Dict]:
        """
        Score skills match between profile and job
        
        Returns:
            Tuple of (score 0-100, details dict)
        """
        profile_skills = {skill.name.lower() for skill in profile.skills}
        required_skills = {skill.lower() for skill in job.required_skills}
        preferred_skills = {skill.lower() for skill in job.preferred_skills}
        
        # Check matches using skill extractor for synonym handling
        skill_gaps = self.skill_extractor.find_skill_gaps(
            profile.skills,
            job.required_skills,
            job.preferred_skills
        )
        
        matched_required = set(skill_gaps["matched_required"])
        matched_preferred = set(skill_gaps["matched_preferred"])
        missing_required = set(skill_gaps["missing_required"])
        missing_preferred = set(skill_gaps["missing_preferred"])
        
        # Calculate score
        # Required skills: 70% weight
        # Preferred skills: 30% weight
        required_score = 0.0
        if required_skills:
            required_score = (len(matched_required) / len(required_skills)) * 100
        else:
            required_score = 100.0  # No required skills = perfect match
        
        preferred_score = 0.0
        if preferred_skills:
            preferred_score = (len(matched_preferred) / len(preferred_skills)) * 100
        else:
            preferred_score = 100.0  # No preferred skills
        
        total_score = (required_score * 0.7) + (preferred_score * 0.3)
        
        # Bonus: Extra skills beyond requirements
        extra_skills = profile_skills - required_skills - preferred_skills
        if extra_skills:
            bonus = min(10, len(extra_skills) * 2)  # Up to 10 bonus points
            total_score = min(100, total_score + bonus)
        
        details = {
            "matched": list(matched_required | matched_preferred),
            "missing": list(missing_required | missing_preferred),
            "required_match_rate": len(matched_required) / len(required_skills) if required_skills else 1.0,
            "preferred_match_rate": len(matched_preferred) / len(preferred_skills) if preferred_skills else 1.0,
        }
        
        return total_score, details
    
    def _score_experience_match(
        self,
        profile: LinkedInProfile,
        job: JobPosting
    ) -> Tuple[float, Dict]:
        """
        Score experience match
        
        Returns:
            Tuple of (score 0-100, details dict)
        """
        total_years = profile.total_experience_years
        required_years = job.required_experience_years or 0
        
        # Score based on experience requirements
        if required_years == 0:
            # No experience requirement
            exp_score = 100.0
        elif total_years >= required_years:
            # Meets or exceeds requirement
            # Perfect score if within 2x requirement, slight penalty for too much overqualification
            if total_years <= required_years * 2:
                exp_score = 100.0
            else:
                # Slightly penalize extreme overqualification
                excess = total_years - (required_years * 2)
                exp_score = max(80, 100 - (excess * 2))
        else:
            # Below requirement - score proportionally
            exp_score = (total_years / required_years) * 100
        
        # Check experience level match
        level_score = self._score_experience_level(profile, job)
        
        # Check industry experience
        industry_score = self._score_industry_experience(profile, job)
        
        # Combined experience score
        final_score = (exp_score * 0.5) + (level_score * 0.3) + (industry_score * 0.2)
        
        details = {
            "total_years": total_years,
            "required_years": required_years,
            "years_score": exp_score,
            "level_score": level_score,
            "industry_score": industry_score,
            "meets_requirement": total_years >= required_years,
        }
        
        return final_score, details
    
    def _score_experience_level(self, profile: LinkedInProfile, job: JobPosting) -> float:
        """Score experience level match"""
        if not profile.experiences:
            return 50.0  # Default middle score
        
        # Map profile experience to level
        total_years = profile.total_experience_years
        profile_level = self._map_years_to_level(total_years)
        
        # Compare with job level
        job_level = job.experience_level
        
        # Level hierarchy
        level_order = [
            ExperienceLevel.ENTRY_LEVEL,
            ExperienceLevel.ASSOCIATE,
            ExperienceLevel.MID_LEVEL,
            ExperienceLevel.SENIOR,
            ExperienceLevel.LEAD,
            ExperienceLevel.PRINCIPAL,
            ExperienceLevel.EXECUTIVE,
        ]
        
        try:
            profile_idx = level_order.index(profile_level)
            job_idx = level_order.index(job_level)
            
            # Perfect match
            if profile_idx == job_idx:
                return 100.0
            # One level difference
            elif abs(profile_idx - job_idx) == 1:
                return 80.0
            # Two levels difference
            elif abs(profile_idx - job_idx) == 2:
                return 60.0
            # More than 2 levels
            else:
                return 40.0
        except ValueError:
            return 50.0
    
    def _score_industry_experience(self, profile: LinkedInProfile, job: JobPosting) -> float:
        """Score industry experience match"""
        profile_industries = {exp.industry for exp in profile.experiences}
        job_industry = job.industry
        
        if job_industry in profile_industries:
            return 100.0  # Direct industry match
        
        # Check if profile has experience in related industries
        # For simplicity, any industry experience gets partial credit
        if profile_industries:
            return 50.0
        
        return 0.0
    
    def _score_education_match(
        self,
        profile: LinkedInProfile,
        job: JobPosting
    ) -> Tuple[float, Dict]:
        """
        Score education match
        
        Returns:
            Tuple of (score 0-100, details dict)
        """
        if not job.required_education:
            # No education requirement
            return 100.0, {"meets_requirement": True}
        
        if not profile.education:
            # Education required but profile has none
            return 0.0, {"meets_requirement": False}
        
        # Get highest degree
        degree_hierarchy = {
            "phd": 5, "doctorate": 5,
            "master": 4, "masters": 4, "ms": 4, "ma": 4, "mba": 4,
            "bachelor": 3, "bachelors": 3, "bs": 3, "ba": 3,
            "associate": 2, "associates": 2, "as": 2, "aa": 2,
            "diploma": 1, "certificate": 1,
        }
        
        # Find highest degree level
        max_level = 0
        for edu in profile.education:
            degree_lower = edu.degree.lower()
            for key, level in degree_hierarchy.items():
                if key in degree_lower:
                    max_level = max(max_level, level)
                    break
        
        # Find required level
        required_level = 0
        required_lower = job.required_education.lower()
        for key, level in degree_hierarchy.items():
            if key in required_lower:
                required_level = level
                break
        
        # Calculate score
        if max_level >= required_level:
            score = 100.0
        elif max_level == required_level - 1:
            score = 70.0  # Close enough
        else:
            score = max(0, 50 - ((required_level - max_level) * 20))
        
        details = {
            "meets_requirement": max_level >= required_level,
            "profile_level": max_level,
            "required_level": required_level,
        }
        
        return score, details
    
    def _score_location_match(
        self,
        profile: LinkedInProfile,
        job: JobPosting
    ) -> Tuple[float, Dict]:
        """
        Score location match
        
        Returns:
            Tuple of (score 0-100, details dict)
        """
        if not profile.location or not job.location:
            return 50.0, {}  # Unknown, give benefit of doubt
        
        profile_loc = profile.location.lower()
        job_loc = job.location.lower()
        
        # Check for remote
        if "remote" in job_loc:
            return 100.0, {"match_type": "remote"}
        
        # Exact match (city level)
        if profile_loc == job_loc:
            return 100.0, {"match_type": "exact"}
        
        # State/region match
        # Simple heuristic: check if any word overlaps
        profile_words = set(profile_loc.split(","))
        job_words = set(job_loc.split(","))
        if profile_words & job_words:
            return 70.0, {"match_type": "region"}
        
        # No match
        return 30.0, {"match_type": "different"}
    
    def _map_years_to_level(self, years: float) -> ExperienceLevel:
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
    
    def _get_matched_requirements(
        self,
        profile: LinkedInProfile,
        job: JobPosting,
        skills_details: Dict,
        exp_details: Dict,
        edu_details: Dict
    ) -> List[str]:
        """Get list of matched requirements"""
        matched = []
        
        # Skills
        if skills_details["matched"]:
            matched.append(f"Has {len(skills_details['matched'])} required skills: {', '.join(skills_details['matched'][:5])}")
        
        # Experience
        if exp_details.get("meets_requirement"):
            matched.append(f"Has {exp_details['total_years']} years of experience (required: {exp_details['required_years']})")
        
        # Education
        if edu_details.get("meets_requirement"):
            matched.append("Meets education requirements")
        
        return matched
    
    def _get_missing_requirements(
        self,
        profile: LinkedInProfile,
        job: JobPosting,
        skills_details: Dict,
        exp_details: Dict,
        edu_details: Dict
    ) -> List[str]:
        """Get list of missing requirements"""
        missing = []
        
        # Skills
        if skills_details["missing"]:
            missing.append(f"Missing {len(skills_details['missing'])} required skills: {', '.join(skills_details['missing'][:5])}")
        
        # Experience
        if not exp_details.get("meets_requirement"):
            missing.append(f"Needs {exp_details['required_years'] - exp_details['total_years']:.1f} more years of experience")
        
        # Education
        if not edu_details.get("meets_requirement"):
            missing.append("Does not meet education requirements")
        
        return missing
    
    def _identify_strengths(
        self,
        profile: LinkedInProfile,
        job: JobPosting,
        match_score: MatchScore
    ) -> List[str]:
        """Identify profile strengths for this job"""
        strengths = []
        
        if match_score.skills_match_score >= 80:
            strengths.append("Strong technical skill match")
        
        if match_score.experience_match_score >= 80:
            strengths.append("Excellent experience level for this role")
        
        if match_score.education_match_score >= 90:
            strengths.append("Exceeds education requirements")
        
        # Check for relevant certifications
        if profile.certifications:
            active_certs = [cert for cert in profile.certifications if cert.is_active]
            if active_certs:
                strengths.append(f"Has {len(active_certs)} relevant certifications")
        
        # Check current position relevance
        if profile.current_position:
            current = profile.current_position
            if any(skill.lower() in [s.lower() for s in job.all_skills] for skill in current.skills_used):
                strengths.append("Currently using relevant skills in current role")
        
        return strengths
    
    def _identify_gaps(
        self,
        profile: LinkedInProfile,
        job: JobPosting,
        match_score: MatchScore
    ) -> List[str]:
        """Identify profile gaps for this job"""
        gaps = []
        
        if match_score.skills_match_score < 60:
            gaps.append("Significant skill gap - missing key technical skills")
        
        if match_score.experience_match_score < 50:
            gaps.append("Insufficient experience for this role")
        
        if match_score.missing_skills:
            top_missing = match_score.missing_skills[:3]
            gaps.append(f"Missing critical skills: {', '.join(top_missing)}")
        
        return gaps
    
    def _generate_improvement_suggestions(
        self,
        profile: LinkedInProfile,
        job: JobPosting,
        match_score: MatchScore
    ) -> List[str]:
        """Generate suggestions to improve match"""
        suggestions = []
        
        # Skill suggestions
        if match_score.missing_skills:
            top_missing = match_score.missing_skills[:3]
            suggestions.append(f"Consider learning: {', '.join(top_missing)}")
            suggestions.append("Take online courses or certifications in missing skills")
        
        # Experience suggestions
        if match_score.experience_match_score < 70:
            suggestions.append("Gain more relevant experience in similar roles")
            suggestions.append("Consider contract or freelance work to build experience")
        
        # Education suggestions
        if match_score.education_match_score < 70:
            suggestions.append("Consider pursuing additional education or certifications")
        
        # Profile optimization
        if not profile.summary:
            suggestions.append("Add a professional summary highlighting relevant experience")
        
        if not profile.certifications:
            suggestions.append("Obtain industry-recognized certifications")
        
        return suggestions
    
    def _calculate_confidence(self, profile: LinkedInProfile, job: JobPosting) -> float:
        """Calculate confidence score based on data completeness"""
        confidence = 1.0
        
        # Reduce confidence for incomplete data
        if not profile.skills:
            confidence *= 0.7
        if not profile.experiences:
            confidence *= 0.8
        if not profile.education:
            confidence *= 0.9
        if not profile.summary:
            confidence *= 0.95
        
        if not job.required_skills:
            confidence *= 0.8
        if not job.required_experience_years:
            confidence *= 0.9
        
        return round(confidence, 2)
