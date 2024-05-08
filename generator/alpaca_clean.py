import json
import time
import sys

def align_dataset(input_file: str, output_file: str) -> None:
    """
    Aligns the JSONL dataset to the desired Alpaca format
    and outputs a cleaned JSONL dataset (still has to be rearranged).

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
                    aligned_message = f"System: {content}"
                elif role == 'user':
                    aligned_message = f"User: {content}"
                elif role == 'assistant':
                    aligned_message = f"Assistant: {content}"
                else:
                    continue  # Skip messages with unknown roles
                
                aligned_messages.append(aligned_message)
            
            aligned_data = {'text': '\n'.join(aligned_messages)}
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
        output_file = 'comments/aligned_course_comments_dataset.jsonl'
    elif choice == '2':
        input_file = 'details/cleaned_course_details_dataset.jsonl'
        output_file = 'details/aligned_course_details_dataset.jsonl'
    elif choice == '3':
        input_file = '/scratch/gpfs/mn4560/sage/generator/unclean_llama3_dataset.jsonl'
        output_file = 'cleaned_alpaca_dataset.jsonl'
    else:
        print("Invalid choice.")
        sys.exit(1)

    start_time = time.time()
    align_dataset(input_file, output_file)
    end_time = time.time()
    print(f'Dataset alignment completed.\nExecution time: {end_time - start_time:.2f} seconds')

if __name__ == "__main__":
    main()
