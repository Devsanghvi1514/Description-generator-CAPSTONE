import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import torch
from PIL import Image, ImageDraw
from transformers import AutoProcessor, AutoModelForCausalLM

proc = AutoProcessor.from_pretrained('microsoft/Florence-2-base', trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained('microsoft/Florence-2-base', trust_remote_code=True)

img = Image.new('RGB', (400, 300), color='white')
draw = ImageDraw.Draw(img)
draw.ellipse([100, 100, 200, 200], fill='green')

queries = [
    'What color is the circle?',
    '<VQA>What color is the circle?',
    '<DocVQA>What color is the circle?',
]

for q in queries:
    inp = proc(text=q, images=img, return_tensors='pt')
    out = model.generate(**inp, max_new_tokens=40)
    print(q, "-->", repr(proc.batch_decode(out, skip_special_tokens=True)[0]))
