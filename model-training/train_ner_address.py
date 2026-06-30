import os
import json
import torch
from transformers import AutoTokenizer, AutoModelForTokenClassification, Trainer, TrainingArguments
from datasets import Dataset, DatasetDict

# ==============================================================================
# NLP/NER Training Script for Address Detection in Text
# ==============================================================================
# This script fine-tunes a BERT-based model for Token Classification using BIO 
# tagging (B-STREET, I-STREET, B-CITY, I-CITY, B-ZIP, O).
# You can use datasets like the Kaggle Delivery Address Dataset.
# ==============================================================================

DATASET_FILE = "./datasets/address-ner/train_bio.json"
MODEL_NAME = "bert-base-uncased"
OUTPUT_DIR = "./address_ner_model"

# Define the label mapping
label_list = [
    "O", "B-STREET", "I-STREET", "B-CITY", "I-CITY", 
    "B-STATE", "I-STATE", "B-ZIP", "I-ZIP", "B-COUNTRY", "I-COUNTRY"
]
label2id = {label: i for i, label in enumerate(label_list)}
id2label = {i: label for i, label in enumerate(label_list)}

def load_bio_dataset(filepath):
    """
    Loads a BIO-tagged dataset from a JSON file.
    Expected format:
    [
        {"tokens": ["123", "Main", "St", "New", "York", "NY", "10001"], 
         "ner_tags": ["B-STREET", "I-STREET", "I-STREET", "B-CITY", "I-CITY", "B-STATE", "B-ZIP"]}
    ]
    """
    if not os.path.exists(filepath):
        print(f"Dataset not found at {filepath}. Please add your Kaggle dataset.")
        # Return dummy data for demonstration
        return Dataset.from_dict({
            "tokens": [["123", "Main", "St", "New", "York"]],
            "ner_tags": [[label2id["B-STREET"], label2id["I-STREET"], label2id["I-STREET"], label2id["B-CITY"], label2id["I-CITY"]]]
        })
        
    with open(filepath, "r") as f:
        data = json.load(f)
        
    tokens = [item["tokens"] for item in data]
    ner_tags = [[label2id[tag] for tag in item["ner_tags"]] for item in data]
    
    return Dataset.from_dict({"tokens": tokens, "ner_tags": ner_tags})

def tokenize_and_align_labels(examples, tokenizer):
    tokenized_inputs = tokenizer(examples["tokens"], truncation=True, is_split_into_words=True)
    labels = []
    
    for i, label in enumerate(examples["ner_tags"]):
        word_ids = tokenized_inputs.word_ids(batch_index=i)
        previous_word_idx = None
        label_ids = []
        for word_idx in word_ids:
            if word_idx is None:
                label_ids.append(-100)
            elif word_idx != previous_word_idx:
                label_ids.append(label[word_idx])
            else:
                label_ids.append(-100)
            previous_word_idx = word_idx
        labels.append(label_ids)
        
    tokenized_inputs["labels"] = labels
    return tokenized_inputs

def train_ner():
    print("Loading Tokenizer and Model...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForTokenClassification.from_pretrained(
        MODEL_NAME, 
        num_labels=len(label_list),
        id2label=id2label,
        label2id=label2id
    )

    print("Loading Dataset...")
    raw_dataset = load_bio_dataset(DATASET_FILE)
    tokenized_dataset = raw_dataset.map(lambda x: tokenize_and_align_labels(x, tokenizer), batched=True)
    
    # Split into train/test
    split_dataset = tokenized_dataset.train_test_split(test_size=0.1)
    dataset = DatasetDict({
        "train": split_dataset["train"],
        "test": split_dataset["test"]
    })

    print("Configuring Training Arguments...")
    training_args = TrainingArguments(
        output_dir=OUTPUT_DIR,
        evaluation_strategy="epoch",
        learning_rate=2e-5,
        per_device_train_batch_size=16,
        per_device_eval_batch_size=16,
        num_train_epochs=5,
        weight_decay=0.01,
        save_strategy="epoch",
        load_best_model_at_end=True,
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=dataset["train"],
        eval_dataset=dataset["test"],
        tokenizer=tokenizer,
    )

    print("Starting Training...")
    # Uncomment to train
    # trainer.train()
    
    # print("Saving Model...")
    # trainer.save_model(OUTPUT_DIR)
    print("Training pipeline ready! Add your Kaggle dataset and uncomment `trainer.train()` to begin.")

if __name__ == "__main__":
    print("=== Address NER (BIO Tags) Training Pipeline ===")
    train_ner()
