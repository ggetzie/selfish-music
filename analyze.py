from django.conf import settings
from django.template import Template, Context
from gdutils.utils import post, XMLDict

import datetime
import codecs
import urllib, urllib2
import BeautifulSoup as BS

UASTRING = "GreaterDebater Crawler - report abuse to admin@greaterdebater.com"
YEARS = range(1959, 2012)
MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', \
              'August', 'September', 'October', 'November', 'December']
SEARCH_URL = 'http://lyricsfly.com/search/search.php'
RESULT_URL = 'http://lyricsfly.com/search/'

def make_urls():
    urlfile = open('/home/gabe/data/music/urls.txt', 'w')
    urls = ["http://en.wikipedia.org/wiki/List_of_Hot_100_number-one_singles_of_%i_(U.S.)\n" % year for year in range(1959, 2012)]
    for url in urls:
        urlfile.write(url)
    urlfile.close()
        
def get_text(cell):
    return ''.join([x.strip() + ' ' for x in cell.findAll(text=True)]).strip()
        
def read_wiki():
    base_path = '/home/gabe/data/music/'
    songdata = []
    for year in range(1959, 2012):
        filename = "List_of_Hot_100_number-one_singles_of_%i_(U.S.)" % year
        f = open(base_path + filename)
        soup = BS.BeautifulSoup(f.read())
        if year < 2010:
            table = soup.table
        else:
            table = soup.find('table', {'class': 'wikitable'})

        # remove superscripts
        ss = table.findAll('sup')
        [s.extract() for s in ss]

        for row in table.findAll('tr'):
            song = {}
            cells = row.findAll('td')
            try:
                txt = get_text(cells[0])
                if txt.find("Issue") != -1:
                    continue
                song['date'] = get_text(cells[0]) + ', ' + str(year)
                song['title'] = get_text(cells[1])
                song['artist'] = get_text(cells[2])
                songdata.append(song)
            except IndexError:
                pass 
                # last = len(songdata) - 1
                # print "year: %i" % year
                # print "IndexError at: "
                # print row

    # remove duplicates
    checked = {}
    for song in songdata:
        date = [x.strip(' ,').encode('ascii', 'ignore') for x in song['date'].split(' ')]

        song['date'] = datetime.date(month=MONTHS.index(date[0]) + 1,
                                     day=int(date[1]),
                                     year=int(date[2]))
        song['title'] = song['title'].strip('" ')
        checked[(song['artist'], song['title'])] = song

    songs = checked.values()
    songs.sort(key=lambda x: x['date'])
    return songs

def save_songs(songs):
    try:
        settings.configure(DEBUG=True,
                           TEMPLATE_DEBUG=True,
                           TEMPLATE_DIRS='/home/gabe/python/selfishmusic/templates/',
                           DATE_FORMAT='F d, Y')
    except RuntimeError:
        pass

    song_t_file = open('songtemplate.xml')
    song_t = Template(song_t_file.read())
    song_c = Context({'songs': songs})
    outfile = codecs.open('/home/gabe/data/music/songs.xml', 
                          encoding='utf-8', mode='w')
    outfile.write(song_t.render(song_c))
    outfile.close()
    print "Wrote %i songs to file" % len(songs)

def read_songs():
    songfile = open('/home/gabe/data/music/songs.xml')
    soup = BS.BeautifulSoup(songfile.read())
    songsxml = soup.findAll('song')
    songs = []
    for song in songsxml:
        sd = {}
        sd['title'] = get_text(song.title)
        sd['artist'] = get_text(song.artist)
        date = get_text(song.date)
        date = [x.strip(' ,') for x in date.split(' ')]
        sd['date'] = datetime.date(month=MONTHS.index(date[0]) + 1,
                                     day=int(date[1]),
                                     year=int(date[2]))
        songs.append(sd)
    songfile.close()
    return songs

def get_search_results(song):

    # search lyricsfly by song title
    postdata = {'keywords': song['title'], 'options':1, 'sort':3}
    response = post(SEARCH_URL, urllib.urlencode(postdata))
    soup = BS.BeautifulSoup(response, convertEntities=BS.BeautifulSoup.HTML_ENTITIES)
    results = soup.find('table', {'id': 69})
    if results:
        return results
    else:
        return -1

def get_lyrics(song, results):
    rows = results.findAll('tr')
    best_artist = 0
    best_title = 0
    best_index = -1
    song_artist_words = song['artist'].split(' ')
    song_title_words = song['title'].split(' ')
    for i in range(len(rows)):
        cells = rows[i].findAll('td')
        row_artist = get_text(cells[0]).split()
        row_title = get_text(cells[1])
        row_artist_words = row_artist.split()
        row_title_words = row_title.split()
        artist_count = 0
        title_count = 0
        for word in song_artist_words:
            if word in row_artist_words:
                artist_count += 1
        for word in song_title_words:
            if word in row_title_words:
                title_count += 1
        if (artist_count > 0 and title_count > 0) and \
                (artist_count >= best_artist and title_count >= best_title):
            best_index = i
            best_artist = artist_count
            best_title = title_count
        
        
