#imports
import os
import logging
from pathlib import Path
from typing import Dict, List, Tuple
from pypdf import PdfReader
from transformers import pipeline, AutoTokenizer, BitsAndBytesConfig
from transformers import AutoModelForCausalLM
import torch
import gc
import sys
import csv
import yaml
import requests

MAXPDF_LENGTH = 40000

try:
    from huggingface_hub import InferenceClient
except Exception:
    InferenceClient = None

# Suppress pypdf warnings about wrong pointing objects
logging.getLogger('pypdf').setLevel(logging.ERROR)
MODEL_ID = "google/gemma-3-1b-it"
USE_REMOTE_GEMMA = os.getenv("USE_REMOTE_GEMMA", "0") == "1"
HF_TOKEN = os.getenv("HF_TOKEN") or os.getenv("HUGGING_FACE_HUB_TOKEN")
ALLOW_CPU_LOCAL_GEMMA = os.getenv("ALLOW_CPU_LOCAL_GEMMA", "0") == "1"
REMOTE_MODEL_IDS = [
    model_id.strip()
    for model_id in os.getenv(
        "HF_REMOTE_MODEL_IDS",
        f"{MODEL_ID},Qwen/Qwen2.5-3B-Instruct,Qwen/Qwen2.5-1.5B-Instruct,mistralai/Mistral-7B-Instruct-v0.3",
    ).split(",")
    if model_id.strip()
]


def load_model() -> tuple[AutoModelForCausalLM, dict]:
    """Load Gemma-3-1B with a GPU-quantized path and a CPU fallback path."""
    # Configure 4-bit quantization for GPU environments.
    quantization_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
    )

    if torch.cuda.is_available():
        try:
            print("Loading model with 4-bit quantization...")
            quantized_model = AutoModelForCausalLM.from_pretrained(
                MODEL_ID,
                quantization_config=quantization_config,
                device_map="auto",
                low_cpu_mem_usage=True,
                trust_remote_code=True,
            )
            return quantized_model, {"device_map": "auto"}
        except Exception as exc:
            print(f"4-bit GPU load failed, trying 4-bit CPU fallback: {exc}")

    try:
        print("Loading model with 4-bit quantization on CPU...")
        cpu_quantized_model = AutoModelForCausalLM.from_pretrained(
            MODEL_ID,
            quantization_config=quantization_config,
            device_map={"": "cpu"},
            low_cpu_mem_usage=True,
            trust_remote_code=True,
        )
        return cpu_quantized_model, {"device": -1}
    except Exception as exc:
        raise RuntimeError(
            "Unable to load google/gemma-3-1b-it in this environment. "
            f"Tried 4-bit GPU and 4-bit CPU paths. Last error: {exc}"
        )


pipe = None
model_name_for_logs = MODEL_ID
remote_client = None
active_remote_model_id = MODEL_ID


def _is_model_not_supported_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return "model_not_supported" in text or "not supported by any provider" in text


def initialize_generation_backend() -> None:
    """Initialize generation backend with local-first strategy and remote fallback."""
    global pipe, remote_client, active_remote_model_id

    def setup_remote() -> bool:
        global remote_client
        if InferenceClient is None or not HF_TOKEN:
            return False
        # Use provider auto-routing. Forcing hf-inference fails for some models.
        remote_client = InferenceClient(token=HF_TOKEN)
        print("Using remote Hugging Face inference.")
        return True

    if USE_REMOTE_GEMMA:
        if not setup_remote():
            raise RuntimeError(
                "USE_REMOTE_GEMMA=1 requires huggingface_hub InferenceClient and "
                "HF_TOKEN or HUGGING_FACE_HUB_TOKEN."
            )
        return

    # On CPU-only hosts, remote inference is more stable when credentials are available.
    if not torch.cuda.is_available() and setup_remote():
        print("Auto-selected remote inference because no CUDA GPU is available.")
        return

    # Prevent repeated host-level termination on CPU-only environments unless explicitly overridden.
    if not torch.cuda.is_available() and not ALLOW_CPU_LOCAL_GEMMA:
        print(
            "No CUDA GPU detected and remote credentials were not found. "
            "Proceeding without a generation backend; deterministic fallback KDE output will be used."
        )
        return

    try:
        model, pipeline_device_args = load_model()

        print("\nModel loaded successfully!")
        if torch.cuda.is_available():
            print(f"GPU Memory allocated: {torch.cuda.memory_allocated(0) / 1024**3:.2f} GB")
            print(f"GPU Memory reserved: {torch.cuda.memory_reserved(0) / 1024**3:.2f} GB")

        tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)

        model.generation_config.do_sample = False
        model.generation_config.repetition_penalty = 1.1
        model.generation_config.max_new_tokens = 96
        model.generation_config.max_length = None

        pipe = pipeline(
            "text-generation",
            model=model,
            tokenizer=tokenizer,
            batch_size=1,
            return_full_text=False,
            **pipeline_device_args,
        )
    except Exception as exc:
        print(f"Local Gemma load failed: {exc}")
        if setup_remote():
            print("Fell back to remote inference automatically.")
            return
        raise RuntimeError(
            "Local Gemma load failed and automatic remote fallback was unavailable. "
            "Set HF_TOKEN (or HUGGING_FACE_HUB_TOKEN) and rerun, or set USE_REMOTE_GEMMA=1."
        )


