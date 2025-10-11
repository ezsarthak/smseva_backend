import requests
import json

# API base URL
BASE_URL = "http://localhost:8000"

def test_specific_issue():
    """Test the specific issue from user"""
    
    print("🐛 Debugging Specific Issue")
    print("=" * 60)
    
    # Test Case 1: First user - Shyam
    print("\n1️⃣ Test Case 1: Shyam reports light issue")
    test_data_1 = {
        "text": "मेरा नाम है shyam, light की समस्या है, vijay nagar में",
        "email": "shyam@example.com",
        "name": "shyam",
        "location": {
            "latitude": 87479.586316,
            "longitude": 55784.779812
        }
    }
    
    response = requests.post(f"{BASE_URL}/submit-issue", json=test_data_1)
    print(f"First submission - Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"Ticket ID: {result['ticket_id']}")
        print(f"Category: {result['category']}")
        print(f"Issue Count: {result['issue_count']}")
        print(f"Users: {result['users']}")
    else:
        print(f"Error: {response.text}")
    
    # Test Case 2: Second user - Monu
    print("\n2️⃣ Test Case 2: Monu reports similar light issue")
    test_data_2 = {
        "text": "मेरा नाम है monu, light की समस्या है, vijay nagar में",
        "email": "monu@example.com",
        "name": "monu",
        "location": {
            "latitude": 87479.586315,
            "longitude": 55784.779812
        }
    }
    
    response = requests.post(f"{BASE_URL}/submit-issue", json=test_data_2)
    print(f"Second submission - Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"Ticket ID: {result['ticket_id']}")
        print(f"Category: {result['category']}")
        print(f"Issue Count: {result['issue_count']}")
        print(f"Users: {result['users']}")
    else:
        print(f"Error: {response.text}")
    
    # Get all issues
    print("\n📊 Final Summary:")
    response = requests.get(f"{BASE_URL}/issues")
    if response.status_code == 200:
        issues = response.json()
        print(f"Total issues: {len(issues)}")
        for issue in issues:
            print(f"- {issue['ticket_id']}: {issue['category']} in {issue['address']} (Count: {issue['issue_count']}, Users: {issue['users']})")
    
    # Test text similarity manually
    print("\n🔤 Manual Text Similarity Check:")
    text1 = "मेरा नाम है shyam, light की समस्या है, vijay nagar में"
    text2 = "मेरा नाम है monu, light की समस्या है, vijay nagar में"
    
    from difflib import SequenceMatcher
    import re
    
    text1_clean = re.sub(r'[^\w\s]', '', text1.lower().strip())
    text2_clean = re.sub(r'[^\w\s]', '', text2.lower().strip())
    
    similarity = SequenceMatcher(None, text1_clean, text2_clean).ratio()
    print(f"Text 1 (clean): {text1_clean}")
    print(f"Text 2 (clean): {text2_clean}")
    print(f"Similarity: {similarity:.2f}")
    
    # Test keyword extraction
    print("\n🔤 Keyword Extraction:")
    common_words = {'मेरा', 'नाम', 'है', 'में', 'की', 'का', 'के', 'और', 'या', 'पर', 'से', 'तक', 'दूर', 'पास'}
    
    words1 = re.findall(r'\w+', text1.lower())
    keywords1 = [word for word in words1 if word not in common_words and len(word) > 2]
    
    words2 = re.findall(r'\w+', text2.lower())
    keywords2 = [word for word in words2 if word not in common_words and len(word) > 2]
    
    print(f"Keywords 1: {keywords1}")
    print(f"Keywords 2: {keywords2}")
    
    common_keywords = set(keywords1) & set(keywords2)
    keyword_similarity = len(common_keywords) / max(len(keywords1), len(keywords2))
    print(f"Common keywords: {common_keywords}")
    print(f"Keyword similarity: {keyword_similarity:.2f}")

if __name__ == "__main__":
    test_specific_issue()
