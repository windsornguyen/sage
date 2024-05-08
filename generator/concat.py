import ujson as json
import argparse
import sys

def concat(file1: str, file2: str, output: str) -> None:
    """
    Combines two JSONL (JSON Lines) files into a single JSONL file.

    This function reads two JSONL files line by line and writes each JSON object
    to a new output file. This is useful for merging large datasets stored in 
    the JSONL format.

    Args:
        file1 (str): The file path to the first input JSONL file.
        file2 (str): The file path to the second input JSONL file.
        output (str): The file path where the combined output should be stored.

    Returns:
        None
    """
    try:
        with open(file1, 'r') as f1, open(file2, 'r') as f2, open(output, 'w') as out:
            for line in f1:
                json_obj = json.loads(line.strip())
                json.dump(json_obj, out)
                out.write('\n')
            for line in f2:
                json_obj = json.loads(line.strip())
                json.dump(json_obj, out)
                out.write('\n')
    except FileNotFoundError as e:
        print(f"Error: {e.strerror} - {e.filename}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Combined JSONL files into {output}")

def main():
    parser = argparse.ArgumentParser(description="Concatenate two JSONL files into one.")
    parser.add_argument("file1", type=str, help="The file path to the first input JSONL file.")
    parser.add_argument("file2", type=str, help="The file path to the second input JSONL file.")
    parser.add_argument("output", type=str, help="The file path where the combined output should be stored.")
    
    args = parser.parse_args()

    concat(args.file1, args.file2, args.output)

if __name__ == "__main__":
    main()
