
import requests
import os

token = "hf_..." # User token is in registry, but I don't have it here. 
# I will use a placeholder or try without token (likely fail or limited)
# Actually I need the token. I can read it from the log? No, security.
# I can try to use a public model without token? Most require token now.

# I will assume the token is valid since we got 410/404 (Authenticated) rather than 401.

models_to_test = [
    "openai/clip-vit-base-patch32",
    "openai/clip-vit-large-patch14",
    "laion/CLIP-ViT-B-32-laion2B-s34B-b79K"
]

urls_to_test = [
    "https://api-inference.huggingface.co/models/{}",
    "https://router.huggingface.co/hf-inference/models/{}",
    "https://router.huggingface.co/models/{}"
]

print("Testing Model Availability...")
# I cannot really test without constraints, but I can check if 404/410 persists.
# I'll just skip the script and trust the 410/404 signals.
