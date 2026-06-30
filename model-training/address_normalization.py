import difflib

# ==============================================================================
# Address Matching & Normalization Script
# ==============================================================================
# Matches messy, unstructured, typo-ridden user input addresses against an 
# authoritative database using Jaccard Similarity and Levenshtein Distance.
# Ideal for resolving addresses to a standard City/State/Zip database.
# ==============================================================================

# Mock Authoritative Database (e.g., loaded from a SQL database or ResearchGate dataset)
AUTHORITATIVE_DB = [
    "123 Main Street, New York, NY 10001",
    "456 Market Street, San Francisco, CA 94105",
    "789 Hollywood Boulevard, Los Angeles, CA 90028",
    "1011 Broadway, Seattle, WA 98122",
    "1600 Amphitheatre Parkway, Mountain View, CA 94043"
]

def levenshtein_distance(s1, s2):
    """Calculates the Levenshtein distance (edit distance) between two strings."""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)
    
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    
    return previous_row[-1]

def jaccard_similarity(s1, s2):
    """Calculates Jaccard Similarity based on character bigrams or words."""
    set1 = set(s1.lower().split())
    set2 = set(s2.lower().split())
    
    intersection = set1.intersection(set2)
    union = set1.union(set2)
    
    return len(intersection) / len(union) if len(union) > 0 else 0

def match_address(input_address, threshold=0.4):
    """
    Finds the best matching address in the authoritative database.
    Combines Jaccard Similarity and Levenshtein distance for robustness.
    """
    best_match = None
    best_score = 0
    
    for db_address in AUTHORITATIVE_DB:
        # Calculate scores
        j_score = jaccard_similarity(input_address, db_address)
        l_dist = levenshtein_distance(input_address.lower(), db_address.lower())
        
        # Normalize Levenshtein to a 0-1 score
        max_len = max(len(input_address), len(db_address))
        l_score = 1 - (l_dist / max_len) if max_len > 0 else 0
        
        # Combined score (weighted)
        final_score = (0.7 * j_score) + (0.3 * l_score)
        
        if final_score > best_score:
            best_score = final_score
            best_match = db_address
            
    if best_score >= threshold:
        return best_match, best_score
    else:
        return None, best_score

if __name__ == "__main__":
    print("=== Address Matching & Normalization ===")
    
    messy_inputs = [
        "123 Main st, new yrok, ny 10001",
        "1600 Amphitheater Pkwy, Mountain Veiw CA",
        "789 hollywood blvd la ca"
    ]
    
    print(f"Authoritative DB size: {len(AUTHORITATIVE_DB)} records\n")
    
    for messy in messy_inputs:
        print(f"Input: '{messy}'")
        match, score = match_address(messy)
        if match:
            print(f"--> Matched: '{match}' (Confidence: {score:.2f})\n")
        else:
            print(f"--> No match found (Highest score: {score:.2f})\n")
