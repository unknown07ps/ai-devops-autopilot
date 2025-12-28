import httpx
import json

print("Testing Ollama connection with llama3:latest...")

try:
    # First check if Ollama is responding
    tags_response = httpx.get("http://localhost:11434/api/tags", timeout=5)
    print(f"\n✅ Ollama API is reachable")
    print(f"Available models: {tags_response.json()}")
    
    # Now test generation
    response = httpx.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "llama3:latest",
            "prompt": "You are an SRE. API latency spiked from 100ms to 1000ms. What's the likely cause? Reply in JSON: {\"cause\": \"...\", \"action\": \"...\"}",
            "stream": False,
            "format": "json"
        },
        timeout=60
    )
    
    if response.status_code == 200:
        result = response.json()
        print("\n✅ Ollama generation working!")
        
        if 'response' in result:
            print(f"\nModel response:\n{result['response']}")
            
            # Try to parse as JSON
            try:
                parsed = json.loads(result['response'])
                print(f"\n✅ JSON parsing successful:")
                print(json.dumps(parsed, indent=2))
            except:
                print("\n⚠️ Response is not valid JSON, but that's okay for testing")
        else:
            print(f"\nResponse keys: {list(result.keys())}")
            print(f"Full response: {json.dumps(result, indent=2)}")
    else:
        print(f"\n❌ HTTP Error: {response.status_code}")
        print(response.text)
    
except httpx.ConnectError:
    print("\n❌ Cannot connect to Ollama!")
    print("Make sure Ollama is running. Try: ollama serve")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()