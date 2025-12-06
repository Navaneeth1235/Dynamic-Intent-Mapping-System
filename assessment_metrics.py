"""
Assessment Metrics for Intent Expansion Pipeline
================================================
Metrics to evaluate the quality and impact of intent proposals.
"""

from typing import Dict, List
from collections import defaultdict
import json


class IntentExpansionMetrics:
    """Metrics to assess intent expansion proposals."""
    
    def __init__(self, original_intents: Dict, messages: List[Dict], proposals: List):
        """
        Initialize metrics calculator.
        
        Args:
            original_intents: Original intent definitions
            messages: All customer messages
            proposals: Proposed new intents
        """
        self.original_intents = original_intents
        self.messages = messages
        self.proposals = proposals
    
    def calculate_coverage_improvement(self) -> Dict:
        """
        Calculate how much coverage improves with new intents.
        Coverage = % of messages that can be confidently classified.
        """
        # Count messages with low confidence in original system
        low_conf_original = 0
        high_conf_original = 0
        
        for msg in self.messages:
            # This would need actual confidence scores from original classification
            # For now, we estimate based on message length and clarity
            msg_text = msg.get('message', '')
            if len(msg_text) < 10 or '?' not in msg_text:
                low_conf_original += 1
            else:
                high_conf_original += 1
        
        total = len(self.messages)
        original_coverage = (high_conf_original / total) * 100 if total > 0 else 0
        
        # Estimate improvement (messages that would map to new intents)
        messages_for_new_intents = 0
        for proposal in self.proposals:
            msg_count = proposal.quantitative_evidence.get('message_count', 0)
            messages_for_new_intents += msg_count
        
        # Assume these were previously low confidence
        improved_coverage = ((high_conf_original + messages_for_new_intents) / total) * 100 if total > 0 else 0
        
        return {
            'original_coverage': original_coverage,
            'improved_coverage': improved_coverage,
            'coverage_improvement': improved_coverage - original_coverage,
            'messages_addressed': messages_for_new_intents
        }
    
    def calculate_intent_granularity_score(self) -> Dict:
        """
        Calculate granularity score - balance between specificity and over-clustering.
        Lower is better (fewer intents, but still meaningful).
        """
        original_count = len(self.original_intents)
        proposed_count = len(self.proposals)
        
        # Calculate average messages per intent
        total_messages = len(self.messages)
        original_avg = total_messages / original_count if original_count > 0 else 0
        proposed_avg = total_messages / (original_count + proposed_count) if (original_count + proposed_count) > 0 else 0
        
        # Granularity penalty: too many intents = higher score
        granularity_penalty = (proposed_count / original_count) * 0.5 if original_count > 0 else 0
        
        # Balance score: want meaningful splits without over-clustering
        balance_score = 1.0 - min(granularity_penalty, 0.5)
        
        return {
            'original_intent_count': original_count,
            'proposed_intent_count': proposed_count,
            'total_after_expansion': original_count + proposed_count,
            'original_avg_messages_per_intent': original_avg,
            'proposed_avg_messages_per_intent': proposed_avg,
            'granularity_penalty': granularity_penalty,
            'balance_score': balance_score
        }
    
    def calculate_distinctness_scores(self) -> List[Dict]:
        """Calculate distinctness scores for each proposal."""
        distinctness_scores = []
        
        for proposal in self.proposals:
            # Get distinctness from quantitative evidence
            distinctness = proposal.quantitative_evidence.get('distinctness_score', 0.0)
            
            # Check overlap with existing intents
            overlap_scores = []
            proposal_keywords = set(proposal.description.lower().split())
            
            for intent_id, intent_data in self.original_intents.items():
                existing_desc = intent_data.get('description', '').lower()
                existing_keywords = set(existing_desc.split())
                
                if proposal_keywords and existing_keywords:
                    overlap = len(proposal_keywords & existing_keywords) / len(proposal_keywords | existing_keywords)
                    overlap_scores.append(overlap)
            
            avg_overlap = sum(overlap_scores) / len(overlap_scores) if overlap_scores else 0.0
            distinctness_from_existing = 1.0 - avg_overlap
            
            distinctness_scores.append({
                'proposal_id': proposal.id,
                'proposal_name': proposal.name,
                'pattern_distinctness': distinctness,
                'distinctness_from_existing': distinctness_from_existing,
                'overall_distinctness': (distinctness + distinctness_from_existing) / 2
            })
        
        return distinctness_scores
    
    def calculate_confidence_distribution(self) -> Dict:
        """Calculate confidence score distribution."""
        confidences = [p.confidence_score for p in self.proposals]
        
        if not confidences:
            return {
                'mean': 0.0,
                'min': 0.0,
                'max': 0.0,
                'high_confidence_count': 0,
                'medium_confidence_count': 0,
                'low_confidence_count': 0
            }
        
        mean_conf = sum(confidences) / len(confidences)
        min_conf = min(confidences)
        max_conf = max(confidences)
        
        high_conf = sum(1 for c in confidences if c >= 0.8)
        medium_conf = sum(1 for c in confidences if 0.6 <= c < 0.8)
        low_conf = sum(1 for c in confidences if c < 0.6)
        
        return {
            'mean': mean_conf,
            'min': min_conf,
            'max': max_conf,
            'high_confidence_count': high_conf,
            'medium_confidence_count': medium_conf,
            'low_confidence_count': low_conf,
            'distribution': {
                'high': (high_conf / len(confidences)) * 100,
                'medium': (medium_conf / len(confidences)) * 100,
                'low': (low_conf / len(confidences)) * 100
            }
        }
    
    def generate_assessment_report(self) -> Dict:
        """Generate comprehensive assessment report."""
        coverage = self.calculate_coverage_improvement()
        granularity = self.calculate_intent_granularity_score()
        distinctness = self.calculate_distinctness_scores()
        confidence = self.calculate_confidence_distribution()
        
        # Overall quality score
        quality_score = (
            coverage['coverage_improvement'] / 10.0 +  # Normalize to 0-1
            granularity['balance_score'] * 0.3 +
            (sum(d['overall_distinctness'] for d in distinctness) / len(distinctness) if distinctness else 0) * 0.3 +
            confidence['mean'] * 0.2
        )
        quality_score = max(0.0, min(1.0, quality_score))
        
        report = {
            'overall_quality_score': quality_score,
            'coverage_metrics': coverage,
            'granularity_metrics': granularity,
            'distinctness_metrics': distinctness,
            'confidence_metrics': confidence,
            'recommendations': self._generate_recommendations(coverage, granularity, distinctness, confidence)
        }
        
        return report
    
    def _generate_recommendations(self, coverage: Dict, granularity: Dict, 
                                  distinctness: List[Dict], confidence: Dict) -> List[str]:
        """Generate recommendations based on metrics."""
        recommendations = []
        
        # Coverage recommendations
        if coverage['coverage_improvement'] < 5:
            recommendations.append(
                "Low coverage improvement. Consider analyzing more message patterns or "
                "lowering the minimum message threshold."
            )
        
        # Granularity recommendations
        if granularity['granularity_penalty'] > 0.4:
            recommendations.append(
                "High granularity penalty detected. Consider merging similar proposals "
                "or increasing the minimum message threshold to avoid over-clustering."
            )
        
        # Distinctness recommendations
        low_distinct = [d for d in distinctness if d['overall_distinctness'] < 0.5]
        if low_distinct:
            recommendations.append(
                f"{len(low_distinct)} proposals have low distinctness. Review if they "
                "should be merged with existing intents instead."
            )
        
        # Confidence recommendations
        if confidence['mean'] < 0.7:
            recommendations.append(
                "Average confidence is below threshold. Review proposals and consider "
                "refining the analysis methodology."
            )
        
        if not recommendations:
            recommendations.append(
                "All metrics look good! The proposals are well-balanced and distinct."
            )
        
        return recommendations

