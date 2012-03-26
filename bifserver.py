#!/usr/bin/env python
import os
import sys, traceback
import shutil
import urllib
import struct
import subprocess
import BaseHTTPServer
import SimpleHTTPServer
import Queue
import threading
import re

devnull=open(os.devnull)
bif_queue = Queue.LifoQueue()

# Use the ffmpeg installed to the current dir if we find it there,
# otherwise assume it's on the system path.
ffmpeg_bin_prefix = os.path.dirname(__file__)+"/bin/"
if not os.path.isfile(ffmpeg_bin_prefix+"ffmpeg"):
  ffmpeg_bin_prefix = ""

def intbytes(value):
  return struct.pack("<I1", value)

def process_bif_queue():

  # TODO: perhaps make these options configurable
  interval = 15

  while True:
    print("Background thread waiting for next queued bif creation request")
    sys.stdout.flush()
    args = bif_queue.get()
    video_path = args[0]
    bif_path = args[1]
    hd = args[2]
    try:

      if not os.path.isfile(bif_path):

        print("Generating bif for: "+video_path)
        sys.stdout.flush()

        tmpdir = bif_path+".tmp"
        bif_file = None
        try:

          # Find out what the video's aspect ratio is...
          video_info = subprocess.check_output([ffmpeg_bin_prefix+"ffprobe", video_path], stderr=subprocess.STDOUT)
          match = re.compile('Video: [^,]+, [^,]+, (\\d+)x(\\d+) ', re.MULTILINE).search(video_info)
          if match:
            video_aspect_ratio = float(match.group(1)) / float(match.group(2))
            if video_aspect_ratio > 1.5 :
              print("Video resolution 16:9 (%sx%s)"%(match.group(1), match.group(2)))
              if hd :
                resolution = "320x180" # HD 16:9 ~ 1.7 ratio
              else :
                resolution = "240x136" # SD 16:9 ~ 1.7 ratio
            else :
              print("Video resolution 4:3 (%sx%s)"%(match.group(1), match.group(2)))
              if hd :
                resolution = "320x240" # HD 4:3 ~ 1.3 ratio
              else :
                resolution = "240x180" # SD 4:3 ~ 1.3 ratio
          else:
            print("Could not detect video resolution.")
            if hd :
              resolution = "320x240" # HD 4:3 ~ 1.3 ratio
            else :
              resolution = "240x180" # SD 4:3 ~ 1.3 ratio

          # Export the video to the temp dir @ 1 frame/second
          if os.path.isdir(tmpdir):
           shutil.rmtree(tmpdir)

          sys.stdout.flush()
          if not os.path.isdir(tmpdir):
            os.mkdir(tmpdir)
            ffmpeg= [ffmpeg_bin_prefix+"ffmpeg", "-i", video_path, "-s", resolution, "-r", "1", tmpdir+"/%016d.jpg"]
            print(ffmpeg)
            sys.stdout.flush()
            if subprocess.call(ffmpeg, stdout=devnull, stderr=devnull):
              raise Exception("Could not extract images from video")

          images = 0
          while os.path.isfile("%s/%016d.jpg" % (tmpdir, images + 1)):
            images += 1
          bif_images = images/interval
          bif_file = open(bif_path, "wb")

          # Write the bif header.
          bif_file.write("\x89\x42\x49\x46\x0d\x0a\x1a\x0a")
          bif_file.write("\x00"*4)
          bif_file.write(intbytes(bif_images))
          bif_file.write(intbytes(interval*1000))
          bif_file.write("\x00"*(64-20))

          # Write the bif index.
          image_offset = 64 + (8 * bif_images) + 8
          for i in range(bif_images):
            bif_file.write(intbytes(i))
            bif_file.write(intbytes(image_offset))
            image_offset += os.stat("%s/%016d.jpg" % (tmpdir, (i*interval)+1)).st_size

          bif_file.write("\xff"*4)
          bif_file.write(intbytes(image_offset))

          # Write the bif images.
          for i in range(bif_images):
            image_file = open("%s/%016d.jpg" % (tmpdir, (i*interval)+1), "rb")
            try:
              shutil.copyfileobj(image_file, bif_file)
            finally:
              image_file.close()

          print("Created bif at: %s"%(bif_path))
  		
        finally:
          if bif_file:
            bif_file.close()
          if os.path.isdir(tmpdir): 
           shutil.rmtree(tmpdir)

    except Exception:
      print("Failed to create bif: "+bif_path)
      traceback.print_exc(file=sys.stdout)
    finally:
      sys.stdout.flush()

class RequestHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):
  
  def do_HEAD(self):
    self.get(False, 503)

  def do_GET(self):
    if self.headers.getheader('X-HTTP-Method-Override') == 'QUEUE':
      self.get(False, 200)
    else:
      self.get(True, 503)

  def get(self, include_body, queue_result):

    bif_path = urllib.unquote_plus(self.path)
    bif_file = None
    try:

      # We only hand requests for bif files..
      if bif_path.endswith(".hd.bif"):
        hd = True
      elif bif_path.endswith(".sd.bif"):
        hd = False
      else:
        raise Exception("Not a bif request")

      # For files the exist.
      video_path = bif_path[0:-7]
      if not os.path.isfile(video_path):
        # Try again, this time striping off the leading / (To handle windwows paths like c:/temp/... )
        video_path = video_path[1:]
        bif_path = bif_path[1:]
        if not os.path.isfile(video_path):
          raise Exception("Not Found")

      # If it does not yet exist...
      if not os.path.isfile(bif_path):
        # Queue a request to have a bif created for the video file.
        bif_queue.put([video_path, bif_path, hd])
        self.send_error(queue_result, "bif file is being created")
        self.end_headers()

      else:
        bif_file = open(bif_path, 'rb')
        self.send_response(200)
        self.send_header("Content-type", "application/octet-stream")
        self.send_header("Content-Length", str(os.path.getsize(bif_path)))
        self.end_headers()

        if include_body:
          shutil.copyfileobj(bif_file, self.wfile)

    except IOError:
      self.send_error(404, "Not Found")
      self.end_headers()
    except Exception as error:
      self.send_error(404, error.__str__())
      self.end_headers()
    finally:
      if bif_file != None:
        bif_file.close()
      sys.stdout.flush()

if sys.argv[1:]:
  port = int(sys.argv[1])
else:
  port = 32405

# Process the bif queue in the background so we don't hang the http requests.
threading.Thread(target=process_bif_queue).start()
server = BaseHTTPServer.HTTPServer(('0.0.0.0', port), RequestHandler)
sa = server.socket.getsockname()
print "Serving HTTP on", sa[0], "port", sa[1], "..."
sys.stdout.flush()
server.serve_forever()

