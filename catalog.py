'''Python program to scrape UC San Diego's Course Catalog. Created by Aykan Fonseca.'''

# Bulitins
import re
import itertools

# Pip installed packages.
from firebase import firebase
from bs4 import BeautifulSoup
import requests

# Global Variables.
SESSION = requests.Session()
SUBJECTS_URL = 'http://blink.ucsd.edu/instructors/courses/schedule-of-classes/subject-codes.html'
URL_CATALOG = 'http://www.ucsd.edu/catalog/courses/'
URL_CATALOG2 = 'http://www.ucsd.edu/catalog/front/courses.html'

# FIREBASE_DB = "https://schedule-of-classes-8b222.firebaseio.com/"
FIREBASE_DB = "https://winter-2019-rd.firebaseio.com/"

def get_subjects():
    '''Gets all the subjects.'''

    subject_post = SESSION.get(SUBJECTS_URL)
    soup = BeautifulSoup(subject_post.content, 'lxml').findAll('td')

    subject_post2 = SESSION.get(URL_CATALOG2)
    soup2 = BeautifulSoup(subject_post2.content, 'lxml').findAll('a')

    subjects = [i.text for i in soup if i.text.isupper()]
    subjects2 = [i['href'][11:-5] for i in soup2 if i.text == "courses"]

    return subjects + list(set(subjects2) - set(subjects))


def get_data(url_subject_tuple):
    '''Retrieves the data.'''

    master = []
    s = SESSION

    for url, subject in url_subject_tuple:
        # Occasionally, the first call will fail.
        try:
            post = s.get(url, stream=True)
        except requests.exceptions.HTTPError:
            post = s.get(url, stream=True)
        except requests.exceptions.ConnectionError:
            post = s.get(url, stream=True)

        if post.status_code != 404:
            # Parse the response into HTML.
            soup = BeautifulSoup(post.content, 'lxml')

            course = soup.findAll('p')
            start = 0
            end = 0

            # Filters out useless stuff at beginning.
            for index, item in enumerate(course):
                try:
                    if item['class'] == ["course-name"] and start == 0:
                        start = index
                    if item['class'] == ["course-list-courses"] or item['class'] == ["course-descriptions"]:
                        end = index
                except KeyError:
                    pass

            # This will contain all the classes for a single page.
            page_list = []

            for i in course[start:end+1]:
                try:
                    if i['class'] in (['course-name'], ['course-list-courses']):
                        page_list.append(' NXC')
                except KeyError:
                    pass
                    
                parsed_text = ' '.join(i.text.split()).encode('utf-8')

                # Linguistics exception.
                if subject == 'LING' and 'Linguistics' in parsed_text and parsed_text.count(')') == 2 and parsed_text.count('(') == 2 and re.findall(r'.+\((\w+)\)', parsed_text):
                    starter = parsed_text.find('(')
                    ender = parsed_text.find(')')
                    parsed_text = parsed_text[starter + 1: ender] + " " + parsed_text[ender+1:].strip()

                # Graduate Sociology exception.
                if 'Soc/G' in parsed_text and subject == "SOC":
                    parsed_text = "SOCG " + " ".join(parsed_text.split(" ")[1:])

                # Classics exception.
                if subject == 'CLAS' and "Classics " in parsed_text:
                    parsed_text = "CLAS " + " ".join(parsed_text.split(" ")[1:])

                # Jewish Studies exception. 
                if subject == 'JUDA' and '(' in parsed_text and ')' in parsed_text and "Jewish Studies " in parsed_text:
                    parsed_text = "JUDA " + " ".join(parsed_text.split(" ")[2:])

                # Revelle classes exception. 
                if subject == "REV" and "Revelle " in parsed_text and '(' in parsed_text and ')' in parsed_text and 'Prerequisites' not in parsed_text:
                    parsed_text = "REV " + " ".join(parsed_text.split(" ")[1:])

                # Clinical Psychology exception.
                try:
                    if subject == "CLIN" and 'Prerequisites' not in parsed_text and i['class'] == ['course-name']:
                        parsed_text = "CLIN " + parsed_text[re.search("\d", parsed_text).start():]
                except:
                    pass

                # Bioengineering exception.
                if 'BENG/BIMM/CSE' in parsed_text:
                    parsed_text = "BENG " + " ".join(parsed_text.split(" ")[1:])

                try:
                    # Japanese exception.
                    if subject == "JAPN" and 'Prerequisites' not in parsed_text and i['class'] == ['course-name'] and '-' in parsed_text:
                        parsed_text = "JAPN " + parsed_text
                except:
                    pass

                page_list.append(parsed_text)
            
            print("Completed {}\n").format(subject)
            master.append(page_list)

    return master


