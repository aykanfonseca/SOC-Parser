from bs4 import BeautifulSoup
import requests, time, multiprocessing
import re
import itertools

# Starts the timer.
start = time.time()

URL_SubjectCodes = 'http://ucsd.edu/catalog/front/courses.html'
URL_Catalog = 'http://www.ucsd.edu/catalog/courses/'

# Gets all the subjects listed in select menu.
def getSubjects():
    subjectPost = s.post(URL_SubjectCodes)
    subjectSoup = BeautifulSoup(subjectPost.content, 'lxml')

    # Gets all the subject Codes for post request
    subjects = []
    for x in subjectSoup.findAll('a', href=True):
        if '../courses/' in x['href']:
            subjects.append(x['href'].partition('/')[2].partition('/')[2].partition('.')[0])

    return sorted(subjects)

# Formats the list and separates according to class.
def formatList(ls):
    # Flattens list of lists into list.
    Catalog = [item for sublist in ls for item in sublist]

    # Spliting a list into lists of lists based on a delimiter word.
    Catalog = [list(y) for x, y in itertools.groupby(Catalog, lambda z: z == ' NXC') if not x]

    # Sorts list based on sorting criteria.
    return [x for x in Catalog if len(x) >= 3 and (x != '')]

# Parses the page
def parsePage(subject):
    # The parsing of the page.
    subjectPage = s.post(''.join([URL_Catalog, subject, '.html']))
    soup = BeautifulSoup(subjectPage.content, 'lxml')
    course = soup.findAll(attrs = {'class' : re.compile(r"^(course-list-courses|course-descriptions|course-name)$")})

    Catalog = []
    # Reformats the text and adds a 'new class' to indicate a new class
    for item in course:
        if item.get('class') in (['course-name'], ['course-list-courses']):
            Catalog.append(' NXC')

        parsedText = ' '.join(item.text.split()).replace(u'\u2014', '-').replace(u"\u2018", "'").replace(u"\u2019", "'").replace(u'\u201c', '"').replace(u'\u201d', '"').replace(u'\u2013', '-')

        parsedText = str(parsedText.replace(u'\ufeff', "").replace(u'\u04e7', 'o')

        # Pre-Exception formatting.
        # if (parsedText == '10A-B-C. First-Year Japanese') or (parsedText == '20A-B-C. Second-Year Japanese') or (parsedText == '130A-B-C. Third-Year Japanese') or (parsedText == '140A-B-C. Fourth-Year Japanese') or (parsedText == '150A-B-C. Advanced Japanese'):
        #     parsedText = 'JAPN '+ parsedText

        # Linguistics Exception.
        # if any(substring in parsedText for substring in ['Linguistics/American Sign Language (', 'Linguistics/Arabic (', 'Linguistics/French (', 'Linguistics/German (', 'Linguistics/Heritage Languages (', 'Linguistics/Hindi (', 'Linguistics/Italian (', 'Linguistics/Portuguese (', 'Linguistics/Spanish (', 'Linguistics (LIDS']):
        #     parsedText = parsedText.partition('(')[2].replace(') ', ' ')

        # # MUS 192 Exception.
        # if ('192. Senior Seminar in Music (1)' == parsedText):
        #     continue

        # # Japanese Exception for duplicated listed courses.
        # if ((parsedText == 'LTEA 130. Earlier Japanese Literature in Translation') or (parsedText == 'LTEA 132. Later Japanese Literature in Translation')) and (subject == 'JAPN'):
        #     print ("Completed {}").format(subject)
        #     return Catalog

        # if ' Prerequisites:' in parsedText:
        #     prequisites = parsedText.partition(" Prerequisites:")[2].strip()
        #     parsedText = parsedText.partition(" Prerequisites")[0]
        # else:
        #     prequisites = "No Prequisites"

        # Catalog.append(parsedText)

        # if item.get('class') not in (['course-name'], ['course-list-courses']):
        #     Catalog.append(prequisites.capitalize())

        # Post-Exception formatting.
        # if (parsedText == 'BILD 26. Human Physiology (4)'):
        #     Catalog.append('Introduction to the elements of human physiology and the functioning of the various organ systems. The course presents a broad, yet detailed, analysis of human physiology, with particular emphasis toward understanding disease processes. This course is designed for nonbiology students and does not satisfy a lower-division requirement for any biology major. Open to nonbiology majors only. Exclude the following major codes: BI28, BI29, BI30, BI31, BI32, BI33, BI34, BI35, BI36. Note: Students may not receive credit for BILD 26 after receiving credit for BIPN 100.')
        #     Catalog.append('No Prequisites')

    # print("Completed {}").format(subject)

    return Catalog

# The main program excluding timing.
def main():
    global s

    s = requests.Session()
    subjectCodes = getSubjects()

    # Parses and formats into: Full name of class, class description, class prequisites. This is done for each class.
    parsed = [parsePage(subjectCodes[i]) for i in range(len(subjectCodes))]
    return formatList(parsed)

#removes duplicates, preserves order, and keeps the first one you find.
def unique(ls):
    found = set()
    for item in ls:
        if item[0] not in found:
            yield item[0]
            found.add(item[0])

if __name__ == '__main__':
    parsed = main()

    # DUPLICATE FINDER TOOL
    count = 0
    found = set()
    for item in parsed:
        if item[0] not in found:
            found.add(item[0])
        else:
            print item
            print '\n'
            count += 1

    print count

    results = unique(parsed)

    for item in results:
        print(item)
        print('\n')

    # Ends the timer.
    end = time.time()

    # Prints how long it took for program to run.
    print('\n' + str(end - start))
