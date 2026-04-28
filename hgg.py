from huggingface_hub import InferenceClient

# Initialize client with your token
client = InferenceClient(token="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")

# Call the model (replace with your desired Gemma version)
response = client.chat_completion(
    model="google/gemma-2-9b-it",
    messages=[{"role": "user", "content": "What is the capital of France?"}],
    max_tokens=500,
)

print(response.choices[0].message.content)
