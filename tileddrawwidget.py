# This file is part of MyPaint.
# Copyright (C) 2008 by Martin Renold <martinxyz@gmx.ch>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY. See the COPYING file for more details.

# First widget that allows drawing on a tiled layer.
# TODO:
# - dragging, zooming
# - allow more than one layer (external document object?)

import gtk, numpy, time
gdk = gtk.gdk
import mypaintlib, tilelib, brush
from math import floor, ceil

class TiledDrawWidget(gtk.DrawingArea):
    def __init__(self):
        gtk.DrawingArea.__init__(self)
        #self.connect("dragging-finished", self.dragging_finished_cb)
        self.connect("proximity-in-event", self.proximity_cb)
        self.connect("proximity-out-event", self.proximity_cb)
        self.toolchange_observers = []

        self.connect("motion-notify-event", self.motion_notify_cb)
        #self.connect("button-press-event", self.button_updown_cb)
        #self.connect("button-release-event", self.button_updown_cb)
        self.connect("expose-event", self.expose_cb)

        self.set_events(gdk.EXPOSURE_MASK
                        | gdk.LEAVE_NOTIFY_MASK
                        | gdk.BUTTON_PRESS_MASK
                        | gdk.BUTTON_RELEASE_MASK
                        | gdk.POINTER_MOTION_MASK
                        | gdk.PROXIMITY_IN_MASK
                        | gdk.PROXIMITY_OUT_MASK
                        )

        self.set_extension_events (gdk.EXTENSION_EVENTS_ALL)

        self.brush = None
        self.layer = None # tilelib.TiledLayer()
        self.displayed_layers = None # tilelib.TiledLayer()

        self.last_event_time = None

        self.recording = None

        self.disableGammaCorrection = False

    def proximity_cb(self, widget, something):
        for f in self.toolchange_observers:
            f()

    def motion_notify_cb(self, widget, event):
        pressure = event.get_axis(gdk.AXIS_PRESSURE)
        if pressure is None:
            if event.state & gdk.BUTTON1_MASK:
                pressure = 0.5
            else:
                pressure = 0.0

        if not self.brush:
            print 'no brush!'
            return
        assert isinstance(self.layer, tilelib.TiledLayer)

        if not self.last_event_time:
            self.last_event_time = event.time
            return
        dtime = (event.time - self.last_event_time)/1000.0
        self.last_event_time = event.time

        x, y = event.x, event.y

        if self.recording is not None:
            self.recording.append((dtime, x, y, pressure))
        bbox = self.brush.tiled_surface_stroke_to (self.layer, x, y, pressure, dtime)
        if bbox:
            x1, y1, w, h = bbox
            x2 = x1 + w - 1
            y2 = y1 + h - 1
            # transform 4 bbox corners to screen coordinates
            cr = self.get_model_coordinates_cairo_context()
            corners = [(x1, y1), (x1+w-1, y1), (x1, y1+h-1), (x1+w-1, y1+h-1)]
            corners = [cr.user_to_device(x, y) for (x, y) in corners]
            # find bbox containing the old (rotated, translated) rectangle
            list_y = [y for (x, y) in corners]
            list_x = [x for (x, y) in corners]
            x1 = floor(min(list_x))
            y1 = floor(min(list_y))
            x2 = ceil(max(list_x))
            y2 = ceil(max(list_y))
            self.queue_draw_area(x1, y1, x2-x1+1, y2-y1+1)

    def expose_cb(self, widget, event):
        t = time.time()
        if hasattr(self, 'last_expose_time'):
            # just for basic performance comparisons... but we could sleep if we make >50fps
            print '%d fps' % int(1.0/(t-self.last_expose_time))
        self.last_expose_time = t
        print 'expose', tuple(event.area)

        self.repaint()

    def get_model_coordinates_cairo_context(self):
        cr = self.window.cairo_create()
        cr.rotate(0.1)
        cr.scale(0.3, 0.3)
        return cr

    def repaint(self):
        cr = self.get_model_coordinates_cairo_context()
        #cr.rectangle(*event.area)
        #cr.clip()

        w, h = self.window.get_size()
        pixbuf = gdk.Pixbuf(gdk.COLORSPACE_RGB, False, 8, w, h)

        pixbuf.fill(0xffffffff)
        arr = pixbuf.get_pixels_array()
        arr = mypaintlib.gdkpixbuf2numpy(arr)

        #if not self.disableGammaCorrection:
        #    for surface in self.displayed_layers:
        #        surface.compositeOverWhiteRGB8(arr)
        #else:
        for surface in self.displayed_layers:
            surface.compositeOverRGB8(arr)

        #widget.window.draw_pixbuf(None, pixbuf, 0, 0, 0, 0)
        #cr.rectangle(0,0,w,h)
        #cr.clip()
        cr.set_source_pixbuf(pixbuf, 0, 0)
        cr.paint()

    def clear(self):
        print 'TODO: clear'

    def allow_dragging(self):
        print 'TODO: allow dragging'

    def scroll(self, dx, dy):
        print 'DEBUG'
        self.repaint()

    def set_brush(self, b):
        self.brush = b


    def start_recording(self):
        assert self.recording is None
        self.recording = []

    def stop_recording(self):
        # OPTIMIZE 
        # - for space: just gzip? use integer datatypes?
        # - for time: maybe already use array storage while recording?
        data = numpy.array(self.recording, dtype='float64').tostring()
        version = '2'
        self.recording = None
        return version + data

    def playback(self, data):
        version, data = data[0], data[1:]
        assert version == '2'
        for dtime, x, y, pressure in numpy.fromstring(data, dtype='float64'):
            self.brush.tiled_surface_stroke_to (self.layer, x, y, pressure, dtime)


