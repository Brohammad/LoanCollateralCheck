"""
LinkedIn Data Models

Pydantic models for LinkedIn profile data, job postings, skills, and analysis results.
"""

from datetime import datetime, date
from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, HttpUrl


class SkillCategory(str, Enum):
    """Skill category classification"""
    TECHNICAL = "technical"
    SOFT_SKILLS = "soft_skills"
    DOMAIN_KNOWLEDGE = "domain_knowledge"
    TOOLS = "tools"
    LANGUAGES = "languages"
    CERTIFICATIONS = "certifications"
    MANAGEMENT = "management"
    DESIGN = "design"
    ANALYTICS = "analytics"
    COMMUNICATION = "communication"


class ExperienceLevel(str, Enum):
    """Experience level classification"""
    ENTRY_LEVEL = "entry_level"
    ASSOCIATE = "associate"
    MID_LEVEL = "mid_level"
    SENIOR = "senior"
    LEAD = "lead"
    PRINCIPAL = "principal"
    EXECUTIVE = "executive"


class EmploymentType(str, Enum):
    """Employment type"""
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    FREELANCE = "freelance"
    INTERNSHIP = "internship"


class IndustryType(str, Enum):
    """Industry classification"""
    TECHNOLOGY = "technology"
    FINANCE = "finance"
    HEALTHCARE = "healthcare"
    EDUCATION = "education"
    RETAIL = "retail"
    MANUFACTURING = "manufacturing"
    CONSULTING = "consulting"
    MEDIA = "media"
    REAL_ESTATE = "real_estate"
    TELECOMMUNICATIONS = "telecommunications"
    OTHER = "other"


class Skill(BaseModel):
    """Skill model"""
    name: str = Field(..., description="Skill name")
    category: SkillCategory = Field(..., description="Skill category")
    proficiency_level: Optional[int] = Field(None, ge=1, le=5, description="Proficiency (1-5)")
    years_experience: Optional[float] = Field(None, ge=0, description="Years of experience")
    endorsements: int = Field(0, ge=0, description="Number of endorsements")
    verified: bool = Field(False, description="Verified through assessments")
    
    # Metadata
    last_used: Optional[date] = Field(None, description="Last time skill was used")
    source: Optional[str] = Field(None, description="Where skill was mentioned")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Python",
                "category": "technical",
                "proficiency_level": 4,
                "years_experience": 5.0,
                "endorsements": 23,
                "verified": True,
                "last_used": "2026-02-01"
            }
        }


class Experience(BaseModel):
    """Work experience entry"""
    company: str = Field(..., description="Company name")
    title: str = Field(..., description="Job title")
    location: Optional[str] = Field(None, description="Location")
    start_date: date = Field(..., description="Start date")
    end_date: Optional[date] = Field(None, description="End date (None if current)")
    description: Optional[str] = Field(None, description="Job description")
    
    # Derived fields
    employment_type: EmploymentType = Field(EmploymentType.FULL_TIME, description="Employment type")
    industry: IndustryType = Field(IndustryType.OTHER, description="Industry")
    skills_used: List[str] = Field(default_factory=list, description="Skills used in this role")
    achievements: List[str] = Field(default_factory=list, description="Key achievements")
    
    @property
    def is_current(self) -> bool:
        """Check if this is current employment"""
        return self.end_date is None
    
    @property
    def duration_months(self) -> int:
        """Calculate duration in months"""
        end = self.end_date or date.today()
        months = (end.year - self.start_date.year) * 12 + (end.month - self.start_date.month)
        return max(0, months)
    
    @property
    def duration_years(self) -> float:
        """Calculate duration in years"""
        return round(self.duration_months / 12, 1)


class Education(BaseModel):
    """Education entry"""
    institution: str = Field(..., description="Institution name")
    degree: str = Field(..., description="Degree type (BS, MS, PhD, etc.)")
    field_of_study: str = Field(..., description="Field of study/major")
    start_date: Optional[date] = Field(None, description="Start date")
    end_date: Optional[date] = Field(None, description="End date/graduation")
    grade: Optional[str] = Field(None, description="GPA or grade")
    activities: List[str] = Field(default_factory=list, description="Activities and societies")
    description: Optional[str] = Field(None, description="Description")


class Certification(BaseModel):
    """Certification or license"""
    name: str = Field(..., description="Certification name")
    issuing_organization: str = Field(..., description="Issuing organization")
    issue_date: date = Field(..., description="Issue date")
    expiration_date: Optional[date] = Field(None, description="Expiration date")
    credential_id: Optional[str] = Field(None, description="Credential ID")
    credential_url: Optional[HttpUrl] = Field(None, description="Credential URL")
    
    @property
    def is_active(self) -> bool:
        """Check if certification is currently active"""
        if self.expiration_date is None:
            return True
        return self.expiration_date >= date.today()


