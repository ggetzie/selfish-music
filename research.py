from django.conf import settings
from django.template import Template, Context
from gdutils.utils import post, get

import BeautifulSoup as BS
import html5lib as hl
import datetime
import codecs
import time
import sys
import urllib, urllib2


UASTRING = "GreaterDebater Crawler - report abuse to admin@greaterdebater.com"
YEARS = range(1959, 2012)
MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', \
              'August', 'September', 'October', 'November', 'December']
SEARCH_URL = 'http://lyricsfly.com/search/search.php'
RESULT_URL = 'http://lyricsfly.com/search/'
ERR_TEMPLATE = 'errtemplate.xml'
ERR_FILE = '/home/gabe/python/selfishmusic/errors.xml'


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

def save_songs(songs, template="songtemplate.xml", ofile="/home/gabe/data/music/songs.xml"):
    """ save songs to xml file """
    try:
        settings.configure(DEBUG=True,
                           TEMPLATE_DEBUG=True,
                           TEMPLATE_DIRS='/home/gabe/python/selfishmusic/templates/',
                           DATE_FORMAT='F d, Y')
    except RuntimeError:
        # running in interpreter and have already loaded settings
        pass

    song_t_file = open(template)
    song_t = Template(song_t_file.read())
    song_c = Context({'songs': songs})
    outfile = codecs.open(ofile,
                          encoding='utf-8', mode='w')
    outfile.write(song_t.render(song_c))
    outfile.close()
    print "Wrote %i songs to file" % len(songs)

def read_songs():
    """ read song data from xml file to a list of dictionaries """
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
        sd['lyrics'] = get_text(song.lyrics)
        sd['found_title'] = get_text(song.found_title)
        sd['found_artist'] = get_text(song.found_artist)
        songs.append(sd)
    songfile.close()
    return songs

def read_err_songs():
    """ read song data from xml file to a list of dictionaries """
    songfile = open('/home/gabe/python/selfishmusic/errors.xml')
    soup = BS.BeautifulSoup(songfile.read())
    songsxml = soup.findAll('song')
    songs = []
    for song in songsxml:
        sd = {}
        sd['songnum'] = int(get_text(song.songnum))
        sd['title'] = get_text(song.title)
        sd['artist'] = get_text(song.artist)
        date = get_text(song.date)
        date = [x.strip(' ,') for x in date.split(' ')]
        sd['date'] = datetime.date(month=MONTHS.index(date[0]) + 1,
                                     day=int(date[1]),
                                     year=int(date[2]))
        sd['lyrics'] = get_text(song.lyrics)
        sd['found_title'] = get_text(song.found_title)
        sd['found_artist'] = get_text(song.found_artist)
        songs.append(sd)
    songfile.close()
    return songs

def save_err_songs(indexes, songs):
    allbad = [songs[i] for i in indexes]
    save_songs(allbad, template=ERR_TEMPLATE, ofile=ERR_FILE)

def get_search_results(song, options=1, sort=3, aside=False):

    # search lyricsfly by song title
    title = song['title']
    if aside and ('/' in title):
        title = title.split('/')[0].strip()

    postdata = {'keywords': title.encode('ascii', errors='ignore'), 'options':options, 'sort':sort}
    def search(url):
        response = post(url, urllib.urlencode(postdata))
        try:
            soup = BS.BeautifulSoup(response, convertEntities=BS.BeautifulSoup.HTML_ENTITIES)
        except TypeError:
            soup = hl.parse(response, treebuilder='beautifulsoup')
        cell = soup.find('td', {'class': 'list'})
        if not cell: 
            return -1, -1
        results_table = cell.parent.parent
        rows = results_table.findAll('tr')
        return rows, soup

    rows, soup = search(SEARCH_URL)
    if rows == -1: return -1

    # check for a second page of results
    # This should be more general, for n pages, but I think lyricsfly
    # only ever returns 2 pages at most.
    page2 = soup.find('form', {'name': 'search2'})
    url2 = SEARCH_URL + '?page=2'
    if page2:
        # wait 1.1 seconds before requesting next page
        time.sleep(1.1)
        rows2, soup = search(url2)
        if rows2 == -1: 
            return rows
        rows.extend(rows2)

    return rows

