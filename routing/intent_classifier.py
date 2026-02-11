"""
Intent Classifier

Advanced intent classification using multiple techniques:
- Pattern matching with regex
- Keyword/phrase matching with TF-IDF
- Machine learning classification (optional)
- Multi-intent detection
- Confidence scoring
- Entity extraction
"""

import re
import logging
from typing import List, Dict, Optional, Tuple
from collections import Counter, defaultdict
import uuid
from datetime import datetime

from routing.models import (
    Intent,
    IntentType,
    IntentConfidence,
    IntentPattern,
    MultiIntentResult,
)

logger = logging.getLogger(__name__)


class IntentClassifier:
    """
    Classify user intents using multiple techniques
    
    Features:
    - Pattern-based classification
    - Keyword and phrase matching
    - Entity extraction
    - Multi-intent detection
    - Confidence scoring
    - Context-aware classification
    """
    
    def __init__(self):
        """Initialize intent classifier"""
        self.patterns: Dict[IntentType, IntentPattern] = self._load_intent_patterns()
        self.intent_history: List[Intent] = []
        
        # Thresholds
        self.confidence_thresholds = {
            IntentConfidence.VERY_HIGH: 0.9,
            IntentConfidence.HIGH: 0.75,
            IntentConfidence.MEDIUM: 0.5,
            IntentConfidence.LOW: 0.3,
            IntentConfidence.VERY_LOW: 0.0,
        }
        
        # Multi-intent threshold
        self.multi_intent_threshold = 0.6
        self.min_confidence = 0.3
    
    def classify(
        self,
        user_input: str,
        context: Optional[Dict[str, any]] = None,
        detect_multiple: bool = True
    ) -> Intent:
        """
        Classify user intent
        
        Args:
            user_input: User's input text
            context: Optional context for classification
            detect_multiple: Whether to detect multiple intents
        
        Returns:
            Intent classification result
        """
        user_input_clean = user_input.strip()
        
        if not user_input_clean:
            return self._create_unknown_intent(user_input)
        
        # Score all intents
        intent_scores = self._score_all_intents(user_input_clean, context)
        
        # Get best match
        best_intent_type, best_score = max(intent_scores.items(), key=lambda x: x[1])
        
        # Check if confidence is too low
        if best_score < self.min_confidence:
            return self._create_unknown_intent(user_input)
        
        # Extract entities
        entities = self._extract_entities(user_input_clean, best_intent_type)
        
        # Determine sentiment
        sentiment = self._detect_sentiment(user_input_clean)
        
        # Create intent
        intent = Intent(
            intent_id=f"intent_{uuid.uuid4().hex[:12]}",
            type=best_intent_type,
            confidence=best_score,
            confidence_level=self._get_confidence_level(best_score),
            user_input=user_input,
            entities=entities,
            parameters={},
            sentiment=sentiment,
            timestamp=datetime.utcnow(),
        )
        
        # Track history
        self.intent_history.append(intent)
        
        return intent
    
    def classify_multi(
        self,
        user_input: str,
        context: Optional[Dict[str, any]] = None
    ) -> MultiIntentResult:
        """
        Classify and detect multiple intents
        
        Args:
            user_input: User's input text
            context: Optional context
        
        Returns:
            MultiIntentResult with primary and secondary intents
        """
        user_input_clean = user_input.strip()
        
        # Score all intents
        intent_scores = self._score_all_intents(user_input_clean, context)
        
        # Filter by threshold
        valid_intents = [
            (intent_type, score)
            for intent_type, score in intent_scores.items()
            if score >= self.multi_intent_threshold
        ]
        
        # Sort by score
        valid_intents.sort(key=lambda x: x[1], reverse=True)
        
        if not valid_intents:
            # No valid intents, return unknown
            primary = self._create_unknown_intent(user_input)
            return MultiIntentResult(
                primary_intent=primary,
                secondary_intents=[],
                execution_order=[primary.intent_id],
                requires_clarification=True,
            )
        
        # Create intent objects
        intents = []
        for intent_type, score in valid_intents:
            entities = self._extract_entities(user_input_clean, intent_type)
            intent = Intent(
                intent_id=f"intent_{uuid.uuid4().hex[:12]}",
                type=intent_type,
                confidence=score,
                confidence_level=self._get_confidence_level(score),
                user_input=user_input,
                entities=entities,
                parameters={},
                timestamp=datetime.utcnow(),
            )
            intents.append(intent)
        
        # Determine if clarification needed
        requires_clarification = False
        if len(intents) > 1:
            score_diff = intents[0].confidence - intents[1].confidence
            if score_diff < 0.15:  # Very close scores
                requires_clarification = True
        
        # Create result
        result = MultiIntentResult(
            primary_intent=intents[0],
            secondary_intents=intents[1:] if len(intents) > 1 else [],
            execution_order=[intent.intent_id for intent in intents],
            requires_clarification=requires_clarification,
        )
        
        # Track all intents
        self.intent_history.extend(intents)
        
        return result
    
    def _score_all_intents(
        self,
        user_input: str,
        context: Optional[Dict[str, any]] = None
    ) -> Dict[IntentType, float]:
        """Score all intent types"""
        scores = {}
        user_input_lower = user_input.lower()
        
        for intent_type, pattern in self.patterns.items():
            score = 0.0
            
            # Keyword matching
            keyword_matches = sum(
                1 for keyword in pattern.keywords
                if keyword.lower() in user_input_lower
            )
            if pattern.keywords:
                keyword_score = (keyword_matches / len(pattern.keywords)) * pattern.keyword_weight
                score += keyword_score
            
            # Phrase matching (higher confidence)
            phrase_matches = sum(
                1 for phrase in pattern.phrases
                if phrase.lower() in user_input_lower
            )
            if pattern.phrases:
                phrase_score = (phrase_matches / len(pattern.phrases)) * pattern.phrase_weight
                score += phrase_score
            
            # Regex matching
            regex_matches = sum(
                1 for regex_pattern in pattern.regex_patterns
                if re.search(regex_pattern, user_input, re.IGNORECASE)
            )
            if pattern.regex_patterns:
                regex_score = (regex_matches / len(pattern.regex_patterns)) * pattern.regex_weight
                score += regex_score
            
            # Context bonus
            if context:
                score = self._apply_context_bonus(score, intent_type, context)
            
            scores[intent_type] = min(1.0, score)  # Cap at 1.0
        
        return scores
    
    def _extract_entities(self, user_input: str, intent_type: IntentType) -> Dict[str, any]:
        """Extract entities based on intent type"""
        entities = {}
        pattern = self.patterns.get(intent_type)
        
        if not pattern or not pattern.entity_patterns:
            return entities
        
        for entity_name, entity_pattern in pattern.entity_patterns.items():
            match = re.search(entity_pattern, user_input, re.IGNORECASE)
            if match:
                # Extract matched group (first group or full match)
                if match.groups():
                    entities[entity_name] = match.group(1)
                else:
                    entities[entity_name] = match.group(0)
        
        return entities
    
    def _detect_sentiment(self, user_input: str) -> str:
        """Detect sentiment (positive/negative/neutral)"""
        user_input_lower = user_input.lower()
        
        # Simple keyword-based sentiment
        positive_keywords = ["great", "excellent", "good", "thanks", "thank you", "love", "perfect"]
        negative_keywords = ["bad", "terrible", "hate", "issue", "problem", "error", "fail", "wrong"]
        
        positive_count = sum(1 for word in positive_keywords if word in user_input_lower)
        negative_count = sum(1 for word in negative_keywords if word in user_input_lower)
        
        if positive_count > negative_count:
            return "positive"
        elif negative_count > positive_count:
            return "negative"
        else:
            return "neutral"
    
    def _get_confidence_level(self, score: float) -> IntentConfidence:
        """Map confidence score to level"""
        if score >= self.confidence_thresholds[IntentConfidence.VERY_HIGH]:
            return IntentConfidence.VERY_HIGH
        elif score >= self.confidence_thresholds[IntentConfidence.HIGH]:
            return IntentConfidence.HIGH
        elif score >= self.confidence_thresholds[IntentConfidence.MEDIUM]:
            return IntentConfidence.MEDIUM
        elif score >= self.confidence_thresholds[IntentConfidence.LOW]:
            return IntentConfidence.LOW
        else:
            return IntentConfidence.VERY_LOW
    
    def _apply_context_bonus(
        self,
        base_score: float,
        intent_type: IntentType,
        context: Dict[str, any]
    ) -> float:
        """Apply bonus based on conversation context"""
        bonus = 0.0
        
        # Check if this intent matches recent conversation topic
        last_topic = context.get("current_topic")
        if last_topic and last_topic == intent_type.value:
            bonus += 0.1  # 10% bonus for topic continuity
        
        # Check user history/preferences
        user_preferences = context.get("user_preferences", {})
        preferred_intents = user_preferences.get("frequent_intents", [])
        if intent_type.value in preferred_intents:
            bonus += 0.05  # 5% bonus for frequent intent
        
        return min(1.0, base_score + bonus)
    
    def _create_unknown_intent(self, user_input: str) -> Intent:
        """Create unknown intent"""
        return Intent(
            intent_id=f"intent_{uuid.uuid4().hex[:12]}",
            type=IntentType.UNKNOWN,
            confidence=0.0,
            confidence_level=IntentConfidence.VERY_LOW,
            user_input=user_input,
            entities={},
            parameters={},
            timestamp=datetime.utcnow(),
        )
    
    def _load_intent_patterns(self) -> Dict[IntentType, IntentPattern]:
        """Load intent patterns for classification"""
        patterns = {
            # Greeting
            IntentType.GREETING: IntentPattern(
                pattern_id="pattern_greeting",
                intent_type=IntentType.GREETING,
                keywords=["hello", "hi", "hey", "greetings", "good morning", "good afternoon"],
                phrases=["hi there", "hello there", "hey there"],
                regex_patterns=[r"^(hi|hello|hey)\b"],
                keyword_weight=0.4,
                phrase_weight=0.4,
                regex_weight=0.2,
            ),
            
            # Question
            IntentType.QUESTION: IntentPattern(
                pattern_id="pattern_question",
                intent_type=IntentType.QUESTION,
                keywords=["what", "how", "why", "when", "where", "who", "can", "could", "would"],
                phrases=["can you", "could you", "would you", "tell me", "explain"],
                regex_patterns=[r"\?$", r"^(what|how|why|when|where|who|can|could|would)\b"],
                keyword_weight=0.3,
                phrase_weight=0.4,
                regex_weight=0.3,
            ),
            
            # Command
            IntentType.COMMAND: IntentPattern(
                pattern_id="pattern_command",
                intent_type=IntentType.COMMAND,
                keywords=["do", "make", "create", "update", "delete", "show", "get", "set"],
                phrases=["please do", "i want to", "i need to"],
                regex_patterns=[r"^(do|make|create|update|delete|show|get|set)\b"],
                keyword_weight=0.3,
                phrase_weight=0.4,
                regex_weight=0.3,
            ),
            
            # Loan Application
            IntentType.LOAN_APPLICATION: IntentPattern(
                pattern_id="pattern_loan_application",
                intent_type=IntentType.LOAN_APPLICATION,
                keywords=["loan", "apply", "application", "borrow", "lending", "finance"],
                phrases=[
                    "apply for a loan", "loan application", "apply for loan",
                    "want a loan", "need a loan", "get a loan"
                ],
                regex_patterns=[
                    r"apply.*loan",
                    r"loan.*application",
                    r"(business|personal|auto|home|student)\s+loan"
                ],
                entity_patterns={
                    "loan_type": r"(business|personal|auto|home|student|mortgage)\s+loan",
                    "amount": r"\$?\s*(\d+(?:,\d{3})*(?:\.\d{2})?)\s*(?:dollars?|USD)?",
                },
                keyword_weight=0.3,
                phrase_weight=0.5,
                regex_weight=0.2,
            ),
            
            # Collateral Check
            IntentType.COLLATERAL_CHECK: IntentPattern(
                pattern_id="pattern_collateral",
                intent_type=IntentType.COLLATERAL_CHECK,
                keywords=["collateral", "asset", "security", "property", "equity", "valuation"],
                phrases=[
                    "check collateral", "collateral value", "asset verification",
                    "property value", "evaluate collateral"
                ],
                regex_patterns=[r"collateral.*check", r"check.*collateral", r"asset.*verification"],
                entity_patterns={
                    "asset_type": r"(property|vehicle|equipment|inventory|securities)",
                },
                keyword_weight=0.4,
                phrase_weight=0.4,
                regex_weight=0.2,
            ),
            
            # Credit History
            IntentType.CREDIT_HISTORY: IntentPattern(
                pattern_id="pattern_credit",
                intent_type=IntentType.CREDIT_HISTORY,
                keywords=["credit", "score", "history", "report", "rating", "check credit"],
                phrases=[
                    "credit score", "credit history", "credit report",
                    "check credit", "credit check", "credit rating"
                ],
                regex_patterns=[r"credit.*(score|history|report|check)", r"(check|view).*credit"],
                entity_patterns={},
                keyword_weight=0.4,
                phrase_weight=0.4,
                regex_weight=0.2,
            ),
            
            # Document Upload
            IntentType.DOCUMENT_UPLOAD: IntentPattern(
                pattern_id="pattern_document",
                intent_type=IntentType.DOCUMENT_UPLOAD,
                keywords=["upload", "document", "file", "attach", "send", "submit"],
                phrases=[
                    "upload document", "send file", "attach file",
                    "submit document", "upload file"
                ],
                regex_patterns=[r"upload.*(?:document|file)", r"(?:send|attach|submit).*(?:document|file)"],
                entity_patterns={
                    "document_type": r"(tax|bank|statement|id|proof|invoice|receipt)",
                },
                keyword_weight=0.3,
                phrase_weight=0.5,
                regex_weight=0.2,
            ),
            
            # Profile Analysis (LinkedIn)
            IntentType.PROFILE_ANALYSIS: IntentPattern(
                pattern_id="pattern_profile",
                intent_type=IntentType.PROFILE_ANALYSIS,
                keywords=["profile", "analyze", "analysis", "review", "linkedin", "resume"],
                phrases=[
                    "analyze my profile", "profile analysis", "review my profile",
                    "check my profile", "profile review"
                ],
                regex_patterns=[r"(?:analyze|review|check).*profile", r"profile.*(?:analysis|review)"],
                entity_patterns={},
                keyword_weight=0.4,
                phrase_weight=0.4,
                regex_weight=0.2,
            ),
            
            # Job Matching
            IntentType.JOB_MATCHING: IntentPattern(
                pattern_id="pattern_job_match",
                intent_type=IntentType.JOB_MATCHING,
                keywords=["job", "match", "recommend", "find", "search", "position", "opening"],
                phrases=[
                    "find jobs", "job recommendations", "match jobs",
                    "recommend jobs", "job search", "job openings"
                ],
                regex_patterns=[r"(?:find|match|recommend|search).*job", r"job.*(?:match|search|recommendation)"],
                entity_patterns={
                    "job_type": r"(software|engineer|manager|analyst|developer|designer)",
                },
                keyword_weight=0.3,
                phrase_weight=0.5,
                regex_weight=0.2,
            ),
            
            # Skill Recommendation
            IntentType.SKILL_RECOMMENDATION: IntentPattern(
                pattern_id="pattern_skill",
                intent_type=IntentType.SKILL_RECOMMENDATION,
                keywords=["skill", "learn", "recommend", "improve", "training", "course"],
                phrases=[
                    "recommend skills", "skills to learn", "improve skills",
                    "skill recommendations", "what skills"
                ],
                regex_patterns=[r"(?:recommend|suggest).*skill", r"skill.*(?:learn|recommendation)"],
                entity_patterns={},
                keyword_weight=0.4,
                phrase_weight=0.4,
                regex_weight=0.2,
            ),
            
            # Help
            IntentType.HELP: IntentPattern(
                pattern_id="pattern_help",
                intent_type=IntentType.HELP,
                keywords=["help", "assist", "support", "guide", "how to", "instructions"],
                phrases=["need help", "can you help", "help me", "i need assistance"],
                regex_patterns=[r"^help\b", r"\bhelp\s*(?:me|please)\b"],
                keyword_weight=0.4,
                phrase_weight=0.4,
                regex_weight=0.2,
            ),
            
            # Status
            IntentType.STATUS: IntentPattern(
                pattern_id="pattern_status",
                intent_type=IntentType.STATUS,
                keywords=["status", "progress", "state", "check", "update", "track"],
                phrases=[
                    "check status", "application status", "what's the status",
                    "track application", "progress update"
                ],
                regex_patterns=[r"(?:check|what(?:'s| is)).*status", r"status.*(?:check|update)"],
                entity_patterns={},
                keyword_weight=0.4,
                phrase_weight=0.4,
                regex_weight=0.2,
            ),
        }
        
        return patterns
    
    def add_pattern(self, pattern: IntentPattern):
        """Add custom intent pattern"""
        self.patterns[pattern.intent_type] = pattern
        logger.info(f"Added pattern for intent type: {pattern.intent_type}")
    
    def remove_pattern(self, intent_type: IntentType):
        """Remove intent pattern"""
        if intent_type in self.patterns:
            del self.patterns[intent_type]
            logger.info(f"Removed pattern for intent type: {intent_type}")
    
    def get_statistics(self) -> Dict[str, any]:
        """Get classifier statistics"""
        if not self.intent_history:
            return {
                "total_classifications": 0,
                "by_type": {},
                "avg_confidence": 0.0,
            }
        
        # Count by type
        type_counts = Counter(intent.type for intent in self.intent_history)
        
        # Calculate average confidence
        avg_confidence = sum(intent.confidence for intent in self.intent_history) / len(self.intent_history)
        
        return {
            "total_classifications": len(self.intent_history),
            "by_type": dict(type_counts),
            "avg_confidence": round(avg_confidence, 3),
            "most_common": type_counts.most_common(5),
        }
