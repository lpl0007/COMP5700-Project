#!/usr/bin/env python3
"""
Script to clean up zero_shot_outputs.txt by replacing literal '\\n' with actual newlines.
"""

def cleanup_output(input_file='zero_shot_outputs.txt', output_file='zero_shot_outputs_cleaned.txt'):
    """
    Read the input file and replace literal \\n with actual newline characters.
    
    Args:
        input_file: Path to the input file to clean
        output_file: Path to save the cleaned output
    """
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace literal \n with actual newlines
    cleaned_content = content.replace('\\n', '\n')
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(cleaned_content)
    
    print(f"Cleaned output saved to: {output_file}")
    print(f"Original file size: {len(content)} characters")
    print(f"Cleaned file size: {len(cleaned_content)} characters")


if __name__ == '__main__':
    import sys
    
    # Allow command-line arguments for input and output files
    input_file = sys.argv[1] if len(sys.argv) > 1 else 'zero_shot_outputs.txt'
    output_file = sys.argv[2] if len(sys.argv) > 2 else 'zero_shot_outputs_cleaned.txt'
    
    cleanup_output(input_file, output_file)
