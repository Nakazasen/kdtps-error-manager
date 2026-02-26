
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))

def test_translation():
    print("Testing Translation...")
    try:
        from core.translator import translate_text
        res = translate_text("Hello", "vi")
        print(f"Translation Result: {res}")
        if res:
            print("Translation OK")
        else:
            print("Translation Failed (None)")
    except Exception as e:
        print(f"Translation Error: {e}")

if __name__ == "__main__":
    test_translation()