def get_lyrics(song, rows):
    best_artist = 1 
    best_title = 1
    best_index = -1
    song_artist_words = song['artist'].split(' ')
    song_title_words = song['title'].split(' ')
    # titles and artists may not match up exactly
    # pick the result that has the most words in common for both
    # the artist and the title
    for i, row in enumerate(rows):
        cells = row.findAll('td')
        row_artist_words = get_text(cells[0])
        row_title_words = get_text(cells[1])
        artist_count = 0
        title_count = 0
        for word in song_artist_words:
            if word in row_artist_words:
                artist_count += 1
        for word in song_title_words:
            if word in row_title_words:
                title_count += 1
        if artist_count >= best_artist and title_count >= best_title:
            best_index = i
            best_artist = artist_count
            best_title = title_count

    if best_index == -1:
        return best_index, -1, -1
    
    lyrics_url = RESULT_URL + rows[best_index].findAll('td')[1].a['href']
    print lyrics_url
    found_title = get_text(rows[best_index].findAll('td')[1])
    found_artist = get_text(rows[best_index].findAll('td')[0])
    lyrics_page = get(lyrics_url)
    try:
        soup = BS.BeautifulSoup(lyrics_page, convertEntities=BS.BeautifulSoup.HTML_ENTITIES)
    except TypeError:
        soup = hl.parse(lyrics_page, treebuilder='beautifulsoup')
    span = soup.findAll('span', {'class':'adbriteinline'})[0]
    # remove linebreaks
    br = soup.findAll('br')
    [b.extract() for b in br]

    try:
        lyrics = ''.join(span.contents)
    except TypeError:
        lyrics = ''.join(soup.p.contents)
        
    if not lyrics:
        lyrics = ''.join(soup.p.contents)

    lyrics = lyrics.replace(u"\ufffd", '')

    return lyrics, found_title, found_artist

def get_all_lyrics(songs):
    # loop through all songs and search lyricsfly for lyrics
    for songnum, song in enumerate(songs):
        print "Song %i getting lyrics for %s by %s" % (songnum, song['title'], song['artist'])
        try:
            rows = get_search_results(song)
            if rows == -1:
                print "\tSong %i No results for %s by %s" % (songnum, song['title'], song['artist'])
                song['lyrics'] = 'Not found'
                continue
            lyrics, found_title, found_artist = get_lyrics(song, rows)
            time.sleep(1.1)
            if lyrics == -1:
                print "\t Song %i No match for %s by %s" % (songnum, song['title'], song['artist'])
                song['lyrics'] = "No match"
                continue
            song['lyrics'] = lyrics
            song['found_artist'] = found_artist
            song['found_title'] = found_title
            print "\tFound %s by %s -- saving lyrics" % (found_title, found_artist)
            time.sleep(1.1)
        except:
            print "\t Song %i Error fetching lyrics for %s by %s - skipping" % (songnum, song['title'], song['artist'])
            song['lyrics'] = "Error"
    return songs

def find_errors(songs):
    notfound = []
    nomatch = []
    err = []
    empty = []
    for index, song in enumerate(songs):
        song['songnum'] = index
        if song['lyrics'] == 'Not found':
            notfound.append(index)
        elif song['lyrics'] == 'No match':
            nomatch.append(index)
        elif song['lyrics'] == 'Error':
            err.append(index)
        elif song['lyrics'] == '':
            empty.append(index)
    
    return notfound, nomatch, err, empty



def fix_empties(empties, songs, aside=False):
    for e in empties:
        songnum = e
        print "Song %i getting lyrics for %s by %s" % (songnum, songs[e]['title'], songs[e]['artist'])
        
        if aside and (not '/' in songs[e]['title']): continue
        
        try:
            rows = get_search_results(songs[e], aside=aside)
            if rows == -1:
                print "\tSong %i No results for %s by %s" % (songnum, title, songs[e]['artist'])
                songs[e]['lyrics'] = 'Not found'
                continue
            lyrics, found_title, found_artist = get_lyrics(songs[e], rows)
            time.sleep(1.1)
            if lyrics == -1:
                print "\t Song %i No match for %s by %s" % (songnum, songs[e]['title'], songs[e]['artist'])
                songs[e]['lyrics'] = "No match"
                continue
            songs[e]['lyrics'] = lyrics
            songs[e]['found_artist'] = found_artist
            songs[e]['found_title'] = found_title
            print "\tFound %s by %s -- saving lyrics" % (found_title, found_artist)
            time.sleep(1.1)
        except:
            print "\t Song %pi Error fetching lyrics for %s by %s - skipping" % (songnum, songs[e]['title'], songs[e]['artist'])
            songs[e]['lyrics'] = "Error"
    save_songs(songs)

def update_err_songs():
    songs = read_songs()
    errs = read_err_songs()
    for e in errs:
        songs[e['songnum']]['lyrics'] = e['lyrics']
        songs[e['songnum']]['artist'] = e['artist']
        
    save_songs(songs)
    bad = find_errors(songs)
    indexes = reduce(lambda x,y: x+y, bad)
    save_err_songs(indexes, songs)
    return songs, bad
    
