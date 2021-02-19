#!/usr/bin/env python
import rospy
import numpy as np
import cv2
import urllib.request
import os
from math import *
from staticmap import StaticMap # OpenStreetMap

class Map:
    def __init__(self):
        self.WIN_W = 480
        self.WIN_H = 320
        # gg*:googleMap,  other:cyberjapandata:kokudochiriinn, open street map
        #self.map_type_name = ["gghybrid","ggsatellite","ggroadmap", "std","ort_old10","gazo1","seamlessphoto", "osm"]
        # 国土地理院:cyberjapandata:kokudochiriinn, Open Street Map:osm
        self.map_type_name = ["std","ort_old10","gazo1","seamlessphoto", "osm"]
        self.map_cyber = ["std","ort_old10","gazo1","seamlessphoto"]
        self.map_osm = ["osm"]
        self.TILE_W = [256,256,256,256,256]
        self.TILE_H = [256,256,256,256,256]
        self.min_zoom = [2,10,10, 2, 2]
        self.max_zoom = [18,17,17,18, 22]
        self.fmt = ["png", "png","jpg","jpg", "png"]
        self.mtype = 4
        self.zoom = 22
        self.TILES_DIR = "/home/takesato/workspace/mapdb/"
        self.max_pixels = [256*2**zm for zm in range(22)]
        self.opened_tiles = {}
        self.white_tiles = {}

    def ll2pix(self, lon, lat):
        pix_x = 2**(self.zoom+7)*(lon/180+1)
        pix_y = 2**(self.zoom+7)*(-np.arctanh(np.sin(np.pi/180*lat))/np.pi+1)
        return pix_x, pix_y

    def pix2ll(self, x, y):
        lon = 180*(x/(2**(self.zoom+7))-1)
        lat = 180/np.pi*(np.arcsin(np.tanh(-np.pi/(2**(self.zoom+7))*y+np.pi)))
        return lon, lat

    def new_ll(self, lon_cur, lat_cur, dx, dy):
        x,y = self.ll2pix(lon_cur, lat_cur)
        return self.pix2ll(x+dx, y+dy)

    def dddmm2f(self, dddmm_mmmm):
        #12345.6789 -> 123.45.6789 -> 123.(45.6789/60)
        ddd = int(dddmm_mmmm)//100
        mm_mmmm = dddmm_mmmm-ddd*100
        return ddd+mm_mmmm/60

    def load_win_img(self, lon, lat):
        cx, cy = self.ll2pix(lon, lat)
        win_left = int(cx-self.WIN_W/2)
        win_top = int(cy-self.WIN_H/2)
        x_nth = win_left//self.TILE_W[self.mtype]
        y_nth = win_top//self.TILE_H[self.mtype]
        left_offset = win_left%self.TILE_W[self.mtype]
        top_offset = win_top%self.TILE_H[self.mtype]
        vcon_list = []
        tot_height = 0
        tot_height += self.TILE_H[self.mtype]-top_offset
        j=0
        while True:
            hcon_list = []
            tot_width = 0
            tot_width += self.TILE_W[self.mtype]-left_offset
            i = 0
            while True:
                img_tmp = self.open_tile_img(x_nth+i, y_nth+j)
                hcon_list.append(img_tmp) #
                if tot_width >= self.WIN_W:
                    break
                tot_width += self.TILE_W[self.mtype]
                i += 1
            hcon_img = cv2.hconcat(hcon_list)
            vcon_list.append(hcon_img)
            if tot_height >= self.WIN_H:
                break
            tot_height += self.TILE_H[self.mtype]
            j += 1
        convined_img = cv2.vconcat(vcon_list)
        return convined_img[top_offset:top_offset+self.WIN_H, left_offset:left_offset+self.WIN_W, :]

    def tile_file_name(self, x_nth, y_nth):
        return self.TILES_DIR+"z%02d/%s_z%02d_%dx%d_%07d_%07d"%(self.zoom, self.map_type_name[self.mtype], self.zoom, self.TILE_W[self.mtype], self.TILE_H[self.mtype], x_nth, y_nth) + "." + self.fmt[self.mtype]

    def open_tile_img(self, x_nth, y_nth):
        if (self.mtype, self.zoom, x_nth, y_nth) in self.opened_tiles:
            #print("opened_tiles(%d,%d,%d,%d)"%(self.mtype, self.zoom, x_nth, y_nth))
            return self.opened_tiles[(self.mtype, self.zoom, x_nth, y_nth)]

        fname = self.tile_file_name(x_nth, y_nth)
        if os.path.exists(fname):
            print("opening tile(%d,%d,%d,%d)"%(self.mtype, self.zoom, x_nth, y_nth) +" -> "+fname)
        else:
            c_lon,c_lat = self.pix2ll((x_nth+0.5)*self.TILE_W[self.mtype],(y_nth+0.5)*self.TILE_H[self.mtype])
            if self.mtype <= 6:
                url = "http://cyberjapandata.gsi.go.jp/xyz/%s/%d/%d/%d.%s"%(self.map_type_name[self.mtype], self.zoom, x_nth, y_nth, self.fmt[self.mtype])
            print("Downloading... ")
            try:
                if(self.map_type_name[self.mtype] in self.map_cyber):
                    print(url)
                    print(" -> "+fname)
                    urllib.request.urlretrieve(url,fname) #python3
                    #urllib.urlretrieve(url,fname) #python2
                elif(self.map_type_name[self.mtype] in self.map_osm):
                    map = StaticMap(256, 256)
                    image = map.render(zoom=self.zoom, center=[c_lon,c_lat])
                    image.save(fname)
            except Exception as e:
                print(e)
                print("Download faild -> blank")
                if (self.TILE_W[self.mtype], self.TILE_H[self.mtype]) in self.white_tiles:
                    return self.white_tiles[(self.TILE_W[self.mtype], self.TILE_H[self.mtype])]
                else:
                    white = np.zeros([self.TILE_H[self.mtype], self.TILE_W[self.mtype], 3], dtype=np.uint8)
                    white[:,:,:] = 255
                    self.white_tiles[(self.TILE_W[self.mtype], self.TILE_H[self.mtype])] = white
                    return white
        self.opened_tiles[(self.mtype, self.zoom, x_nth, y_nth)] = cv2.imread(fname)
        return self.opened_tiles[(self.mtype, self.zoom, x_nth, y_nth)]

    def makeMap_XYYV(self, c_lon, c_lat, yaw, velo):
        center_pos = (int(self.WIN_W/2), int(self.WIN_H/2))
        ang = (90-yaw)/180*pi
        velo_pos = (int(self.WIN_W/2+3*velo*cos(ang)), int(self.WIN_H/2-3*velo*sin(ang)))
        win_img = self.load_win_img(c_lon, c_lat)
        cv2.circle(win_img, center_pos, 5, (0, 0, 255), thickness=-1)
        cv2.arrowedLine(win_img, center_pos, velo_pos, (255, 0, 255), tipLength=0.3)
        return win_img
    
    def makeMap_XY(self, c_lon, c_lat):
        center_pos = (int(self.WIN_W/2), int(self.WIN_H/2))
        win_img = self.load_win_img(c_lon, c_lat)
        cv2.circle(win_img, center_pos, 5, (0, 0, 255), thickness=-1)
        return win_img
        
if __name__ == "__main__":
    map = Map()
    lat = 35.681647
    lon = 139.767174
    win_img = map.makeMap_XY(lon, lat)
    cv2.imshow("Map", win_img)
    k=cv2.waitKey(0) & 0xff
    if k == 27:         # wait for ESC key to exit
        cv2.destroyAllWindows()
