import torch
from datasets import load_dataset
from transformers import AutoProcessor, AutoModelForCausalLM, TrainingArguments, Trainer
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training

def main():
    model_id = "microsoft/Florence-2-base"
    print(f"Loading {model_id} in 4-bit precision for QLoRA...")
    
    # AutoProcessor handles both Image and Text inputs
    processor = AutoProcessor.from_pretrained(model_id, trust_remote_code=True)
    
    # Load model with 4-bit quantization (requires bitsandbytes)
    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        trust_remote_code=True,
        device_map="auto",
        load_in_4bit=True
    )
    
    # Prepare model for QLoRA
    model = prepare_model_for_kbit_training(model)
    
    # Define LoRA Config targeting the attention layers
    config = LoraConfig(
        r=16,
        lora_alpha=32,
        target_modules=["q_proj", "v_proj"], 
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM"
    )
    
    model = get_peft_model(model, config)
    model.print_trainable_parameters()
    
    print("Loading prepared JSONL dataset...")
    # NOTE: You must point this to the merged qlora_train.jsonl file
    try:
        dataset = load_dataset("json", data_files="datasets/qlora_train.jsonl", split="train")
    except Exception as e:
        print(f"Dataset load failed: {e}. Make sure you run prepare_qlora_data.py first.")
        return
        
    # Standard QLoRA Training Arguments
    training_args = TrainingArguments(
        output_dir="./qlora-florence2-address",
        per_device_train_batch_size=2,
        gradient_accumulation_steps=4,
        learning_rate=2e-4,
        num_train_epochs=3,
        logging_steps=10,
        save_steps=100,
        optim="paged_adamw_8bit", # 8-bit optimizer to save memory
        fp16=True,                # Mixed precision
        remove_unused_columns=False,
    )
    
    # Initialize the Hugging Face Trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=dataset,
        # Note: A production script requires a custom DataCollator to pass images through `processor`
    )
    
    print("Starting QLoRA fine-tuning...")
    trainer.train()
    
    print("Saving final LoRA adapter weights...")
    model.save_pretrained("./final_qlora_adapter")
    print("Training complete! You can now load this adapter on top of the base model.")

if __name__ == "__main__":
    main()