class LinkedInProfile(BaseModel):
    """Complete LinkedIn profile model"""
    # Basic info
    profile_id: str = Field(..., description="Unique profile identifier")
    first_name: str = Field(..., description="First name")
    last_name: str = Field(..., description="Last name")
    headline: Optional[str] = Field(None, description="Professional headline")
    summary: Optional[str] = Field(None, description="About/summary section")
    location: Optional[str] = Field(None, description="Location")
    
    # Contact
    email: Optional[str] = Field(None, description="Email address")
    phone: Optional[str] = Field(None, description="Phone number")
    linkedin_url: Optional[HttpUrl] = Field(None, description="LinkedIn profile URL")
    website: Optional[HttpUrl] = Field(None, description="Personal website")
    
    # Profile sections
    experiences: List[Experience] = Field(default_factory=list, description="Work experience")
    education: List[Education] = Field(default_factory=list, description="Education")
    skills: List[Skill] = Field(default_factory=list, description="Skills")
    certifications: List[Certification] = Field(default_factory=list, description="Certifications")
    
    # Metadata
    profile_views: int = Field(0, ge=0, description="Profile views")
    connections_count: int = Field(0, ge=0, description="Number of connections")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    @property
    def full_name(self) -> str:
        """Get full name"""
        return f"{self.first_name} {self.last_name}"
    
    @property
    def total_experience_years(self) -> float:
        """Calculate total years of experience"""
        if not self.experiences:
            return 0.0
        return sum(exp.duration_years for exp in self.experiences)
    
    @property
    def current_position(self) -> Optional[Experience]:
        """Get current position"""
        current = [exp for exp in self.experiences if exp.is_current]
        return current[0] if current else None
    
    @property
    def all_skills(self) -> List[str]:
        """Get list of all skill names"""
        return [skill.name for skill in self.skills]


class JobPosting(BaseModel):
    """Job posting model"""
    job_id: str = Field(..., description="Unique job identifier")
    title: str = Field(..., description="Job title")
    company: str = Field(..., description="Company name")
    location: str = Field(..., description="Job location")
    description: str = Field(..., description="Job description")
    
    # Requirements
    required_skills: List[str] = Field(default_factory=list, description="Required skills")
    preferred_skills: List[str] = Field(default_factory=list, description="Preferred skills")
    required_experience_years: Optional[float] = Field(None, description="Required years of experience")
    required_education: Optional[str] = Field(None, description="Required education level")
    
    # Job details
    employment_type: EmploymentType = Field(EmploymentType.FULL_TIME)
    experience_level: ExperienceLevel = Field(ExperienceLevel.MID_LEVEL)
    industry: IndustryType = Field(IndustryType.OTHER)
    salary_range: Optional[str] = Field(None, description="Salary range")
    
    # Metadata
    posted_date: datetime = Field(default_factory=datetime.utcnow)
    application_url: Optional[HttpUrl] = Field(None, description="Application URL")
    benefits: List[str] = Field(default_factory=list, description="Benefits")
    
    @property
    def all_skills(self) -> List[str]:
        """Get all skills (required + preferred)"""
        return list(set(self.required_skills + self.preferred_skills))


class MatchScore(BaseModel):
    """Profile-job match score"""
    profile_id: str = Field(..., description="Profile identifier")
    job_id: str = Field(..., description="Job identifier")
    overall_score: float = Field(..., ge=0, le=100, description="Overall match score (0-100)")
    
    # Component scores
    skills_match_score: float = Field(..., ge=0, le=100, description="Skills match score")
    experience_match_score: float = Field(..., ge=0, le=100, description="Experience match score")
    education_match_score: float = Field(..., ge=0, le=100, description="Education match score")
    location_match_score: float = Field(..., ge=0, le=100, description="Location match score")
    
    # Detailed analysis
    matched_skills: List[str] = Field(default_factory=list, description="Matched skills")
    missing_skills: List[str] = Field(default_factory=list, description="Missing skills")
    matched_requirements: List[str] = Field(default_factory=list, description="Met requirements")
    missing_requirements: List[str] = Field(default_factory=list, description="Unmet requirements")
    
    # Recommendations
    strengths: List[str] = Field(default_factory=list, description="Profile strengths for this job")
    gaps: List[str] = Field(default_factory=list, description="Profile gaps for this job")
    improvement_suggestions: List[str] = Field(default_factory=list, description="How to improve match")
    
    # Metadata
    confidence: float = Field(1.0, ge=0, le=1.0, description="Confidence in match score")
    calculated_at: datetime = Field(default_factory=datetime.utcnow)


