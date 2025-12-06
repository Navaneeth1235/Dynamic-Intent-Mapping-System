"""
Example script demonstrating how to use the Intent Expansion Pipeline.
This can be used for testing or as a reference implementation.
"""

import json
import os
from intent_expansion_pipeline import IntentExpansionPipeline


def create_sample_data():
    """Create a sample dataset for testing."""
    sample_data = {
        "intent_mapper": {
            "about_product": {
                "level": "primary",
                "name": "About Product",
                "description": "Customer is asking about product information, features, benefits, or specifications"
            },
            "about_product_product_info": {
                "level": "secondary",
                "name": "Product Info",
                "description": "General product information including benefits, ingredients, specialty, and features",
                "parent": "about_product"
            },
            "recommendation": {
                "level": "primary",
                "name": "Recommendation",
                "description": "Customer is asking for product recommendations based on their needs"
            },
            "order_management": {
                "level": "primary",
                "name": "Order Management",
                "description": "Customer inquiries about orders including status, tracking, cancellation, or refunds"
            },
            "order_management_order_status": {
                "level": "secondary",
                "name": "Order Status",
                "description": "Customer wants to know the current status or tracking information of their order",
                "parent": "order_management"
            }
        },
        "messages": [
            {
                "message": "How do I use this product? What's the recommended dosage?",
                "intent": {"primary": "about_product", "secondary": "about_product_product_info"}
            },
            {
                "message": "How should I apply this cream? How many times a day?",
                "intent": {"primary": "about_product", "secondary": "about_product_product_info"}
            },
            {
                "message": "What's the usage instructions for this supplement?",
                "intent": {"primary": "about_product", "secondary": "about_product_product_info"}
            },
            {
                "message": "Can you tell me about the ingredients in this product?",
                "intent": {"primary": "about_product", "secondary": "about_product_product_info"}
            },
            {
                "message": "What are the benefits of this product?",
                "intent": {"primary": "about_product", "secondary": "about_product_product_info"}
            },
            {
                "message": "How often should I take this?",
                "intent": {"primary": "about_product", "secondary": "about_product_product_info"}
            },
            {
                "message": "What's the status of my order?",
                "intent": {"primary": "order_management", "secondary": "order_management_order_status"}
            },
            {
                "message": "When will my order arrive?",
                "intent": {"primary": "order_management", "secondary": "order_management_order_status"}
            }
        ],
        "classification_prompt": "Classify customer messages into primary and secondary intents."
    }
    
    return sample_data


def main():
    """Run example pipeline."""
    print("=" * 60)
    print("Intent Expansion Pipeline - Example Run")
    print("=" * 60)
    
    # Create sample data file
    sample_data = create_sample_data()
    data_file = "example_input.json"
    
    with open(data_file, 'w', encoding='utf-8') as f:
        json.dump(sample_data, f, indent=2, ensure_ascii=False)
    
    print(f"\nCreated sample data file: {data_file}")
    print(f"  - {len(sample_data['intent_mapper'])} existing intents")
    print(f"  - {len(sample_data['messages'])} messages")
    
    # Configuration
    config = {
        'min_message_threshold': 3,  # Lower for example
        'min_confidence': 0.6,  # Lower for example
        'openai_api_key': os.getenv('OPENAI_API_KEY'),  # Optional
        'llm_model': 'gpt-4o-mini'
    }
    
    print("\nConfiguration:")
    print(f"  - Min message threshold: {config['min_message_threshold']}")
    print(f"  - Min confidence: {config['min_confidence']}")
    print(f"  - LLM model: {config['llm_model']}")
    print(f"  - API key: {'Set' if config['openai_api_key'] else 'Not set (using mock)'}")
    
    # Initialize pipeline
    print("\n" + "=" * 60)
    pipeline = IntentExpansionPipeline(config)
    
    # Run pipeline
    try:
        proposals, report = pipeline.run(data_file, batch_size=10)
        
        # Display results
        print("\n" + "=" * 60)
        print("RESULTS SUMMARY")
        print("=" * 60)
        
        print(f"\nTotal Proposals Generated: {len(proposals)}")
        
        if proposals:
            print("\nProposed Intents:")
            for i, prop in enumerate(proposals, 1):
                print(f"\n{i}. {prop.name} ({prop.id})")
                print(f"   Level: {prop.level}")
                print(f"   Description: {prop.description}")
                print(f"   Confidence: {prop.confidence_score:.2f}")
                print(f"   Message Count: {prop.quantitative_evidence.get('message_count', 0)}")
                print(f"   Rationale: {prop.rationale[:100]}...")
        else:
            print("\nNo proposals generated. This could be because:")
            print("  - Patterns don't meet minimum thresholds")
            print("  - All proposals were filtered by guardrails")
            print("  - LLM determined no new intents are needed")
        
        # Display report summary
        if 'assessment' in report:
            assessment = report['assessment']
            print("\n" + "=" * 60)
            print("ASSESSMENT METRICS")
            print("=" * 60)
            print(f"Overall Quality Score: {assessment['overall_quality_score']:.2f}")
            print(f"Coverage Improvement: {assessment['coverage_metrics']['coverage_improvement']:.1f}%")
            print(f"Granularity Balance: {assessment['granularity_metrics']['balance_score']:.2f}")
            
            if assessment['recommendations']:
                print("\nRecommendations:")
                for rec in assessment['recommendations']:
                    print(f"  - {rec}")
        
        print("\n" + "=" * 60)
        print("Full report saved to: intent_expansion_report.json")
        print("=" * 60)
        
    except Exception as e:
        print(f"\nError running pipeline: {e}")
        import traceback
        traceback.print_exc()
    
    # Cleanup
    if os.path.exists(data_file):
        print(f"\nCleaning up: {data_file}")
        # Uncomment to auto-delete: os.remove(data_file)


if __name__ == "__main__":
    main()

