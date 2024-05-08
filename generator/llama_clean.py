import json
import time
import sys

def align_dataset(input_file: str, output_file: str) -> None:
    """
    Aligns the dataset to the desired format and writes to the output file.

    Args:
    input_file (str): The path to the input file containing JSON lines.
    output_file (str): The path to the output file where aligned JSON lines are saved.
    """
    with open(input_file, 'r') as infile, open(output_file, 'w') as outfile:
        for line in infile:
            data = json.loads(line)
            messages = data['messages']
            aligned_messages = []
            
            for message in messages:
                role = message['role']
                content = message['content']
                
                if role == 'system':
                    aligned_message = f"<|start_header_id|>system<|end_header_id|>\n{content}<|eot_id|>"
                elif role == 'user':
                    aligned_message = f"<|start_header_id|>user<|end_header_id|>\n{content}<|eot_id|>"
                elif role == 'assistant':
                    aligned_message = f"<|start_header_id|>assistant<|end_header_id|>\n{content}<|eot_id|>"
                else:
                    continue  # Skip messages with unknown roles
                
                aligned_messages.append(aligned_message)
            
            aligned_data = {'text': "<|begin_of_text|>" + ''.join(aligned_messages) + "<|start_header_id|>assistant<|end_header_id|>\n<|end_of_text|>"}
            aligned_line = json.dumps(aligned_data)
            outfile.write(aligned_line + '\n')

def main():
    print("Select the dataset to align:")
    print("1: Comments")
    print("2: Details")
    print("3: Final dataset")
    choice = input("Enter your choice (1, 2, or 3): ")

    if choice == '1':
        input_file = 'comments/cleaned_course_comments_dataset.jsonl'
        output_file = 'comments/llama3_course_comments_dataset.jsonl'
    elif choice == '2':
        input_file = 'details/cleaned_course_details_dataset.jsonl'
        output_file = 'details/llama3_course_details_dataset.jsonl'
    elif choice == '3':
        input_file = 'unclean_llama3_dataset.jsonl'
        output_file = 'llama3_final_dataset.jsonl'
    else:
        print("Invalid choice.")
        sys.exit(1)

    start_time = time.time()
    align_dataset(input_file, output_file)
    end_time = time.time()
    print(f'Dataset alignment completed.\nExecution time: {end_time - start_time:.2f} seconds')

if __name__ == "__main__":
    main()