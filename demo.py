from transformers import pipeline
import torch
from pypdf import PdfReader

pipe     = pipeline("text-generation", model="google/gemma-3-1b-it", device="cpu", dtype=torch.bfloat16)
pdfFile  = "PDFS/cis-r1.pdf" 

# Extract text from PDF
pdf_reader = PdfReader(pdfFile)
pdf_text = ""
for page in pdf_reader.pages:
    pdf_text += page.extract_text()

messages = [
    [
        {
            "role": "system",
            "content": [{"type": "text", "text": "You are a helpful document analyzer."},]
        },
        {
            "role": "user",
            "content": [{"type": "text", "text": "Please summarize the following document:\n\n" + pdf_text},]

        },
    ],
]

output = pipe(messages, max_new_tokens=50)
print("="*25)
print(output[0][0]['generated_text'][-1]['content'])
print("="*25)
print("Full output")
print(output)
print("="*25)
# model="google/gemma-3-1b-it",  
# device="cpu",  
# torch_dtype=torch.bfloat16  