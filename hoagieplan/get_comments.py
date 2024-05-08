import json
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from compass.models import CourseComments


def export_comments_to_json(filename='./mapreduce/comments.json'):
    comments = CourseComments.objects.exclude(comment='').values(
        'course_guid', 'comment'
    )
    with open(filename, 'w') as file:
        json.dump(list(comments), file, indent=2)


if __name__ == '__main__':
    export_comments_to_json()
