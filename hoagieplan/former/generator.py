import json
import os
from tqdm import tqdm
from openai import OpenAI
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from compass.models import CourseComments
from django.db.models import Q
from former.fetch_context import fetch, clean_response

system_prompt = ''
model_content = 'Your job is to imagine yourself as a student curious about '
'academic course planning. Your goal is to anticipate and simulate what a '
'Princeton University undergraduate might have asked to the large language '
'model on the course planning web application. Carefully and realistically '
'craft a prompt that the student would have most likely used to generate '
'the following response: '


def create_dataset(comments, filename='dataset.jsonl'):
    client = OpenAI()
    cache = {}  # Initialize cache for course details

    with open(filename, 'w') as file:
        for comment in tqdm(comments, desc='Generating dataset...'):
            guid = comment.course_guid
            context_data = fetch(guid, cache)  # Retrieve the course details

            # Format the context with the course details
            formatted_context = (
                '#### CONTEXT START ####\n'
                + clean_response(context_data)
                + '\n#### CONTEXT END ####'
            )

            # Generate the user prompt using the OpenAI API
            completion = client.chat.completions.create(
                model='gpt-3.5-turbo',
                messages=[
                    {'role': 'system', 'content': system_prompt},
                    {
                        'role': 'user',
                        'content': f'{formatted_context}\n\n{model_content}.',
                    },
                ],
            )
            user_prompt = completion.choices[0].text.strip()

            # Create the messages list for the JSONL entry
            messages = [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt},
                {
                    'role': 'assistant',
                    'content': formatted_context + '\n\nResponse: ' + comment.comment,
                },
            ]

            # Write each entry as a separate JSON object followed by a newline
            json.dump({'messages': messages}, file)
            file.write('\n')  # Ensures JSON Lines format


# Process the CourseComments table
comments = CourseComments.objects.exclude(
    Q(comment__isnull=True) | Q(comment__exact='')
).all()

# Specify the filename for the dataset
filename = 'final_dataset.jsonl'

# Create the dataset, checking if the file already exists and generating a new filename if needed
counter = 1
while os.path.exists(filename):
    filename = f'final_dataset_{counter}.jsonl'
    counter += 1

# Generate the dataset
create_dataset(comments[:3], filename)