#imports
import os
import warnings
import logging
from typing import Tuple, Dict
from pypdf import PdfReader
from transformers import pipeline, AutoTokenizer, BitsAndBytesConfig
from accelerate import infer_auto_device_map
from transformers import AutoModelForCausalLM
import torch
import gc
import sys
import csv

# Suppress pypdf warnings about wrong pointing objects
logging.getLogger('pypdf').setLevel(logging.ERROR)
# model setup
# Configure 4-bit quantization
quantization_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_compute_dtype=torch.bfloat16,
    bnb_4bit_use_double_quant=True,
    bnb_4bit_quant_type="nf4"
)

print("Loading model with 4-bit quantization...")
model = AutoModelForCausalLM.from_pretrained(
    "google/gemma-3-1b-it",
    quantization_config=quantization_config,
    device_map="auto",
    low_cpu_mem_usage=True,
    trust_remote_code=True
)

# Verify quantization was applied
print(f"\nModel loaded successfully!")
if torch.cuda.is_available():
    print(f"GPU Memory allocated: {torch.cuda.memory_allocated(0) / 1024**3:.2f} GB")
    print(f"GPU Memory reserved: {torch.cuda.memory_reserved(0) / 1024**3:.2f} GB")

tokenizer = AutoTokenizer.from_pretrained("google/gemma-3-1b-it")

pipe = pipeline(
    "text-generation",
    model=model,
    tokenizer=tokenizer,
    #max_new_tokens=1024,
    batch_size=1,  # Process one at a time to reduce memory
    return_full_text=False,
    do_sample=True,  # Enable sampling instead of greedy decoding
    temperature=0.7,  # Control randomness (0.7 is good balance)
    top_p=0.9,  # Nucleus sampling
    repetition_penalty=1.2,  # Prevent repetitive output
    device_map="auto"
)

# IO functions
def read_document(pdf_path: str) -> str:
    """
    Load and validate a PDF document.
    Args:
        pdf_path: Path to the PDF document
    Returns:
        The text content from the PDF
    Raises:
        FileNotFoundError: If the PDF file does not exist
        ValueError: If the file is not a valid PDF or cannot be read
    """
    # Validate that the file exists
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    # Validate file extension
    if not pdf_path.lower().endswith('.pdf'):
        raise ValueError(f"File is not a PDF: {pdf_path}")

    # Extract text from PDF
    try:
        reader = PdfReader(pdf_path)  # instance
        text = ""
        for page in reader.pages:    
            text += page.extract_text()
        if not text.strip():
            raise ValueError(f"PDF contains no extractable text: {pdf_path}")

    except Exception as e:
        raise ValueError(f"Failed to read first PDF {pdf_path}: {str(e)}")

    return text

    #prints the prompt out
def PrintPrompt(prompt, promptType: str, LLMoutput):
    with open('LLMoutputs.txt', 'a', encoding='utf-8') as f:
        f.write(model.config._name_or_path) #model name
        f.write(f"\n...\n")
        f.write(prompt) # prompt used
        f.write(f"\n...\n")
        f.write(promptType) # prompt type
        f.write(f"\n...\n")
        f.write(str(LLMoutput)) # LLM output
        f.write(f"\n...\n")
        f.flush()  # Ensure data is written immediately
        print(f"print successfull")

import csv
import os

