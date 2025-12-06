# Intent Expansion Pipeline

A scalable Python pipeline to identify missing or split-worthy intents in conversational AI systems.

## Overview

This pipeline analyzes customer messages to automatically discover new intents or identify existing intents that should be split. It uses a structured workflow that combines deterministic analysis with LLM-powered proposals, ensuring scalability and quality.

## Features

- ✅ **Scalable**: Processes messages in batches (handles hundreds → thousands)
- ✅ **Intelligent**: Uses LLMs strategically (not bulk processing)
- ✅ **Guarded**: Multiple guardrails prevent over-clustering
- ✅ **Evidence-Based**: Quantitative and qualitative justification for proposals
- ✅ **Assessable**: Built-in metrics to evaluate proposal quality
- ✅ **Configurable**: Adjustable thresholds and parameters

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Set OpenAI API key (optional, for LLM features)
export OPENAI_API_KEY="your-api-key-here"
```

## Quick Start

```bash
# Run with default settings
python intent_expansion_pipeline.py --data inputs_for_assignment.json

# Customize parameters
python intent_expansion_pipeline.py \
    --data inputs_for_assignment.json \
    --batch-size 50 \
    --min-threshold 5 \
    --min-confidence 0.7 \
    --api-key your-key-here
```

## Input Data Format

The pipeline expects a JSON file with the following structure:

```json
{
  "intent_mapper": {
    "primary_secondary": {
      "level": "secondary",
      "name": "Intent Name",
      "description": "Intent description",
      "parent": "primary_intent_id"
    }
  },
  "messages": [
    {
      "message": "Customer message text",
      "intent": {
        "primary": "primary_intent_id",
        "secondary": "secondary_intent_id"
      },
      "conversation_history": ["previous messages..."]
    }
  ],
  "classification_prompt": "System prompt used for classification..."
}
```

## Output

The pipeline generates:

1. **Console Output**: Progress updates and summary
2. **JSON Report** (`intent_expansion_report.json`): Comprehensive report with:
   - Summary statistics
   - Proposed intents with evidence
   - Assessment metrics
   - Recommendations

## Configuration

### Key Parameters

- `--min-threshold`: Minimum messages required to propose new intent (default: 5)
- `--min-confidence`: Minimum confidence score for proposals (default: 0.7)
- `--batch-size`: Messages processed per batch (default: 50)
- `--api-key`: OpenAI API key (or set `OPENAI_API_KEY` env var)

### Guardrails

The pipeline applies multiple guardrails:

1. **Minimum Message Threshold**: Only propose intents with sufficient examples
2. **Confidence Threshold**: Only accept high-confidence proposals
3. **Similarity Check**: Reject proposals too similar to existing intents
4. **Granularity Validation**: Prevent over-clustering (e.g., ingredients/components split)

## Architecture

```
Input Data → Batch Analysis → Pattern Identification → 
LLM Proposals → Guardrails → Assessment → Report
```

See `APPROACH_AND_LEARNING.md` for detailed architecture and design decisions.

## Assessment Metrics

The pipeline includes built-in metrics:

- **Coverage Improvement**: % increase in confidently classified messages
- **Granularity Balance**: Prevents over-clustering
- **Distinctness Scores**: Measures how distinct proposals are
- **Confidence Distribution**: Quality of proposals

## Example Output

```
=== Starting Message Analysis ===
Processing batch 1/4 (50 messages)
Processing batch 2/4 (50 messages)
...

=== Identifying Split Candidates ===
Found 3 potential split candidates

=== Proposing New Intents ===
Analyzing pattern: how to use (15 messages)
  ✓ Proposed: Product Usage (product_usage)

=== Applying Guardrails ===
  ✓ product_usage: Passed all guardrails

=== Calculating Assessment Metrics ===
Overall Quality Score: 0.82
Coverage Improvement: 12.5%

=== Report Generated ===
Saved to: intent_expansion_report.json
```

## Limitations

- Requires OpenAI API key for LLM features (mock mode available for testing)
- Currently optimized for English language
- Keyword-based analysis might miss semantic patterns (mitigated by LLM)

## Troubleshooting

### "LLM not configured" Warning
- Set `OPENAI_API_KEY` environment variable or use `--api-key` flag
- Pipeline will use mock responses for testing

### No Proposals Generated
- Check if messages meet minimum threshold
- Review guardrail logs to see why proposals were rejected
- Consider lowering `--min-threshold` if needed

### Low Confidence Scores
- Review message quality and clarity
- Check if patterns are distinct enough
- Consider refining analysis methodology

## Documentation

- **`APPROACH_AND_LEARNING.md`**: Comprehensive documentation of approach, workflow, and design decisions
- **`intent_expansion_pipeline.py`**: Main pipeline code with detailed docstrings
- **`assessment_metrics.py`**: Metrics calculation module

## License

This is an assignment submission for AI Workflow Analyst Intern position.

## Contact

For questions or issues, please refer to the assignment submission guidelines.

