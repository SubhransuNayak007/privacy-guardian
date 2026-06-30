import os
from gliner import GLiNER
from gliner.training import TrainingArguments, Trainer
import json

def get_synthetic_data():
    """
    Generates a small synthetic dataset for fine-tuning GLiNER on Indian PII.
    In a real scenario, this would be loaded from a JSONL file with thousands of examples.
    """
    return [
        {
            "tokenized_text": ["My", "Aadhaar", "number", "is", "1234", "5678", "9012", "."],
            "ner": [
                [4, 6, "AADHAAR"]  # tokens 1234 5678 9012
            ]
        },
        {
            "tokenized_text": ["Please", "contact", "me", "at", "9876543210", "or", "test@example.com"],
            "ner": [
                [4, 4, "PHONE"],
                [6, 6, "EMAIL"]
            ]
        },
        {
            "tokenized_text": ["The", "PAN", "card", "for", "the", "user", "is", "ABCDE1234F", "."],
            "ner": [
                [7, 7, "PAN"]
            ]
        },
        {
            "tokenized_text": ["Transfer", "funds", "to", "account", "123456789012", "with", "IFSC", "SBIN0001234", "."],
            "ner": [
                [4, 4, "ACCOUNT"],
                [7, 7, "IFSC"]
            ]
        }
    ] * 20 # Duplicate to create a pseudo-batch

def main():
    print("Loading base GLiNER model...")
    # knowledgator/gliner-pii-base-v1.0 is a good base for PII fine-tuning
    model = GLiNER.from_pretrained("knowledgator/gliner-pii-base-v1.0")

    print("Generating synthetic dataset...")
    train_data = get_synthetic_data()

    # GLiNER Training arguments
    # Depending on the GLiNER version, Trainer API differs. This is a conceptual standard usage.
    # To run this successfully, ensure `gliner` is installed in the environment.
    training_args = TrainingArguments(
        output_dir="models/gliner_pii",
        learning_rate=5e-6,
        weight_decay=0.01,
        others_lr=1e-5,
        others_weight_decay=0.01,
        lr_scheduler_type="linear",
        warmup_ratio=0.1,
        per_device_train_batch_size=8,
        num_train_epochs=3,
        save_steps=10,
        save_total_limit=2,
        dataloader_num_workers=0,
        use_cpu=False # Will use GPU if available
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_data,
        eval_dataset=train_data,
        tokenizer=model.data_processor.transformer_tokenizer,
        data_collator=model.data_processor.collate_fn,
    )

    print("Starting training...")
    try:
        trainer.train()
        
        print("Training complete. Saving model...")
        model.save_pretrained("models/gliner_pii")
        print("Model saved to 'models/gliner_pii'")
    except Exception as e:
        print(f"Error during training: {e}")
        print("Note: If 'Trainer' is not natively supported in your GLiNER version, please refer to the GLiNER fine-tuning docs.")

if __name__ == "__main__":
    main()
