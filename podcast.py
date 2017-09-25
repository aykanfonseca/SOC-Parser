from bs4 import BeautifulSoup
from firebase import firebase
import requests

# Global variables.
PODCAST_URL = 'https://podcast.ucsd.edu'
SESSION = requests.Session()

def main():
    try:
        post = SESSION.get(PODCAST_URL, stream=True)
    except requests.exceptions.HTTPError:
        post = SESSION.get(PODCAST_URL, stream=True)

    # Parse the response into HTML and look only for tr tags.
    div_elements = BeautifulSoup(post.content, 'lxml').findAll(attrs = {'class' : 'quarter'})
    # tr_elements = BeautifulSoup(post.content, 'lxml').findAll('tr')

    for i in div_elements:
        print i.text
        print "\n"

    # for i in tr_elements:
    #     print i
    #     print "\n"

    print(len(div_elements))

if __name__ == '__main__':
    main()