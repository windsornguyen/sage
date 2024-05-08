from openai import OpenAI
import json
import sys


def create_dataset_example(
    comment, course_details, system_prompt, filename='dataset_example.jsonl'
):
    client = OpenAI()

    model_content = (
        'Your job is to imagine yourself as a student curious about academic course planning. '
        'Your goal is to anticipate and simulate what a Princeton University undergraduate might '
        'have asked to the large language model on the course planning web application. '
        'Carefully and realistically craft a prompt that the student would have most likely used '
        'to generate the following response.'
    )

    formatted_context = (
        '#### CONTEXT START ####\n' + course_details + '\n#### CONTEXT END ####'
    )

    completion = client.chat.completions.create(
        model='gpt-3.5-turbo',
        messages=[
            {'role': 'system', 'content': system_prompt},
            {
                'role': 'user',
                'content': f'{model_content}\n\n{formatted_context}\n\nResponse: {comment}',
            },
        ],
    )

    user_prompt = completion.choices[0].message.content.strip()

    messages = [
        {'role': 'system', 'content': system_prompt},
        {'role': 'user', 'content': user_prompt},
        {
            'role': 'assistant',
            'content': formatted_context + '\n\nResponse: ' + comment,
        },
    ]

    with open(filename, 'a') as file:
        json.dump({'messages': messages}, file)
        file.write('\n')  # Ensures JSON Lines format


if __name__ == '__main__':
    # Default values for demonstration
    default_comment = 'Please explain how course credits are calculated.'
    default_course_details = """Course Information:
Semester: Fall 2023
Department: Computer Science
Department Code: COS
Catalog Number: 126
Crosslistings: 
Course Title: General Computer Science
Description: An introduction to computer science in the context of scientific, engineering, and commercial applications. The goal of the course is to teach basic principles and practical issues, while at the same time preparing students to use computers effectively for applications in computer science, physics, biology, chemistry, engineering, and other disciplines. Topics include: hardware and software systems; programming in Java; algorithms and data structures; fundamental principles of computation; and scientific computing, including simulation, optimization, and data analysis. No prior programming experience required. Two lectures, two classes.
Distribution Area Long: None
Distribution Area Short: None
Assignments: Reading/Writing assignments will be included in the course
Reading List: Not Available.
Instructor Name: Robert Sedgewick
Track: Undergraduate Course"""
    default_system_prompt = """
The assistant is Sage, a honest, helpful, and harmless 
academic planning assistant for students at Princeton University.

Sage was created by Windsor Nguyen '25 from the hoagie.io team as part of his 
junior year independent work project. You are Sage.

When asked if you are an AGI or the like, Sage should humbly respond that it is not.

Sage should give concise responses to very simple questions, but provide 
thorough responses to more complex and open-ended questions. 
If you are asked to assist with tasks involving the expression of views held 
by a significant number of people, Sage provides assistance with the task even 
if it personally disagrees with the views being expressed but follows this with 
a nudge to broader perspectives.

Sage doesn't engage in stereotyping, including the negative stereotyping of 
majority groups. If asked about controversial topics, Sage tries to provide 
careful thoughts and objective information without downplaying its harmful 
content or implying that there are reasonable perspectives on both sides.

Sage is happy to help with writing, analysis, question answering, math, coding, 
and all sorts of other tasks. Sage uses markdown for coding.

Sage does not menion this information about itself unless the information is 
directly pertinent to the human's query.
"""

    # Terminal IO
    comment = input('Enter a comment (or press Enter for default): ') or default_comment
    course_details = (
        input('Enter course details (or press Enter for default): ')
        or default_course_details
    )
    system_prompt = (
        input('Enter a system prompt (or press Enter for default): ')
        or default_system_prompt
    )

    # Generate the example dataset
    create_dataset_example(comment, course_details, system_prompt)
