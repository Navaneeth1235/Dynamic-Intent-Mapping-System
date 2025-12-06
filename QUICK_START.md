# Quick Start Guide

## Installation

```bash
pip install -r requirements.txt
```

## Basic Usage

```bash
python intent_expansion_pipeline.py --data inputs_for_assignment.json
```

## With Custom Parameters

```bash
python intent_expansion_pipeline.py \
    --data inputs_for_assignment.json \
    --batch-size 50 \
    --min-threshold 5 \
    --min-confidence 0.7 \
    --api-key your-openai-api-key
```

## Using Environment Variable for API Key

```bash
export OPENAI_API_KEY="your-api-key-here"
python intent_expansion_pipeline.py --data inputs_for_assignment.json
```

## Testing Without API Key

The pipeline will run in mock mode (no LLM calls) for testing:

```bash
python intent_expansion_pipeline.py --data inputs_for_assignment.json
```

## Running Example

```bash
python run_example.py
```

## Output Files

- `intent_expansion_report.json`: Comprehensive report with proposals and metrics

## Key Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--min-threshold` | 5 | Minimum messages needed to propose new intent |
| `--min-confidence` | 0.7 | Minimum confidence score for proposals |
| `--batch-size` | 50 | Messages processed per batch |
| `--api-key` | None | OpenAI API key (or use env var) |

## Understanding Output

### Console Output
- Progress updates for each batch
- Pattern identification results
- Proposal generation status
- Guardrail filtering results
- Assessment metrics summary

### JSON Report
- `summary`: Overall statistics
- `proposals`: List of proposed intents with evidence
- `assessment`: Quality metrics and recommendations
- `methodology`: Configuration used

## Troubleshooting

**"LLM not configured"**: Set `OPENAI_API_KEY` or use `--api-key`

**No proposals generated**: 
- Check if messages meet minimum threshold
- Review guardrail logs
- Consider lowering `--min-threshold`

**Low confidence scores**:
- Review message quality
- Check pattern distinctness
- Consider refining analysis

## Next Steps

1. Review `APPROACH_AND_LEARNING.md` for detailed documentation
2. Check `example_data_structure.json` for input format
3. Run `run_example.py` to see pipeline in action
4. Customize parameters based on your data

