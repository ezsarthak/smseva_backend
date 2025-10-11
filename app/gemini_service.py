import os
import json
import re
import google.generativeai as genai
from typing import Dict, Any
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv(), override=True)

# Configure Gemini AI
# GEMINI_API_KEY = "AIzaSyDe24c5uX4H9kL6nvjkKbw_5t_DeRiOQCw"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# print("GEMINI_API_KEY:", GEMINI_API_KEY)

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
    except:
        try:
            model = genai.GenerativeModel('gemini-2.5-flash')
        except:
            print("Warning: Could not initialize Gemini model, using fallback mode")
            model = None
else:
    model = None

async def analyze_text(text: str) -> Dict[str, Any]:
    """
    Analyze text using Gemini AI to extract:
    - Category
    - Address
    - Description (basic 2-liner from Gemini)
    - Title
    """
    
    if model is None:
        # Fallback to rule-based approach if Gemini is not available
        return await fallback_analyze_text(text)
    
    try:
        # Prompt for address extraction
        address_prompt = f"Extract the address or location from this municipal issue text: {text}. Output only the address/location, nothing else, no formatting."
        
        # Prompt for title generation
        title_prompt = f"Generate a concise title for this municipal issue: {text}. Output only the title, nothing else, no formatting."
        
        # Prompt for description generation
        description_prompt = f"Write a basic 2-line description for this municipal issue: {text}. Do not write anything else, just the 2 lines of description without any formatting."
        
        # Generate address using Gemini
        address_response = model.generate_content(address_prompt)
        address = address_response.text.strip()
        
        # Generate title using Gemini
        title_response = model.generate_content(title_prompt)
        title = title_response.text.strip()
        
        # Generate description using Gemini
        description_response = model.generate_content(description_prompt)
        description = description_response.text.strip()
        
        # Use fallback for category (keeping the existing logic for now)
        fallback_result = await fallback_analyze_text(text)
        
        # Replace with Gemini outputs
        fallback_result["address"] = address
        fallback_result["title"] = title
        fallback_result["description"] = description
        fallback_result["original_text"] = text
        
        return fallback_result
        
    except Exception as e:
        print(f"Error calling Gemini API: {e}")
        # Fallback to rule-based approach
        return await fallback_analyze_text(text)

async def fallback_analyze_text(text: str) -> Dict[str, Any]:
    """
    Fallback rule-based analysis when Gemini AI is not available
    """
    text_lower = text.lower()
    
    # Determine category based on keywords
    category = "Other"
    
    # Sanitation & Waste
    if any(word in text_lower for word in ["garbage", "कचरा", "waste", "trash", "sanitation", "सफाई", "clean", "dustbin", "डस्टबिन"]):
        category = "Sanitation & Waste"
    
    # Water & Drainage
    elif any(word in text_lower for word in ["water", "पानी", "supply", "tap", "drainage", "नाली", "sewer", "सीवर", "flood", "बाढ़"]):
        category = "Water & Drainage"
    
    # Electricity & Streetlights
    elif any(word in text_lower for word in ["electricity", "बिजली", "power", "light", "streetlight", "स्ट्रीटलाइट", "bulb", "बल्ब", "wire", "तार"]):
        category = "Electricity & Streetlights"
    
    # Roads & Transport
    elif any(word in text_lower for word in ["गड्ढा", "pothole", "road", "street", "गली", "सड़क", "transport", "यातायात", "traffic", "signal", "bus", "बस"]):
        category = "Roads & Transport"
    
    # Public Health & Safety
    elif any(word in text_lower for word in ["health", "स्वास्थ्य", "safety", "सुरक्षा", "hospital", "अस्पताल", "clinic", "क्लिनिक", "medical", "चिकित्सा"]):
        category = "Public Health & Safety"
    
    # Environment & Parks
    elif any(word in text_lower for word in ["park", "पार्क", "garden", "बगीचा", "tree", "पेड़", "environment", "पर्यावरण", "pollution", "प्रदूषण"]):
        category = "Environment & Parks"
    
    # Building & Infrastructure
    elif any(word in text_lower for word in ["building", "भवन", "infrastructure", "बुनियादी ढांचा", "construction", "निर्माण", "bridge", "पुल", "wall", "दीवार"]):
        category = "Building & Infrastructure"
    
    # Taxes & Documentation
    elif any(word in text_lower for word in ["tax", "कर", "document", "दस्तावेज", "certificate", "प्रमाणपत्र", "license", "लाइसेंस", "permit", "अनुमति"]):
        category = "Taxes & Documentation"
    
    # Emergency Services
    elif any(word in text_lower for word in ["emergency", "आपातकाल", "fire", "आग", "police", "पुलिस", "ambulance", "एम्बुलेंस", "rescue", "बचाव"]):
        category = "Emergency Services"
    
    # Animal Care & Control
    elif any(word in text_lower for word in ["animal", "जानवर", "dog", "कुत्ता", "stray", "आवारा", "pet", "पालतू", "veterinary", "पशु चिकित्सा"]):
        category = "Animal Care & Control"
    
    # Extract address
    address = extract_address(text, text_lower)
    
    # Generate title
    title = generate_title(category, text, text_lower, address)
    
    # Basic description
    description = f"Issue reported in {address}. This {category.lower()} problem requires attention from authorities."
    
    return {
        "category": category,
        "address": address,
        "description": description,
        "title": title,
        "original_text": text,
        "urgency_level": "medium"
    }

def extract_address(text: str, text_lower: str) -> str:
    """Extract address information from the text"""
    
    # Look for sector information
    if "सेक्टर" in text or "sector" in text_lower:
        sector_match = re.search(r'(?:सेक्टर|sector)\s*(\d+)', text, re.IGNORECASE)
        if sector_match:
            sector_num = sector_match.group(1)
            return f"Sector {sector_num}"
        else:
            return "Sector Area"
    
    # Look for other address patterns
    elif any(word in text_lower for word in ["street", "गली", "road", "सड़क", "lane", "गली"]):
        return "Street/Road"
    
    elif any(word in text_lower for word in ["park", "पार्क", "garden", "बगीचा"]):
        return "Park/Garden"
    
    elif any(word in text_lower for word in ["market", "बाजार", "shopping", "शॉपिंग"]):
        return "Market Area"
    
    elif any(word in text_lower for word in ["hospital", "अस्पताल", "clinic", "क्लिनिक"]):
        return "Healthcare Facility"
    
    else:
        return "Specified Location"

def generate_title(category: str, original_text: str, text_lower: str, address: str) -> str:
    """Generate simple title based on category and content"""
    
    if "गड्ढा" in original_text or "pothole" in text_lower:
        return f"Pothole in {address}"
    elif "garbage" in text_lower or "कचरा" in original_text:
        return f"Garbage Issue in {address}"
    elif "water" in text_lower or "पानी" in original_text:
        return f"Water Problem in {address}"
    elif "electricity" in text_lower or "बिजली" in original_text:
        return f"Electrical Issue in {address}"
    elif "streetlight" in text_lower or "स्ट्रीटलाइट" in original_text:
        return f"Streetlight Problem in {address}"
    elif "drainage" in text_lower or "नाली" in original_text:
        return f"Drainage Issue in {address}"
    else:
        return f"{category} Issue in {address}"