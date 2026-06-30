import random
import csv
from faker import Faker

# ==============================================================================
# Synthetic PII Data Generator (India / Aadhaar Focus)
# ==============================================================================
# Generates thousands of synthetic training samples for NLP / NER pipelines.
# Specifically generates localized Indian names, mobile numbers, and Aadhaar cards.
# ==============================================================================

fake = Faker("en_IN")  # Generates Indian-specific localized names/phones

def generate_pii_sentence():
    name = fake.name()
    dob = fake.date_of_birth(minimum_age=18, maximum_age=70).strftime("%d/%m/%Y")
    
    # Generate an Indian mobile number (+91 optionally followed by 10 digits starting with 6-9)
    mobile = f"+91 {random.randint(6, 9)}{random.randint(1000, 9999)} {random.randint(10000, 9999)}"

    # Generate a random Aadhaar format (must not start with 0 or 1, so 2-9)
    aadhaar = f"{random.randint(2000, 9999)} {random.randint(1000, 9999)} {random.randint(1000, 9999)}"

    templates = [
        f"User {name} born on {dob} holds Aadhaar number {aadhaar}. Contact at {mobile}.",
        f"Verification failed for Aadhaar {aadhaar}. DOB: {dob}. Mobile number provided: {mobile}.",
        f"Please update the mobile {mobile} for account linked to ID {aadhaar}.",
        f"Name: {name}, Aadhaar: {aadhaar}, Phone: {mobile}, Birth Date: {dob}",
        f"The applicant {name} (DOB: {dob}) submitted Aadhaar card {aadhaar} and can be reached at {mobile}."
    ]
    return random.choice(templates), name, dob, aadhaar, mobile

def create_synthetic_dataset(num_samples=1000, output_file="synthetic_pii_dataset.csv"):
    """Generates a CSV file containing synthetic PII sentences and their extracted entities."""
    print(f"Generating {num_samples} synthetic PII records...")
    
    with open(output_file, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["sentence", "extracted_name", "extracted_dob", "extracted_aadhaar", "extracted_mobile"])
        
        for _ in range(num_samples):
            sentence, name, dob, aadhaar, mobile = generate_pii_sentence()
            writer.writerow([sentence, name, dob, aadhaar, mobile])
            
    print(f"Dataset successfully saved to {output_file}")

if __name__ == "__main__":
    # Generate 10 sample training rows to console
    print("=== Sample Synthetic PII ===")
    for _ in range(10):
        sentence, _, _, _, _ = generate_pii_sentence()
        print("-", sentence)
        
    print("\n")
    # Generate full dataset
    create_synthetic_dataset(num_samples=5000, output_file="./datasets/address-ner/synthetic_pii.csv")
