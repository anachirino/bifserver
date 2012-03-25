# Overview

Implements a BIF server which can produce the BIF files which are needed
by a [Roku Player](http://www.roku.com/) to support the video trick modes so that you can 
see thumbnails of the video when start fast forwarding or rewinding.

# Requirements

* [Python 2.7](http://www.python.org/download/)
* [ffmpeg](http://ffmpeg.org/download.html)

Make sure the `python`, `ffmpeg`, and `ffprobe` commands all on your PATH
so that they can be run from the command line.

# Running

Execute:

    python bifserver.py

This starts the BIF server on port 32405

# Acessing BIF Images

Lets say you have a video file at `/media/example.mkv`, then you can get
a standard definition BIF via HTTP by using the `http://localhost:32405/media/example.mkv.sd.bif`
URL and a high definition BIF by accessing the `http://localhost:32405/media/example.mkv.hd.bif` URL.

The first time you try to access the BIF file you will get an HTTP 503 errors until the BIF
is created.  The BIF file will get created in a background thread.  ffmpeg will 
be used to extract the BIF file images.  Once the BIF file is created requsts for the file will 
succeed.  

Creating the BIF file can take a couple of minutes. It depends on the size of the media
and speed of your machine.  You should try trigger the creation of the BIF files eagerly before
you need to use them on your Roku Player.  The could be done on the command line using the 
`curl` command.  For example:

    curl -I http://localhost:32405/media/example.mkv.sd.bif

# Eagerly Creating the BIF files using Plex Media Server

You can have the [Plex Media Server](http://plexapp.com/) trigger the eager creation of the BIF file when a media
file is first added the the Plex library.  Just add the `BifServer.bundle` as Plex plugin.
Then enable it as an agent for your TV shows and Movies.

