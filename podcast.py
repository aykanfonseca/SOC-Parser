'''Python program to scrape UC San Diego's podcasts for a quarter. Created by Aykan Fonseca.'''

# TODO:
# 1. Update to parse any quarter. Currently only parses the current quarter.

# Builtins
import time

# Pip install packages.
from bs4 import BeautifulSoup
from firebase import firebase
import requests

# Used to convert between shortened codes.
quarter_mapping = {'Fall':'FA', 'Winter':'WI', 'Spring':'SP', 'Summer Med School':'SU', 'Summer Session 1':'S1', 'Summer Session 2':'S2', 'Summer Session 3':'S3', 'Summer':'SA'}
podcast_url = "https://podcast.ucsd.edu"


def parse_data():
    post = requests.get(podcast_url)
    soup = BeautifulSoup(post.content, 'lxml')

    # A list of dictionaries where each list is contains: title of course, professor, authentication, and podcast link.
    podcasts = []

    quarter_year = soup.find('div', {'class': 'quarter'}).h2.span.text.split(' ')[::2]

    quarter = quarter_mapping[quarter_year[0]] + quarter_year[1][-2:]

    table = soup.find('div', {'class': 'quarter'}).findAll('tr')

    for item in table:
        sub = {}

        # # Append the Class name & Professor.
        sub['class'] = item.findAll('td')[0].text.strip().partition('-')[0].strip()
        sub['professor'] = item.findAll('td')[1].text.strip()

        # True / False value if log in authentication is required. Assume false. 
        authentication = False

        if (item.findAll('td')[0].div != None):
            authentication = True
        
        # Append the authentication.
        sub['authentication'] = authentication

        # Podcast link.
        sub['link'] = item.findAll('td')[2].findAll('a')[0]['href'][:-4]

        podcasts.append(sub)

    return podcasts, quarter


def update_db(podcasts, quarter):
    database = firebase.FirebaseApplication("https://schedule-of-classes-8b222.firebaseio.com/")

    for item in podcasts:
        # If the podcast is for two courses, just pick the first one. TODO: NEED TO UPDATE.
        if item['class'].split(' ') > 2:
            item['class'] = ' '.join(item['class'].split(' ')[:2])
        
        path = "/quarter/" + quarter + "/" + str(item['class']) + "/"

        # Updates node when node exists. If not, don't add because we won't use.
        if (database.get(path, None) != None): 
            database.put(path, 'podcast', {'authentication': item['authentication'], 'link': item['link']})


def reset_db():
    """ Deletes data to firebase."""

    print("Wiping information in database.")

    database = firebase.FirebaseApplication("https://schedule-of-classes-8b222.firebaseio.com/")

    database.delete('/quarter', None)


def main():
    '''The main function.'''
    print(sys.version)

    reset = False

    if (reset):
        reset_db()

    start = time.time()

    podcasts, quarter = parse_data()

    update_db(podcasts, quarter)

    print("\nTime taken: " + str(time.time() - start))

if __name__ == '__main__':
    main()