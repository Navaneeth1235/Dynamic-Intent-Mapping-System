"""
Intent Expansion Pipeline
=========================
A scalable pipeline to identify missing or split-worthy intents in conversational AI systems.

Author: AI Workflow Analyst Intern Candidate
Date: 2024
"""

import json
import os
from typing import Dict, List, Tuple, Optional, Set
from collections import defaultdict, Counter
from dataclasses import dataclass, asdict
from pathlib import Path
import re
from datetime import datetime

# Load environment variables from .env file if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed, skip

# LLM Integration (using OpenAI API as example - can be adapted to other providers)
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("Warning: OpenAI not available. Using mock responses.")

# Assessment Metrics
try:
    from assessment_metrics import IntentExpansionMetrics
    METRICS_AVAILABLE = True
except ImportError:
    METRICS_AVAILABLE = False
    print("Warning: Assessment metrics not available.")


@dataclass
class IntentProposal:
    """Represents a proposed new or refined intent."""
    level: str  # 'primary' or 'secondary'
    name: str
    id: str
    description: str
    parent_id: Optional[str] = None  # For secondary intents
    rationale: str = ""
    quantitative_evidence: Dict = None
    qualitative_evidence: List[str] = None
    confidence_score: float = 0.0
    sample_messages: List[str] = None
    
    def __post_init__(self):
        if self.quantitative_evidence is None:
            self.quantitative_evidence = {}
        if self.qualitative_evidence is None:
            self.qualitative_evidence = []
        if self.sample_messages is None:
            self.sample_messages = []


@dataclass
class MessageAnalysis:
    """Analysis result for a single message."""
    message_id: str
    current_intent: Dict
    suggested_intent: Optional[str] = None
    confidence: float = 0.0
    reasoning: str = ""
    keywords: List[str] = None
    
    def __post_init__(self):
        if self.keywords is None:
            self.keywords = []


class IntentAnalyzer:
    """Core analyzer for identifying intent patterns."""
    
    def __init__(self, min_message_threshold: int = 5, min_confidence: float = 0.7):
        """
        Initialize the analyzer.
        
        Args:
            min_message_threshold: Minimum number of messages to propose a new intent
            min_confidence: Minimum confidence score for proposals
        """
        self.min_message_threshold = min_message_threshold
        self.min_confidence = min_confidence
        self.message_patterns = defaultdict(list)
        self.intent_coverage = defaultdict(int)
        
    def extract_key_phrases(self, message: str) -> List[str]:
        """Extract key phrases that might indicate intent patterns."""
        # Remove common stop words and extract meaningful phrases
        stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 
                     'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 
                     'can', 'could', 'should', 'may', 'might', 'this', 'that', 
                     'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they'}
        
        # Extract phrases (2-4 words)
        words = re.findall(r'\b\w+\b', message.lower())
        phrases = []
        
        for i in range(len(words) - 1):
            if words[i] not in stop_words or words[i+1] not in stop_words:
                phrases.append(f"{words[i]} {words[i+1]}")
        
        for i in range(len(words) - 2):
            phrases.append(f"{words[i]} {words[i+1]} {words[i+2]}")
            
        return phrases
    
    def analyze_message_intent_fit(self, message: str, current_intent: Dict, 
                                   intent_definitions: Dict) -> Tuple[float, str]:
        """
        Analyze how well a message fits its current intent classification.
        Returns confidence score and reasoning.
        """
        primary = current_intent.get('primary', '')
        secondary = current_intent.get('secondary', '')
        
        # Get intent definition
        intent_key = f"{primary}_{secondary}" if secondary else primary
        intent_def = intent_definitions.get(intent_key, {})
        intent_description = intent_def.get('description', '')
        
        # Simple keyword matching (can be enhanced with embeddings)
        message_lower = message.lower()
        description_keywords = set(re.findall(r'\b\w+\b', intent_description.lower()))
        message_keywords = set(re.findall(r'\b\w+\b', message_lower))
        
        # Calculate overlap
        if description_keywords:
            overlap = len(message_keywords & description_keywords) / len(description_keywords)
        else:
            overlap = 0.0
        
        # Check for explicit intent indicators
        intent_indicators = {
            'how to': ['how to', 'how do i', 'how can i', 'instructions', 'guide'],
            'when': ['when', 'what time', 'schedule', 'timing'],
            'where': ['where', 'location', 'place'],
            'why': ['why', 'reason', 'because'],
            'what is': ['what is', 'what are', 'explain', 'tell me about'],
            'compare': ['compare', 'difference', 'vs', 'versus', 'better'],
            'problem': ['issue', 'problem', 'error', 'not working', 'broken'],
            'cancel': ['cancel', 'refund', 'return', 'remove'],
            'status': ['status', 'track', 'where is', 'when will'],
        }
        
        confidence = overlap * 0.6  # Base confidence from keyword overlap
        
        reasoning = f"Keyword overlap: {overlap:.2f}"
        
        # Boost confidence if explicit indicators match
        for indicator_type, patterns in intent_indicators.items():
            if any(pattern in message_lower for pattern in patterns):
                if indicator_type in intent_description.lower():
                    confidence += 0.2
                    reasoning += f", {indicator_type} indicator match"
                else:
                    confidence -= 0.1  # Mismatch suggests wrong intent
                    reasoning += f", {indicator_type} mismatch"
        
        confidence = max(0.0, min(1.0, confidence))
        
        return confidence, reasoning


