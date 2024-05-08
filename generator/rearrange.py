import json
import time
import sys

def reorder_json_fields(input_file: str, output_file: str) -> None:
    """
    Reorders JSON fields in each line of the input file and writes to the output file.

    Args:
    input_file (str): The path to the input file containing JSON lines.
    output_file (str): The path to the output file where reordered JSON lines are saved.
    """
    with open(input_file, 'r') as infile, open(output_file, 'w') as outfile:
        for line in infile:
            data = json.loads(line)
            messages = data['messages']
            corrected_messages = [
                {'role': message['role'], 'content': message['content']}
                for message in messages
            ]
            corrected_data = {'messages': corrected_messages}
            corrected_line = json.dumps(corrected_data)
            outfile.write(corrected_line + '\n')

def main():
    print("Select the dataset to clean:")
    print("1: Comments")
    print("2: Details")
    print("3: Final dataset")
    choice = input("Enter your choice (1, 2, or 3): ")

    if choice == '1':
        input_file = 'comments/course_comments_dataset.jsonl'
        output_file = 'comments/cleaned_course_comments_dataset.jsonl'
    elif choice == '2':
        input_file = 'details/course_details_dataset.jsonl'
        output_file = 'details/cleaned_course_details_dataset.jsonl'
    elif choice == '3':
        input_file = '/scratch/gpfs/mn4560/sage/generator/cleaned_alpaca_dataset.jsonl'
        output_file = 'princeton-courses-data.jsonl'
    else:
        print("Invalid choice.")
        sys.exit(1)

    start_time = time.time()
    reorder_json_fields(input_file, output_file)
    end_time = time.time()
    print(
        f'Field ordering correction completed.\nExecution time: {end_time - start_time:.2f} seconds'
    )

if __name__ == "__main__":
    main()
