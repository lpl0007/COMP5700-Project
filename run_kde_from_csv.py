import csv
import os
from pathlib import Path

import torch
from transformers import pipeline


def authenticate_hf() -> None:
    """Authenticate to Hugging Face if a token is available via environment."""
    token = os.getenv("HF_TOKEN") or os.getenv("HUGGING_FACE_HUB_TOKEN")
    if not token:
        return

    try:
        from huggingface_hub import login
        login(token=token, add_to_git_credential=False)
    except Exception as exc:
        raise RuntimeError(
            "Failed to authenticate with Hugging Face. Check HF_TOKEN/HUGGING_FACE_HUB_TOKEN."
        ) from exc


def build_kde_prompt(prompt_text: str) -> str:
    """Build the KDE extraction prompt used by Task 1 logic."""
    return f"""You are an expert document analyst. Your task is to analyze the prompt given identify key data elements present in it.
    prompt:
    {prompt_text}

    Please analyze the prompt given and generate a output in yaml format like so:
    element1:
    name:
    requirements:
    req1
    req2
    req3
    """


def build_generator():
    """Create a generation pipeline with safe defaults for limited environments."""
    model_id = os.getenv("KDE_MODEL_ID", "distilgpt2")

    # Keep runtime small and robust by default. If you want Gemma, set KDE_MODEL_ID.
    if torch.cuda.is_available():
        return pipeline(
            "text-generation",
            model=model_id,
            device_map="auto",
            do_sample=True,
            temperature=0.7,
            top_p=0.9,
            repetition_penalty=1.1,
            max_new_tokens=256,
        )

    return pipeline(
        "text-generation",
        model=model_id,
        device=-1,
        do_sample=True,
        temperature=0.7,
        top_p=0.9,
        repetition_penalty=1.1,
        max_new_tokens=256,
    )


def run_kde_from_csv(csv_path: str = "temp.csv", out_dir: str = "KDEs") -> None:
    """Read Task 1 CSV outputs and generate KDE YAML files for each row."""
    authenticate_hf()
    generator = build_generator()

    col_map = {
        "Z": "zero",
        "F": "few",
        "C": "chain",
    }

    os.makedirs(out_dir, exist_ok=True)

    with open(csv_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)

        for row_index, row in enumerate(reader, start=1):
            for col, tag in col_map.items():
                prompt_output = (row.get(col) or "").strip()
                if not prompt_output:
                    continue

                kde_prompt = build_kde_prompt(prompt_output)
                kde_output = generator(kde_prompt)[0]["generated_text"]
                out_name = f"row{row_index} {tag} KDEs.yaml"
                out_path = Path(out_dir) / out_name

                with open(out_path, "w", encoding="utf-8") as out_file:
                    out_file.write(str(kde_output))

                print(f"Wrote {out_path}")


if __name__ == "__main__":
    run_kde_from_csv()
