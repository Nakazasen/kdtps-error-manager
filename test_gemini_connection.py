# Test script to diagnose Gemini API SSL issues
# Usage: python test_gemini_connection.py YOUR_API_KEY
import ssl
import sys

print("="*50)
print("GEMINI API CONNECTION DIAGNOSTIC")
print("="*50)

# Step 1: Get API Key from command line
if len(sys.argv) < 2:
    print("[FAIL] Usage: python test_gemini_connection.py YOUR_API_KEY")
    sys.exit(1)

api_key = sys.argv[1]
print("[1] API Key provided (ends with: ...{})".format(api_key[-4:]))

# Step 2: Check Python version & SSL version
print("[2] Python Version:", sys.version.split()[0])
print("[3] SSL Version:", ssl.OPENSSL_VERSION)

# Step 3: Try import google-genai
print("\n[4] Checking google-genai import...")
try:
    from google import genai
    print("    [OK] google-genai (NEW SDK) imported")
    SDK_TYPE = "NEW"
except ImportError as e:
    print("    [WARN] google-genai not found, trying google.generativeai...")
    try:
        import google.generativeai as genai
        print("    [OK] google.generativeai (OLD SDK) imported")
        SDK_TYPE = "OLD"
    except ImportError as e2:
        print("    [FAIL] Both imports failed:", e2)
        sys.exit(1)

# Step 4: Test Connection WITHOUT SSL Patch first
model_id = "gemini-2.5-flash"  # Correct model name
print("\n[5] Testing Connection WITHOUT SSL Patch...")
print("    Model:", model_id)

if SDK_TYPE == "NEW":
    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=model_id,
            contents="Say hello"
        )
        print("    [OK] SUCCESS! Response:", response.text[:80])
    except Exception as e:
        print("    [FAIL] Error:", type(e).__name__)
        print("    Message:", str(e)[:300])
else:
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_id)
        response = model.generate_content("Say hello")
        print("    [OK] SUCCESS! Response:", response.text[:80])
    except Exception as e:
        print("    [FAIL] Error:", type(e).__name__)
        print("    Message:", str(e)[:300])

# Step 5: Test WITH SSL Patch
print("\n[6] Testing Connection WITH SSL Patch...")
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    print("    [SKIP] SSL patch not available on this Python version")
else:
    ssl._create_default_https_context = _create_unverified_https_context
    ssl.create_default_context = _create_unverified_https_context
    print("    SSL Patch applied")
    
    if SDK_TYPE == "NEW":
        try:
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model=model_id,
                contents="Say hello"
            )
            print("    [OK] SUCCESS with patch! Response:", response.text[:80])
        except Exception as e:
            print("    [FAIL] Still failing with patch:", type(e).__name__)
            print("    Message:", str(e)[:300])

print("\n" + "="*50)
print("DIAGNOSTIC COMPLETE")
print("="*50)
