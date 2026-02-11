"""
LinkedIn Profile Parser

Extracts and parses LinkedIn profile data from various formats (HTML, JSON, PDF, text).
Handles data normalization, validation, and enrichment.
"""

import re
import logging
from datetime import datetime, date
from typing import Dict, Any, List, Optional, Tuple
from dateutil.parser import parse as parse_date

from linkedin.models import (
    LinkedInProfile,
    Experience,
    Education,
    Skill,
    Certification,
    SkillCategory,
    ExperienceLevel,
    EmploymentType,
    IndustryType,
)

logger = logging.getLogger(__name__)


class ProfileParser:
    """
    Parse LinkedIn profiles from various formats
    
    Supports:
    - JSON data from LinkedIn API
    - Structured dictionaries
    - HTML scraped data (with BeautifulSoup)
    - PDF resumes (with pypdf)
    - Plain text parsing with NLP
    """
    
    def __init__(self):
        """Initialize the profile parser"""
        self.skill_keywords = self._load_skill_keywords()
        self.company_patterns = self._load_company_patterns()
    
    def parse_profile(self, data: Dict[str, Any], source: str = "json") -> LinkedInProfile:
        """
        Parse profile from data
        
        Args:
            data: Profile data dictionary
            source: Data source type (json, html, text, pdf)
        
        Returns:
            LinkedInProfile object
        """
        try:
            if source == "json":
                return self._parse_json_profile(data)
            elif source == "html":
                return self._parse_html_profile(data)
            elif source == "text":
                return self._parse_text_profile(data)
            elif source == "pdf":
                return self._parse_pdf_profile(data)
            else:
                raise ValueError(f"Unsupported source type: {source}")
        except Exception as e:
            logger.error(f"Error parsing profile from {source}: {e}")
            raise
    
    def _parse_json_profile(self, data: Dict[str, Any]) -> LinkedInProfile:
        """Parse profile from JSON/dict data"""
        # Extract basic info
        profile_data = {
            "profile_id": data.get("profile_id", data.get("id", f"profile_{datetime.utcnow().timestamp()}")),
            "first_name": data.get("first_name", data.get("firstName", "")),
            "last_name": data.get("last_name", data.get("lastName", "")),
            "headline": data.get("headline"),
            "summary": data.get("summary", data.get("about")),
            "location": data.get("location", data.get("locationName")),
            "email": data.get("email"),
            "phone": data.get("phone"),
            "linkedin_url": data.get("linkedin_url", data.get("publicProfileUrl")),
            "website": data.get("website"),
            "profile_views": data.get("profile_views", 0),
            "connections_count": data.get("connections_count", data.get("numConnections", 0)),
        }
        
        # Parse experiences
        experiences_data = data.get("experiences", data.get("positions", []))
        profile_data["experiences"] = [
            self._parse_experience(exp) for exp in experiences_data
        ]
        
        # Parse education
        education_data = data.get("education", data.get("educations", []))
        profile_data["education"] = [
            self._parse_education(edu) for edu in education_data
        ]
        
        # Parse skills
        skills_data = data.get("skills", [])
        profile_data["skills"] = [
            self._parse_skill(skill) for skill in skills_data
        ]
        
        # Parse certifications
        certs_data = data.get("certifications", data.get("certificates", []))
        profile_data["certifications"] = [
            self._parse_certification(cert) for cert in certs_data
        ]
        
        return LinkedInProfile(**profile_data)
    
    def _parse_experience(self, data: Dict[str, Any]) -> Experience:
        """Parse work experience entry"""
        # Parse dates
        start_date = self._parse_date(data.get("start_date", data.get("startDate")))
        end_date = self._parse_date(data.get("end_date", data.get("endDate")))
        
        # Determine employment type
        title = data.get("title", "").lower()
        employment_type = EmploymentType.FULL_TIME
        if "intern" in title or "internship" in title:
            employment_type = EmploymentType.INTERNSHIP
        elif "contract" in title or "contractor" in title:
            employment_type = EmploymentType.CONTRACT
        elif "freelance" in title:
            employment_type = EmploymentType.FREELANCE
        
        # Determine industry
        company = data.get("company", data.get("companyName", ""))
        industry = self._classify_industry(company, data.get("description", ""))
        
        # Extract skills from description
        description = data.get("description", "")
        skills_used = self._extract_skills_from_text(description)
        
        return Experience(
            company=company,
            title=data.get("title", ""),
            location=data.get("location"),
            start_date=start_date,
            end_date=end_date,
            description=description,
            employment_type=employment_type,
            industry=industry,
            skills_used=skills_used,
            achievements=data.get("achievements", []),
        )
    
    def _parse_education(self, data: Dict[str, Any]) -> Education:
        """Parse education entry"""
        start_date = self._parse_date(data.get("start_date", data.get("startDate")))
        end_date = self._parse_date(data.get("end_date", data.get("endDate")))
        
        return Education(
            institution=data.get("institution", data.get("schoolName", "")),
            degree=data.get("degree", data.get("degreeName", "")),
            field_of_study=data.get("field_of_study", data.get("fieldOfStudy", "")),
            start_date=start_date,
            end_date=end_date,
            grade=data.get("grade"),
            activities=data.get("activities", []),
            description=data.get("description"),
        )
    
    def _parse_skill(self, data: Any) -> Skill:
        """Parse skill entry"""
        # Handle both dict and string formats
        if isinstance(data, str):
            skill_name = data
            skill_data = {"name": skill_name}
        else:
            skill_name = data.get("name", data.get("skillName", ""))
            skill_data = data
        
        # Classify skill category
        category = self._classify_skill(skill_name)
        
        # Parse last used date if available
        last_used = None
        if "last_used" in skill_data:
            last_used = self._parse_date(skill_data["last_used"])
        
        return Skill(
            name=skill_name,
            category=category,
            proficiency_level=skill_data.get("proficiency_level", skill_data.get("proficiency")),
            years_experience=skill_data.get("years_experience", skill_data.get("yearsExperience")),
            endorsements=skill_data.get("endorsements", skill_data.get("endorsementCount", 0)),
            verified=skill_data.get("verified", False),
            last_used=last_used,
            source=skill_data.get("source"),
        )
    
    def _parse_certification(self, data: Dict[str, Any]) -> Certification:
        """Parse certification entry"""
        issue_date = self._parse_date(data.get("issue_date", data.get("startDate")))
        expiration_date = self._parse_date(data.get("expiration_date", data.get("endDate")))
        
        return Certification(
            name=data.get("name", data.get("certificationName", "")),
            issuing_organization=data.get("issuing_organization", data.get("authority", "")),
            issue_date=issue_date,
            expiration_date=expiration_date,
            credential_id=data.get("credential_id", data.get("licenseNumber")),
            credential_url=data.get("credential_url", data.get("url")),
        )
    
    def _parse_html_profile(self, data: Dict[str, Any]) -> LinkedInProfile:
        """Parse profile from HTML data (e.g., scraped)"""
        # This would use BeautifulSoup to parse HTML
        # For now, extract what we can from the data dict
        logger.warning("HTML parsing not fully implemented, using basic extraction")
        return self._parse_json_profile(data)
    
    def _parse_text_profile(self, data: Dict[str, Any]) -> LinkedInProfile:
        """Parse profile from plain text (e.g., resume text)"""
        text = data.get("text", "")
        
        # Extract basic info using regex
        profile_data = {
            "profile_id": f"profile_{datetime.utcnow().timestamp()}",
            "first_name": "",
            "last_name": "",
            "experiences": [],
            "education": [],
            "skills": [],
            "certifications": [],
        }
        
        # Extract email
        email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
        if email_match:
            profile_data["email"] = email_match.group()
        
        # Extract phone
        phone_match = re.search(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', text)
        if phone_match:
            profile_data["phone"] = phone_match.group()
        
        # Extract skills
        skills = self._extract_skills_from_text(text)
        profile_data["skills"] = [
            Skill(name=skill, category=self._classify_skill(skill))
            for skill in skills
        ]
        
        return LinkedInProfile(**profile_data)
    
    def _parse_pdf_profile(self, data: Dict[str, Any]) -> LinkedInProfile:
        """Parse profile from PDF (e.g., resume)"""
        # This would use pypdf or similar to extract text
        # Then use text parsing
        logger.warning("PDF parsing not fully implemented, using text extraction")
        return self._parse_text_profile(data)
    
    def _parse_date(self, date_value: Any) -> Optional[date]:
        """Parse date from various formats"""
        if date_value is None:
            return None
        
        if isinstance(date_value, date):
            return date_value
        
        if isinstance(date_value, datetime):
            return date_value.date()
        
        if isinstance(date_value, str):
            if date_value.lower() in ["present", "current", "now", ""]:
                return None
            try:
                return parse_date(date_value).date()
            except Exception as e:
                logger.warning(f"Could not parse date '{date_value}': {e}")
                return None
        
        if isinstance(date_value, dict):
            # Handle LinkedIn API format: {"year": 2020, "month": 5}
            year = date_value.get("year")
            month = date_value.get("month", 1)
            day = date_value.get("day", 1)
            if year:
                return date(year, month, day)
        
        return None
    
    def _classify_skill(self, skill_name: str) -> SkillCategory:
        """Classify skill into category"""
        skill_lower = skill_name.lower()
        
        # Technical skills
        tech_keywords = [
            "python", "java", "javascript", "typescript", "c++", "go", "rust",
            "react", "vue", "angular", "node", "django", "flask", "fastapi",
            "sql", "postgresql", "mongodb", "redis", "docker", "kubernetes",
            "aws", "azure", "gcp", "machine learning", "deep learning", "ai",
            "tensorflow", "pytorch", "scikit-learn", "git", "linux",
        ]
        if any(kw in skill_lower for kw in tech_keywords):
            return SkillCategory.TECHNICAL
        
        # Tools
        tool_keywords = [
            "jira", "confluence", "slack", "figma", "adobe", "office",
            "excel", "powerpoint", "tableau", "power bi", "salesforce",
        ]
        if any(kw in skill_lower for kw in tool_keywords):
            return SkillCategory.TOOLS
        
        # Management
        mgmt_keywords = [
            "management", "leadership", "project management", "agile", "scrum",
            "team building", "stakeholder", "strategic planning",
        ]
        if any(kw in skill_lower for kw in mgmt_keywords):
            return SkillCategory.MANAGEMENT
        
        # Communication
        comm_keywords = [
            "communication", "presentation", "public speaking", "writing",
            "negotiation", "collaboration", "teamwork",
        ]
        if any(kw in skill_lower for kw in comm_keywords):
            return SkillCategory.COMMUNICATION
        
        # Analytics
        analytics_keywords = [
            "data analysis", "analytics", "statistics", "data visualization",
            "business intelligence", "reporting",
        ]
        if any(kw in skill_lower for kw in analytics_keywords):
            return SkillCategory.ANALYTICS
        
        # Design
        design_keywords = [
            "design", "ui", "ux", "user experience", "graphic design",
            "web design", "product design",
        ]
        if any(kw in skill_lower for kw in design_keywords):
            return SkillCategory.DESIGN
        
        # Languages
        if any(lang in skill_lower for lang in ["english", "spanish", "french", "german", "chinese", "japanese"]):
            return SkillCategory.LANGUAGES
        
        # Default to soft skills
        return SkillCategory.SOFT_SKILLS
    
    def _classify_industry(self, company: str, description: str) -> IndustryType:
        """Classify company industry"""
        combined = f"{company} {description}".lower()
        
        if any(kw in combined for kw in ["software", "tech", "technology", "ai", "saas", "cloud"]):
            return IndustryType.TECHNOLOGY
        elif any(kw in combined for kw in ["bank", "finance", "trading", "investment", "insurance"]):
            return IndustryType.FINANCE
        elif any(kw in combined for kw in ["health", "medical", "hospital", "pharma", "biotech"]):
            return IndustryType.HEALTHCARE
        elif any(kw in combined for kw in ["education", "university", "school", "learning"]):
            return IndustryType.EDUCATION
        elif any(kw in combined for kw in ["retail", "ecommerce", "store", "shopping"]):
            return IndustryType.RETAIL
        elif any(kw in combined for kw in ["manufacturing", "production", "factory"]):
            return IndustryType.MANUFACTURING
        elif any(kw in combined for kw in ["consulting", "advisory", "consulting"]):
            return IndustryType.CONSULTING
        elif any(kw in combined for kw in ["media", "entertainment", "publishing", "broadcasting"]):
            return IndustryType.MEDIA
        elif any(kw in combined for kw in ["real estate", "property", "construction"]):
            return IndustryType.REAL_ESTATE
        elif any(kw in combined for kw in ["telecom", "telecommunications", "wireless", "network"]):
            return IndustryType.TELECOMMUNICATIONS
        
        return IndustryType.OTHER
    
    def _extract_skills_from_text(self, text: str) -> List[str]:
        """Extract skills from text using keyword matching"""
        skills = []
        text_lower = text.lower()
        
        for skill_keyword in self.skill_keywords:
            if skill_keyword.lower() in text_lower:
                skills.append(skill_keyword)
        
        return list(set(skills))  # Remove duplicates
    
    def _load_skill_keywords(self) -> List[str]:
        """Load skill keywords for extraction"""
        # In production, this would load from a comprehensive database
        return [
            # Programming languages
            "Python", "Java", "JavaScript", "TypeScript", "C++", "C#", "Go", "Rust",
            "PHP", "Ruby", "Swift", "Kotlin", "Scala", "R", "MATLAB",
            
            # Frameworks & libraries
            "React", "Vue", "Angular", "Node.js", "Django", "Flask", "FastAPI",
            "Spring", "Express", "TensorFlow", "PyTorch", "scikit-learn",
            
            # Databases
            "SQL", "PostgreSQL", "MySQL", "MongoDB", "Redis", "Elasticsearch",
            "DynamoDB", "Cassandra", "Oracle",
            
            # Cloud & DevOps
            "AWS", "Azure", "GCP", "Docker", "Kubernetes", "Terraform", "Jenkins",
            "CI/CD", "Git", "Linux", "Ansible",
            
            # AI/ML
            "Machine Learning", "Deep Learning", "Natural Language Processing",
            "Computer Vision", "Data Science", "AI", "Neural Networks",
            
            # Soft skills
            "Leadership", "Communication", "Problem Solving", "Teamwork",
            "Project Management", "Agile", "Scrum",
        ]
    
    def _load_company_patterns(self) -> Dict[str, IndustryType]:
        """Load company name to industry mappings"""
        return {
            "google": IndustryType.TECHNOLOGY,
            "microsoft": IndustryType.TECHNOLOGY,
            "amazon": IndustryType.TECHNOLOGY,
            "apple": IndustryType.TECHNOLOGY,
            "facebook": IndustryType.TECHNOLOGY,
            "goldman sachs": IndustryType.FINANCE,
            "jpmorgan": IndustryType.FINANCE,
            "mckinsey": IndustryType.CONSULTING,
            "deloitte": IndustryType.CONSULTING,
            # Add more mappings
        }
    
    def enrich_profile(self, profile: LinkedInProfile) -> LinkedInProfile:
        """
        Enrich profile with additional data and insights
        
        Args:
            profile: LinkedInProfile to enrich
        
        Returns:
            Enriched LinkedInProfile
        """
        # Extract skills from experience descriptions
        for experience in profile.experiences:
            if experience.description:
                extracted_skills = self._extract_skills_from_text(experience.description)
                experience.skills_used = list(set(experience.skills_used + extracted_skills))
        
        # Add skills from experiences to profile skills if not present
        all_experience_skills = set()
        for exp in profile.experiences:
            all_experience_skills.update(exp.skills_used)
        
        existing_skill_names = {skill.name for skill in profile.skills}
        for skill_name in all_experience_skills:
            if skill_name not in existing_skill_names:
                profile.skills.append(
                    Skill(
                        name=skill_name,
                        category=self._classify_skill(skill_name),
                        source="experience",
                    )
                )
        
        return profile
    
    def validate_profile(self, profile: LinkedInProfile) -> Tuple[bool, List[str]]:
        """
        Validate profile completeness and quality
        
        Args:
            profile: LinkedInProfile to validate
        
        Returns:
            Tuple of (is_valid, list of validation errors)
        """
        errors = []
        
        # Check required fields
        if not profile.first_name:
            errors.append("First name is missing")
        if not profile.last_name:
            errors.append("Last name is missing")
        
        # Check profile sections
        if not profile.experiences:
            errors.append("No work experience provided")
        if not profile.education:
            errors.append("No education provided")
        if not profile.skills:
            errors.append("No skills provided")
        
        # Check experience quality
        for i, exp in enumerate(profile.experiences):
            if not exp.company:
                errors.append(f"Experience {i+1}: Company name is missing")
            if not exp.title:
                errors.append(f"Experience {i+1}: Job title is missing")
        
        is_valid = len(errors) == 0
        return is_valid, errors
