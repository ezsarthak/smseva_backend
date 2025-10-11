import google.generativeai as genai

genai.configure(api_key="AIzaSyDe24c5uX4H9kL6nvjkKbw_5t_DeRiOQCw")
model = genai.GenerativeModel("gemini-2.5-flash")
response = model.generate_content("Hello Gemini")
print(response.text)