# Captions Downloader

This script downloads captions, subtitles or transcripts from *YouTube* videos, playlists or channels.

## The Problem

From time to time, it is valuable to have access to the captions or transcripts of a video or a set of videos. *YouTube* and other platforms don't make it easy to download these. Further, *YouTube* uses a 'rolling' model, meaning even the downloaded *vtt* files would have lots of repetitions.

## Usage

### Running the script

When you run the *Python* script, it will ask you for two inputs:

1. The folder into which it should store the downloaded file(s).
2. The source URL from which to download the captions, subtitles or transcripts. If you provide the URL to a *YouTube* video, then the script will download the captions for that video. If you provide the URL for a playlist or a channel, then the script will attempt to parse the whole playlist or channel and download the transcripts of all videos in it.
3. Whether or not you would like to include *YouTube Shorts*. While *Shorts* can sometimes be sources themselves, many longer-format videos, such as *podcasts* often use *Shorts* as promotional clips for the full video.

The script can also identify URLs for *Spotify* or *iTunes* shows and attempt to download the captions, if available. However, *Spotify* and *Apple iTunes* usually keep these on lockdown. In case the script cannot download the capstions from the *Spotify* or *iTunes* link, it attempts to find the analogous link for its *YouTube* version, if available, and provides that link to you, in case you may want to download the capstions from that *YouTube* link.

### Output

The script will save the output as the original downloaded *VTT* or *SRT* file(s) and converted *TXT* file(s) in the output folder you selected. When converting to *TXT*, the script strips out any duplications caused by *YouTube*'s' 'rolling' model and any timestamps, yielding uninterrupted running text.

Filenames are indexed in the same order as the source.

### Note

1. The script uses some standard *Python* libraries. If you don't have them installed on your system, then in the first run, the script will try to install these dependencies. If the script can't install these dependencies, for instance if your PC environment precludes it, then it will usually give you the console commands you can use to install these.
2. If some of your libraries and executables sit outside the *Path*, such as if you don't have Admin rights to your work laptop, then you should include the folder addresses in the '*path.txt*' file, which should sit in the same folder as the '*captions-downloader.py*' file, e.g. '*C:\Users\Username\AppData\Roaming\Python\Python313\Scripts*' and '*C:\Users\Username\AppData\Roaming\Python\Python313\site-packages*'.

## Caveat

Tested on *Windows 11 Education 64-bit*.

Not tested on *Apple iOS* or *Linux*.

## Never run a Python script before?

It's straightforward, but you may need to install *Python* on your machine first.

### Install Python

*Anaconda* is one of the most popular distributions of *Python*. Download and install from https://www.anaconda.com/download

Installation is simple, but if you need help, check out https://www.anaconda.com/docs/getting-started/anaconda/install/overview

### Start Spyder

*Anaconda* comes with *Spyder IDE*. Start *Spyder*.

Once *Spyder* is ready, open the file '*captions-downloader.py*' that has the script.

All that's left is for you to hit 'Run', i.e. the green 'Play' button.