def format_data(lst):
    '''Formats the result list into the one we want.'''

    # Flattens list of lists into list.
    flattened = [item for sublist in lst for item in sublist]

    # Spliting a list into lists of lists based on a delimiter word.
    grouped = [list(y) for x, y in itertools.groupby(flattened, lambda z: z == ' NXC') if not x]

    formatted = []
    problem = []
    for i in grouped:
        course = [text for text in i if text != ""]

        if len(course) == 2:
            formatted.append(course)
        elif len(course) != 2 and len(course) > 0:
            problem.append(course)

    return formatted, problem


def handle_problem_data_partially(formatted_data, problem_data):
    case_one_problem_data = [] # We accidently picked up more stuff.
    case_two_problem_data = [] # We only have the DEPT + CODE + TITLE basically.

    # Filter data appropriately.
    for i in problem_data:
        if len(i) > 1:
            case_one_problem_data.append(i)
        else:
            case_two_problem_data.append(i)

    # Disregard everything after the second portion and include it in the okay data.
    for i in case_one_problem_data:
        formatted_data.append(i[:2])

    # Remove duplicates. Have to do case by case because some descriptions are better.
    final = {}
    for i in formatted_data:
        if i[0] not in final:
            final[i[0]] = i
        else: # Handle specific descriptions where they are better.
            if 'MGTF 410' in i[0]:
                final[i[0]] = i
            if 'MGTF 432' in i[0]:
                final[i[0]] = i
            if 'HISC 165' in i[0]:
                final[i[0]] = i
            if 'HISC 166/266' in i[0]:
                final[i[0]] = i
            if 'HISC 167/267' in i[0]:
                final[i[0]] = i
            if 'HISC 180/280' in i[0]:
                final[i[0]] = i
            if 'PHIL 280' in i[0]:
                final[i[0]] = i
            if 'TDHT 111' in i[0]:
                final[i[0]] = i
            if 'LTEN 181' in i[0]:
                final[i[0]] = i
            if 'SIOB 286' in i[0]:
                final[i[0]] = i
            if 'SIOC 210' in i[0]:
                final[i[0]] = i
            if 'SIOC 217A' in i[0]:
                final[i[0]] = i
            if 'SIOC 217B' in i[0]:
                final[i[0]] = i
            if 'SIOC 217C' in i[0]:
                final[i[0]] = i
            if 'SIOC 217D' in i[0]:
                final[i[0]] = i
            if 'SIOG 252A' in i[0]:
                final[i[0]] = i
            if 'SIOG 260' in i[0]:
                final[i[0]] = i
            if 'TWS 21' in i[0]:
                final[i[0]] = i


    return case_two_problem_data, final


def split_description_for_prerequisites(lst):
    ''' Split prereq into separate selection. So list format for each is: [DEPT CODE TITLE, DESCRIPTION, PREREQS].'''

    new_final = []

    for i in lst:
        if "Prerequisites: " in i[1]: # Has prerequisites.
            split = i[1].split("Prerequisites: ")
            part = [i[0].strip(), split[0].strip(), split[1].strip()]
        else: # Doesn't.
            part = [i[0].strip(), i[1].strip(), "None."]
            
        new_final.append(part)

    return new_final


