"""
LinkedIn Recommendation Engine

Generate personalized recommendations for jobs, skills, courses, and connections
based on profile analysis and machine learning insights.
"""

import logging
from typing import List, Dict, Optional
from datetime import datetime
import uuid

from linkedin.models import (
    LinkedInProfile,
    JobPosting,
    Recommendation,
    RecommendationType,
    Skill,
    MatchScore,
)
from linkedin.skill_extractor import SkillExtractor
from linkedin.job_matcher import JobMatcher

logger = logging.getLogger(__name__)


class RecommendationEngine:
    """
    Generate personalized recommendations for LinkedIn profiles
    
    Features:
    - Job recommendations with relevance scoring
    - Skill recommendations based on career goals
    - Course and certification recommendations
    - Content recommendations
    """
    
    def __init__(
        self,
        skill_extractor: Optional[SkillExtractor] = None,
        job_matcher: Optional[JobMatcher] = None
    ):
        """
        Initialize recommendation engine
        
        Args:
            skill_extractor: SkillExtractor instance
            job_matcher: JobMatcher instance
        """
        self.skill_extractor = skill_extractor or SkillExtractor()
        self.job_matcher = job_matcher or JobMatcher(self.skill_extractor)
    
    def generate_all_recommendations(
        self,
        profile: LinkedInProfile,
        available_jobs: Optional[List[JobPosting]] = None,
        target_role: Optional[str] = None,
        max_per_type: int = 5
    ) -> List[Recommendation]:
        """
        Generate comprehensive recommendations across all types
        
        Args:
            profile: LinkedInProfile to generate recommendations for
            available_jobs: Available job postings
            target_role: Target job role/title
            max_per_type: Maximum recommendations per type
        
        Returns:
            List of all recommendations sorted by priority and relevance
        """
        all_recommendations = []
        
        # Job recommendations
        if available_jobs:
            job_recs = self.recommend_jobs(profile, available_jobs, max_results=max_per_type)
            all_recommendations.extend(job_recs)
        
        # Skill recommendations
        skill_recs = self.recommend_skills(profile, target_role=target_role, max_results=max_per_type)
        all_recommendations.extend(skill_recs)
        
        # Course recommendations
        course_recs = self.recommend_courses(profile, target_role=target_role, max_results=max_per_type)
        all_recommendations.extend(course_recs)
        
        # Certification recommendations
        cert_recs = self.recommend_certifications(profile, max_results=max_per_type)
        all_recommendations.extend(cert_recs)
        
        # Sort by priority (1=highest) and relevance
        all_recommendations.sort(key=lambda x: (x.priority, -x.relevance_score))
        
        return all_recommendations
    
    def recommend_jobs(
        self,
        profile: LinkedInProfile,
        available_jobs: List[JobPosting],
        max_results: int = 10,
        min_score: float = 50.0
    ) -> List[Recommendation]:
        """
        Recommend jobs for a profile
        
        Args:
            profile: LinkedInProfile
            available_jobs: List of available JobPostings
            max_results: Maximum number of recommendations
            min_score: Minimum match score threshold
        
        Returns:
            List of job recommendations
        """
        # Match profile to all jobs
        matches = self.job_matcher.match_profile_to_jobs(
            profile,
            available_jobs,
            top_n=max_results * 2,  # Get more to filter
            min_score=min_score
        )
        
        recommendations = []
        for match in matches[:max_results]:
            job = next((j for j in available_jobs if j.job_id == match.job_id), None)
            if not job:
                continue
            
            # Determine priority based on match score
            if match.overall_score >= 80:
                priority = 1  # High priority
            elif match.overall_score >= 65:
                priority = 2  # Medium priority
            else:
                priority = 3  # Lower priority
            
            # Build reason
            reason = self._build_job_recommendation_reason(match, job)
            
            # Action items
            action_items = [
                f"Review job description at {job.company}",
                "Tailor your resume to highlight matching skills",
            ]
            
            if match.missing_skills:
                action_items.append(f"Consider brushing up on: {', '.join(match.missing_skills[:3])}")
            
            action_items.append("Prepare for technical interview focusing on required skills")
            
            recommendation = Recommendation(
                recommendation_id=str(uuid.uuid4()),
                profile_id=profile.profile_id,
                type=RecommendationType.JOB,
                title=f"{job.title} at {job.company}",
                description=job.description[:200] + "..." if len(job.description) > 200 else job.description,
                relevance_score=match.overall_score,
                reason=reason,
                action_items=action_items,
                expected_impact=f"Strong fit with {match.overall_score:.0f}% match",
                job_id=job.job_id,
                priority=priority,
            )
            
            recommendations.append(recommendation)
        
        return recommendations
    
    def recommend_skills(
        self,
        profile: LinkedInProfile,
        target_role: Optional[str] = None,
        max_results: int = 10
    ) -> List[Recommendation]:
        """
        Recommend skills to learn
        
        Args:
            profile: LinkedInProfile
            target_role: Target job role
            max_results: Maximum recommendations
        
        Returns:
            List of skill recommendations
        """
        # Get skill recommendations from skill extractor
        if not target_role and profile.current_position:
            target_role = profile.current_position.title
        
        if not target_role:
            # Default to common in-demand skills
            recommended_skills = self._get_trending_skills(profile)
        else:
            recommended_skills = self.skill_extractor.get_skill_recommendations(
                profile.skills,
                target_role,
                industry=profile.current_position.industry if profile.current_position else None
            )
        
        recommendations = []
        for i, skill_name in enumerate(recommended_skills[:max_results]):
            # Determine relevance based on demand and career alignment
            relevance = 85 - (i * 3)  # Decrease slightly for each subsequent skill
            
            # Priority based on position
            if i < 3:
                priority = 1
            elif i < 7:
                priority = 2
            else:
                priority = 3
            
            # Build reason
            reason = f"This skill is highly valued for {target_role or 'your career path'}"
            
            # Get skill category
            skill_category = self.skill_extractor.skill_taxonomy.get(
                skill_name, {}
            ).get("category", "technical")
            
            # Action items
            action_items = [
                "Take online courses (Coursera, Udemy, LinkedIn Learning)",
                "Practice through personal projects",
                "Add to LinkedIn profile once proficient",
            ]
            
            if skill_category == "technical":
                action_items.append("Build portfolio projects demonstrating this skill")
            
            recommendation = Recommendation(
                recommendation_id=str(uuid.uuid4()),
                profile_id=profile.profile_id,
                type=RecommendationType.SKILL,
                title=f"Learn {skill_name}",
                description=f"Acquiring {skill_name} will enhance your profile and increase job opportunities",
                relevance_score=relevance,
                reason=reason,
                action_items=action_items,
                expected_impact="Increase job match scores by 10-20%",
                skill_name=skill_name,
                priority=priority,
            )
            
            recommendations.append(recommendation)
        
        return recommendations
    
    def recommend_courses(
        self,
        profile: LinkedInProfile,
        target_role: Optional[str] = None,
        max_results: int = 5
    ) -> List[Recommendation]:
        """
        Recommend courses to take
        
        Args:
            profile: LinkedInProfile
            target_role: Target job role
            max_results: Maximum recommendations
        
        Returns:
            List of course recommendations
        """
        # Get skill gaps
        skill_recs = self.recommend_skills(profile, target_role, max_results=max_results)
        
        # Map skills to courses
        recommendations = []
        for skill_rec in skill_recs[:max_results]:
            skill_name = skill_rec.skill_name
            
            # Find relevant courses (in production, query course database)
            courses = self._find_courses_for_skill(skill_name)
            
            if courses:
                course = courses[0]  # Take top course
                
                recommendation = Recommendation(
                    recommendation_id=str(uuid.uuid4()),
                    profile_id=profile.profile_id,
                    type=RecommendationType.COURSE,
                    title=course["title"],
                    description=course["description"],
                    relevance_score=skill_rec.relevance_score,
                    reason=f"Build {skill_name} skills recommended for your career",
                    action_items=[
                        f"Enroll in course on {course['provider']}",
                        "Complete course within recommended timeframe",
                        "Apply learnings to practical projects",
                        "Add completed course to LinkedIn profile",
                    ],
                    expected_impact=f"Master {skill_name} skill",
                    skill_name=skill_name,
                    provider=course["provider"],
                    url=course["url"],
                    estimated_time=course["duration"],
                    priority=skill_rec.priority,
                )
                
                recommendations.append(recommendation)
        
        return recommendations
    
    def recommend_certifications(
        self,
        profile: LinkedInProfile,
        max_results: int = 5
    ) -> List[Recommendation]:
        """
        Recommend certifications to obtain
        
        Args:
            profile: LinkedInProfile
            max_results: Maximum recommendations
        
        Returns:
            List of certification recommendations
        """
        # Identify valuable certifications based on profile
        recommended_certs = self._get_relevant_certifications(profile)
        
        recommendations = []
        for i, cert_info in enumerate(recommended_certs[:max_results]):
            relevance = 80 - (i * 5)
            priority = 1 if i < 2 else 2
            
            recommendation = Recommendation(
                recommendation_id=str(uuid.uuid4()),
                profile_id=profile.profile_id,
                type=RecommendationType.CERTIFICATION,
                title=cert_info["name"],
                description=cert_info["description"],
                relevance_score=relevance,
                reason=cert_info["reason"],
                action_items=[
                    f"Review certification requirements on {cert_info['provider']}",
                    "Study recommended materials",
                    "Schedule and pass certification exam",
                    "Add certification to LinkedIn profile",
                ],
                expected_impact="Validate expertise and increase credibility",
                provider=cert_info["provider"],
                url=cert_info["url"],
                estimated_time=cert_info["prep_time"],
                priority=priority,
            )
            
            recommendations.append(recommendation)
        
        return recommendations
    
    def _build_job_recommendation_reason(self, match: MatchScore, job: JobPosting) -> str:
        """Build reason for job recommendation"""
        reasons = []
        
        if match.skills_match_score >= 80:
            reasons.append(f"{len(match.matched_skills)} matching skills")
        
        if match.experience_match_score >= 80:
            reasons.append("experience level aligns well")
        
        if match.education_match_score >= 90:
            reasons.append("strong educational background")
        
        if not reasons:
            reasons.append("good overall fit for your profile")
        
        return f"Recommended because: {', '.join(reasons)}"
    
    def _get_trending_skills(self, profile: LinkedInProfile) -> List[str]:
        """Get trending skills relevant to profile"""
        # In production, this would query a database of trending skills
        # For now, return commonly in-demand skills
        
        # Analyze profile's dominant category
        if profile.skills:
            skill_analysis = self.skill_extractor.analyze_skill_trends(profile.skills)
            most_common = skill_analysis.get("most_common_category")
            
            if most_common and most_common[0] == "technical":
                return [
                    "Python", "AWS", "Kubernetes", "Machine Learning",
                    "React", "TypeScript", "Docker", "CI/CD", "PostgreSQL", "REST APIs"
                ]
        
        # Default trending skills
        return [
            "Python", "Machine Learning", "Cloud Computing", "Data Analysis",
            "Leadership", "Project Management", "Agile", "Communication"
        ]
    
    def _find_courses_for_skill(self, skill_name: str) -> List[Dict]:
        """Find courses for a skill"""
        # In production, query course database/API
        # Mock data for demonstration
        
        course_templates = {
            "Python": [
                {
                    "title": "Complete Python Bootcamp",
                    "description": "Learn Python from basics to advanced topics",
                    "provider": "Udemy",
                    "url": "https://www.udemy.com/course/complete-python-bootcamp/",
                    "duration": "40 hours",
                }
            ],
            "Machine Learning": [
                {
                    "title": "Machine Learning Specialization",
                    "description": "Master machine learning fundamentals and algorithms",
                    "provider": "Coursera",
                    "url": "https://www.coursera.org/specializations/machine-learning",
                    "duration": "3 months",
                }
            ],
            "AWS": [
                {
                    "title": "AWS Certified Solutions Architect",
                    "description": "Prepare for AWS certification and master cloud architecture",
                    "provider": "AWS Training",
                    "url": "https://aws.amazon.com/training/",
                    "duration": "2 months",
                }
            ],
        }
        
        # Return courses for skill or generic course
        if skill_name in course_templates:
            return course_templates[skill_name]
        
        # Generic course for skill
        return [{
            "title": f"Mastering {skill_name}",
            "description": f"Comprehensive course covering {skill_name} from fundamentals to advanced topics",
            "provider": "LinkedIn Learning",
            "url": f"https://www.linkedin.com/learning/search?keywords={skill_name.replace(' ', '+')}",
            "duration": "20 hours",
        }]
    
    def _get_relevant_certifications(self, profile: LinkedInProfile) -> List[Dict]:
        """Get relevant certifications for profile"""
        certifications = []
        
        # Check profile skills for relevant certifications
        profile_skill_names = {skill.name.lower() for skill in profile.skills}
        
        # Cloud certifications
        if any(cloud in profile_skill_names for cloud in ["aws", "amazon web services", "cloud"]):
            certifications.append({
                "name": "AWS Certified Solutions Architect - Associate",
                "description": "Validate expertise in designing distributed systems on AWS",
                "provider": "Amazon Web Services",
                "url": "https://aws.amazon.com/certification/",
                "prep_time": "2-3 months",
                "reason": "Your AWS skills make this certification highly relevant",
            })
        
        if any(cloud in profile_skill_names for cloud in ["azure", "microsoft cloud"]):
            certifications.append({
                "name": "Microsoft Azure Fundamentals",
                "description": "Demonstrate foundational knowledge of cloud services",
                "provider": "Microsoft",
                "url": "https://docs.microsoft.com/en-us/learn/certifications/",
                "prep_time": "1-2 months",
                "reason": "Complement your Azure experience with official certification",
            })
        
        # Data science certifications
        if any(ds in profile_skill_names for ds in ["machine learning", "data science", "python"]):
            certifications.append({
                "name": "TensorFlow Developer Certificate",
                "description": "Demonstrate proficiency in using TensorFlow for ML",
                "provider": "Google",
                "url": "https://www.tensorflow.org/certificate",
                "prep_time": "2-3 months",
                "reason": "Validate your machine learning skills with industry recognition",
            })
        
        # Project management
        if any(pm in profile_skill_names for pm in ["project management", "agile", "scrum"]):
            certifications.append({
                "name": "Project Management Professional (PMP)",
                "description": "Globally recognized project management certification",
                "provider": "PMI",
                "url": "https://www.pmi.org/certifications/project-management-pmp",
                "prep_time": "3-6 months",
                "reason": "Formalize your project management expertise",
            })
        
        # Security
        if any(sec in profile_skill_names for sec in ["security", "cybersecurity", "infosec"]):
            certifications.append({
                "name": "Certified Information Systems Security Professional (CISSP)",
                "description": "Premier certification for information security professionals",
                "provider": "ISC2",
                "url": "https://www.isc2.org/Certifications/CISSP",
                "prep_time": "6 months",
                "reason": "Establish yourself as a security expert",
            })
        
        # Default certifications if none matched
        if not certifications:
            certifications.append({
                "name": "Google Data Analytics Professional Certificate",
                "description": "Gain in-demand data analytics skills",
                "provider": "Google",
                "url": "https://www.coursera.org/professional-certificates/google-data-analytics",
                "prep_time": "6 months",
                "reason": "Build valuable data analysis skills",
            })
        
        return certifications
