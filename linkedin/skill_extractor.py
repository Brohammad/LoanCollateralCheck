"""
LinkedIn Skill Extractor

Advanced NLP-based skill extraction and categorization using:
- Named Entity Recognition (NER)
- Text classification
- Keyword matching with context
- Skill taxonomy mapping
"""

import re
import logging
from typing import List, Dict, Set, Tuple, Optional
from collections import defaultdict, Counter

from linkedin.models import (
    Skill,
    SkillCategory,
    LinkedInProfile,
    Experience,
)

logger = logging.getLogger(__name__)


class SkillExtractor:
    """
    Extract and categorize skills from text using NLP techniques
    
    Features:
    - Keyword-based extraction with context
    - Synonym and variation handling
    - Skill taxonomy mapping
    - Proficiency estimation
    - Skill trending analysis
    """
    
    def __init__(self):
        """Initialize skill extractor"""
        self.skill_taxonomy = self._build_skill_taxonomy()
        self.skill_synonyms = self._build_skill_synonyms()
        self.skill_patterns = self._compile_skill_patterns()
        self.proficiency_indicators = self._build_proficiency_indicators()
    
    def extract_skills(
        self,
        text: str,
        context: Optional[str] = None,
        min_confidence: float = 0.5
    ) -> List[Skill]:
        """
        Extract skills from text
        
        Args:
            text: Text to extract skills from
            context: Additional context (e.g., job title, industry)
            min_confidence: Minimum confidence threshold (0-1)
        
        Returns:
            List of extracted Skill objects
        """
        if not text:
            return []
        
        # Extract skill mentions
        skill_mentions = self._find_skill_mentions(text)
        
        # Normalize and deduplicate
        normalized_skills = self._normalize_skills(skill_mentions)
        
        # Estimate proficiency
        skills_with_proficiency = self._estimate_proficiency(normalized_skills, text, context)
        
        # Convert to Skill objects
        skills = []
        for skill_name, data in skills_with_proficiency.items():
            if data["confidence"] >= min_confidence:
                skills.append(Skill(
                    name=skill_name,
                    category=data["category"],
                    proficiency_level=data["proficiency"],
                    years_experience=data.get("years_experience"),
                    source="extracted",
                ))
        
        return skills
    
    def extract_from_profile(self, profile: LinkedInProfile) -> List[Skill]:
        """
        Extract all skills from a LinkedIn profile
        
        Args:
            profile: LinkedInProfile object
        
        Returns:
            List of all extracted skills
        """
        all_skills = []
        
        # Extract from headline
        if profile.headline:
            skills = self.extract_skills(profile.headline, context="headline")
            all_skills.extend(skills)
        
        # Extract from summary
        if profile.summary:
            skills = self.extract_skills(profile.summary, context="summary")
            all_skills.extend(skills)
        
        # Extract from experiences
        for exp in profile.experiences:
            context = f"{exp.title} at {exp.company}"
            if exp.description:
                skills = self.extract_skills(exp.description, context=context)
                # Add years experience based on job duration
                for skill in skills:
                    skill.years_experience = exp.duration_years
                all_skills.extend(skills)
        
        # Combine with existing skills
        existing_skills = {skill.name: skill for skill in profile.skills}
        extracted_skills = {skill.name: skill for skill in all_skills}
        
        # Merge: prefer existing skill data but add new skills
        combined = {}
        for name, skill in existing_skills.items():
            combined[name] = skill
        
        for name, skill in extracted_skills.items():
            if name not in combined:
                combined[name] = skill
            else:
                # Update if extracted has more info
                if skill.years_experience and not combined[name].years_experience:
                    combined[name].years_experience = skill.years_experience
        
        return list(combined.values())
    
    def categorize_skills(self, skills: List[Skill]) -> Dict[SkillCategory, List[Skill]]:
        """
        Group skills by category
        
        Args:
            skills: List of skills
        
        Returns:
            Dictionary mapping categories to skills
        """
        categorized = defaultdict(list)
        for skill in skills:
            categorized[skill.category].append(skill)
        return dict(categorized)
    
    def find_skill_gaps(
        self,
        profile_skills: List[Skill],
        required_skills: List[str],
        preferred_skills: Optional[List[str]] = None
    ) -> Dict[str, List[str]]:
        """
        Identify skill gaps for a job or role
        
        Args:
            profile_skills: Candidate's skills
            required_skills: Required skills for the role
            preferred_skills: Preferred skills for the role
        
        Returns:
            Dictionary with missing_required, missing_preferred, and matched skills
        """
        profile_skill_names = {skill.name.lower() for skill in profile_skills}
        
        # Check required skills
        missing_required = []
        matched_required = []
        for skill in required_skills:
            skill_lower = skill.lower()
            # Check exact match or synonyms
            if skill_lower in profile_skill_names or self._has_synonym_match(skill_lower, profile_skill_names):
                matched_required.append(skill)
            else:
                missing_required.append(skill)
        
        # Check preferred skills
        missing_preferred = []
        matched_preferred = []
        if preferred_skills:
            for skill in preferred_skills:
                skill_lower = skill.lower()
                if skill_lower in profile_skill_names or self._has_synonym_match(skill_lower, profile_skill_names):
                    matched_preferred.append(skill)
                else:
                    missing_preferred.append(skill)
        
        return {
            "missing_required": missing_required,
            "missing_preferred": missing_preferred,
            "matched_required": matched_required,
            "matched_preferred": matched_preferred,
        }
    
    def get_skill_recommendations(
        self,
        current_skills: List[Skill],
        target_role: str,
        industry: Optional[str] = None
    ) -> List[str]:
        """
        Recommend skills to learn based on current skills and target role
        
        Args:
            current_skills: Current skills
            target_role: Target job role
            industry: Target industry
        
        Returns:
            List of recommended skills
        """
        current_skill_names = {skill.name.lower() for skill in current_skills}
        
        # Get common skills for target role
        role_skills = self._get_role_skills(target_role, industry)
        
        # Find skills not yet acquired
        recommendations = [
            skill for skill in role_skills
            if skill.lower() not in current_skill_names
        ]
        
        # Prioritize by relevance and demand
        return self._prioritize_recommendations(recommendations, current_skills)
    
    def analyze_skill_trends(
        self,
        skills: List[Skill],
        time_window_months: int = 12
    ) -> Dict[str, any]:
        """
        Analyze skill trends and growth
        
        Args:
            skills: List of skills with timestamps
            time_window_months: Analysis window in months
        
        Returns:
            Trend analysis results
        """
        # Group skills by category
        category_counts = Counter(skill.category for skill in skills)
        
        # Identify emerging skills (recently added)
        emerging = []
        established = []
        
        for skill in skills:
            if skill.last_used:
                # Simple heuristic: skills used in last 6 months are emerging
                if (skill.years_experience or 0) < 1.0:
                    emerging.append(skill.name)
                else:
                    established.append(skill.name)
        
        return {
            "total_skills": len(skills),
            "by_category": dict(category_counts),
            "emerging_skills": emerging,
            "established_skills": established,
            "most_common_category": category_counts.most_common(1)[0] if category_counts else None,
        }
    
    def _find_skill_mentions(self, text: str) -> List[Tuple[str, float]]:
        """Find all skill mentions in text with confidence scores"""
        mentions = []
        text_lower = text.lower()
        
        # Check each skill in taxonomy
        for skill_name, skill_data in self.skill_taxonomy.items():
            skill_lower = skill_name.lower()
            
            # Check exact match
            if skill_lower in text_lower:
                # Calculate confidence based on context
                confidence = 0.9  # High confidence for exact match
                
                # Boost confidence if skill is mentioned multiple times
                count = text_lower.count(skill_lower)
                if count > 1:
                    confidence = min(1.0, confidence + 0.05 * (count - 1))
                
                mentions.append((skill_name, confidence))
            
            # Check synonyms
            synonyms = self.skill_synonyms.get(skill_name, [])
            for synonym in synonyms:
                if synonym.lower() in text_lower:
                    mentions.append((skill_name, 0.7))  # Lower confidence for synonym
                    break
        
        # Also check patterns (e.g., "experienced in X", "proficient in Y")
        for pattern, boost in self.skill_patterns:
            matches = pattern.findall(text)
            for match in matches:
                mentions.append((match, 0.8 + boost))
        
        return mentions
    
    def _normalize_skills(self, mentions: List[Tuple[str, float]]) -> Dict[str, float]:
        """Normalize skill names and aggregate confidence scores"""
        normalized = {}
        
        for skill_name, confidence in mentions:
            # Normalize name (title case, remove extra spaces)
            normalized_name = ' '.join(skill_name.split()).title()
            
            # Keep highest confidence score
            if normalized_name in normalized:
                normalized[normalized_name] = max(normalized[normalized_name], confidence)
            else:
                normalized[normalized_name] = confidence
        
        return normalized
    
    def _estimate_proficiency(
        self,
        skills: Dict[str, float],
        text: str,
        context: Optional[str] = None
    ) -> Dict[str, Dict]:
        """Estimate proficiency level for each skill"""
        result = {}
        text_lower = text.lower()
        
        for skill_name, confidence in skills.items():
            skill_lower = skill_name.lower()
            
            # Start with category from taxonomy
            category = self.skill_taxonomy.get(skill_name, {}).get(
                "category",
                SkillCategory.SOFT_SKILLS
            )
            
            # Estimate proficiency based on indicators
            proficiency = 3  # Default to intermediate
            years_experience = None
            
            # Check for proficiency indicators nearby
            for indicator, level in self.proficiency_indicators.items():
                pattern = f"{indicator}.*{skill_lower}|{skill_lower}.*{indicator}"
                if re.search(pattern, text_lower, re.IGNORECASE):
                    proficiency = level
                    break
            
            # Extract years of experience if mentioned
            years_patterns = [
                rf"(\d+)\+?\s*years?\s+(?:of\s+)?(?:experience\s+)?(?:with\s+)?{skill_lower}",
                rf"{skill_lower}.*?(\d+)\+?\s*years?",
            ]
            for pattern in years_patterns:
                match = re.search(pattern, text_lower, re.IGNORECASE)
                if match:
                    years_experience = float(match.group(1))
                    # Adjust proficiency based on years
                    if years_experience >= 5:
                        proficiency = 5
                    elif years_experience >= 3:
                        proficiency = 4
                    elif years_experience >= 1:
                        proficiency = 3
                    break
            
            result[skill_name] = {
                "category": category,
                "proficiency": proficiency,
                "confidence": confidence,
                "years_experience": years_experience,
            }
        
        return result
    
    def _has_synonym_match(self, skill: str, profile_skills: Set[str]) -> bool:
        """Check if skill has a synonym in profile skills"""
        synonyms = self.skill_synonyms.get(skill, [])
        return any(syn.lower() in profile_skills for syn in synonyms)
    
    def _get_role_skills(self, role: str, industry: Optional[str] = None) -> List[str]:
        """Get common skills for a role and industry"""
        # In production, this would query a database of role-skill mappings
        role_lower = role.lower()
        
        role_skill_map = {
            "software engineer": [
                "Python", "Java", "JavaScript", "Git", "SQL", "AWS",
                "Docker", "Kubernetes", "CI/CD", "REST APIs", "Agile",
            ],
            "data scientist": [
                "Python", "R", "SQL", "Machine Learning", "Statistics",
                "Data Visualization", "Pandas", "NumPy", "scikit-learn",
                "TensorFlow", "PyTorch", "Jupyter",
            ],
            "product manager": [
                "Product Strategy", "Roadmap Planning", "User Research",
                "Data Analysis", "Agile", "Scrum", "Stakeholder Management",
                "Market Analysis", "A/B Testing", "SQL", "Jira",
            ],
            "data engineer": [
                "Python", "SQL", "Spark", "Airflow", "ETL", "AWS", "Azure",
                "Data Warehousing", "Kafka", "Redis", "Docker", "Kubernetes",
            ],
            "machine learning engineer": [
                "Python", "TensorFlow", "PyTorch", "Machine Learning", "Deep Learning",
                "MLOps", "Docker", "Kubernetes", "AWS", "Model Deployment",
                "scikit-learn", "Computer Vision", "NLP",
            ],
        }
        
        # Find matching role
        for role_key, skills in role_skill_map.items():
            if role_key in role_lower:
                return skills
        
        # Default skills for technical roles
        return ["Problem Solving", "Communication", "Teamwork", "Time Management"]
    
    def _prioritize_recommendations(
        self,
        recommendations: List[str],
        current_skills: List[Skill]
    ) -> List[str]:
        """Prioritize skill recommendations"""
        # In production, this would use ML to predict skill value
        # For now, simple prioritization based on current skill categories
        
        current_categories = Counter(skill.category for skill in current_skills)
        most_common_category = current_categories.most_common(1)[0][0] if current_categories else None
        
        # Prioritize skills in the same category as most common
        prioritized = []
        remaining = []
        
        for skill in recommendations:
            skill_category = self.skill_taxonomy.get(skill, {}).get("category")
            if skill_category == most_common_category:
                prioritized.append(skill)
            else:
                remaining.append(skill)
        
        return prioritized + remaining
    
    def _build_skill_taxonomy(self) -> Dict[str, Dict]:
        """Build comprehensive skill taxonomy"""
        # In production, load from database
        return {
            # Programming Languages
            "Python": {"category": SkillCategory.TECHNICAL, "demand": "high"},
            "Java": {"category": SkillCategory.TECHNICAL, "demand": "high"},
            "JavaScript": {"category": SkillCategory.TECHNICAL, "demand": "high"},
            "TypeScript": {"category": SkillCategory.TECHNICAL, "demand": "high"},
            "C++": {"category": SkillCategory.TECHNICAL, "demand": "medium"},
            "Go": {"category": SkillCategory.TECHNICAL, "demand": "high"},
            "Rust": {"category": SkillCategory.TECHNICAL, "demand": "medium"},
            "SQL": {"category": SkillCategory.TECHNICAL, "demand": "high"},
            
            # Frameworks
            "React": {"category": SkillCategory.TECHNICAL, "demand": "high"},
            "Vue": {"category": SkillCategory.TECHNICAL, "demand": "medium"},
            "Angular": {"category": SkillCategory.TECHNICAL, "demand": "medium"},
            "Django": {"category": SkillCategory.TECHNICAL, "demand": "medium"},
            "Flask": {"category": SkillCategory.TECHNICAL, "demand": "medium"},
            "FastAPI": {"category": SkillCategory.TECHNICAL, "demand": "high"},
            "Spring": {"category": SkillCategory.TECHNICAL, "demand": "medium"},
            
            # Cloud & DevOps
            "AWS": {"category": SkillCategory.TECHNICAL, "demand": "high"},
            "Azure": {"category": SkillCategory.TECHNICAL, "demand": "high"},
            "GCP": {"category": SkillCategory.TECHNICAL, "demand": "high"},
            "Docker": {"category": SkillCategory.TOOLS, "demand": "high"},
            "Kubernetes": {"category": SkillCategory.TOOLS, "demand": "high"},
            "Terraform": {"category": SkillCategory.TOOLS, "demand": "high"},
            "CI/CD": {"category": SkillCategory.TECHNICAL, "demand": "high"},
            
            # Data & ML
            "Machine Learning": {"category": SkillCategory.TECHNICAL, "demand": "high"},
            "Deep Learning": {"category": SkillCategory.TECHNICAL, "demand": "high"},
            "TensorFlow": {"category": SkillCategory.TOOLS, "demand": "high"},
            "PyTorch": {"category": SkillCategory.TOOLS, "demand": "high"},
            "scikit-learn": {"category": SkillCategory.TOOLS, "demand": "medium"},
            "Pandas": {"category": SkillCategory.TOOLS, "demand": "high"},
            "NumPy": {"category": SkillCategory.TOOLS, "demand": "high"},
            
            # Soft Skills
            "Leadership": {"category": SkillCategory.MANAGEMENT, "demand": "high"},
            "Communication": {"category": SkillCategory.COMMUNICATION, "demand": "high"},
            "Problem Solving": {"category": SkillCategory.SOFT_SKILLS, "demand": "high"},
            "Teamwork": {"category": SkillCategory.SOFT_SKILLS, "demand": "high"},
            "Project Management": {"category": SkillCategory.MANAGEMENT, "demand": "high"},
            "Agile": {"category": SkillCategory.MANAGEMENT, "demand": "high"},
            "Scrum": {"category": SkillCategory.MANAGEMENT, "demand": "medium"},
        }
    
    def _build_skill_synonyms(self) -> Dict[str, List[str]]:
        """Build skill synonym mappings"""
        return {
            "Python": ["Python3", "Python 3", "Py"],
            "JavaScript": ["JS", "Javascript", "ECMAScript"],
            "TypeScript": ["TS"],
            "Machine Learning": ["ML", "Machine-Learning"],
            "Deep Learning": ["DL", "Deep-Learning"],
            "Artificial Intelligence": ["AI"],
            "Natural Language Processing": ["NLP"],
            "Computer Vision": ["CV"],
            "CI/CD": ["Continuous Integration", "Continuous Deployment", "CI", "CD"],
            "AWS": ["Amazon Web Services"],
            "Azure": ["Microsoft Azure"],
            "GCP": ["Google Cloud Platform", "Google Cloud"],
        }
    
    def _compile_skill_patterns(self) -> List[Tuple[re.Pattern, float]]:
        """Compile regex patterns for skill extraction"""
        patterns = [
            (re.compile(r"experienced in (\w+)", re.IGNORECASE), 0.1),
            (re.compile(r"proficient in (\w+)", re.IGNORECASE), 0.1),
            (re.compile(r"expert in (\w+)", re.IGNORECASE), 0.15),
            (re.compile(r"skilled in (\w+)", re.IGNORECASE), 0.1),
            (re.compile(r"knowledge of (\w+)", re.IGNORECASE), 0.05),
        ]
        return patterns
    
    def _build_proficiency_indicators(self) -> Dict[str, int]:
        """Build proficiency level indicators"""
        return {
            "expert": 5,
            "advanced": 5,
            "proficient": 4,
            "experienced": 4,
            "intermediate": 3,
            "familiar": 2,
            "basic": 2,
            "beginner": 1,
            "novice": 1,
        }