def csvPrompt(filepath: str, row: list[str], header: list[str] = None) -> None:
    """
    Append a single row to a CSV file. Creates the file with a header if it doesn't exist.

    Args:
        filepath: Path to the CSV file.
        row:      List of strings representing the row, e.g. ["item1", "item2"].
        header:   Column names to write on file creation. Omitted if not provided.
    """
    file_exists = os.path.isfile(filepath)

    with open(filepath, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        if not file_exists and header:
            writer.writerow(header)

        writer.writerow(row)

#prompt functions
def zero_shot_prompt(doc: str,  max_chars: int = 100000) -> str:
    """
    Construct a zero-shot prompt to identify key data elements in two input documents.
    
    Args:
        doc1: Text content of the first document
        doc2: Text content of the second document
        max_chars: Maximum characters per document to avoid memory issues (default: 2000)
    
    Returns:
        A string containing the zero-shot prompt for the LLM
    """
    # Truncate documents significantly to avoid OOM errors
    doc_truncated = doc[:max_chars] + ("..." if len(doc) > max_chars else "")
    prompt = f"""You are an expert document analyst. Your task is to analyze two documents and identify key data elements present in each.

    Document 1:
    {doc_truncated}

    Please analyze both documents and identify:
    1. Key data elements (e.g., version numbers, dates, entity names, specifications)
    2. Common elements that appear in both documents
    3. Elements that are unique to each document
    4. Any significant differences in how similar information is presented

    Provide your analysis in a structured format."""
        
    return prompt

def few_shot_prompt(doc: str, max_chars: int = 100000) -> str:
    """
    Construct a few-shot prompt to identify key data elements in two input documents.
    
    Args:
        doc1: Text content of the first document
        doc2: Text content of the second document
        max_chars: Maximum characters per document to avoid memory issues
    
    Returns:
        A string containing the few-shot prompt for the LLM
    """

    # Truncate documents to avoid OOM
    doc_truncated = doc[:max_chars] + ("..." if len(doc) > max_chars else "")

    # Few-shot examples
    example_1 = """
    Example 1:

    Document 1:
    Version: 1.0
    Date: 2023-01-01
    Company: ABC Corp

    Document 2:
    Version: 1.1
    Date: 2023-02-01
    Company: ABC Corp

    Output:
    - Key Data Elements:
    - Version Numbers: 1.0, 1.1
    - Dates: 2023-01-01, 2023-02-01
    - Entity Name: ABC Corp
    - Common Elements:
    - Company: ABC Corp
    - Unique Elements:
    - Document 1: Version 1.0, Date 2023-01-01
    - Document 2: Version 1.1, Date 2023-02-01
    - Differences:
    - Version and date updated in Document 2
    """

    example_2 = """
    Example 2:

    Document 1:
    Product: Router X
    IP: 192.168.1.1
    Protocol: HTTP

    Document 2:
    Product: Router X
    IP: 192.168.1.2
    Protocol: HTTPS

    Output:
    - Key Data Elements:
    - Product Name: Router X
    - IP Addresses: 192.168.1.1, 192.168.1.2
    - Protocols: HTTP, HTTPS
    - Common Elements:
    - Product: Router X
    - Unique Elements:
    - Document 1: IP 192.168.1.1, HTTP
    - Document 2: IP 192.168.1.2, HTTPS
    - Differences:
    - IP address and protocol differ
    """

    # Final prompt
    prompt = f"""You are an expert document analyst. Your task is to analyze the document and identify key data elements.

    Here are some examples:

    {example_1}

    {example_2}

    Now analyze the following:


    {doc_truncated}


    Please provide:
    1. Key data elements
    2. Common elements
    3. Unique elements
    4. Differences

    Return the answer in a structured format similar to the examples above.
    """

    return prompt

def chain_of_thought_prompt(doc: str, max_chars: int = 80000) -> str:
    """
    Construct a chain-of-thought prompt to identify key data elements in a document.

    Args:
        doc: Text content of the document
        max_chars: Maximum characters per document to avoid memory issues

    Returns:
        A string containing the chain-of-thought prompt for the LLM
    """

    # Truncate document to avoid OOM
    doc_truncated = doc[:max_chars] + ("..." if len(doc) > max_chars else "")

    prompt = f"""You are an expert document analyst. Your task is to analyze the document and identify key data elements.

    Think step by step to:
    1. Extract all relevant data elements (e.g., version numbers, dates, entity names, specifications)
    2. Group similar elements together
    3. Identify relationships or patterns among elements
    4. Determine which elements are repeated or unique
    5. Note any inconsistencies or differences in how information is presented

    Document:
    {doc_truncated}

    After reasoning through the document, provide your final answer in the following structured format:

    - Key Data Elements:
    - Common Elements:
    - Unique Elements:
    - Differences:
    """

    return prompt

# Define the nine input combinations



# Test each combination
for i, pdf in enumerate(sys.argv, 0):
    if (i==0):
        continue
    OutputList = [] #then zero, few, chain of thought
    #load the doc
    print(f"\nInput-{i}: {pdf}")
    doc = read_document(sys.argv[i])
    print(f"Successfully loaded document {pdf}")

    #zero shot
    print(f"running zero shot")
    prompt = zero_shot_prompt(doc) # DO THIS SEQUENCALLY
    promptoutput = pipe(prompt)[0]['generated_text'] # make sure to use this! (outputs are actually a dictionary and its silly, but this gets around that)
    print("prompt generated, saving to LLMoutputs.txt")
    OutputList.append(promptoutput) # used for KDE
    
    torch.cuda.empty_cache() #clean up memory (we may need it!)
    gc.collect()

    #fewshot
    print(f"running few shot")
    prompt = few_shot_prompt(doc)
    promptoutput = pipe(prompt)[0]['generated_text']
    print("Prompt generated, saving to LLMoutputs.txt")
    OutputList.append(promptoutput) # used for KDE
    torch.cuda.empty_cache() #clean up memory (we may need it!)
    gc.collect()
    PrintPrompt(prompt, "Few Shot", promptoutput)

    # chain of thought
    print("running chain of thought")
    prompt = chain_of_thought_prompt(doc)
    promptoutput = pipe(prompt)[0]['generated_text']
    print("Prompt generated, saving to LLMoutputs.txt")
    OutputList.append(promptoutput)
    torch.cuda.empty_cache()
    gc.collect()
    PrintPrompt(prompt, "Chain of Thought", promptoutput)
    csvPrompt("temp.csv",OutputList,["Z","F","C"])
print(f"\nAll outputs saved to LLMoutputs.txt")

#TODO: change this to be deterministic
def KDE(prompt: str) -> str:
    """
    Construct a zero-shot prompt to identify key data elements in two input documents.

    Args:
        doc1: Text content of the first document
        doc2: Text content of the second document
        max_chars: Maximum characters per document to avoid memory issues (default: 2000)

    Returns:
        A string containing the zero-shot prompt for the LLM
    """
    # Truncate documents significantly to avoid OOM errors (kept incase needed later)
    # doc1_truncated = doc1[:max_chars] + ("..." if len(doc1) > max_chars else "")
    # doc2_truncated = doc2[:max_chars] + ("..." if len(doc2) > max_chars else "")

    prompt = f"""You are an expert document analyst. Your task is to analyze the prompt given identify key data elements present in it.
    prompt:
    {prompt}

    Please analyze the prompt given and generate a output in yaml format like so:
    element1:
    name:
    requirements: 
    req1
    req2 
    req3 
    """

    return prompt

KDEFolder = "KDEs"
input("waiting to cont")
for PromptType, output in enumerate(OutputList):
    match PromptType:
        case 0: # zero shot
            KDEFilePath = "zero"
        case 1: # few shot
            KDEFilePath = "few"
        case 2: # chain of thought
            KDEFilePath = "chain"
    KDEFilePath = os.path.join(KDEFolder, files[item].replace(".pdf", "") + " "+ KDEFilePath + " KDEs.yaml")
    KDEoutput = pipe(KDE(output))[0]['generated_text']
    with open(KDEFilePath, 'w', encoding='utf-8') as f:
        f.write(str(KDEoutput))
        f.flush()

# Path.unlink("temp.csv")