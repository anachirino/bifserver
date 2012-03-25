import datetime, re, time, unicodedata, hashlib, urlparse, types, urllib
import shutil
import sys

class BifServerMediaMovie(Agent.Movies):
  name = 'BifServer Assets (Movies)'
  languages = [Locale.Language.NoLanguage]
  primary_provider = False
  contributes_to = ['com.plexapp.agents.imdb', 'com.plexapp.agents.none']
  
  def search(self, results, media, lang):
    results.Append(MetadataSearchResult(id='null', score = 100))
    
  def update(self, metadata, media, lang, force):
    # Set title if needed.
    for i in media.items:
      for part in i.parts:
        QueueBiff(part)

class BifServerMediaTV(Agent.TV_Shows):
  name = 'BifServer Assets (TV)'
  languages = [Locale.Language.NoLanguage]
  primary_provider = False
  contributes_to = ['com.plexapp.agents.thetvdb', 'com.plexapp.agents.none']

  def search(self, results, media, lang):
    results.Append(MetadataSearchResult(id='null', score = 100))

  def update(self, metadata, media, lang, force):
    for s in media.seasons:
      if int(s) < 1900:
        for e in media.seasons[s].episodes:
          for i in media.seasons[s].episodes[e].items:
            for part in i.parts:
              AddBiff(part)

def AddBiff(part):
  file = part.file.decode('utf-8')
  url = 'http://localhost:32405'+String.Quote(file)+".sd.bif"
  Log("Hitting URL : "+url)
  try:
    HTTP.Request(url, None, {'X-HTTP-Method-Override': 'QUEUE'}).content()
  except Exception:
    1
    

  