class LLMIntentProposer:
    """Uses LLM to propose new intents based on patterns."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        """
        Initialize LLM proposer.
        
        Args:
            api_key: OpenAI API key (or set OPENAI_API_KEY env var)
            model: Model to use for analysis
        """
        self.model = model
        # Try to get API key from multiple sources
        self.api_key = api_key or os.getenv('OPENAI_API_KEY') or os.getenv('OPENAI_API_KEY')
        self.client = None
        
        if OPENAI_AVAILABLE and self.api_key:
            try:
                # Try new OpenAI client (v1.0+)
                from openai import OpenAI
                self.client = OpenAI(api_key=self.api_key)
                print(f"✓ LLM initialized with API key (model: {model})")
            except ImportError:
                # Fallback to old API
                openai.api_key = self.api_key
                self.client = openai
                print(f"✓ LLM initialized with API key (model: {model})")
        else:
            if not OPENAI_AVAILABLE:
                print("Warning: OpenAI package not available. Using mock responses.")
            elif not self.api_key:
                print("Warning: OPENAI_API_KEY not found. Using mock responses.")
                print("  Set it via: export OPENAI_API_KEY='your-key' or --api-key argument")
    
    def propose_intent_from_pattern(self, pattern_messages: List[Dict], 
                                    current_intents: Dict,
                                    parent_intent: Optional[str] = None) -> Optional[IntentProposal]:
        """
        Propose a new intent based on a pattern of messages.
        Uses LLM in a structured way (not bulk processing).
        """
        if len(pattern_messages) < 3:  # Guardrail: need minimum messages
            return None
        
        # Extract sample messages (limit to avoid token bloat)
        sample_texts = [msg.get('message', '')[:200] for msg in pattern_messages[:10]]
        
        # Build structured prompt
        prompt = self._build_proposal_prompt(sample_texts, current_intents, parent_intent)
        
        # Call LLM with structured output
        response = self._call_llm(prompt)
        
        if response:
            return self._parse_llm_response(response, pattern_messages)
        
        return None
    
    def _build_proposal_prompt(self, sample_messages: List[str], 
                               current_intents: Dict,
                               parent_intent: Optional[str]) -> str:
        """Build a structured prompt for intent proposal."""
        intent_summary = self._summarize_intents(current_intents)
        
        prompt = f"""You are an intent classification expert. Analyze the following customer messages and propose a NEW intent if they represent a distinct pattern not well-covered by existing intents.

