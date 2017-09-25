from bs4 import BeautifulSoup
import requests
import re
import itertools

# Global Variables.
SESSION = requests.Session()
SUBJECTS_URL = 'http://blink.ucsd.edu/instructors/courses/schedule-of-classes/subject-codes.html'
SUBJECTS = 'http://www.ucsd.edu/catalog/front/courses.html'
URL_CATALOG = 'http://www.ucsd.edu/catalog/courses/'

def get_subjects():
    '''Gets all the subjects listed in select menu. List returned is of all subject codes.'''

    # subject_post = SESSION.get(SUBJECTS_URL)
    # soup = BeautifulSoup(subject_post.content, 'lxml').findAll('td')

    # return [i.text for i in soup if len(i.text) <= 4]

    subject_post = SESSION.get(SUBJECTS)
    soup = BeautifulSoup(subject_post.content, 'lxml').findAll('a')

    return [i['href'][11:] for i in soup if i.text == "courses"]
     

def get_data(url_subject_tuple):
    master = []
    s = SESSION

    for url, subject in url_subject_tuple:
        # Occasionally, the first call will fail.
        try:
            post = s.get(url, stream=True)
        except requests.exceptions.HTTPError:
            post = s.get(url, stream=True)

        # Parse the response into HTML.
        soup = BeautifulSoup(post.content, 'lxml')
        # course = soup.findAll(attrs = {'class' : re.compile(r"^(course-list-courses|course-descriptions|course-name)$")})
        course = soup.find('div', id="content").findAll('p')

        start = 0

        # Filters out useless stuff at beginning.
        for index, item in enumerate(course):
            try:
                if item['class'] == ["course-name"]:
                    start = index
                    break
            except KeyError:
                pass

        # This will contain all the classes for a single page.
        page_list = []

        for i in course[index:]:
            parsed_text = ' '.join(i.text.split()).replace(u'\u2014', '-').replace(u"\u2018", "'").replace(u"\u2019", "'").replace(u'\u201c', '"').replace(u'\u201d', '"').replace(u'\u2013', '-')

            try:
                if i['class'] in (['course-name'], ['course-list-courses']):
                    page_list.append(' NXC')
            except KeyError:
                pass

            page_list.append(parsed_text)

            # if ' Prerequisites:' in parsed_text:
            #     prequisites = parsed_text.partition(" Prerequisites:")[2].strip().capitalize()
            #     parsed_text = parsed_text.partition(" Prerequisites")[0]
            # else:
            #     prequisites = "No Prequisites"

            # if i['class'] not in (['course-name'], ['course-list-courses']):
            #     page_list.append(parsed_text)
            #     page_list.append(prequisites)
            # else:
            #     split_period = parsed_text.partition(".")
            #     split_left_parens = split_period[2].partition("(")

            #     # Dept + number. Ex. BILD 1
            #     page_list.append(split_period[0])
            #     # Name. Ex. Intro to Mathematical Reasoning
            #     page_list.append(split_left_parens[0].strip())
            #     # Units. Ex. 4
            #     if split_left_parens[2].strip()[:-1] == "":
            #         page_list.append("N/A")
            #     else:
            #         page_list.append(split_left_parens[2].strip()[:-1])

        print("Completed {}").format(subject)
        print("\n")
        master.append(page_list)

    return master


def format_list(lst):
    '''Formats the result list into the one we want.'''

   # Flattens list of lists into list.
    flattened = [item for sublist in lst for item in sublist]

    # Spliting a list into lists of lists based on a delimiter word.
    grouped = [list(y) for x, y in itertools.groupby(flattened, lambda z: z == ' NXC') if not x]

    # Sorts list based on sorting criteria.
    return [x for x in grouped if len(x) >= 3 and (x != '')]


def main():
    '''The main function.'''

    subject_codes = get_subjects()

    # data = get_data(((URL_CATALOG + x + '.html', x) for x in subject_codes))
    data = get_data(((URL_CATALOG + x, x[:-5]) for x in subject_codes))

    formatted = format_list(data)

    with open("catalog.txt", 'w') as file:
        for i in formatted:
            file.write(str(i))
            file.write("\n")
            file.write("\n")

if __name__ == '__main__':
    main()