initialize_generation_backend()


def generate_text(prompt_text: str) -> str:
    """Generate text with Gemma-3-1B via local pipeline or remote inference."""
    global model_name_for_logs, active_remote_model_id

    if remote_client is not None:
        remote_errors: List[str] = []
        for model_id in REMOTE_MODEL_IDS:
            # Route 0: InferenceClient text-generation API.
            try:
                generated = remote_client.text_generation(
                    model=model_id,
                    prompt=prompt_text,
                    max_new_tokens=96,
                    do_sample=False,
                    return_full_text=False,
                )
                active_remote_model_id = model_id
                model_name_for_logs = model_id
                return generated
            except Exception as exc:
                remote_errors.append(f"[{model_id}] InferenceClient.text_generation failed: {exc}")
                print(f"InferenceClient text_generation failed for {model_id}, trying chat-completions fallback: {exc}")

            # Fallback 1: Hugging Face client chat-completions API.
            try:
                chat_completion = remote_client.chat.completions.create(
                    model=model_id,
                    messages=[{"role": "user", "content": prompt_text}],
                    max_tokens=96,
                    temperature=0.0,
                )
                if chat_completion and getattr(chat_completion, "choices", None):
                    message = chat_completion.choices[0].message
                    content = getattr(message, "content", None)
                    if isinstance(content, str) and content.strip():
                        active_remote_model_id = model_id
                        model_name_for_logs = model_id
                        return content
            except Exception as exc:
                remote_errors.append(f"[{model_id}] InferenceClient.chat.completions.create failed: {exc}")
                print(f"InferenceClient chat-completions failed for {model_id}, trying router HTTP fallback: {exc}")

            # Fallback 2: Hugging Face router OpenAI-compatible chat completions over HTTP.
            headers = {
                "Authorization": f"Bearer {HF_TOKEN}",
                "Content-Type": "application/json",
            }
            chat_payload = {
                "model": model_id,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt_text,
                    }
                ],
                "max_tokens": 96,
                "temperature": 0.0,
                "stream": False,
            }
            chat_url = "https://router.huggingface.co/v1/chat/completions"
            try:
                chat_response = requests.post(chat_url, headers=headers, json=chat_payload, timeout=120)
                if chat_response.ok:
                    chat_body = chat_response.json()
                    choices = chat_body.get("choices") if isinstance(chat_body, dict) else None
                    if isinstance(choices, list) and choices:
                        message = choices[0].get("message", {})
                        content = message.get("content")
                        if isinstance(content, str) and content.strip():
                            active_remote_model_id = model_id
                            model_name_for_logs = model_id
                            return content
                    remote_errors.append(f"[{model_id}] Router HTTP returned unexpected body: {chat_body}")
                else:
                    remote_errors.append(
                        f"[{model_id}] Router HTTP chat-completions failed "
                        f"{chat_response.status_code}: {chat_response.text[:400]}"
                    )
            except Exception as exc:
                remote_errors.append(f"[{model_id}] Router HTTP chat-completions exception: {exc}")

            # Fallback 3: Router HTTP OpenAI-compatible completions for non-chat models.
            completion_payload = {
                "model": model_id,
                "prompt": prompt_text,
                "max_tokens": 96,
                "temperature": 0.0,
                "stream": False,
            }
            completion_url = "https://router.huggingface.co/v1/completions"
            try:
                completion_response = requests.post(
                    completion_url,
                    headers=headers,
                    json=completion_payload,
                    timeout=120,
                )
                if completion_response.ok:
                    completion_body = completion_response.json()
                    choices = completion_body.get("choices") if isinstance(completion_body, dict) else None
                    if isinstance(choices, list) and choices:
                        text = choices[0].get("text")
                        if isinstance(text, str) and text.strip():
                            active_remote_model_id = model_id
                            model_name_for_logs = model_id
                            return text
                    remote_errors.append(
                        f"[{model_id}] Router HTTP completions returned unexpected body: {completion_body}"
                    )
                else:
                    remote_errors.append(
                        f"[{model_id}] Router HTTP completions failed "
                        f"{completion_response.status_code}: {completion_response.text[:400]}"
                    )
            except Exception as exc:
                remote_errors.append(f"[{model_id}] Router HTTP completions exception: {exc}")

            print(f"All remote routes failed for {model_id}. Trying next remote model...")

        active_remote_model_id = REMOTE_MODEL_IDS[0] if REMOTE_MODEL_IDS else MODEL_ID
        model_name_for_logs = active_remote_model_id

        raise RuntimeError(
            "Remote inference failed across all available routes and model fallbacks. "
            + " | ".join(remote_errors)
        )

    if pipe is None:
        raise RuntimeError("Local generation pipeline was not initialized.")

    return pipe(prompt_text)[0]["generated_text"]


