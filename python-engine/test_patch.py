import sys
import re

# We will just import main and test the functions
sys.path.append('.')
import main

def test_verhoeff():
    # 1. 12-digit passing Aadhaar (This is a sample mathematically valid verhoeff number, e.g. 123456789012, let's see if it's valid)
    # wait, 123456789012 is usually not valid. Let's find one that is valid, or just rely on the test passing/failing.
    # 999999999999 is definitely false.
    assert main.is_valid_aadhaar_verhoeff("999999999999") == False
    
    # 000000000000 passes Verhoeff
    assert main.is_valid_aadhaar_verhoeff("000000000000") == True

    print("Verhoeff test passed")

if __name__ == "__main__":
    test_verhoeff()
    print("main.py imported successfully, syntax is OK.")