def convert_to_dictionary_final(lst):
    dictionary_form = {}
    for i in lst:
        temp = i[0].partition('.')
        temp2 = temp[2].partition('(')
        
        dept_code = temp[0]
        title = temp2[0].strip()
        units = temp2[2].partition(')')[0].strip()

        dictionary_form[dept_code.strip()] = {'title': title, 'units': units, 'description': i[1], 'prerequisites': i[2]}

    return dictionary_form


def reset_db():
    """ Deletes data to firebase."""

    print("Wiping information in database.")

    database = firebase.FirebaseApplication(FIREBASE_DB)

    database.delete('/catalog', None)


def write_to_db(dictionary):
    """ Adds data to firebase."""

    print("Writing information to database.")

    database = firebase.FirebaseApplication(FIREBASE_DB)

    path = "catalog"

    count = 0
    for key in dictionary:
        count += 1

        if count % 100 == 0:
            print str(count / len(dictionary)) + " percent done."

        database.put(path, key, dictionary[key])


def main():
    reset_db()

    global s

    s = requests.Session()
    subjects = get_subjects()

    # Forms pairs of (URL, subject code).
    url_subject_tuples = ((URL_CATALOG + x + ".html", x) for x in subjects)

    raw_data = get_data(url_subject_tuples)

    formatted_data, problem_data = format_data(raw_data)

    case_two_problem_data, final = handle_problem_data_partially(formatted_data, problem_data)

    # Convert final 'dictionary' back to list.
    converted = [val for key, val in final.items()]

    # Split descriptions for each into description and prereq portions.
    new_final = split_description_for_prerequisites(converted)

    # lister = {}
    # lister2 = {}
    cleaned_final = []

    errors = []
    for i in new_final:
        # Checks if the department code + Course numnber has only alphabetic or numbers or spaces. 
        if i[0].partition('.')[0].replace(' ', '').isalnum():
            if 'or' in i[0].partition('.')[0]:
                print i[0].partition('.')[0]
            else:
                cleaned_final.append(i)
        else:
            errors.append(i[0].partition('.')[0]) 

    # for i in new_final:
        # text = i[0][:i[0].find('.')]
        # if '-' in text:
        #     lister[text] = i
        # if '/' in text:
        #     lister2[text] = i
        # else:
        #     cleaned_final.append(i)

    finalized = convert_to_dictionary_final(cleaned_final)

    print len(finalized)
    # for key, value in lister.items():
    #     split_by_dash = key.split('-')

    #     # Ensure everything has two spaces: like: CSE 132 A instead of CSE 132A.
    #     if split_by_dash[0].count(' ') < 2:
    #         index_of_last_digit = re.match('.+([0-9])[^0-9]*$', split_by_dash[0]).start(1)

    #         dept_code = split_by_dash[0][:index_of_last_digit + 1]
    #         letter = split_by_dash[0][index_of_last_digit + 1:]

    #         # Only numbers no alphabets. Ex. "TWS 21".
    #         if letter is '':
    #             split_no_letters_single_space = dept_code.split(' ')

    #             title = value[0].partition('.')[2].partition('(')[0].strip()
    #             units = value[0].partition('.')[2].partition('(')[2].partition(')')[0].split('-')

    #             # Check if all values in the units list are the same or not.
    #             if units.count(units[0]) == len(units):
    #                 unit = units[0]
    #             else:
    #                 print("1.) ERROR!")

    #             if dept_code not in finalized:
    #                 if (len(dept_code) > 9):
    #                     print "(A)"
    #                     print dept_code
    #                     print "\n"

    #                 finalized[dept_code] = {'title': title, 'units': units, 'description': value[1], 'prerequisites': value[2]}
    #             else:
    #                 if dept_code == "HILD 10":
    #                     pass
    #                 else:
    #                     print(dept_code)
    #                     print finalized[dept_code]
    #                     print("2.) ERROR!")
    #                     print("\n")

    #             for j in split_by_dash[1:]:
    #                 dept_code = split_no_letters_single_space[0] + " " + j

    #                 if dept_code not in finalized:
    #                     if (len(dept_code) > 9):
    #                         print "(B)"
    #                         print dept_code
    #                         print "\n"

    #                     finalized[dept_code] = {'title': title, 'units': units, 'description': value[1], 'prerequisites': value[2]}
    #                 else:
    #                     if dept_code == 'HILD 11' or dept_code == 'HILD 12':
    #                         pass
    #                     else:
    #                         print(dept_code)
    #                         print finalized[dept_code]
    #                         print("3.) ERROR!")
    #                         print("\n")

    #         # Has letters at the end. Ex. "MATH 20A".
    #         else:
    #             title = value[0].partition('.')[2].partition('(')[0].strip()
    #             units = value[0].partition('.')[2].partition('(')[2].partition(')')[0].split('-')

    #             # Check if all values in the units list are the same or not.
    #             if units.count(units[0]) == len(units):
    #                 unit = units[0]
    #             else:
    #                 print("4.) ERROR!")

    #             if dept_code + letter not in finalized:
    #                 if (len(dept_code + letter) > 9):
    #                     print "(C)"
    #                     print dept_code
    #                     print "\n"

    #                 finalized[dept_code + letter] = {'title': title, 'units': units, 'description': value[1], 'prerequisites': value[2]}
    #             else:
    #                 if dept_code + letter == "HILD 7A":
    #                     pass
    #                 else:
    #                     print(dept_code + letter)
    #                     print finalized[dept_code + letter]
    #                     print("5.) ERROR!")
    #                     print("\n")

    #             for j in split_by_dash[1:]:
    #                 dept_code = dept_code + j

    #                 if dept_code not in finalized:
    #                     if (len(dept_code) > 9):
    #                         print "(D)"
    #                         print dept_code
    #                         print "\n"

    #                     finalized[dept_code] = {'title': title, 'units': units, 'description': value[1], 'prerequisites': value[2]}
    #                 else:
    #                     if dept_code == "HILD 7B":
    #                         pass
    #                     else:
    #                         print(dept_code)
    #                         print finalized[dept_code]
    #                         print("6.) ERROR!")
    #                         print("\n")
            
    #     else:
    #         dept_code_letter_triplet = split_by_dash[0].split(' ')
    #         formatted_correctly = dept_code_letter_triplet[0] + " " + dept_code_letter_triplet[1] + dept_code_letter_triplet[2]


    #         title = value[0].partition('.')[2].rpartition('(')[0].strip()
    #         units = value[0].rpartition('(')[2].partition(')')[0].split('-')

    #         # Check all units are identical.
    #         if len(set(units)) <= 1:
    #             units = units[0]
    #         else:
    #             print(units)
    #             print("7.) ERROR!")
    #             print("\n")

    #         if formatted_correctly not in finalized:
    #             finalized[formatted_correctly] = {'title': title, 'units': units, 'description': value[1], 'prerequisites': value[2]}
    #         else:
    #             print(formatted_correctly)
    #             print("8.) ERROR!")
    #             print("\n")

    #         for j in split_by_dash[1:]:
    #             dept_code =  dept_code_letter_triplet[0] + " " + dept_code_letter_triplet[1] + j

    #             if dept_code not in finalized:
    #                 if (len(dept_code) > 9):
    #                     print "(E)"
    #                     print dept_code
    #                     print "\n"

    #                 finalized[dept_code] = {'title': title, 'units': units, 'description': value[1], 'prerequisites': value[2]}
    #             else:
    #                 print(dept_code)
    #                 print("9.) ERROR!")
    #                 print("\n")

    # with open('a.txt', 'w+') as file:
    #     for i in finalized:
    #         file.write(str(i))
    #         file.write("\n")

    write_to_db(finalized)

    # for key, value in lister2.items():
    #     print key
    #     print "\n"



if __name__ == '__main__':
    main()