def resolve_pdf_path(pdf_path: str) -> str:
    """Resolve a PDF path from common locations (cwd and PDFS) and return an existing file path."""
    candidate = Path(pdf_path)

    search_candidates = [
        candidate,
        Path.cwd() / candidate,
        Path.cwd() / "PDFS" / candidate,
    ]

    # If extension is omitted, try with .pdf as well.
    if candidate.suffix.lower() != ".pdf":
        search_candidates.extend([
            candidate.with_suffix(".pdf"),
            Path.cwd() / candidate.with_suffix(".pdf"),
            Path.cwd() / "PDFS" / candidate.with_suffix(".pdf"),
        ])

    for path_candidate in search_candidates:
        if path_candidate.exists() and path_candidate.is_file() and path_candidate.suffix.lower() == ".pdf":
            return str(path_candidate)

    raise FileNotFoundError(
        "PDF not found. Tried: " + ", ".join(str(p) for p in search_candidates)
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
    # Resolve common path patterns first (e.g., bare filename, PDFS/<name>.pdf)
    pdf_path = resolve_pdf_path(pdf_path)

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
        f.write(model_name_for_logs) # model name
        f.write(f"\n...\n")
        f.write(prompt) # prompt used
        f.write(f"\n...\n")
        f.write(promptType) # prompt type
        f.write(f"\n...\n")
        f.write(str(LLMoutput)) # LLM output
        f.write(f"\n...\n")
        f.flush()  # Ensure data is written immediately
        print(f"print successfull")



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
def zero_shot_prompt(doc: str,  max_chars: int = MAXPDF_LENGTH) -> str:
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

def few_shot_prompt(doc: str, max_chars: int = MAXPDF_LENGTH) -> str:
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

def chain_of_thought_prompt(doc: str, max_chars: int = MAXPDF_LENGTH) -> str:
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


def _build_final_kde_prompt(document_name: str, prompt_payloads: Dict[str, str]) -> str:
    """Build a KDE extraction prompt that enforces a strict YAML schema."""
    return f"""You are an expert document analyst.

Below are three constructed prompts for the same requirements document ({document_name}).
Use the information from all three prompts to identify KDEs.

ZERO SHOT PROMPT:
{prompt_payloads.get('zero', '')}

FEW SHOT PROMPT:
{prompt_payloads.get('few', '')}

CHAIN OF THOUGHT PROMPT:
{prompt_payloads.get('chain', '')}

Identify key data elements (KDEs) and map each KDE to one or more requirements.

Return ONLY valid YAML in this exact schema:
element1:
  name: <kde name>
  requirements:
    - <requirement reference>
    - <another requirement reference>
element2:
  name: <kde name>
  requirements:
    - <requirement reference>

Rules:
1. Include at least 3 KDEs when possible.
2. Each KDE must include one or more requirements.
3. A KDE can map to multiple requirements.
4. Do not include markdown fences, commentary, or extra keys.
"""


def _normalize_kde_dict(parsed_yaml) -> Dict[str, Dict[str, list]]:
    """Normalize model YAML into the required nested dictionary shape."""
    normalized: Dict[str, Dict[str, list]] = {}

    if not isinstance(parsed_yaml, dict):
        return normalized

    index = 1
    for _, value in parsed_yaml.items():
        if not isinstance(value, dict):
            continue

        name = str(value.get("name", "")).strip()
        requirements = value.get("requirements", [])

        if isinstance(requirements, str):
            requirements = [requirements]
        elif not isinstance(requirements, list):
            requirements = [str(requirements)]

        cleaned_requirements = [str(req).strip() for req in requirements if str(req).strip()]

        if not name:
            continue

        normalized[f"element{index}"] = {
            "name": name,
            "requirements": cleaned_requirements,
        }
        index += 1

    return normalized


def _fallback_kde_dict(prompt_outputs: Dict[str, str]) -> Dict[str, Dict[str, list]]:
    """Fallback output if the model does not return parseable YAML."""
    fallback = {}
    for i, prompt_name in enumerate(["zero", "few", "chain"], start=1):
        fallback[f"element{i}"] = {
            "name": f"KDE extracted from {prompt_name} prompt",
            "requirements": [
                f"Derived from {prompt_name} prompt output",
                "Manual review recommended",
            ],
        }
    return fallback


def validate_kde_schema(kde_dict: Dict[str, Dict[str, list]]) -> Tuple[bool, List[str]]:
    """Validate that KDE output matches the required nested dictionary schema."""
    issues: List[str] = []

    if not isinstance(kde_dict, dict) or not kde_dict:
        return False, ["Top-level KDE object must be a non-empty dictionary."]

    for element_key, element_value in kde_dict.items():
        if not str(element_key).startswith("element"):
            issues.append(f"Invalid key '{element_key}'. Keys must use the pattern elementN.")

        if not isinstance(element_value, dict):
            issues.append(f"{element_key} must map to a dictionary.")
            continue

        name = element_value.get("name")
        requirements = element_value.get("requirements")

        if not isinstance(name, str) or not name.strip():
            issues.append(f"{element_key}.name must be a non-empty string.")

        if not isinstance(requirements, list) or not requirements:
            issues.append(f"{element_key}.requirements must be a non-empty list.")
            continue

        for idx, req in enumerate(requirements, start=1):
            if not isinstance(req, str) or not req.strip():
                issues.append(f"{element_key}.requirements[{idx}] must be a non-empty string.")

    return len(issues) == 0, issues


def extract_kdes_for_document(doc_text: str, document_name: str) -> Dict[str, Dict[str, list]]:
    """Run all constructed prompts and produce a normalized KDE dictionary."""
    prompt_builders = {
        "zero": zero_shot_prompt,
        "few": few_shot_prompt,
        "chain": chain_of_thought_prompt,
    }

    prompt_payloads: Dict[str, str] = {}
    for prompt_name, prompt_builder in prompt_builders.items():
        prompt_payloads[prompt_name] = prompt_builder(doc_text)

    final_prompt = _build_final_kde_prompt(document_name, prompt_payloads)
    try:
        final_yaml_output = generate_text(final_prompt)
    except Exception as exc:
        print(
            "Generation failed for "
            f"{document_name}; using deterministic fallback KDE output. Error: {exc}"
        )
        return _fallback_kde_dict(prompt_payloads)

    torch.cuda.empty_cache()
    gc.collect()

    try:
        parsed_yaml = yaml.safe_load(final_yaml_output)
        normalized = _normalize_kde_dict(parsed_yaml)
        if normalized:
            return normalized
    except yaml.YAMLError:
        pass

    return _fallback_kde_dict(prompt_payloads)


def create_kde_yaml_files(pdf_paths: list[str], output_dir: str = "KDEs") -> Dict[str, Dict[str, Dict[str, list]]]:
    """Generate KDE YAML outputs for each input PDF using Gemma-3-1B."""
    os.makedirs(output_dir, exist_ok=True)

    all_results: Dict[str, Dict[str, Dict[str, list]]] = {}
    for pdf_path in pdf_paths:
        doc_name = Path(pdf_path).stem
        print(f"Processing document: {pdf_path}")

        document_text = read_document(pdf_path)
        kde_dict = extract_kdes_for_document(document_text, doc_name)
        is_valid, validation_issues = validate_kde_schema(kde_dict)
        if not is_valid:
            raise ValueError(
                "Generated KDE dictionary failed schema validation for "
                f"{doc_name}: {' | '.join(validation_issues)}"
            )

        all_results[doc_name] = kde_dict

        output_file = Path(output_dir) / f"{doc_name}-kdes.yaml"
        with open(output_file, "w", encoding="utf-8") as f:
            yaml.safe_dump(kde_dict, f, sort_keys=False, allow_unicode=False)

        with open(output_file, "r", encoding="utf-8") as f:
            file_kde = yaml.safe_load(f)

        file_valid, file_issues = validate_kde_schema(file_kde)
        if not file_valid:
            raise ValueError(
                "Written YAML failed schema validation for "
                f"{doc_name}: {' | '.join(file_issues)}"
            )

        print(f"Wrote KDE YAML: {output_file}")

    return all_results


def create_kde_yaml_files_for_two_documents(
        pdf_path_1: str,
        pdf_path_2: str,
        output_dir: str = "KDEs",
) -> Dict[str, Dict[str, Dict[str, list]]]:
        """
        Generate KDE YAML outputs for exactly two requirement documents using Gemma-3-1B.

        Output schema per document:
        element1:
            name: <kde name>
            requirements:
                - req1
                - req2
                - req3
        """
        return create_kde_yaml_files([pdf_path_1, pdf_path_2], output_dir=output_dir)



if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python task1Extactor.py <requirements_doc_1.pdf> <requirements_doc_2.pdf>")
        sys.exit(1)
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
    create_kde_yaml_files_for_two_documents(sys.argv[1], sys.argv[2], output_dir="KDEs")

# Path.unlink("temp.csv")