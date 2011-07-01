from collections import Counter
from gdutils.stats import spearman

import matplotlib.mlab as mlab
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

import datetime
import pylab
import re
import research

me_words = (u"i", u"i'd", u"i'll", u"i'm", u"me", u"myself", u"my", u"mine")

def me_ratio(song):
    words = [word.lower() for word in re.split("[^-'\w]+", song['lyrics'])]
    wc = Counter(words)
    me_count = 0
    for word, count in wc.items():
        if word in me_words: me_count += count
    mr = me_count / float(len(words))
    return mr

def calc_all_mr(songs):
    for song in songs:
        song['mr'] = me_ratio(song)
    research.save_songs(songs, ofile='clean_songs.xml')
    return songs

def get_days_mr(songs):
    songs_sorted = songs[:]
    songs_sorted.sort(key=lambda x: x['date'])
    
    days = [mdates.date2num(s['date']) for s in songs_sorted]
    mrs = [s['mr'] for s in songs_sorted]
    return days, mrs

def histogram(mrs):

    fig = plt.figure()
    ax = fig.add_subplot(111)
    n, bins, patches = ax.hist(mrs, 50, normed=True, facecolor='green', alpha=0.75)
    bincenters = 0.5*(bins[1:] + bins[:-1])
    ax.set_xlabel('me-ratio')
    ax.set_ylabel('probability')
    plt.savefig('histo.svg')

if __name__ == "__main__":
    songs = research.read_songs('clean_songs.xml')
    days, mrs = get_days_mr(songs)
    plt.plot_date(days, mrs, fmt='-', xdate=True, ydate=False, ms=1.5)
    plt.xlabel('year')
    plt.ylabel('me-ratio')
    plt.title('Self-Centeredness of Number 1 Songs: 1958-2011')
    sp = spearman(days, mrs)
    plt.figtext(0.4, 0.01, "Spearman's correlation = %.3f" % sp, multialignment='center')

    fig = pylab.gcf()
    fig.set_size_inches(12,6)
    fig.savefig('out.svg', dpi=100)
    
    # plt.savefig('out.svg')
