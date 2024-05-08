import ujson as json
import os
from django.db.models import Prefetch
from tqdm import tqdm

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django

django.setup()

from django.db.models import Prefetch, Q
from compass.models import Course, CourseComments, Section


def clean_reading_list(reading_list):
    entries = reading_list.split(';')
    formatted_entries = []
    for entry in entries:
        parts = entry.split('//')
        if len(parts) == 2:
            title, authors = parts
            formatted_entry = f'- {authors.strip()}, {title.strip()}.'
        else:
            # Handle entries with missing authors
            title = parts[0]
            formatted_entry = f'- {title.strip()}'
        formatted_entries.append(formatted_entry)
    return '\n'.join(formatted_entries)


def clean_response(data):
    formatted_details = 'Course Information:\n'
    for key, value in data.items():
        if isinstance(value, list):
            value = '\n - ' + '\n - '.join(value)
        formatted_details += f"{key.replace('_', ' ').title()}: {value}\n"
    return formatted_details.strip()


def guid_to_semester(guid):
    guid_map = {
        '1252': 'Fall 2024',
        '1242': 'Fall 2023',
        '1232': 'Fall 2022',
        '1222': 'Fall 2021',
        '1212': 'Fall 2020',
        '1244': 'Spring 2024',
        '1234': 'Spring 2023',
        '1224': 'Spring 2022',
        '1214': 'Spring 2021',
    }
    guid_prefix = guid[:4]
    return guid_map.get(guid_prefix, 'Unknown Semester')


def fetch(guid, cache):
    if guid in cache:
        return cache[guid]

    sections_prefetch = Prefetch(
        'section_set',
        queryset=Section.objects.select_related('instructor', 'term').all(),
    )

    try:
        course = Course.objects.prefetch_related(sections_prefetch).get(guid=guid)

        course_details = {
            'Semester': guid_to_semester(course.guid),
            'Department': course.department.name if course.department else None,
            'Department Code': course.department.code if course.department else None,
            'Catalog Number': course.catalog_number,
            'Crosslistings': course.crosslistings,
            'Course Title': course.title,
            'Description': course.description,
            'Distribution Area Long': course.distribution_area_long
            if course.distribution_area_long
            else 'None',
            'Distribution Area Short': course.distribution_area_short
            if course.distribution_area_short
            else 'None',
            'Assignments': course.reading_writing_assignment
            if course.reading_writing_assignment
            else 'N/A',
            'Reading List': clean_reading_list(course.reading_list)
            if course.reading_list
            else 'Not Available.',
        }

        if course.section_set.exists():
            section = course.section_set.first()
            course_details['Instructor Name'] = (
                section.instructor.full_name if section.instructor else 'Not Available'
            )
            track = (
                'Undergraduate Course'
                if section.track == 'UGRD'
                else 'Graduate Course'
                if section.track == 'GRAD'
                else 'Not Specified'
            )
            course_details['Track'] = track
        else:
            course_details['Instructor Name'] = 'Not Available'
            course_details['Origin Semester'] = 'Not Available'
            course_details['Track'] = 'Not Specified'

        cache[guid] = course_details  # Store the course details in the cache
        return course_details
    except Course.DoesNotExist:
        return 'Course not found.'


def fetch_course_data(filename='./mapreduce/dataset.jsonl'):
    cache = {}

    comments = CourseComments.objects.exclude(Q(comment__isnull=True) | Q(comment__exact=''))

    with open(filename, 'w') as file:
        for comment in tqdm(comments, desc='Fetching course data...'):
            guid = comment.course_guid
            context = fetch(guid, cache)  # Retrieve the course details

            formatted_context = '#### CONTEXT START ####\n' + clean_response(context) + '\n#### CONTEXT END ####'

            entry = {
                'messages': [
                    {"role": "system", "content": "You are a helpful course planning assistant at Princeton University."},
                    {"role": "user", "content": "Provide insights and advice about this course based on the given context."},
                    {"role": "assistant", "content": formatted_context + "\n\nResponse: " + comment.comment}
                ]
            }

            # JSONL: Write each entry as a separate JSON object followed by a newline
            json.dump(entry, file)
            file.write('\n')  # Ensures JSON Lines format



def main():
    fetch_course_data()

if __name__ == '__main__':
    main()