EXISTING INTENTS:
{intent_summary}

SAMPLE MESSAGES (showing a pattern):
"""
        for i, msg in enumerate(sample_messages, 1):
            prompt += f"{i}. {msg}\n"
        
        prompt += f"""
PARENT INTENT (if proposing secondary): {parent_intent or 'N/A'}

TASK:
1. Determine if these messages represent a distinct intent pattern
2. If yes, propose a new intent with:
   - Level (primary or secondary)
   - Name (clear, concise)
   - ID (snake_case, descriptive)
   - Description (what customer is asking for)
   - Rationale (why this is distinct from existing intents)

IMPORTANT CONSTRAINTS:
- Don't create too granular intents (avoid splitting into ingredients/components/materials separately)
- Each intent should represent a meaningful customer goal
- Secondary intents must have a clear parent
- Consider if this could be handled by refining existing intents instead

Respond in JSON format:
{{
    "should_propose": true/false,
    "level": "primary" or "secondary",
    "name": "Intent Name",
    "id": "intent_id",
    "description": "Clear description",
    "rationale": "Why this is needed",
    "confidence": 0.0-1.0
}}
"""
        return prompt
    
    def _summarize_intents(self, intents: Dict) -> str:
        """Create a concise summary of existing intents."""
        summary = []
        for intent_id, intent_data in intents.items():
            level = intent_data.get('level', 'unknown')
            name = intent_data.get('name', '')
            desc = intent_data.get('description', '')[:100]
            summary.append(f"- {intent_id} ({level}): {name} - {desc}")
        return "\n".join(summary)
    
    def _call_llm(self, prompt: str) -> Optional[str]:
        """Call LLM API with error handling."""
        if not self.client:
            # Mock response for testing
            return json.dumps({
                "should_propose": False,
                "reason": "LLM not configured"
            })
        
        try:
            # Try new OpenAI API format (v1.0+)
            if hasattr(self.client, 'chat') and hasattr(self.client.chat, 'completions'):
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are a precise intent classification expert. Always respond with valid JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_tokens=500
                )
                return response.choices[0].message.content
            # Fallback to old API format
            elif hasattr(self.client, 'ChatCompletion'):
                response = self.client.ChatCompletion.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are a precise intent classification expert. Always respond with valid JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_tokens=500
                )
                return response.choices[0].message.content
            else:
                print("Warning: Unsupported OpenAI API format")
                return None
        except Exception as e:
            print(f"LLM call failed: {e}")
            return None
    
    def _parse_llm_response(self, response: str, pattern_messages: List[Dict]) -> Optional[IntentProposal]:
        """Parse LLM response into IntentProposal."""
        try:
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if not json_match:
                return None
            
            data = json.loads(json_match.group())
            
            if not data.get('should_propose', False):
                return None
            
            proposal = IntentProposal(
                level=data.get('level', 'secondary'),
                name=data.get('name', ''),
                id=data.get('id', ''),
                description=data.get('description', ''),
                rationale=data.get('rationale', ''),
                confidence_score=float(data.get('confidence', 0.0)),
                sample_messages=[msg.get('message', '')[:150] for msg in pattern_messages[:5]]
            )
            
            return proposal
            
        except Exception as e:
            print(f"Failed to parse LLM response: {e}")
            return None


class IntentExpansionPipeline:
    """Main pipeline for intent expansion."""
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize the pipeline.
        
        Args:
            config: Configuration dictionary with settings
        """
        self.config = config or {}
        self.analyzer = IntentAnalyzer(
            min_message_threshold=self.config.get('min_message_threshold', 5),
            min_confidence=self.config.get('min_confidence', 0.7)
        )
        self.llm_proposer = LLMIntentProposer(
            api_key=self.config.get('openai_api_key'),
            model=self.config.get('llm_model', 'gpt-4o-mini')
        )
        self.intent_definitions = {}
        self.messages = []
        self.proposals = []
        
    def load_data(self, data_path: str):
        """Load data from JSON file."""
        with open(data_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Handle intent_mapper - convert array to dictionary
        intent_mapper_raw = data.get('intent_mapper', [])
        if isinstance(intent_mapper_raw, list):
            # Convert array format to dictionary
            self.intent_definitions = {}
            for primary_intent in intent_mapper_raw:
                primary_id = primary_intent.get('primary_intent_id', '')
                primary_name = primary_intent.get('primary_intent_name', '')
                
                # Add primary intent
                self.intent_definitions[primary_id] = {
                    'level': 'primary',
                    'name': primary_name,
                    'description': f"Primary intent: {primary_name}"
                }
                
                # Add secondary intents
                for secondary in primary_intent.get('secondary_intents', []):
                    secondary_id = secondary.get('id', '')
                    intent_key = f"{primary_id}_{secondary_id}"
                    self.intent_definitions[intent_key] = {
                        'level': 'secondary',
                        'name': secondary.get('name', ''),
                        'description': secondary.get('description', ''),
                        'parent': primary_id
                    }
        else:
            self.intent_definitions = intent_mapper_raw
        
        # Handle messages - support both 'messages' and 'customer_messages'
        raw_messages = data.get('customer_messages', data.get('messages', []))
        
        # Convert message format if needed
        self.messages = []
        for msg in raw_messages:
            # Handle different message formats
            if 'current_human_message' in msg:
                # New format: has current_human_message and history
                message_text = msg.get('current_human_message', '')
                history = msg.get('history', '')
                # For now, we'll work with unclassified messages
                # In a real scenario, you'd classify them first
                self.messages.append({
                    'message': message_text,
                    'history': history,
                    'intent': {}  # Will be analyzed/classified
                })
            elif 'message' in msg:
                # Standard format
                self.messages.append(msg)
            else:
                # Skip malformed messages
                continue
        
        self.classification_prompt = data.get('prompt_for_classification', data.get('classification_prompt', ''))
        
        print(f"Loaded {len(self.intent_definitions)} intent definitions")
        print(f"Loaded {len(self.messages)} messages")
        
    def analyze_messages(self, batch_size: int = 50):
        """
        Analyze messages in batches for scalability.
        
        Args:
            batch_size: Number of messages to process per batch
        """
        print("\n=== Starting Message Analysis ===")
        
        # Track patterns
        intent_message_map = defaultdict(list)
        low_confidence_messages = []
        
        # Process in batches
        total_batches = (len(self.messages) + batch_size - 1) // batch_size
        
        for batch_idx in range(total_batches):
            start_idx = batch_idx * batch_size
            end_idx = min(start_idx + batch_size, len(self.messages))
            batch = self.messages[start_idx:end_idx]
            
            print(f"Processing batch {batch_idx + 1}/{total_batches} ({len(batch)} messages)")
            
            for msg in batch:
                message_text = msg.get('message', '')
                if not message_text:
                    continue
                
                current_intent = msg.get('intent', {})
                
                # If message is unclassified, analyze patterns directly
                if not current_intent or not current_intent.get('primary'):
                    # For unclassified messages, we'll analyze patterns directly
                    # and group them for potential new intent discovery
                    low_confidence_messages.append({
                        'message': message_text,
                        'history': msg.get('history', ''),
                        'intent': {},
                        'confidence': 0.0,
                        'reasoning': 'Unclassified message - analyzing for new patterns'
                    })
                    continue
                
                # Analyze intent fit for classified messages
                confidence, reasoning = self.analyzer.analyze_message_intent_fit(
                    message_text, current_intent, self.intent_definitions
                )
                
                # Track by intent
                intent_key = f"{current_intent.get('primary', '')}_{current_intent.get('secondary', '')}"
                intent_message_map[intent_key].append({
                    'message': message_text,
                    'confidence': confidence,
                    'reasoning': reasoning,
                    'original_msg': msg
                })
                
                # Track low confidence
                if confidence < self.analyzer.min_confidence:
                    low_confidence_messages.append({
                        'message': message_text,
                        'history': msg.get('history', ''),
                        'intent': current_intent,
                        'confidence': confidence,
                        'reasoning': reasoning
                    })
        
        print(f"\nFound {len(low_confidence_messages)} messages with low confidence")
        print(f"Analyzed {len(intent_message_map)} intent categories")
        
        return intent_message_map, low_confidence_messages
    
    def identify_split_candidates(self, intent_message_map: Dict) -> List[Dict]:
        """
        Identify intents that might need splitting.
        
        Args:
            intent_message_map: Dictionary mapping intent keys to messages
        """
        print("\n=== Identifying Split Candidates ===")
        
        split_candidates = []
        
        for intent_key, messages in intent_message_map.items():
            if len(messages) < self.analyzer.min_message_threshold:
                continue
            
            # Analyze message patterns within this intent
            patterns = self._extract_patterns(messages)
            
            # Check if patterns suggest splitting
            for pattern, pattern_messages in patterns.items():
                if len(pattern_messages) >= self.analyzer.min_message_threshold:
                    # Calculate pattern distinctness
                    distinctness = self._calculate_pattern_distinctness(
                        pattern, pattern_messages, intent_key
                    )
                    
                    if distinctness > 0.6:  # Threshold for distinctness
                        split_candidates.append({
                            'parent_intent': intent_key,
                            'pattern': pattern,
                            'messages': pattern_messages,
                            'distinctness': distinctness,
                            'count': len(pattern_messages)
                        })
        
        print(f"Found {len(split_candidates)} potential split candidates")
        return split_candidates
    
    def _extract_patterns(self, messages: List[Dict]) -> Dict[str, List[Dict]]:
        """Extract distinct patterns from messages."""
        patterns = defaultdict(list)
        
        # Group by key phrases
        for msg_data in messages:
            message = msg_data['message']
            phrases = self.analyzer.extract_key_phrases(message)
            
            # Find dominant phrase
            if phrases:
                top_phrase = Counter(phrases).most_common(1)[0][0]
                patterns[top_phrase].append(msg_data)
        
        # Filter patterns with sufficient messages
        return {p: msgs for p, msgs in patterns.items() 
                if len(msgs) >= self.analyzer.min_message_threshold}
    
    def _calculate_pattern_distinctness(self, pattern: str, pattern_messages: List[Dict],
                                       parent_intent: str) -> float:
        """Calculate how distinct a pattern is from its parent intent."""
        # Simple heuristic: check if pattern keywords appear in intent description
        intent_def = self.intent_definitions.get(parent_intent, {})
        intent_desc = intent_def.get('description', '').lower()
        pattern_lower = pattern.lower()
        
        # If pattern keywords are NOT in description, it's more distinct
        pattern_words = set(pattern_lower.split())
        desc_words = set(re.findall(r'\b\w+\b', intent_desc))
        
        overlap = len(pattern_words & desc_words) / max(len(pattern_words), 1)
        distinctness = 1.0 - overlap
        
        return distinctness
    
    def propose_new_intents(self, split_candidates: List[Dict], 
                           low_confidence_messages: List[Dict]) -> List[IntentProposal]:
        """
        Propose new intents using LLM (structured, not bulk).
        
        Args:
            split_candidates: List of split candidates
            low_confidence_messages: Messages with low confidence
        """
        print("\n=== Proposing New Intents ===")
        
        proposals = []
        
        # Process split candidates
        for candidate in split_candidates:
            print(f"Analyzing pattern: {candidate['pattern']} ({candidate['count']} messages)")
            
            proposal = self.llm_proposer.propose_intent_from_pattern(
                candidate['messages'],
                self.intent_definitions,
                parent_intent=candidate['parent_intent']
            )
            
            if proposal and proposal.confidence_score >= self.analyzer.min_confidence:
                # Add quantitative evidence
                proposal.quantitative_evidence = {
                    'message_count': candidate['count'],
                    'distinctness_score': candidate['distinctness'],
                    'parent_intent': candidate['parent_intent']
                }
                proposals.append(proposal)
                print(f"  ✓ Proposed: {proposal.name} ({proposal.id})")
            else:
                print(f"  ✗ Rejected (low confidence or LLM rejection)")
        
        # Analyze low confidence messages for new primary intents
        if low_confidence_messages:
            print(f"\nAnalyzing {len(low_confidence_messages)} low-confidence messages")
            
            # Group by similarity
            grouped_low_conf = self._group_similar_messages(low_confidence_messages)
            print(f"Found {len(grouped_low_conf)} message groups")
            
            for idx, group_messages in enumerate(grouped_low_conf):
                print(f"  Group {idx + 1}: {len(group_messages)} messages")
                if len(group_messages) >= self.analyzer.min_message_threshold:
                    proposal = self.llm_proposer.propose_intent_from_pattern(
                        group_messages,
                        self.intent_definitions,
                        parent_intent=None  # Primary intent
                    )
                    
                    if proposal and proposal.confidence_score >= self.analyzer.min_confidence:
                        # Fix level for primary intents (no parent)
                        # Since parent_intent=None, these should be primary intents
                        proposal.level = 'primary'
                        proposal.parent_id = None
                        proposal.quantitative_evidence = {
                            'message_count': len(group_messages),
                            'source': 'low_confidence_analysis'
                        }
                        proposals.append(proposal)
                        print(f"  ✓ Proposed new primary: {proposal.name} ({proposal.id})")
                    elif proposal:
                        print(f"  ✗ Rejected: Low confidence ({proposal.confidence_score:.2f})")
                    else:
                        print(f"  ✗ Rejected: LLM did not propose intent")
                else:
                    print(f"  ✗ Group too small: {len(group_messages)} < {self.analyzer.min_message_threshold}")
        
        self.proposals = proposals
        return proposals
    
    def _group_similar_messages(self, messages: List[Dict], similarity_threshold: float = 0.3) -> List[List[Dict]]:
        """Group similar messages together."""
        # Improved grouping for unclassified messages
        groups = []
        used = set()
        
        # First pass: group by exact or very similar key phrases
        for i, msg1 in enumerate(messages):
            if i in used:
                continue
            
            group = [msg1]
            used.add(i)
            
            message1 = msg1['message'].lower()
            phrases1 = set(self.analyzer.extract_key_phrases(msg1['message']))
            
            # Also extract important keywords (non-stop words)
            words1 = set(re.findall(r'\b\w{4,}\b', message1))  # Words with 4+ chars
            
            for j, msg2 in enumerate(messages[i+1:], start=i+1):
                if j in used:
                    continue
                
                message2 = msg2['message'].lower()
                phrases2 = set(self.analyzer.extract_key_phrases(msg2['message']))
                words2 = set(re.findall(r'\b\w{4,}\b', message2))
                
                # Calculate similarity using both phrases and keywords
                phrase_similarity = 0.0
                word_similarity = 0.0
                
                if phrases1 and phrases2:
                    phrase_similarity = len(phrases1 & phrases2) / len(phrases1 | phrases2)
                
                if words1 and words2:
                    word_similarity = len(words1 & words2) / len(words1 | words2)
                
                # Combined similarity (weighted)
                combined_similarity = (phrase_similarity * 0.6) + (word_similarity * 0.4)
                
                if combined_similarity >= similarity_threshold:
                    group.append(msg2)
                    used.add(j)
            
            # Only return groups that meet minimum threshold
            if len(group) >= self.analyzer.min_message_threshold:
                groups.append(group)
        
        # Second pass: for remaining ungrouped messages, try pattern-based grouping
        remaining = [msg for i, msg in enumerate(messages) if i not in used]
        if remaining:
            # Group by common question patterns (more aggressive)
            question_groups = defaultdict(list)
            for msg in remaining:
                message = msg['message'].lower()
                # Extract question patterns (can match multiple patterns)
                if 'how to' in message or 'how do' in message or 'how can' in message or 'how' in message:
                    question_groups['how_to'].append(msg)
                if 'what' in message and ('special' in message or 'best' in message):
                    question_groups['what_special'].append(msg)
                if 'track' in message or ('order' in message and ('status' in message or 'where' in message)):
                    question_groups['order_tracking'].append(msg)
                if 'use' in message or 'apply' in message or 'usage' in message:
                    question_groups['usage'].append(msg)
                if 'cancel' in message or 'refund' in message or 'return' in message:
                    question_groups['cancellation'].append(msg)
                if 'ingredient' in message or 'component' in message:
                    question_groups['ingredients'].append(msg)
                if 'price' in message or 'cost' in message or 'discount' in message:
                    question_groups['pricing'].append(msg)
            
            # Add groups that meet threshold
            for pattern, group_msgs in question_groups.items():
                if len(group_msgs) >= self.analyzer.min_message_threshold:
                    groups.append(group_msgs)
                    print(f"    Pattern '{pattern}': {len(group_msgs)} messages")
        
        print(f"    Total groups created: {len(groups)}")
        return groups
    
    def apply_guardrails(self, proposals: List[IntentProposal]) -> List[IntentProposal]:
        """
        Apply guardrails to filter proposals.
        
        Guardrails:
        1. Minimum message count
        2. Minimum confidence
        3. Avoid over-granular splits
        4. Check for existing similar intents
        """
        print("\n=== Applying Guardrails ===")
        
        filtered = []
        
        for proposal in proposals:
            # Guardrail 1: Minimum threshold
            msg_count = proposal.quantitative_evidence.get('message_count', 0)
            if msg_count < self.analyzer.min_message_threshold:
                print(f"  ✗ {proposal.id}: Insufficient messages ({msg_count})")
                continue
            
            # Guardrail 2: Confidence threshold
            if proposal.confidence_score < self.analyzer.min_confidence:
                print(f"  ✗ {proposal.id}: Low confidence ({proposal.confidence_score:.2f})")
                continue
            
            # Guardrail 3: Check for similar existing intents
            if self._has_similar_intent(proposal):
                print(f"  ✗ {proposal.id}: Similar intent already exists")
                continue
            
            # Guardrail 4: Avoid over-granular splits
            if self._is_too_granular(proposal):
                print(f"  ✗ {proposal.id}: Too granular (would cause over-clustering)")
                continue
            
            filtered.append(proposal)
            print(f"  ✓ {proposal.id}: Passed all guardrails")
        
        return filtered
    
    def _has_similar_intent(self, proposal: IntentProposal) -> bool:
        """Check if a similar intent already exists."""
        proposal_keywords = set(re.findall(r'\b\w+\b', proposal.description.lower()))
        
        for intent_id, intent_data in self.intent_definitions.items():
            existing_desc = intent_data.get('description', '').lower()
            existing_keywords = set(re.findall(r'\b\w+\b', existing_desc))
            
            # Calculate similarity
            if proposal_keywords and existing_keywords:
                similarity = len(proposal_keywords & existing_keywords) / len(proposal_keywords | existing_keywords)
                if similarity > 0.7:  # High similarity threshold
                    return True
        
        return False
    
    def _is_too_granular(self, proposal: IntentProposal) -> bool:
        """Check if proposal is too granular (would cause over-clustering)."""
        # Check description length and specificity
        desc = proposal.description.lower()
        
        # Too many specific terms suggests over-granularity
        specific_terms = ['ingredient', 'component', 'material', 'part', 'element']
        if sum(1 for term in specific_terms if term in desc) > 1:
            return True
        
        # Very short descriptions might be too specific
        if len(desc.split()) < 5:
            return True
        
        return False
    
    def generate_report(self, output_path: str = "intent_expansion_report.json", assessment: Optional[Dict] = None):
        """Generate a comprehensive report of findings."""
        filtered = self.apply_guardrails(self.proposals)
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_messages_analyzed': len(self.messages),
                'total_intents_existing': len(self.intent_definitions),
                'proposals_generated': len(self.proposals),
                'proposals_after_guardrails': len(filtered)
            },
            'proposals': [asdict(p) for p in filtered],
            'methodology': {
                'min_message_threshold': self.analyzer.min_message_threshold,
                'min_confidence': self.analyzer.min_confidence,
                'batch_processing': True,
                'llm_model': self.llm_proposer.model
            }
        }
        
        # Add assessment metrics if available
        if assessment:
            report['assessment'] = assessment
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n=== Report Generated ===")
        print(f"Saved to: {output_path}")
        
        return report
    
    def run(self, data_path: str, batch_size: int = 50):
        """Run the complete pipeline."""
        print("=" * 60)
        print("INTENT EXPANSION PIPELINE")
        print("=" * 60)
        
        # Load data
        self.load_data(data_path)
        
        # Analyze messages
        intent_message_map, low_confidence_messages = self.analyze_messages(batch_size)
        
        # Identify split candidates
        split_candidates = self.identify_split_candidates(intent_message_map)
        
        # Propose new intents
        proposals = self.propose_new_intents(split_candidates, low_confidence_messages)
        
        # Apply guardrails
        filtered_proposals = self.apply_guardrails(proposals)
        
        # Calculate assessment metrics
        assessment = None
        if METRICS_AVAILABLE:
            print("\n=== Calculating Assessment Metrics ===")
            metrics = IntentExpansionMetrics(
                self.intent_definitions,
                self.messages,
                filtered_proposals
            )
            assessment = metrics.generate_assessment_report()
            print(f"Overall Quality Score: {assessment['overall_quality_score']:.2f}")
            print(f"Coverage Improvement: {assessment['coverage_metrics']['coverage_improvement']:.1f}%")
        
        # Generate report
        report = self.generate_report(assessment=assessment)
        
        print("\n" + "=" * 60)
        print("PIPELINE COMPLETE")
        print("=" * 60)
        print(f"\nFinal Proposals: {len(filtered_proposals)}")
        for prop in filtered_proposals:
            print(f"  - {prop.name} ({prop.id}): {prop.description[:60]}...")
        
        return filtered_proposals, report


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Intent Expansion Pipeline')
    parser.add_argument('--data', type=str, default='inputs_for_assignment.json',
                       help='Path to input JSON file')
    parser.add_argument('--batch-size', type=int, default=50,
                       help='Batch size for processing messages')
    parser.add_argument('--min-threshold', type=int, default=5,
                       help='Minimum messages required for new intent')
    parser.add_argument('--min-confidence', type=float, default=0.7,
                       help='Minimum confidence score for proposals')
    parser.add_argument('--api-key', type=str, default=None,
                       help='OpenAI API key (or set OPENAI_API_KEY env var)')
    
    args = parser.parse_args()
    
    # Configuration
    config = {
        'min_message_threshold': args.min_threshold,
        'min_confidence': args.min_confidence,
        'openai_api_key': args.api_key,
        'llm_model': 'gpt-4o-mini'
    }
    
    # Initialize and run pipeline
    pipeline = IntentExpansionPipeline(config)
    
    if not os.path.exists(args.data):
        print(f"Error: Data file not found: {args.data}")
        print("Please provide the inputs_for_assignment.json file")
        return
    
    proposals, report = pipeline.run(args.data, batch_size=args.batch_size)
    
    print(f"\n✓ Pipeline completed successfully")
    print(f"✓ Generated {len(proposals)} intent proposals")


if __name__ == "__main__":
    main()