class RecommendationType(str, Enum):
    """Recommendation type"""
    JOB = "job"
    SKILL = "skill"
    COURSE = "course"
    CERTIFICATION = "certification"
    CONNECTION = "connection"
    CONTENT = "content"


class Recommendation(BaseModel):
    """Recommendation model"""
    recommendation_id: str = Field(..., description="Unique recommendation identifier")
    profile_id: str = Field(..., description="Profile this recommendation is for")
    type: RecommendationType = Field(..., description="Recommendation type")
    
    # Content
    title: str = Field(..., description="Recommendation title")
    description: str = Field(..., description="Recommendation description")
    relevance_score: float = Field(..., ge=0, le=100, description="Relevance score (0-100)")
    
    # Details
    reason: str = Field(..., description="Why this is recommended")
    action_items: List[str] = Field(default_factory=list, description="Suggested actions")
    expected_impact: Optional[str] = Field(None, description="Expected impact")
    
    # For job recommendations
    job_id: Optional[str] = Field(None, description="Job ID if type is JOB")
    
    # For skill/course recommendations
    skill_name: Optional[str] = Field(None, description="Skill name")
    provider: Optional[str] = Field(None, description="Course/cert provider")
    url: Optional[HttpUrl] = Field(None, description="Resource URL")
    estimated_time: Optional[str] = Field(None, description="Estimated time to complete")
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    priority: int = Field(1, ge=1, le=5, description="Priority (1=highest, 5=lowest)")


class ProfileAnalysis(BaseModel):
    """Comprehensive profile analysis"""
    profile_id: str = Field(..., description="Profile identifier")
    
    # Summary metrics
    profile_strength_score: float = Field(..., ge=0, le=100, description="Overall profile strength (0-100)")
    completeness_score: float = Field(..., ge=0, le=100, description="Profile completeness (0-100)")
    
    # Skill analysis
    total_skills: int = Field(..., ge=0, description="Total number of skills")
    skill_categories: Dict[str, int] = Field(default_factory=dict, description="Skills by category")
    top_skills: List[str] = Field(default_factory=list, description="Top skills")
    emerging_skills: List[str] = Field(default_factory=list, description="Emerging/trending skills")
    skill_gaps: List[str] = Field(default_factory=list, description="Recommended skills to learn")
    
    # Experience analysis
    total_experience_years: float = Field(..., ge=0, description="Total years of experience")
    experience_level: ExperienceLevel = Field(..., description="Calculated experience level")
    industries: List[str] = Field(default_factory=list, description="Industries worked in")
    career_progression: str = Field(..., description="Career progression assessment")
    
    # Education analysis
    highest_degree: Optional[str] = Field(None, description="Highest degree attained")
    education_institutions: List[str] = Field(default_factory=list, description="Educational institutions")
    
    # Market insights
    market_competitiveness: float = Field(..., ge=0, le=100, description="Market competitiveness (0-100)")
    salary_estimate: Optional[str] = Field(None, description="Estimated salary range")
    demand_level: str = Field(..., description="Market demand level (low/medium/high)")
    
    # Recommendations
    strengths: List[str] = Field(default_factory=list, description="Profile strengths")
    weaknesses: List[str] = Field(default_factory=list, description="Profile weaknesses")
    improvement_areas: List[str] = Field(default_factory=list, description="Areas for improvement")
    next_steps: List[str] = Field(default_factory=list, description="Recommended next steps")
    
    # Metadata
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)


class IndustryInsight(BaseModel):
    """Industry insights and trends"""
    industry: IndustryType = Field(..., description="Industry")
    
    # Trends
    trending_skills: List[str] = Field(default_factory=list, description="Trending skills in industry")
    declining_skills: List[str] = Field(default_factory=list, description="Declining skills")
    emerging_roles: List[str] = Field(default_factory=list, description="Emerging job roles")
    
    # Market data
    average_salary: Optional[str] = Field(None, description="Average salary range")
    job_growth_rate: Optional[float] = Field(None, description="Job growth rate (%)")
    demand_level: str = Field("medium", description="Current demand level")
    
    # Insights
    key_insights: List[str] = Field(default_factory=list, description="Key industry insights")
    future_outlook: Optional[str] = Field(None, description="Future outlook")
    
    # Top companies
    top_companies: List[str] = Field(default_factory=list, description="Top companies in industry")
    
    # Metadata
    data_date: date = Field(default_factory=date.today, description="Data as of date")
    sources: List[str] = Field(default_factory=list, description="Data sources")
