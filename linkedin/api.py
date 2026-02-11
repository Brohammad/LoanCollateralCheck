"""
LinkedIn Features API

FastAPI endpoints for LinkedIn profile analysis, job matching, and recommendations.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from pydantic import BaseModel

from linkedin import (
    ProfileParser,
    JobMatcher,
    SkillExtractor,
    RecommendationEngine,
    ProfileAnalyzer,
    IndustryInsightsEngine,
    LinkedInProfile,
    JobPosting,
    MatchScore,
    Recommendation,
    ProfileAnalysis,
    IndustryInsight,
    IndustryType,
)

router = APIRouter(prefix="/linkedin", tags=["LinkedIn"])

# Initialize components
profile_parser = ProfileParser()
skill_extractor = SkillExtractor()
job_matcher = JobMatcher(skill_extractor)
recommender = RecommendationEngine(skill_extractor, job_matcher)
profile_analyzer = ProfileAnalyzer(skill_extractor)
industry_insights = IndustryInsightsEngine()


# Request/Response models
class ParseProfileRequest(BaseModel):
    data: dict
    source: str = "json"


class MatchJobRequest(BaseModel):
    profile: LinkedInProfile
    job: JobPosting
    detailed: bool = True


class BatchMatchRequest(BaseModel):
    profile: LinkedInProfile
    jobs: List[JobPosting]
    top_n: Optional[int] = 10
    min_score: float = 50.0


class RecommendationsRequest(BaseModel):
    profile: LinkedInProfile
    available_jobs: Optional[List[JobPosting]] = None
    target_role: Optional[str] = None
    max_per_type: int = 5


class ExtractSkillsRequest(BaseModel):
    text: str
    context: Optional[str] = None
    min_confidence: float = 0.5


# Endpoints

@router.post("/profile/parse", response_model=LinkedInProfile)
async def parse_profile(request: ParseProfileRequest):
    """
    Parse LinkedIn profile from various data formats
    
    Supports: JSON, HTML, text, PDF formats
    """
    try:
        profile = profile_parser.parse_profile(request.data, request.source)
        # Enrich with additional data
        profile = profile_parser.enrich_profile(profile)
        return profile
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error parsing profile: {str(e)}")


@router.post("/profile/validate")
async def validate_profile(profile: LinkedInProfile):
    """Validate profile completeness and quality"""
    is_valid, errors = profile_parser.validate_profile(profile)
    return {
        "is_valid": is_valid,
        "errors": errors,
        "error_count": len(errors),
    }


@router.post("/profile/analyze", response_model=ProfileAnalysis)
async def analyze_profile(profile: LinkedInProfile):
    """
    Comprehensive profile analysis
    
    Returns: Profile strength, completeness, skills analysis, career insights
    """
    try:
        analysis = profile_analyzer.analyze_profile(profile)
        return analysis
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing profile: {str(e)}")


@router.post("/skills/extract")
async def extract_skills(request: ExtractSkillsRequest):
    """
    Extract skills from text using NLP
    
    Returns: List of extracted skills with categories and confidence scores
    """
    try:
        skills = skill_extractor.extract_skills(
            request.text,
            request.context,
            request.min_confidence
        )
        return {
            "skills": skills,
            "count": len(skills),
            "by_category": skill_extractor.categorize_skills(skills),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extracting skills: {str(e)}")


@router.post("/skills/extract-from-profile")
async def extract_skills_from_profile(profile: LinkedInProfile):
    """Extract all skills from a complete profile"""
    try:
        skills = skill_extractor.extract_from_profile(profile)
        return {
            "skills": skills,
            "count": len(skills),
            "by_category": skill_extractor.categorize_skills(skills),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extracting skills: {str(e)}")


@router.post("/skills/find-gaps")
async def find_skill_gaps(
    profile: LinkedInProfile,
    required_skills: List[str],
    preferred_skills: Optional[List[str]] = None
):
    """
    Identify skill gaps for a job or role
    
    Returns: Missing required/preferred skills and matched skills
    """
    gaps = skill_extractor.find_skill_gaps(
        profile.skills,
        required_skills,
        preferred_skills
    )
    return gaps


@router.post("/match/job", response_model=MatchScore)
async def match_profile_to_job(request: MatchJobRequest):
    """
    Calculate match score between profile and job
    
    Returns: Overall score, component scores, gaps, and recommendations
    """
    try:
        match = job_matcher.match_profile_to_job(
            request.profile,
            request.job,
            request.detailed
        )
        return match
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error matching profile to job: {str(e)}")


@router.post("/match/jobs", response_model=List[MatchScore])
async def match_profile_to_jobs(request: BatchMatchRequest):
    """
    Match profile against multiple jobs and rank them
    
    Returns: List of match scores sorted by relevance
    """
    try:
        matches = job_matcher.match_profile_to_jobs(
            request.profile,
            request.jobs,
            request.top_n,
            request.min_score
        )
        return matches
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error matching profile to jobs: {str(e)}")


@router.post("/match/candidates")
async def find_best_candidates(
    profiles: List[LinkedInProfile],
    job: JobPosting,
    top_n: int = 10,
    min_score: float = 50.0
):
    """
    Find best candidate profiles for a job
    
    Returns: Top candidates with match scores
    """
    try:
        candidates = job_matcher.find_best_candidates(
            profiles,
            job,
            top_n,
            min_score
        )
        return [
            {
                "profile": profile,
                "match_score": match,
            }
            for profile, match in candidates
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error finding candidates: {str(e)}")


@router.post("/recommendations/all", response_model=List[Recommendation])
async def get_all_recommendations(request: RecommendationsRequest):
    """
    Generate comprehensive recommendations across all types
    
    Returns: Jobs, skills, courses, and certifications to pursue
    """
    try:
        recommendations = recommender.generate_all_recommendations(
            request.profile,
            request.available_jobs,
            request.target_role,
            request.max_per_type
        )
        return recommendations
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating recommendations: {str(e)}")


@router.post("/recommendations/jobs", response_model=List[Recommendation])
async def recommend_jobs(
    profile: LinkedInProfile,
    available_jobs: List[JobPosting],
    max_results: int = 10,
    min_score: float = 50.0
):
    """Recommend jobs for a profile"""
    try:
        recommendations = recommender.recommend_jobs(
            profile,
            available_jobs,
            max_results,
            min_score
        )
        return recommendations
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error recommending jobs: {str(e)}")


@router.post("/recommendations/skills", response_model=List[Recommendation])
async def recommend_skills(
    profile: LinkedInProfile,
    target_role: Optional[str] = None,
    max_results: int = 10
):
    """Recommend skills to learn"""
    try:
        recommendations = recommender.recommend_skills(
            profile,
            target_role,
            max_results
        )
        return recommendations
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error recommending skills: {str(e)}")


@router.post("/recommendations/courses", response_model=List[Recommendation])
async def recommend_courses(
    profile: LinkedInProfile,
    target_role: Optional[str] = None,
    max_results: int = 5
):
    """Recommend courses to take"""
    try:
        recommendations = recommender.recommend_courses(
            profile,
            target_role,
            max_results
        )
        return recommendations
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error recommending courses: {str(e)}")


@router.post("/recommendations/certifications", response_model=List[Recommendation])
async def recommend_certifications(
    profile: LinkedInProfile,
    max_results: int = 5
):
    """Recommend certifications to obtain"""
    try:
        recommendations = recommender.recommend_certifications(
            profile,
            max_results
        )
        return recommendations
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error recommending certifications: {str(e)}")


@router.get("/industry/insights/{industry}", response_model=IndustryInsight)
async def get_industry_insights(industry: IndustryType):
    """
    Get comprehensive insights for an industry
    
    Returns: Trending skills, salary data, growth rates, top companies
    """
    try:
        insights = industry_insights.get_industry_insights(industry)
        return insights
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting industry insights: {str(e)}")


@router.post("/industry/compare")
async def compare_industries(industries: List[IndustryType]):
    """Compare multiple industries"""
    try:
        comparison = industry_insights.compare_industries(industries)
        return comparison
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error comparing industries: {str(e)}")


@router.get("/industry/trending-skills")
async def get_trending_skills(top_n: int = 20):
    """Get globally trending skills across all industries"""
    try:
        skills = industry_insights.get_trending_skills_global(top_n)
        return {"trending_skills": skills, "count": len(skills)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting trending skills: {str(e)}")


@router.post("/industry/salary-benchmark")
async def get_salary_benchmark(
    role: str,
    experience_years: float,
    location: Optional[str] = None,
    industry: Optional[IndustryType] = None
):
    """Get salary benchmark for a role"""
    try:
        benchmark = industry_insights.get_salary_benchmark(
            role,
            experience_years,
            location,
            industry
        )
        return benchmark
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting salary benchmark: {str(e)}")


@router.post("/industry/market-position")
async def analyze_market_position(profile: LinkedInProfile):
    """Analyze where profile stands in the market"""
    try:
        analysis = industry_insights.analyze_profile_market_position(profile)
        return analysis
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing market position: {str(e)}")


@router.post("/industry/career-path")
async def get_career_path_insights(
    current_role: str,
    target_role: str,
    industry: Optional[IndustryType] = None
):
    """Get insights on career path from current to target role"""
    try:
        insights = industry_insights.get_career_path_insights(
            current_role,
            target_role,
            industry
        )
        return insights
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting career path insights: {str(e)}")


# Health check
@router.get("/health")
async def health_check():
    """LinkedIn features health check"""
    return {
        "status": "healthy",
        "features": [
            "profile_parsing",
            "skill_extraction",
            "job_matching",
            "recommendations",
            "profile_analysis",
            "industry_insights",
        ],
    }
